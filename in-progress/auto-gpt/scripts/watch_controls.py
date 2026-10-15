#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["websocket-client>=1.8,<2"]
# ///
"""只读观察控件；只在需要 Agent 核对的事件出现时返回，不采集回复或发送消息。"""
from __future__ import annotations

import argparse
import importlib
import json
import math
import re
import signal
import subprocess
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path
from typing import Protocol, cast
from urllib.parse import urlsplit

sys.dont_write_bytecode = True
from page_scripts import PROBE


class View(StrEnum):
    RUNNING = "running"
    COMPOSER = "composer"
    UNKNOWN = "unknown"


class TargetDiscovery(Protocol):
    def call(self, method: str) -> Mapping[str, object]: ...


class PageSession(TargetDiscovery, Protocol):
    def __enter__(self) -> PageSession: ...
    def __exit__(self, *args: object) -> None: ...
    def evaluate(self, expression: str) -> object: ...


class SessionFactory(Protocol):
    def __call__(self, endpoint: str, *, target: str, expected_url: str) -> PageSession: ...


@dataclass(frozen=True)
class Controls:
    stop: int
    composer: int
    editors: int
    draft: bool
    alerts: int
    dialogs: int
    turns: int
    latest_turn: str
    connection_lost: bool = False

    @property
    def view(self) -> View:
        if self.stop > 0:
            return View.RUNNING
        if self.editors == 1 and self.composer > 0:
            return View.COMPOSER
        return View.UNKNOWN


@dataclass(frozen=True)
class ConnectionNotice:
    since: float
    last_seen: float
    reported: bool = False


@dataclass(frozen=True)
class Observation:
    target: str
    url: str
    controls: Controls
    connection: ConnectionNotice | None = None
    sampled: bool = True


@dataclass(frozen=True)
class Event:
    reason: str
    targets: tuple[str, ...]
    observations: tuple[Observation, ...]


@dataclass(frozen=True)
class SampleFailure:
    target: str
    url: str
    error_type: str
    error_code: str


class ControlSampler:
    """单页失败保留旧事实，恢复时返回新事实；重复错误保持安静。"""

    def __init__(self, anchor: TargetDiscovery, sessions: SessionFactory, endpoint: str,
                 baseline: Sequence[Observation], ignored: set[str],
                 emit: Callable[[Mapping[str, object]], None]):
        self.anchor, self.sessions, self.endpoint = anchor, sessions, endpoint
        self.last = {page.target: page for page in baseline}
        self.failures: dict[str, SampleFailure] = {}
        self.ignored, self.emit = ignored, emit

    def sample(self) -> tuple[Observation, ...]:
        targets = self.anchor.call("Target.getTargets").get("targetInfos")
        if not isinstance(targets, list):
            raise ValueError("Target discovery did not return a list")
        result: list[Observation] = []
        failures: dict[str, SampleFailure] = {}
        for item in targets:
            target = object_fields(item)
            target_id, url = target.get("targetId"), target.get("url")
            if target.get("type") != "page" or not isinstance(url, str) or not isinstance(target_id, str):
                continue
            identifier = conversation(url)
            if identifier is None or identifier in self.ignored:
                continue
            try:
                with self.sessions(self.endpoint, target=target_id, expected_url=url) as page:
                    result.append(Observation(target_id, url, read_controls(page.evaluate(PROBE))))
            except Exception as exc:
                code = getattr(exc, "code", "")
                failures[target_id] = SampleFailure(target_id, url, type(exc).__name__,
                    code if isinstance(code, str) and re.fullmatch(r"[A-Z][A-Z_]+", code) else "")
                prior = self.last.get(target_id)
                if prior is not None and prior.url == url:
                    # 清掉断线计时，失败采样不能增加连续观察时间。
                    result.append(Observation(prior.target, prior.url, prior.controls, sampled=False))
        changed = [failure for target, failure in failures.items() if self.failures.get(target) != failure]
        recovered = [page for page in result if page.target in self.failures and page.target not in failures]
        removed = sorted(set(self.failures) - set(failures) - {page.target for page in result})
        if changed or recovered or removed:
            self.emit({"reason": "sampling-changed", "failures": [asdict(f) for f in changed],
                       "recovered_targets": [page.target for page in recovered],
                       "removed_targets": removed,
                       "observations": [asdict(page) for page in recovered]})
        self.failures = failures
        self.last = {page.target: page for page in result}
        return tuple(sorted(result, key=lambda page: page.target))


def object_fields(value: object) -> Mapping[str, object]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ValueError("Expected a JSON object")
    return cast(Mapping[str, object], value)


def read_controls(value: object) -> Controls:
    fields = object_fields(value)
    integers = ("stop", "composer", "editors", "alerts", "dialogs", "turns")
    if any(type(fields.get(key)) is not int or cast(int, fields[key]) < 0 for key in integers):
        raise ValueError("Invalid control counts")
    if type(fields.get("draft")) is not bool or not isinstance(fields.get("latest_turn"), str):
        raise ValueError("Invalid control observations")
    connection_lost = fields.get("connection_lost", False)
    if type(connection_lost) is not bool:
        raise ValueError("Invalid connection observation")
    return Controls(stop=cast(int, fields["stop"]), composer=cast(int, fields["composer"]),
                    editors=cast(int, fields["editors"]), draft=cast(bool, fields["draft"]),
                    alerts=cast(int, fields["alerts"]), dialogs=cast(int, fields["dialogs"]),
                    turns=cast(int, fields["turns"]), latest_turn=cast(str, fields["latest_turn"]),
                    connection_lost=cast(bool, connection_lost))


def conversation(url: str) -> str | None:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname != "chatgpt.com" or parsed.username or parsed.password:
        return None
    parts = parsed.path.split("/")
    for index in range(len(parts) - 1):
        if parts[index] == "c" and parts[index + 1]:
            return parts[index + 1]
    return ""  # 首页也在范围内；空字符串不表示已存在任务。


def read_baseline(raw: str | None) -> tuple[Observation, ...] | None:
    if raw is None:
        return None
    value: object = json.loads(raw)
    if not isinstance(value, list):
        raise ValueError("Baseline must be the previous event's observations array")
    result: list[Observation] = []
    for item in value:
        fields = object_fields(item)
        target, url = fields.get("target"), fields.get("url")
        if not isinstance(target, str) or not isinstance(url, str) or conversation(url) is None:
            raise ValueError("Invalid baseline target")
        notice = None
        connection = fields.get("connection")
        if connection is not None:
            facts = object_fields(connection)
            since, last_seen, reported = facts.get("since"), facts.get("last_seen"), facts.get("reported")
            if (type(since) not in (float, int) or type(last_seen) not in (float, int)
                    or not math.isfinite(cast(float, since)) or not math.isfinite(cast(float, last_seen))
                    or not 0 <= cast(float, since) <= cast(float, last_seen) or type(reported) is not bool):
                raise ValueError("Invalid connection timing facts")
            notice = ConnectionNotice(float(since), float(last_seen), cast(bool, reported))
        sampled = fields.get("sampled", True)
        if type(sampled) is not bool:
            raise ValueError("Invalid sample status")
        result.append(Observation(target, url, read_controls(fields.get("controls")), notice, sampled))
    return tuple(result)


def observe_connections(previous: Sequence[Observation] | None, current: tuple[Observation, ...],
                        now: float) -> tuple[Observation, ...]:
    old = {page.target: page for page in previous or ()}
    result: list[Observation] = []
    for page in current:
        notice = None
        if page.sampled and page.controls.connection_lost and page.controls.view != View.COMPOSER:
            before = old.get(page.target)
            prior = None
            if (before is not None and before.url == page.url and before.controls.connection_lost
                    and before.controls.view != View.COMPOSER
                    and (before.controls.turns, before.controls.latest_turn) == (page.controls.turns, page.controls.latest_turn)):
                prior = before.connection
            # 没有连续采样证据、采样中断或系统时钟基准失效时，重新计时。
            if prior and 0 <= now - prior.last_seen <= 90:
                notice = ConnectionNotice(prior.since, now, prior.reported)
            else:
                notice = ConnectionNotice(now, now)
        result.append(Observation(page.target, page.url, page.controls, notice, page.sampled))
    return tuple(result)


def changes(previous: Sequence[Observation] | None, current: tuple[Observation, ...]) -> Event | None:
    old = {page.target: page for page in previous or ()}
    affected: list[str] = []
    for page in current:
        if not page.sampled:
            continue
        prior = old.get(page.target)
        now = page.controls
        if prior is None or prior.url != page.url:
            if (now.view != View.RUNNING and not now.connection_lost) or now.alerts or now.dialogs:
                affected.append(page.target)
            continue
        before = prior.controls
        # 正在生成时只累计控件事实，不唤醒 Agent 做正文判断。
        changed = before.view != now.view and now.view != View.RUNNING and not (now.connection_lost and now.view == View.UNKNOWN)
        changed |= (before.alerts, before.dialogs) != (now.alerts, now.dialogs)
        if now.view != View.RUNNING:
            changed |= (before.draft, before.turns, before.latest_turn) != (now.draft, now.turns, now.latest_turn)
        if changed:
            affected.append(page.target)
    affected.extend(target for target in old if target not in {page.target for page in current})
    if affected:
        return Event("controls-changed", tuple(sorted(set(affected))), current)
    return None


def watch(sample: Callable[[], tuple[Observation, ...]], *, baseline: tuple[Observation, ...] | None,
          clock: Callable[[], float] = time.monotonic, sleep: Callable[[float], None] = time.sleep,
          max_wait_seconds: float = 1800.0,
          on_event: Callable[[Event], None] | None = None) -> Event:
    if not math.isfinite(max_wait_seconds) or max_wait_seconds <= 0:
        raise ValueError("Observation wait limit must be positive and finite")
    deadline = clock() + max_wait_seconds
    previous = baseline
    first = True
    while True:
        started = clock()
        if started >= deadline:
            return Event("watch-timeout", (), tuple(previous or ()))
        current = observe_connections(previous, sample(), clock())
        event = changes(previous, current)
        if on_event is not None:
            if first:
                on_event(Event("watch-started", event.targets if event else (), current))
            elif event is not None:
                # 只输出变化项；完整事实仍留在进程内存，到期统一返回。
                on_event(Event(event.reason, event.targets,
                               tuple(page for page in current if page.target in event.targets)))
        elif event is not None:
            return event
        first = False
        previous = current
        now = clock()
        sleep(max(0.0, min(60.0 - (now - started), deadline - now)))


def verify_profile(browser_script: Path, endpoint: str) -> None:
    # status 只读，不调用 ensure/tabs，浏览器退出时交回 Agent 而不是自动重开。
    command = ["uv", "run", "--no-project", "--offline", str(browser_script),
               "--profile", "auto-gpt", "--timeout", "30", "status"]
    # Windows 进程核验实测可超过 CLI 的 15 秒默认值；外层另留启动和返回时间。
    process = subprocess.run(command, capture_output=True, text=True, timeout=45, check=False)
    if process.returncode:
        raise ValueError("Dedicated profile status failed")
    status = object_fields(json.loads(process.stdout))
    if (status.get("connected") is not True or status.get("profileVerified") is not True
            or status.get("profileIdentity") != "auto-gpt" or status.get("endpoint") != endpoint):
        raise ValueError("Dedicated auto-gpt profile was not verified at the requested endpoint")


def observation_error(exc: Exception, *, phase: str, target: str,
                      observations: Sequence[Observation]) -> Mapping[str, object]:
    # 只取规范错误码，不回传异常正文或包含页面内容的协议上下文。
    code = getattr(exc, "code", "")
    return {"reason": "observation-error", "error_type": type(exc).__name__,
            "error_code": code if isinstance(code, str) and re.fullmatch(r"[A-Z][A-Z_]+", code) else "",
            "phase": phase, "failed_target": target,
            "observations": [asdict(page) for page in observations]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser-access-script", type=Path, required=True)
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--anchor-target", required=True)
    parser.add_argument("--anchor-url", required=True)
    parser.add_argument("--baseline", help="上一事件的 observations JSON 数组；只在内存和参数中传递")
    parser.add_argument("--max-wait-seconds", type=float, default=1800.0,
                        help="单次控件等待期限，默认 1800 秒；到期返回基线，由 Agent 继续等待")
    parser.add_argument("--ignore-conversation", action="append", default=[], help="Agent 已暂停的会话标识")
    parser.add_argument("--stream", action="store_true", help="持续输出变化事件，保留内存基线直到单次期限或取消")
    args = parser.parse_args()
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(130))
    observations: tuple[Observation, ...] = ()
    phase, failed_target = "arguments", ""
    try:
        baseline = read_baseline(args.baseline)
        if conversation(args.anchor_url) is None:
            raise ValueError("Anchor must be an HTTPS ChatGPT page")
        browser_script = args.browser_access_script.resolve(strict=True)
        phase = "profile-verification"
        verify_profile(browser_script, args.endpoint)
        sys.path.insert(0, str(browser_script.parent))
        session_type = cast(SessionFactory, importlib.import_module("browser_session").BrowserSession)
        ignored = set(args.ignore_conversation)
        phase, failed_target = "anchor-bind", args.anchor_target
        with session_type(args.endpoint, target=args.anchor_target, expected_url=args.anchor_url) as anchor:
            def output(value: Mapping[str, object]) -> None:
                print(json.dumps(value, ensure_ascii=False, separators=(",", ":")), flush=True)
            sampler = ControlSampler(anchor, session_type, args.endpoint, baseline or (), ignored, output)
            def sample() -> tuple[Observation, ...]:
                nonlocal observations, phase, failed_target
                phase, failed_target = "target-discovery", args.anchor_target
                observations = sampler.sample()
                return observations
            def emit(event: Event) -> None:
                print(json.dumps(asdict(event), ensure_ascii=False, separators=(",", ":")), flush=True)
            event = watch(sample, baseline=baseline, max_wait_seconds=args.max_wait_seconds,
                          on_event=emit if args.stream else None)
        output({**asdict(event), "sampling_failures": [asdict(f) for f in sampler.failures.values()]})
        return 0
    except (KeyboardInterrupt, SystemExit):
        return 130
    except Exception as exc:
        # 只暴露错误类型；不输出协议上下文、正文或自动截图。
        print(json.dumps(observation_error(exc, phase=phase, target=failed_target,
                                           observations=observations), ensure_ascii=False), flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
