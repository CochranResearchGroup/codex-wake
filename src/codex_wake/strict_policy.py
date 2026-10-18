"""Explicit host containment controls, validated before task effects."""
import math


FIELDS={'memory_max_bytes','memory_swap_max_bytes','cpu_quota_percent','tasks_max',
        'stop_grace_seconds','checkpoint_grace_seconds','poll_seconds','accounting_max_age_seconds'}


def strict_policy(limits, configuration):
    if not isinstance(limits,dict) or set(limits)!=FIELDS:
        raise ValueError('strict execution requires every explicit control')
    for key,value in limits.items():
        if type(value) not in (int,float) or not math.isfinite(value) or value<0:
            raise ValueError('invalid strict execution control')
        if value==0 and key!='memory_swap_max_bytes':raise ValueError('zero strict execution control')
    for key in ('memory_max_bytes','memory_swap_max_bytes','tasks_max'):
        if type(limits[key]) is not int:raise ValueError('integer resource limit required')
    if (limits['poll_seconds']>5 or limits['accounting_max_age_seconds']<2*limits['poll_seconds']
            or limits['checkpoint_grace_seconds']+limits['stop_grace_seconds']>=configuration['session_time_limit_seconds']
            or configuration['session_token_limit']>configuration['objective_token_limit']
            or configuration['session_time_limit_seconds']>configuration['objective_time_limit_seconds']):
        raise ValueError('inconsistent strict resource limits')
    return dict(limits=dict(limits),token_enforcement='sampled_stop',maximum_token_overshoot=None,
                coverage='dedicated_local_executor_and_descendants',
                exclusions=['shared_services','external_provider_execution','same_user_ipc_escape'])
