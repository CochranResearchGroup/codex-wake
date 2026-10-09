"""UTC authority shared by mailbox-backed reply registration and evaluation."""
from datetime import UTC, datetime


def mailbox_time(mailbox, *, upper=False):
    """Use the mailbox's declared domain; never change its guarded checkpoint."""
    with mailbox.bus.connection(read_only=True) as database:
        mailbox._schema(database)
        network = mailbox._network_mode(database)
    if not network:
        from .records import utc_now
        return utc_now()
    decision = mailbox._accepted_time()
    with mailbox.bus.connection(read_only=True) as database:
        mailbox._schema(database)
        mailbox._check_network_checkpoint(database, decision)
    return datetime.fromtimestamp(decision.upper if upper else decision.lower, UTC)
