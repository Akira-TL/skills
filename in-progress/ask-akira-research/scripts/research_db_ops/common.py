from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from research_db_support.storage import ResearchDbError, database_path


GIT_TRACKING = {"required", "not_required"}
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_timestamp(value: object, *, field: str) -> datetime:
    raw = text(value, required=True, field=field)
    assert raw is not None
    normalized = raw[:-1] + "+00:00" if raw.endswith("Z") else raw
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ResearchDbError(f"{field} 必须是 ISO 8601 时间戳。") from exc
    if parsed.tzinfo is None:
        raise ResearchDbError(f"{field} 必须包含时区偏移。")
    return parsed.astimezone(timezone.utc)


def db_path(project_root: Path) -> Path:
    path = database_path(project_root)
    if not path.exists():
        raise ResearchDbError("research.sqlite 不存在；先运行 research-db init。")
    return path


def text(value: object, *, required: bool = False, field: str = "字段") -> str | None:
    if value is None:
        if required:
            raise ResearchDbError(f"{field} 不能为空。")
        return None
    result = str(value).strip()
    if not result and required:
        raise ResearchDbError(f"{field} 不能为空。")
    return result or None


def enum_value(value: object, allowed: set[str], *, default: str, field: str) -> str:
    result = text(value) or default
    if result not in allowed:
        raise ResearchDbError(f"{field} 必须是：{', '.join(sorted(allowed))}")
    return result


def slug(value: object, *, field: str = "slug") -> str:
    result = text(value, required=True, field=field)
    assert result is not None
    if not _SLUG_RE.fullmatch(result):
        raise ResearchDbError(f"{field} 必须使用 lowercase kebab-case。")
    return result


def local_path(
    project_root: Path,
    value: object,
    *,
    field: str,
    require_file: bool = False,
) -> str:
    raw = text(value, required=True, field=field)
    assert raw is not None
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = project_root / path
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(project_root.resolve())
    except ValueError as exc:
        raise ResearchDbError(f"{field} 必须位于科研项目目录内：{resolved}") from exc
    exists = resolved.is_file() if require_file else resolved.exists()
    if not exists:
        raise ResearchDbError(f"{field} 指向的文件不存在：{relative.as_posix()}")
    return relative.as_posix()


def tracking(value: object, *, default: str = "required") -> str:
    return enum_value(value, GIT_TRACKING, default=default, field="git_tracking")
