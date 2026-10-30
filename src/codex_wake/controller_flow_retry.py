"""Finite opt-in retries for known observational operations only.

Author claims cannot turn a model turn, native create/fork, terminal input or
other effect into an idempotent operation. Unknown effects always reconcile.
"""
from .managed_inventory import InventoryError

READ_OPERATIONS=frozenset(('inventory.list','inventory.resolve','accounts.list','accounts.resolve',
    'configuration.explain','builds.list','hosts.list','hosts.resolve','history.search','history.read',
    'operations.result','operations.wait','operations.stream','sessions.capabilities','sessions.wait',
    'sessions.checkpoint','health.observe'))


def policy(node):
    value=node.get('retry')
    if value is None:return dict(max_attempts=1,when=[])
    if node.get('operation') not in READ_OPERATIONS:
        raise InventoryError('unsafe_retry','effectful or unknown operations cannot opt into automatic replay')
    if not isinstance(value,dict) or set(value)!={'max_attempts','when'} or type(value['max_attempts']) is not int or not 1<=value['max_attempts']<=3:
        raise InventoryError('invalid_retry','explicit retry bound must be1..3 total attempts')
    if not isinstance(value['when'],list) or not 1<=len(value['when'])<=4 or any(code not in ('timeout','unavailable','source_unavailable','native_unavailable') for code in value['when']):
        raise InventoryError('invalid_retry','explicit supported transient source error codes required')
    return value


def should_retry(node,code,count):
    value=policy(node)
    return count<value['max_attempts'] and code in value['when']


def error_code(error):
    code=getattr(error,'code',None)
    if code:return code
    if isinstance(error,TimeoutError):return 'timeout'
    if isinstance(error,OSError):return 'unavailable'
    from .shared_app_server import SharedSourceError
    if isinstance(error,SharedSourceError):return 'source_unavailable'
    return 'step_effect_uncertain'
