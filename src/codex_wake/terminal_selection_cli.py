"""Translate ordinary selection flags into the shared portable expression."""
from .managed_inventory import InventoryError


def expression(owner, args, initial=None):
    terms=[initial] if initial is not None else []
    for flag,pattern,negated in (('selection_filters',False,False),('selection_patterns',True,False),('selection_excludes',False,True)):
        for value in getattr(args,flag,None) or []:
            if '=' not in value:raise InventoryError('invalid_argument','Selection filters use TRAIT=VALUE.')
            field,value=value.split('=',1)
            term={'field':field,('pattern' if pattern else 'eq'):value}
            if value=='unknown' and not pattern:term={'field':field,'unknown':True}
            terms.append({'not':term} if negated else term)
    for flag,key in (('selection_groups','group'),('selection_labels','label')):
        terms.extend({key:value} for value in getattr(args,flag,None) or [])
    selectors=getattr(args,'selection_tabs',None) or []
    if selectors:
        from .terminal_sessions import TerminalSessions
        from .tab_views import TabViews
        sessions=TerminalSessions(owner.root,tabs=owner)
        resources=owner.execute('tabs.list',{})['resources'];refs=[]
        for selector in selectors:
            if ':' not in selector:raise InventoryError('invalid_argument','Select tabs using SESSION:@WINDOW, for example default:@3.')
            name,window=selector.rsplit(':',1);session=sessions.resolve(name)
            matches=[r for r in resources if r['target']['workspace']==session['workspace'] and r['window']['window_id']==window]
            if len(matches)!=1:raise InventoryError('stale_target','Selected tab is absent from its terminal session.')
            refs.append(TabViews.identity(matches[0]))
        terms.append({'tabs':refs})
    if not terms:return initial
    result=terms[0] if len(terms)==1 else {'all':terms}
    from .tab_selection import validate
    validate(result)
    return result
