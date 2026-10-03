"""Receipt reconstruction with an explicit authority resolver, never path discovery."""
from .a2a_receipt_signals import ReceiptSignalAdapter, ReceiptSignalRunner
from .signals import UnavailableSourceRunner
from .source_registry import BuiltinSourceRegistration


def receipt_source_registration(resolve_authority):
    """Resolver supplies enrolled mailbox/actor authority independently of arm data.

    This injectable registration is not automatically installed in the production
    catalogue. A durable configured resolver must be qualified before that wiring.
    """
    def construct(context, candidates):
        groups = {}
        for candidate in candidates:
            groups.setdefault(candidate.armed.spec.source_instance, []).append(candidate.armed)
        runners = []
        for source_instance, arms in sorted(groups.items()):
            try:
                mailbox, actor = resolve_authority(arms[0])
                adapter = ReceiptSignalAdapter.restore(arms[0], mailbox, actor)
                if any(not adapter.valid_arm(arm) for arm in arms):
                    raise ValueError('conflicting receipt arms')
                runners.append(ReceiptSignalRunner(adapter, arms))
            except Exception:
                runners.append(UnavailableSourceRunner('a2a.receipt', source_instance,
                                                       'A2A_AUTHORITY_UNAVAILABLE'))
        return tuple(runners)

    return BuiltinSourceRegistration('a2a-receipt', frozenset({('a2a.receipt', 'receipt')}), construct)
