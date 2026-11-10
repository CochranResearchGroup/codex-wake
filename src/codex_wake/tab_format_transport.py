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
                    commands.append(('set-option','-t',target,name,value[:-1]+'\\;' if value.endswith(';') else value))
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
    if action not in ('read','write'):
        raise InventoryError('unsupported_operation','Unsupported formatting action.')
    result=tmux_formatting_batch(transport,[dict(arguments,action=action)],deadline)[0]
    if 'error' in result:
        raise InventoryError(result['error']['code'],'Native formatting target or readback changed.')
    return result


def _window_reads(window):
    commands=[('display-message','-p','-t',window,'#{window_id}')]
    for name in WINDOW_OPTIONS:
        commands.extend((('show-options','-w','-t',window,name),
                         ('show-options','-w','-v','-t',window,name),
                         ('show-options','-w','-A','-v','-t',window,name),
                         ('show-options','-g','-w','-v',name)))
    return commands


def tmux_formatting_batch(transport,requests,deadline):
    """Execute only finite window option operations, with bounded cohort readback.

    Four windows bound worst-case 8KiB option readback below the transport's 1MiB
    limit. All members are validated before any cohort can write. Each write and
    its complete explicit/effective/parent readback share one native client.
    """
    if not isinstance(requests,list) or len(requests)>128:
        raise InventoryError('invalid_argument','Native formatting batch exceeds128 windows.')
    prepared=[]
    for request in requests:
        if not isinstance(request,dict) or request.get('action') not in ('read','write'):
            raise InventoryError('invalid_argument','Only finite window reads and writes may be batched.')
        action=request['action'];window=request.get('window')
        allowed={'action','window'}|({'values'} if action=='write' else set())
        if set(request)-allowed or not isinstance(window,str) or not re.fullmatch(r'@[0-9]+',window):
            raise InventoryError('invalid_argument','Exact native window identity required.')
        commands=[]
        if action=='write':
            values=request.get('values')
            if not isinstance(values,dict) or set(values)-set(WINDOW_OPTIONS):
                raise InventoryError('invalid_argument','Only managed formatting options may change.')
            for name,value in values.items():
                if value is None:commands.append(('set-option','-w','-u','-t',window,name))
                elif isinstance(value,str) and len(value)<=8192 and '\x00' not in value:
                    commands.append(('set-option','-w','-t',window,name,value[:-1]+'\\;' if value.endswith(';') else value))
                else:raise InventoryError('invalid_argument','Invalid formatting option value.')
        prepared.append((window,commands))
    results=[]
    for offset in range(0,len(prepared),4):
        commands=[];reads=[]
        for window,writes in prepared[offset:offset+4]:
            commands.extend(writes);reads.append((window,len(commands)))
            commands.extend(_window_reads(window))
        try:values=_command_batch(transport,commands,deadline)
        except subprocess.CalledProcessError:
            cohort=prepared[offset:offset+4]
            # Isolate failures with reads only. A write cohort may have partly
            # applied; reconcile each member without ever repeating its effects.
            if len(cohort)==1 and not cohort[0][1]:
                results.append(dict(error=dict(code='stale_target')))
            else:
                for request,(window,_) in zip(requests[offset:offset+4],cohort):
                    observed=tmux_formatting_batch(transport,[dict(action='read',window=window)],deadline)[0]
                    if request['action']=='write' and 'error' not in observed:
                        if any((observed[name]['explicit'] if wanted is None else observed[name]['value']!=wanted)
                               for name,wanted in request['values'].items()):
                            observed=dict(error=dict(code='formatting_native_failed'))
                    results.append(observed)
            continue
        for window,start in reads:
            if values[start].strip()!=window:
                results.append(dict(error=dict(code='stale_target')));continue
            observed={}
            for index,name in enumerate(WINDOW_OPTIONS):
                raw,value,effective,parent=values[start+1+index*4:start+1+index*4+4]
                observed[name]=dict(explicit=bool(raw),value=value.removesuffix('\n') if raw else None,
                    effective=effective.removesuffix('\n'),parent=parent.removesuffix('\n'))
            results.append(observed)
    return results


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
