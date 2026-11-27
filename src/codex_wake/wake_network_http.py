"""Bounded peer and OAuth client HTTP routes for the Wake hub."""
import json

import anyio
import psycopg
from starlette.responses import JSONResponse
from starlette.routing import Route

from functools import partial

from .controller_auth import AuthError
from .managed_inventory import InventoryError


async def read_json(request):
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > 65536:
            raise InventoryError('invalid_argument', 'request body exceeds limit')
        body.extend(chunk)
    return json.loads(body)


def guard(verifier, host):
    def guarded(function, *, client=False, reverify=False):
        async def endpoint(request):
            status = 200
            try:
                if request.headers.get('host', '').lower() != host.lower():
                    raise InventoryError('invalid_argument', 'unexpected request host')
                value = await read_json(request)
                authorization = request.headers.get('authorization', '')
                if client:
                    if not authorization.startswith('Bearer '):
                        raise AuthError()
                    verify = partial(verifier.actor, authorization[7:])
                    actor = await anyio.to_thread.run_sync(verify)
                    args = (actor, value, verify) if reverify else (actor, value)
                    value = await anyio.to_thread.run_sync(function, *args)
                else:
                    value = await anyio.to_thread.run_sync(
                        function, request.path_params['peer_id'], authorization, value)
            except AuthError as error:
                value, status = {'error': error.code}, 403 if error.code == 'insufficient_scope' else 401
            except InventoryError as error:
                status = {'directory_conflict': 409, 'trusted_time_unavailable': 503}.get(error.code, 400)
                value = {'error': error.code}
            except (ValueError, TypeError):
                value, status = {'error': 'invalid_request'}, 400
            except psycopg.Error:
                value, status = {'error': 'network_store_unavailable'}, 503
            return JSONResponse(value, status_code=status, headers={'Cache-Control': 'no-store'})
        return endpoint

    return guarded


def routes(network, verifier, host):
    guarded = guard(verifier, host)
    return [
        Route('/network/v1/peers/{peer_id}/directory', guarded(network.publish), methods=['PUT']),
        Route('/network/v1/recipients', guarded(network.discover, client=True), methods=['POST']),
    ]
