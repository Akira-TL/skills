#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


CLAIM_NAMESPACE = "akira-parallel"
CLAIM_SCHEMA_VERSION = 1


class ClaimError(RuntimeError):
    """The claim store cannot be used safely."""


@dataclass(frozen=True)
class ClaimRecord:
    schema_version: int
    task: str
    owner: str
    claimed_at: str
    hostname: str
    pid: int
    worktree: str

    @classmethod
    def from_json(cls, raw: object) -> ClaimRecord:
        if not isinstance(raw, dict):
            raise ClaimError("claim 元数据不是 JSON object；拒绝猜测锁的 owner。")
        try:
            schema_version = raw["schema_version"]
            task = raw["task"]
            owner = raw["owner"]
            claimed_at = raw["claimed_at"]
            hostname = raw["hostname"]
            pid = raw["pid"]
            worktree = raw["worktree"]
        except KeyError as exc:
            raise ClaimError(f"claim 元数据缺少字段：{exc.args[0]}") from exc
        if schema_version != CLAIM_SCHEMA_VERSION:
            raise ClaimError(
                f"不支持的 claim schema_version：{schema_version!r}；"
                f"当前版本为 {CLAIM_SCHEMA_VERSION}。"
            )
        if not all(isinstance(value, str) and value for value in (task, owner, claimed_at, hostname, worktree)):
            raise ClaimError("claim 元数据包含无效字符串字段；拒绝猜测锁的 owner。")
        if not isinstance(pid, int):
            raise ClaimError("claim 元数据 pid 无效；拒绝猜测锁的 owner。")
        return cls(
            schema_version=schema_version,
            task=task,
            owner=owner,
            claimed_at=claimed_at,
            hostname=hostname,
            pid=pid,
            worktree=worktree,
        )


@dataclass(frozen=True)
class CliPayload:
    ok: bool
    task: str
    claimed: bool | None
    owner: str | None
    common_dir: str | None
    released: bool | None = None
    error: str | None = None


def emit(payload: CliPayload) -> None:
    print(json.dumps(asdict(payload), ensure_ascii=False, sort_keys=True))


def run_git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "unknown git error"
        raise ClaimError(f"无法读取 Git repository：{detail}")
    return completed.stdout.strip()


def resolve_repo(repo_value: str) -> Path:
    repo = Path(repo_value).expanduser().resolve()
    if not repo.exists():
        raise ClaimError(f"Git repository 路径不存在：{repo}")
    worktree = run_git(repo, "rev-parse", "--show-toplevel")
    return Path(worktree).resolve()


def resolve_common_dir(worktree: Path) -> Path:
    raw = run_git(worktree, "rev-parse", "--git-common-dir")
    common_dir = Path(raw)
    if not common_dir.is_absolute():
        common_dir = worktree / common_dir
    return common_dir.resolve()


def claim_key(task: str) -> str:
    return hashlib.sha256(task.encode("utf-8")).hexdigest()


def claim_store(common_dir: Path) -> Path:
    return common_dir / CLAIM_NAMESPACE / "claims"


def ensure_claim_store(common_dir: Path) -> Path:
    store = claim_store(common_dir)
    store.mkdir(parents=True, exist_ok=True)
    return store


def claim_path(common_dir: Path, task: str) -> Path:
    return claim_store(common_dir) / f"{claim_key(task)}.json"


def load_claim(path: Path, expected_task: str) -> ClaimRecord | None:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ClaimError(f"claim 元数据损坏：{path}") from exc
    record = ClaimRecord.from_json(raw)
    if record.task != expected_task:
        raise ClaimError(
            f"claim 元数据 Task 不匹配：期望 {expected_task!r}，实际 {record.task!r}。"
        )
    return record


def write_claim_atomically(path: Path, record: ClaimRecord) -> bool:
    payload = json.dumps(asdict(record), ensure_ascii=False, sort_keys=True) + "\n"
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.stem}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temp_path = Path(handle.name)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temp_path, path)
        except FileExistsError:
            return False
        return True
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink()
            except FileNotFoundError:
                pass


def new_record(task: str, owner: str, worktree: Path) -> ClaimRecord:
    return ClaimRecord(
        schema_version=CLAIM_SCHEMA_VERSION,
        task=task,
        owner=owner,
        claimed_at=datetime.now(timezone.utc).isoformat(),
        hostname=socket.gethostname(),
        pid=os.getpid(),
        worktree=str(worktree),
    )


def command_claim(task: str, owner: str, worktree: Path, common_dir: Path) -> int:
    ensure_claim_store(common_dir)
    path = claim_path(common_dir, task)
    record = new_record(task, owner, worktree)
    if write_claim_atomically(path, record):
        emit(
            CliPayload(
                ok=True,
                task=task,
                claimed=True,
                owner=owner,
                common_dir=str(common_dir),
            )
        )
        return 0

    current = load_claim(path, task)
    if current is None:
        raise ClaimError("claim 冲突后锁文件消失；请重新执行 claim。")
    if current.owner == owner:
        emit(
            CliPayload(
                ok=True,
                task=task,
                claimed=True,
                owner=current.owner,
                common_dir=str(common_dir),
            )
        )
        return 0
    emit(
        CliPayload(
            ok=False,
            task=task,
            claimed=True,
            owner=current.owner,
            common_dir=str(common_dir),
            error=f"Task 已由 {current.owner} 领取。",
        )
    )
    return 1


def command_status(task: str, common_dir: Path) -> int:
    current = load_claim(claim_path(common_dir, task), task)
    emit(
        CliPayload(
            ok=True,
            task=task,
            claimed=current is not None,
            owner=current.owner if current is not None else None,
            common_dir=str(common_dir),
        )
    )
    return 0


def command_release(task: str, owner: str, common_dir: Path) -> int:
    path = claim_path(common_dir, task)
    current = load_claim(path, task)
    if current is None:
        emit(
            CliPayload(
                ok=False,
                task=task,
                claimed=False,
                owner=None,
                common_dir=str(common_dir),
                released=False,
                error="Task 当前没有确定性 claim。",
            )
        )
        return 1
    if current.owner != owner:
        emit(
            CliPayload(
                ok=False,
                task=task,
                claimed=True,
                owner=current.owner,
                common_dir=str(common_dir),
                released=False,
                error=f"Task 由 {current.owner} 领取；{owner} 无权释放。",
            )
        )
        return 1

    try:
        path.unlink()
    except FileNotFoundError:
        emit(
            CliPayload(
                ok=False,
                task=task,
                claimed=False,
                owner=None,
                common_dir=str(common_dir),
                released=False,
                error="释放时 claim 已不存在；请重新检查 status。",
            )
        )
        return 1

    emit(
        CliPayload(
            ok=True,
            task=task,
            claimed=False,
            owner=None,
            common_dir=str(common_dir),
            released=True,
        )
    )
    return 0


def add_repo_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--repo",
        default=".",
        help="任一属于目标 Git repository 的 worktree 路径；默认当前目录。",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="parallel-claim",
        description="为 Akira Parallel Task 提供同机、跨 Git worktree 的确定性 claim 互斥。",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    claim_parser = subparsers.add_parser("claim", help="原子领取一个 Parallel Task。")
    claim_parser.add_argument("--task", required=True, help="稳定且唯一的 Parallel Task 引用。")
    claim_parser.add_argument("--owner", required=True, help="当前 Worker 的稳定会话身份。")
    add_repo_argument(claim_parser)

    release_parser = subparsers.add_parser("release", help="由当前 owner 释放一个 Parallel Task。")
    release_parser.add_argument("--task", required=True, help="稳定且唯一的 Parallel Task 引用。")
    release_parser.add_argument("--owner", required=True, help="当前 Worker 的稳定会话身份。")
    add_repo_argument(release_parser)

    status_parser = subparsers.add_parser("status", help="查询一个 Parallel Task 的确定性 claim。")
    status_parser.add_argument("--task", required=True, help="稳定且唯一的 Parallel Task 引用。")
    add_repo_argument(status_parser)

    return parser


def validate_identity(value: str, label: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ClaimError(f"{label} 不能为空。")
    return normalized


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    task = "<unknown>"
    try:
        task = validate_identity(args.task, "task")
        worktree = resolve_repo(args.repo)
        common_dir = resolve_common_dir(worktree)
        if args.command == "claim":
            owner = validate_identity(args.owner, "owner")
            return command_claim(task, owner, worktree, common_dir)
        if args.command == "release":
            owner = validate_identity(args.owner, "owner")
            return command_release(task, owner, common_dir)
        return command_status(task, common_dir)
    except (ClaimError, OSError) as exc:
        emit(
            CliPayload(
                ok=False,
                task=task,
                claimed=None,
                owner=None,
                common_dir=None,
                error=str(exc),
            )
        )
        return 2


if __name__ == "__main__":
    sys.exit(main())
