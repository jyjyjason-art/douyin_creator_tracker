#!/usr/bin/env python
"""Keep Windows awake while long browser collection jobs run."""

from __future__ import annotations

import ctypes
import time
from datetime import datetime
from pathlib import Path


ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002
ES_AWAYMODE_REQUIRED = 0x00000040


def main() -> int:
    log_path = Path("evidence") / "keep_awake.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    flags = ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED | ES_AWAYMODE_REQUIRED
    with log_path.open("a", encoding="utf-8") as log:
        log.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] keep_awake started\n")
        log.flush()
        try:
            while True:
                ctypes.windll.kernel32.SetThreadExecutionState(flags)
                log.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] SetThreadExecutionState active\n")
                log.flush()
                time.sleep(45)
        finally:
            ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)


if __name__ == "__main__":
    raise SystemExit(main())
