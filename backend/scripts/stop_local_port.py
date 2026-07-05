#!/usr/bin/env python
"""Stop a local process that is listening on a specific TCP port.

Designed for cleanup of temporary smoke-test servers. The script only targets
LISTENING sockets for the requested port and prints compact status metadata.
"""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
from typing import Optional


def _find_listening_pid(port: int) -> Optional[int]:
    completed = subprocess.run(
        ["netstat", "-ano"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "netstat failed")
    marker = f":{port}"
    for line in completed.stdout.splitlines():
        parts = line.split()
        if len(parts) < 5:
            continue
        local_address = parts[1]
        state = parts[3]
        pid_text = parts[4]
        if marker in local_address and state.upper() == "LISTENING":
            return int(pid_text)
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Stop a local TCP listener by port.")
    parser.add_argument("port", type=int)
    args = parser.parse_args()

    pid = _find_listening_pid(args.port)
    if pid is None:
        print(f"port={args.port} status=not_listening")
        return 0

    if pid == os.getpid():
        print(f"port={args.port} pid={pid} status=refused_self")
        return 2

    signals = [signal.SIGTERM]
    if hasattr(signal, "SIGBREAK"):
        signals.append(signal.SIGBREAK)
    if hasattr(signal, "SIGKILL"):
        signals.append(signal.SIGKILL)

    for sig in signals:
        try:
            os.kill(pid, sig)
            print(f"port={args.port} pid={pid} status=stop_signal_sent signal={sig}")
            return 0
        except Exception as exc:
            last_error = f"{exc.__class__.__name__}: {exc}"

    print(f"port={args.port} pid={pid} status=failed error={last_error}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
