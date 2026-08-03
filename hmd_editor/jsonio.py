"""JSON load/dump that preserves the exact literal text of every float.

GameMaker's JSON writer emits floats with up to 17 significant digits, which does
not always match Python's shortest round-trip repr for the same double (same
value, different text - e.g. ``5682.3180138193011`` vs ``5682.318013819301``).
To make "load, then save with no edits" a true byte-for-byte no-op, RawFloat
remembers the original source text and dumps() replays it verbatim. Editing a
value replaces it with a plain float/int, which serializes normally.
"""

import json
from json.encoder import encode_basestring

_INFINITY = float("inf")


class RawFloat(float):
    """A float that remembers the exact text it was parsed from."""

    __slots__ = ("raw",)

    def __new__(cls, s):
        obj = super().__new__(cls, s)
        obj.raw = s
        return obj


def loads(text):
    return json.loads(text, parse_float=RawFloat)


def dumps(obj):
    out = []
    _encode(obj, out)
    return "".join(out)


def _encode(obj, out):
    if obj is True:
        out.append("true")
    elif obj is False:
        out.append("false")
    elif obj is None:
        out.append("null")
    elif isinstance(obj, str):
        out.append(encode_basestring(obj))
    elif isinstance(obj, RawFloat):
        out.append(obj.raw)
    elif isinstance(obj, float):
        out.append(_float_repr(obj))
    elif isinstance(obj, int):
        out.append(str(obj))
    elif isinstance(obj, dict):
        _encode_dict(obj, out)
    elif isinstance(obj, (list, tuple)):
        _encode_list(obj, out)
    else:
        raise TypeError(f"hmd_editor.jsonio cannot encode {type(obj).__name__!r}")


def _float_repr(o):
    if o != o:
        return "NaN"
    if o == _INFINITY:
        return "Infinity"
    if o == -_INFINITY:
        return "-Infinity"
    return repr(o)


def _encode_dict(d, out):
    out.append("{")
    first = True
    for key, value in d.items():
        if not first:
            out.append(",")
        first = False
        if not isinstance(key, str):
            raise TypeError("hmd_editor.jsonio only supports string keys")
        out.append(encode_basestring(key))
        out.append(":")
        _encode(value, out)
    out.append("}")


def _encode_list(items, out):
    out.append("[")
    first = True
    for value in items:
        if not first:
            out.append(",")
        first = False
        _encode(value, out)
    out.append("]")
