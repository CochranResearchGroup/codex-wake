"""Finite formatting option protocol shared by native terminal adapters."""
import re
from .managed_inventory import InventoryError

WINDOW_OPTIONS = ('window-status-format','window-status-current-format',
                  'window-status-style','window-status-current-style')


def tmux_formatting(transport, action, arguments, deadline):
    """Read explicit local values separately from effective inherited values."""
    window=arguments.get('window')
    if not isinstance(window,str) or not re.fullmatch(r'@[0-9]+',window):
        raise InventoryError('invalid_argument','Exact window identity required.')
    if action=='read':
        result={}
        for name in WINDOW_OPTIONS:
            raw=transport.command(deadline,'show-options','-w','-t',window,name)
            value=transport.command(deadline,'show-options','-w','-v','-t',window,name).removesuffix('\n') if raw else None
            effective=transport.command(deadline,'show-options','-w','-A','-v','-t',window,name).removesuffix('\n')
            result[name]=dict(explicit=bool(raw),value=value,effective=effective)
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
