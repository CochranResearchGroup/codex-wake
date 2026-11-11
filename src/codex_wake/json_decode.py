"""Fast internal JSON decoding with the existing stdlib value/error contract.

Encoding stays with stdlib JSON, including strict finite-number enforcement at
existing persistence boundaries. Legacy JSON values unsupported by msgspec use
stdlib decoding so older stores remain readable.
"""
import json

import msgspec


def decode_json(raw):
    """Decode fresh Python containers, retaining legacy stdlib JSON behavior."""
    try:
        return msgspec.json.decode(raw)
    except (msgspec.DecodeError, UnicodeError):
        return json.loads(raw)
