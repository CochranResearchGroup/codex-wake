"""Portable exit status for the shared retained tab-operation envelope."""


def exit_status(value):
    """A completed request can still retain partial or uncertain tab effects."""
    result=value.get('result')
    retained=result.get('operation',{}) if isinstance(result,dict) else {}
    retained=retained if isinstance(retained,dict) else {}
    outcome=retained.get('result')
    outcome=outcome if isinstance(outcome,dict) else value
    unsuccessful={'partial','uncertain','held','disabled','unsupported','failed','stale_target','unavailable'}
    incomplete=(value.get('status') in unsuccessful or outcome.get('status') in unsuccessful
                or retained.get('phase')=='uncertain' or retained.get('execution') in ('failed','not_started','unknown')
                or bool(outcome.get('error') or outcome.get('failures'))
                or outcome.get('status')=='paused' and retained.get('operation') in
                   ('tabs.format.enable','tabs.format.reenable','tabs.format.resume'))
    return 3 if incomplete else 0
