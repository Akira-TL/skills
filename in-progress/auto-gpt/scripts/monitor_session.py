#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["websocket-client>=1.8,<2"]
# ///
"""会话内持续只读采样与待办确认；不读取正文、不作语义裁决或发送。"""
from __future__ import annotations

import argparse
import importlib
import json
import os
import re
import select
import signal
import sys
import termios
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import TextIO

sys.dont_write_bytecode = True
from watch_controls import ControlSampler, Observation, View, conversation, object_fields, verify_profile


@dataclass(frozen=True)
class Review:
    token: str
    conversation: str
    targets: tuple[str, ...]


@dataclass(frozen=True)
class Decision:
    conversation: str
    disposition: str
    frame: tuple[Observation, ...]


class ReviewQueue:
    def __init__(self) -> None:
        self.observations: tuple[Observation, ...] = ()
        self.pending: dict[str, Review] = {}
        self.decisions: dict[str, Decision] = {}
        self.frames: dict[str, tuple[Observation, ...]] = {}
        self.sequence = 0

    def update(self, observations: Sequence[Observation]) -> None:
        self.observations = tuple(sorted(observations, key=lambda item: item.target))
        groups: dict[str, list[Observation]] = {}
        for page in self.observations:
            identifier = conversation(page.url)
            if identifier is not None:
                groups.setdefault(identifier or page.url, []).append(page)
        for removed in set(self.frames) - set(groups):
            self.pending.pop(removed, None)
            self.decisions.pop(removed, None)
        frames = {key: tuple(pages) for key, pages in groups.items()}
        for key, pages in frames.items():
            if not all(page.sampled for page in pages):
                # 采集失败既不确认完成，也不丢掉已存在的待办。
                continue
            prior = self.frames.get(key)
            decision = self.decisions.get(key)
            if decision and decision.frame != pages:
                self.decisions.pop(key)
                decision = None
            running = all(page.controls.view == View.RUNNING and not page.controls.alerts
                          and not page.controls.dialogs for page in pages)
            empty = all(not page.controls.turns and not page.controls.latest_turn for page in pages)
            if running or empty:
                self.pending.pop(key, None)
            elif not decision and (key not in self.pending or prior != pages):
                self.sequence += 1
                self.pending[key] = Review(str(self.sequence), key, tuple(page.target for page in pages))
        self.frames = frames

    def acknowledge(self, token: str, disposition: str, *, reviewed_version: str, latest_user_id: str) -> None:
        if disposition not in {'complete', 'human', 'error'}:
            raise ValueError('Unknown disposition')
        review = next((item for item in self.pending.values() if item.token == token), None)
        if review is None:
            raise ValueError('Stale or unknown review token')
        pages = self.frames[review.conversation]
        if not all(page.sampled for page in pages):
            raise ValueError('Failed samples cannot be acknowledged')
        if (not re.fullmatch(r'[0-9a-f]{64}', reviewed_version) or not latest_user_id
                or {page.controls.latest_turn for page in pages} != {latest_user_id}):
            raise ValueError('The complete read must belong to the current user message')
        self.decisions[review.conversation] = Decision(review.conversation, disposition, pages)
        del self.pending[review.conversation]

    def status(self) -> Mapping[str, object]:
        return {'observations': [asdict(page) for page in self.observations],
                'pending': [asdict(item) | {'targets': list(item.targets)} for item in self.pending.values()],
                'decisions': [{'conversation': item.conversation, 'disposition': item.disposition}
                              for item in self.decisions.values()]}


def serve(sample: Callable[[], Sequence[Observation]], input_fd: int, output: TextIO, *,
          interval: float = 60, clock: Callable[[], float] = time.monotonic) -> None:
    """前台 JSON 行协议；到期只做下一次采样，直到 EOF、stop 或信号。"""
    if interval <= 0:
        raise ValueError('Sampling interval must be positive')
    queue = ReviewQueue()
    next_sample, last_sample = clock(), None
    failure: Mapping[str, object] | None = None
    buffer = b''
    def emit(kind: str, request: object = None, *, error: str = '') -> None:
        result = {'kind': kind, 'id': request, 'sample_age_seconds':
                  None if last_sample is None else max(0, round(clock() - last_sample, 2)),
                  **queue.status(), 'sampling_error': failure}
        if error:
            result['request_error'] = error
        print(json.dumps(result, ensure_ascii=False, separators=(',', ':')), file=output, flush=True)
    first = True
    while True:
        if clock() >= next_sample:
            started = clock()
            try:
                queue.update(sample())
                last_sample, failure = clock(), None
            except Exception as exc:
                code = getattr(exc, 'code', '')
                failure = {'error_type':type(exc).__name__, 'error_code':
                           code if isinstance(code, str) and code.isupper() and code.replace('_','').isalpha() else ''}
                queue.update(tuple(replace(page, sampled=False) for page in queue.observations))
            next_sample = started + interval
            if first:
                emit('monitor-started')
                first = False
        ready, _, _ = select.select([input_fd], [], [], max(0, next_sample - clock()))
        if not ready:
            continue
        data = os.read(input_fd, 65536)
        if not data:
            return
        buffer += data
        if len(buffer) > 1_048_576:
            raise ValueError('Request exceeds limit')
        while b'\n' in buffer:
            line, buffer = buffer.split(b'\n', 1)
            request: Mapping[str, object] = {}
            try:
                request = object_fields(json.loads(line))
                operation = request.get('op')
                if operation == 'stop':
                    emit('monitor-stopped', request.get('id'))
                    return
                if operation == 'ack':
                    if failure:
                        raise ValueError('Sampling failed')
                    token, disposition = request.get('token'), request.get('disposition')
                    version, identity = request.get('reviewed_version'), request.get('latest_user_id')
                    if (not isinstance(token, str) or not isinstance(disposition, str)
                            or not isinstance(version, str) or not isinstance(identity, str)):
                        raise ValueError('Invalid acknowledgement')
                    queue.acknowledge(token, disposition, reviewed_version=version, latest_user_id=identity)
                elif operation != 'status':
                    raise ValueError('Unknown operation')
                emit('monitor-status', request.get('id'))
            except (ValueError, UnicodeError, TypeError):
                emit('monitor-status', request.get('id'), error='INVALID_REQUEST_OR_STALE_ACK')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser-access-script', type=Path, required=True)
    parser.add_argument('--endpoint', required=True)
    args = parser.parse_args()
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(130))
    try:
        script = args.browser_access_script.resolve(strict=True)
        verify_profile(script, args.endpoint)
        sys.path.insert(0, str(script.parent))
        session_type = importlib.import_module('browser_session').BrowserSession
        list_targets = importlib.import_module('browser_cdp_core').list_targets
        class Directory:
            def call(self, method: str) -> Mapping[str, object]:
                return {'targetInfos': [{'type': target.get('type', 'page'),
                    'targetId':target['id'], 'url':target['url']}
                    for target in list_targets(args.endpoint, timeout=15)]}
        sampler = ControlSampler(Directory(), session_type, args.endpoint, (), set(), lambda _: None)
        descriptor = sys.stdin.fileno()
        terminal = termios.tcgetattr(descriptor) if os.isatty(descriptor) else None
        try:
            if terminal is not None:
                quiet = termios.tcgetattr(descriptor)
                quiet[3] &= ~termios.ECHO
                termios.tcsetattr(descriptor, termios.TCSANOW, quiet)
            serve(sampler.sample, descriptor, sys.stdout)
        finally:
            if terminal is not None:
                termios.tcsetattr(descriptor, termios.TCSANOW, terminal)
        return 0
    except (KeyboardInterrupt, SystemExit):
        return 130
    except Exception as exc:
        print(json.dumps({'kind':'monitor-error', 'error_type':type(exc).__name__}), flush=True)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
