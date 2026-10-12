"""Discord 业务命令的会话范围与公开浏览器操作适配。"""
from __future__ import annotations

import argparse
import json
from collections.abc import Iterator, Mapping
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, TypedDict, cast


class MjDiscordError(RuntimeError):
    def __init__(self, message: str, *, code: str = "MIDJOURNEY_ERROR",
                 context: Mapping[str, object] | None = None):
        super().__init__(message)
        self.code = code
        self.context = context or {}

    def as_dict(self) -> dict[str, object]:
        return {"ok": False, "error_code": self.code, "message": str(self),
                "context": self.context, "error": str(self)}


class PageTarget(TypedDict):
    id: str
    url: str
    title: str
    composer: str | None


class PageSession(Protocol):
    def __enter__(self) -> PageSession: ...
    def __exit__(self, *args: object) -> None: ...
    def execute(self, op: str, **options: object) -> dict[str, object]: ...


class SessionFactory(Protocol):
    def __call__(self, endpoint: str, *, target: str, expected_url: str,
                 timeout: float) -> PageSession: ...


class StructuredError(Protocol):
    def as_dict(self) -> Mapping[str, object]: ...


@dataclass
class BrowserScope:
    cli: Path
    stack: ExitStack
    page: PageSession | None = None
    target: PageTarget | None = None


@contextmanager
def browser_scope(args: argparse.Namespace, cli: Path) -> Iterator[None]:
    with ExitStack() as stack:
        args._browser_scope = BrowserScope(cli, stack)
        try:
            yield
        except MjDiscordError:
            raise
        except Exception as exc:
            if callable(getattr(exc, "as_dict", None)):
                error = cast(StructuredError, exc).as_dict()
                context = error.get("context")
                raise MjDiscordError(str(error.get("message", exc)),
                                     code=str(error.get("error_code", "BROWSER_ERROR")),
                                     context=cast(Mapping[str, object], context) if isinstance(context, dict) else None) from exc
            raise
        finally:
            del args._browser_scope


def scope_for(args: argparse.Namespace) -> BrowserScope | None:
    return cast(BrowserScope | None, getattr(args, "_browser_scope", None))


def session_operation(page: PageSession, parts: tuple[str, ...]) -> dict[str, object]:
    op, target_flag, _target, *tail = parts
    if target_flag != "--target":
        raise MjDiscordError("A session operation requires an exact target", code="INVALID_ARGUMENT")
    if op == "eval" and len(tail) == 1:
        return page.execute("eval", expression=tail[0])
    if op == "click" and len(tail) >= 1:
        return page.execute("click", selector=tail[0], allow_submit="--allow-submit" in tail[1:])
    if op == "type" and len(tail) == 2:
        return page.execute("type", selector=tail[0], value=tail[1])
    if op == "upload" and len(tail) >= 2:
        return page.execute("upload", selector=tail[0], files=tail[1:])
    if op == "call" and len(tail) == 3 and tail[1] == "--params":
        params = json.loads(tail[2])
        if not isinstance(params, dict):
            raise MjDiscordError("CDP parameters must be an object", code="INVALID_ARGUMENT")
        return page.execute("call", method=tail[0], params=params)
    raise MjDiscordError(f"Unsupported browser operation: {op}", code="INVALID_ARGUMENT")
