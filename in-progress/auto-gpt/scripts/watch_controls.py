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
PROBE = Path(__file__).with_name("observe-controls.js").read_text(encoding="utf-8")


class View(StrEnum):
    RUNNING = "running"
    COMPOSER = "composer"
    UNKNOWN = "unknown"


class PageSession(Protocol):
    def __enter__(self) -> PageSession: ...
    def __exit__(self, *args: object) -> None: ...
    def call(self, method: str) -> Mapping[str, object]: ...
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

    @property
    def view(self) -> View:
        if self.stop > 0:
            return View.RUNNING
        if self.editors == 1 and self.composer > 0:
            return View.COMPOSER
        return View.UNKNOWN


@dataclass(frozen=True)
class Observation:
    target: str
    url: str
    controls: Controls


@dataclass(frozen=True)
class Event:
    reason: str
    targets: tuple[str, ...]
    observations: tuple[Observation, ...]


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
    return Controls(stop=cast(int, fields["stop"]), composer=cast(int, fields["composer"]),
                    editors=cast(int, fields["editors"]), draft=cast(bool, fields["draft"]),
                    alerts=cast(int, fields["alerts"]), dialogs=cast(int, fields["dialogs"]),
                    turns=cast(int, fields["turns"]), latest_turn=cast(str, fields["latest_turn"]))


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
        result.append(Observation(target, url, read_controls(fields.get("controls"))))
    return tuple(result)


def changes(previous: Sequence[Observation] | None, current: tuple[Observation, ...]) -> Event | None:
    old = {page.target: page for page in previous or ()}
    affected: list[str] = []
    for page in current:
        prior = old.get(page.target)
        now = page.controls
        if prior is None or prior.url != page.url:
            if now.view != View.RUNNING or now.alerts or now.dialogs:
                affected.append(page.target)
            continue
        before = prior.controls
        # 正在生成时只累计控件事实，不唤醒 Agent 做正文判断。
        changed = before.view != now.view and now.view != View.RUNNING
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
          clock: Callable[[], float] = time.monotonic, sleep: Callable[[float], None] = time.sleep) -> Event:
    previous = baseline
    while True:
        started = clock()
        current = sample()
        event = changes(previous, current)
        if event is not None:
            return event
        previous = current
        sleep(max(0.0, 60.0 - (clock() - started)))


def verify_profile(browser_script: Path, endpoint: str) -> None:
    # status 只读，不调用 ensure/tabs，浏览器退出时交回 Agent 而不是自动重开。
    command = ["uv", "run", "--no-project", "--offline", str(browser_script),
               "--profile", "auto-gpt", "status"]
    process = subprocess.run(command, capture_output=True, text=True, timeout=30, check=False)
    if process.returncode:
        raise ValueError("Dedicated profile status failed")
    status = object_fields(json.loads(process.stdout))
    if (status.get("connected") is not True or status.get("profileVerified") is not True
            or status.get("profileIdentity") != "auto-gpt" or status.get("endpoint") != endpoint):
        raise ValueError("Dedicated auto-gpt profile was not verified at the requested endpoint")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser-access-script", type=Path, required=True)
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--anchor-target", required=True)
    parser.add_argument("--anchor-url", required=True)
    parser.add_argument("--baseline", help="上一事件的 observations JSON 数组；只在内存和参数中传递")
    parser.add_argument("--ignore-conversation", action="append", default=[], help="Agent 已暂停的会话标识")
    args = parser.parse_args()
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(130))
    observations: tuple[Observation, ...] = ()
    try:
        baseline = read_baseline(args.baseline)
        if conversation(args.anchor_url) is None:
            raise ValueError("Anchor must be an HTTPS ChatGPT page")
        browser_script = args.browser_access_script.resolve(strict=True)
        verify_profile(browser_script, args.endpoint)
        sys.path.insert(0, str(browser_script.parent))
        session_type = cast(SessionFactory, importlib.import_module("browser_session").BrowserSession)
        ignored = set(args.ignore_conversation)
        with session_type(args.endpoint, target=args.anchor_target, expected_url=args.anchor_url) as anchor:
            def sample() -> tuple[Observation, ...]:
                nonlocal observations
                targets = anchor.call("Target.getTargets").get("targetInfos")
                if not isinstance(targets, list):
                    raise ValueError("Target discovery did not return a list")
                result: list[Observation] = []
                for item in targets:
                    target = object_fields(item)
                    target_id, url = target.get("targetId"), target.get("url")
                    if target.get("type") != "page" or not isinstance(url, str) or not isinstance(target_id, str):
                        continue
                    identifier = conversation(url)
                    if identifier is None or identifier in ignored:
                        continue
                    with session_type(args.endpoint, target=target_id, expected_url=url) as page:
                        result.append(Observation(target_id, url, read_controls(page.evaluate(PROBE))))
                observations = tuple(sorted(result, key=lambda page: page.target))
                return observations
            event = watch(sample, baseline=baseline)
        print(json.dumps(asdict(event), ensure_ascii=False), flush=True)
        return 0
    except (KeyboardInterrupt, SystemExit):
        return 130
    except Exception as exc:
        # 只暴露错误类型；不输出协议上下文、正文或自动截图。
        print(json.dumps({"reason": "observation-error", "error_type": type(exc).__name__,
                          "observations": [asdict(page) for page in observations]}, ensure_ascii=False), flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
