#!/usr/bin/env python3
"""Supervise the unchanged outbound sender; settings changes restart only this child."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True, type=Path)
    parser.add_argument('--log', required=True, type=Path)
    args = parser.parse_args()
    running = True
    def stop(*_):
        nonlocal running
        running = False
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    # A second service/hook must never duplicate timing uploads.
    with args.config.with_suffix('.lock').open('a') as lock, args.log.open('a', buffering=1) as log:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 0
        child, previous, warned = None, None, False
        try:
            while running:
                try:
                    raw = args.config.read_bytes()
                    config = json.loads(raw)
                    enabled = config.get('enabled', True)
                    if not isinstance(enabled, bool):
                        raise ValueError('Invalid enabled flag')
                    if raw != previous:
                        if child is not None:
                            child.terminate()
                            child.wait(timeout=8)
                            child = None
                        previous = raw
                    if enabled and child is None:
                        child = subprocess.Popen([sys.executable, str(Path(__file__).with_name('sender.py')), '--config', str(args.config)], stdout=log, stderr=log)
                        log.write(time.strftime('%Y-%m-%d %H:%M:%S') + ' Lyrics sender started.\n')
                    if child is not None and child.poll() is not None:
                        child = None
                        time.sleep(4)
                    warned = False
                except (OSError, ValueError):
                    if not warned:
                        log.write('Lyrics configuration unavailable or invalid; check plugin settings.\n')
                        warned = True
                time.sleep(1)
        finally:
            if child is not None:
                child.terminate()
                try:
                    child.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait()
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
