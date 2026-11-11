#!/usr/bin/env python3
"""Shows the usage cat without Claude Code, with made-up figures.

    python3 usage_demo.py          whole scenario, about 50 seconds
    python3 usage_demo.py 85       one session percentage, until Ctrl+C

The demo runs its own cat, with its own files: the real figures are untouched.
"""

import os
import subprocess
import sys
import time

os.environ["USAGE_CAT_DEMO"] = "1"

import usage_common as common  # noqa: E402  (must be imported after the environment variable is set)

SCENARIO = [(12, 6), (34, 6), (63, 8), (86, 8), (97, 8), (100, 8), (2, 10)]


def publish(session, week=40):
    now = time.time()
    common.write_state(
        {
            "five_hour": {"pct": session, "resets_at": now + 4350},
            "seven_day": {"pct": week, "resets_at": now + 3.2 * 86400},
            "ts": now,
            "pid": os.getpid(),
        }
    )


def main():
    single = float(sys.argv[1]) if len(sys.argv) > 1 else None
    publish(single if single is not None else SCENARIO[0][0])
    program = subprocess.Popen(
        [sys.executable, os.path.join(common.BASE_DIR, "usage_cat.py")], cwd=common.BASE_DIR
    )
    try:
        if single is not None:
            program.wait()
            return
        for session, seconds in SCENARIO:
            print(f"session: {session} %")
            publish(session)
            time.sleep(seconds)
    except KeyboardInterrupt:
        pass
    finally:
        program.terminate()


if __name__ == "__main__":
    main()
