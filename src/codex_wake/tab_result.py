"""Portable exit status for the shared retained tab-operation envelope."""


def exit_status(value):
    """A completed request can still retain partial or uncertain tab effects."""
    result=value.get('result')
    retained=result.get('operation',{}) if isinstance(result,dict) else {}
    retained=retained if isinstance(retained,dict) else {}
    outcome=retained.get('result')
    incomplete=(value.get('status') in ('partial','uncertain','held') or retained.get('phase')=='uncertain'
                or isinstance(outcome,dict) and outcome.get('status') in ('partial','uncertain','held'))
    return 3 if incomplete else 0
