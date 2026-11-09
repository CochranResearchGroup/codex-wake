"""Bounded, three-valued selection over qualified attachment observations."""
from fnmatch import fnmatchcase
from .managed_inventory import InventoryError

FIELDS = frozenset(('harness','build','account','repository','remote_host','activity','health','error','session_presence'))


def _invalid():
    raise InventoryError('invalid_argument', 'Invalid or unbounded tab selection expression.')


def validate(expression):
    """Validate a JSON expression (depth <= 8, nodes <= 256)."""
    count = 0
    def visit(expr, depth):
        nonlocal count
        count += 1
        if depth > 8 or count > 256 or not isinstance(expr, dict): _invalid()
        if set(expr) in ({'all'}, {'any'}):
            children = next(iter(expr.values()))
            if not isinstance(children, list) or not 1 <= len(children) <= 32: _invalid()
            for child in children: visit(child, depth + 1)
        elif set(expr) == {'not'}: visit(expr['not'], depth + 1)
        elif set(expr) in ({'field','eq'}, {'field','pattern'}, {'field','unknown'}):
            if not isinstance(expr['field'],str) or expr['field'] not in FIELDS: _invalid()
            if 'unknown' in expr:
                if expr['unknown'] is not True: _invalid()
            else:
                value = expr.get('eq', expr.get('pattern'))
                if not isinstance(value,str) or len(value)>512: _invalid()
        elif set(expr) in ({'group'}, {'label'}):
            value = next(iter(expr.values()))
            if not isinstance(value,str) or not value or len(value)>128 or any(ord(c)<32 for c in value): _invalid()
        elif set(expr) == {'tabs'}:
            refs = expr['tabs']
            if not isinstance(refs,list) or len(refs)>4096: _invalid()
            for ref in refs:
                if not isinstance(ref,dict) or set(ref)!={'id','identity'} or any(not isinstance(v,str) or not v or len(v)>512 for v in ref.values()): _invalid()
        else: _invalid()
    visit(expression, 0)


def select(resources, expression, *, groups=None, labels=None):
    """Return resources whose expression is true; unknown never implies true.

    Explicit tabs and category memberships use {id, identity} birth pins.
    Groups map names to records with members and optional custom labels.
    """
    validate(expression)
    groups, labels = groups or {}, labels or {}
    from .tab_views import TabViews
    def evaluate(resource, expr):
        if 'all' in expr or 'any' in expr:
            conjunction = 'all' in expr
            values = [evaluate(resource,c) for c in expr['all' if conjunction else 'any']]
            if conjunction:
                return False if False in values else None if None in values else True
            return True if True in values else None if None in values else False
        if 'not' in expr:
            value=evaluate(resource,expr['not'])
            return None if value is None else not value
        if 'field' in expr:
            trait=resource.get('traits',{}).get('traits',{}).get(expr['field'],{})
            value=trait.get('value') if isinstance(trait,dict) else None
            known=isinstance(trait,dict) and trait.get('status')=='observed' and value is not None and value!='unknown'
            if 'unknown' in expr: return not known
            if not known: return None
            return value==expr['eq'] if 'eq' in expr else isinstance(value,str) and fnmatchcase(value,expr['pattern'])
        identity=TabViews.identity(resource)
        if 'tabs' in expr: return identity in expr['tabs']
        if 'group' in expr:
            group=groups.get(expr['group'])
            if group is None: raise InventoryError('target_not_found','Referenced named group is unavailable.')
            return identity in group['members']
        members=list(labels.get(expr['label'],[]))
        for group in groups.values():
            if expr['label'] in group.get('labels',[]): members.extend(group['members'])
        return identity in members
    return [resource for resource in resources if evaluate(resource,expression) is True]
