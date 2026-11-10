"""Finite formatting option protocol shared by native terminal adapters."""
import re
import subprocess
import uuid
from .managed_inventory import InventoryError

WINDOW_OPTIONS = ('window-status-format','window-status-current-format',
                  'window-status-style','window-status-current-style')
SESSION_OPTIONS=('status-interval','@wake-format-clock')


def tmux_formatting(transport, action, arguments, deadline):
    """Read explicit local values separately from effective inherited values."""
    if action=='refresh':
        # tmux with no attached client has nothing to redraw; writes remain valid.
        try:transport.command(deadline,'refresh-client','-S')
        except subprocess.CalledProcessError:pass
        return dict(status='refreshed')
    if action in ('read-session','write-session'):
        target=transport.session
        commands=[]
        if action=='write-session':
            values=arguments.get('values')
            if not isinstance(values,dict) or set(values)-set(SESSION_OPTIONS):
                raise InventoryError('invalid_argument','Only managed session formatting options may change.')
            for name,value in values.items():
                if value is None:commands.append(('set-option','-u','-t',target,name))
                elif isinstance(value,str) and len(value)<=128 and '\x00' not in value:
                    commands.append(('set-option','-t',target,name,value))
                else:raise InventoryError('invalid_argument','Invalid session formatting value.')
        writes=len(commands)
        for name in SESSION_OPTIONS:
            commands.extend((('show-options','-q','-t',target,name),
                             ('show-options','-q','-v','-t',target,name),
                             ('show-options','-q','-A','-v','-t',target,name)))
        observations=_command_batch(transport,commands,deadline)[writes:]
        result={}
        for index,name in enumerate(SESSION_OPTIONS):
            raw,value,effective=observations[index*3:index*3+3]
            result[name]=dict(explicit=bool(raw),value=value.removesuffix('\n') if raw else None,
                              effective=effective.removesuffix('\n'))
        return result
    window=arguments.get('window')
    if not isinstance(window,str) or not re.fullmatch(r'@[0-9]+',window):
        raise InventoryError('invalid_argument','Exact window identity required.')
    if action=='read':
        commands=[]
        for name in WINDOW_OPTIONS:
            commands += [('show-options','-w','-t',window,name),
                         ('show-options','-w','-v','-t',window,name),
                         ('show-options','-w','-A','-v','-t',window,name),
                         ('show-options','-g','-w','-v',name)]
        values=_command_batch(transport,commands,deadline)
        result={}
        for index,name in enumerate(WINDOW_OPTIONS):
            raw,value,effective,parent=values[index*4:index*4+4]
            result[name]=dict(explicit=bool(raw),value=value.removesuffix('\n') if raw else None,
                              effective=effective.removesuffix('\n'),parent=parent.removesuffix('\n'))
        return result
    if action=='write':
        values=arguments.get('values')
        if not isinstance(values,dict) or set(values)-set(WINDOW_OPTIONS):
            raise InventoryError('invalid_argument','Only managed formatting options may change.')
        commands=[]
        for name,value in values.items():
            if value is None:
                commands.append(('set-option','-w','-u','-t',window,name))
            elif isinstance(value,str) and len(value)<=8192 and '\x00' not in value:
                commands.append(('set-option','-w','-t',window,name,value))
            else:raise InventoryError('invalid_argument','Invalid formatting option value.')
        if commands:_command_batch(transport,commands,deadline)
        return tmux_formatting(transport,'read',dict(window=window),deadline)
    raise InventoryError('unsupported_operation','Unsupported formatting action.')


def _command_batch(transport,commands,deadline):
    """One native invocation; random boundaries preserve whitespace and newlines."""
    marker='wake-format-'+uuid.uuid4().hex
    argv=[]
    for index,command in enumerate(commands):
        if argv:argv.append(';')
        argv.extend(command)
        argv.extend((';','display-message','-p',marker+str(index)))
    raw=transport.command(deadline,*argv)
    results=[]
    for index in range(len(commands)):
        boundary=marker+str(index)+'\n'
        if boundary not in raw:
            raise InventoryError('formatting_mismatch','Incomplete native formatting batch readback.')
        value,raw=raw.split(boundary,1);results.append(value)
    if raw:raise InventoryError('formatting_mismatch','Unexpected formatting batch readback.')
    return results
