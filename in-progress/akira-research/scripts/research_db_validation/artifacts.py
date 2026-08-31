from __future__ import annotations

from pathlib import Path


def check_artifacts(project_root: Path, connection, errors: list[str], warnings: list[str]) -> None:
    for row in connection.execute(
        "SELECT id, kind, path, content_type FROM artifacts ORDER BY id"
    ):
        stored_path = Path(row["path"])
        if row["kind"] == "main_text" and not stored_path.suffix:
            errors.append(
                f"artifact {row['id']} 的 canonical main_text 路径缺少文件扩展名：{row['path']}"
            )
        artifact_path = stored_path
        if not artifact_path.is_absolute():
            artifact_path = project_root / artifact_path
        if not artifact_path.exists():
            errors.append(f"artifact {row['id']} 文件不存在：{artifact_path}")

    for row in connection.execute(
        "SELECT id, sidecar_path FROM papers WHERE sidecar_path IS NOT NULL AND trim(sidecar_path) <> ''"
    ):
        sidecar_path = Path(row["sidecar_path"])
        if not sidecar_path.is_absolute():
            sidecar_path = project_root / sidecar_path
        if not sidecar_path.exists():
            warnings.append(f"{row['id']} 的 sidecar 不存在：{sidecar_path}")
