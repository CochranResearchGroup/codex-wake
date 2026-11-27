"""HTTP routing for Wake network message custody."""
from starlette.routing import Route

from .wake_network_http import guard


def message_routes(messages, verifier, host):
    guarded = guard(verifier, host)
    entries = (
        ('/network/v1/messages/send', messages.client_send, True),
        ('/network/v1/messages/status', messages.client_status, True),
        ('/network/v1/peers/{peer_id}/messages/send', messages.peer_send, False),
        ('/network/v1/peers/{peer_id}/messages/status', messages.peer_status, False),
        ('/network/v1/peers/{peer_id}/messages/pull', messages.pull, False),
        ('/network/v1/peers/{peer_id}/messages/receipt', messages.receipt, False),
    )
    return [Route(path, guarded(handler, client=client), methods=['POST'])
            for path, handler, client in entries]
