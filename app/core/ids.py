"""UUIDv7 (RFC 9562): time-ordered primary keys, good for B-tree locality and partitioning."""

from __future__ import annotations

import os
import threading
import time
import uuid

_lock = threading.Lock()
_last_ms = 0
_seq = 0


def uuid7() -> uuid.UUID:
    global _last_ms, _seq  # noqa: PLW0603
    with _lock:
        ms = time.time_ns() // 1_000_000
        if ms <= _last_ms:
            ms = _last_ms
            _seq = (_seq + 1) & 0xFFF
            if _seq == 0:  # counter overflow within same ms: advance the clock logically
                ms += 1
        else:
            _seq = int.from_bytes(os.urandom(2), "big") & 0x3FF
        _last_ms = ms
        rand_b = int.from_bytes(os.urandom(8), "big") & ((1 << 62) - 1)
        value = (ms & ((1 << 48) - 1)) << 80
        value |= 0x7 << 76
        value |= _seq << 64
        value |= 0b10 << 62
        value |= rand_b
        return uuid.UUID(int=value)


def uuid7_timestamp_ms(u: uuid.UUID) -> int:
    return u.int >> 80
