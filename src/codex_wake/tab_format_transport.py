"""Finite formatting option protocol shared by native terminal adapters."""
import re
import subprocess
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
        if action=='write-session':
            values=arguments.get('values')
            if not isinstance(values,dict) or set(values)-set(SESSION_OPTIONS):
                raise InventoryError('invalid_argument','Only managed session formatting options may change.')
            for name,value in values.items():
                if value is None:transport.command(deadline,'set-option','-u','-t',target,name)
                elif isinstance(value,str) and len(value)<=128 and '\x00' not in value:
                    transport.command(deadline,'set-option','-t',target,name,value)
                else:raise InventoryError('invalid_argument','Invalid session formatting value.')
        names={line.split(' ',1)[0] for line in transport.command(deadline,'show-options','-t',target).splitlines()}
        result={}
        for name in SESSION_OPTIONS:
            present=name in names
            value=transport.command(deadline,'show-options','-v','-t',target,name).removesuffix('\n') if present else None
            try:effective=transport.command(deadline,'show-options','-A','-v','-t',target,name).removesuffix('\n')
            except subprocess.CalledProcessError:
                if not name.startswith('@'):raise
                effective=''
            result[name]=dict(explicit=present,value=value,effective=effective)
        return result
    window=arguments.get('window')
    if not isinstance(window,str) or not re.fullmatch(r'@[0-9]+',window):
        raise InventoryError('invalid_argument','Exact window identity required.')
    if action=='read':
        result={}
        for name in WINDOW_OPTIONS:
            raw=transport.command(deadline,'show-options','-w','-t',window,name)
            value=transport.command(deadline,'show-options','-w','-v','-t',window,name).removesuffix('\n') if raw else None
            effective=transport.command(deadline,'show-options','-w','-A','-v','-t',window,name).removesuffix('\n')
            parent=transport.command(deadline,'show-options','-g','-w','-v',name).removesuffix('\n')
            result[name]=dict(explicit=bool(raw),value=value,effective=effective,parent=parent)
        return result
    if action=='write':
        values=arguments.get('values')
        if not isinstance(values,dict) or set(values)-set(WINDOW_OPTIONS):
            raise InventoryError('invalid_argument','Only managed formatting options may change.')
        for name,value in values.items():
            if value is None:
                transport.command(deadline,'set-option','-w','-u','-t',window,name)
            elif isinstance(value,str) and len(value)<=8192 and '\x00' not in value:
                transport.command(deadline,'set-option','-w','-t',window,name,value)
            else:raise InventoryError('invalid_argument','Invalid formatting option value.')
        return tmux_formatting(transport,'read',dict(window=window),deadline)
    raise InventoryError('unsupported_operation','Unsupported formatting action.')
