"""Conservative policy admission; approval comes from frozen host bindings.

No observation or missing receipt can manufacture proof of non-submission.
The terminal adapter remains responsible for its qualified UI, fresh generation,
original deadline and protected composer checks under the caller's recipient lock.
"""
from .records import WakeError


def require_wait_policy(policy='wait'):
    """Neither built-in runtime qualifies dequeue expiry or owned interruption."""
    if policy != 'wait':
        raise WakeError('busy_policy_unsupported')


def terminal_fallback(recipient, prompt, preferred, terminal):
    """Switch only on explicit, definitive native-unavailable pre-I/O evidence.

    recipient must have been resolved through a trusted host binding loader;
    client-supplied target fields are never a source of fallback permission.
    An uncertain original attempt must reconcile rather than call this route.
    """
    if (preferred.state != 'not_sent' or preferred.pre_io is not True
            or preferred.reason != 'native_unavailable'
            or recipient.binding.get('allow_terminal_input') is not True
            or recipient.binding.get('allow_terminal_fallback') is not True):
        return preferred
    return terminal.submit(recipient, prompt)
