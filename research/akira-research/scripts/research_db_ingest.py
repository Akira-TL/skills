from __future__ import annotations

import json
import mimetypes
import re
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TypedDict

from research_db_support.normalization import clean_optional_text, normalize_doi, normalize_identifier
from research_db_support.storage import ResearchDbError, connect, database_path

PAPER_ARTIFACT_ROOT = Path(".research") / "artifacts" / "papers"


class ArtifactSpec(TypedDict, total=False):
    kind: str
    path: str
    content_type: str
    version: str
    source: str
    source_url: str
    retrieved_at: str


class PaperIngestBundle(TypedDict, total=False):
    title: str
    doi: str
    pmid: str
    pmcid: str
    authors: list[str]
    journal: str
    year: int
    paper_type: str
    canonical_identity: str
    sidecar_path: str
    artifacts: list[ArtifactSpec]
    reason: str


class PaperArtifactBundle(TypedDict, total=False):
    paper_id: str
    artifacts: list[ArtifactSpec]
    reason: str


class PreparedArtifact(TypedDict):
    kind: str
    source_path: Path
    content_type: str | None
    version: str | None
    source: str | None
    source_url: str | None
    retrieved_at: str | None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_identity(bundle: PaperIngestBundle, doi: str | None, pmid: str | None) -> str | None:
    if doi:
        return f"doi:{doi}"
    if pmid:
        return f"pmid:{pmid}"
    return clean_optional_text(bundle.get("canonical_identity"))


def _paper_id(connection: sqlite3.Connection) -> str:
    highest = 0
    for row in connection.execute("SELECT id FROM papers WHERE id GLOB 'P[0-9]*'"):
        match = re.fullmatch(r"P(\d+)", str(row["id"]))
        if match:
            highest = max(highest, int(match.group(1)))
    return f"P{highest + 1:06d}"


def _prepare_artifacts(
    project_root: Path,
    specs: object,
    *,
    require_main_text: bool = True,
) -> list[PreparedArtifact]:
    if not isinstance(specs, list) or not specs:
        raise ResearchDbError("至少需要一个真实 artifact。")

    prepared: list[PreparedArtifact] = []
    for index, raw in enumerate(specs, start=1):
        if not isinstance(raw, dict):
            raise ResearchDbError(f"artifact #{index} 必须是 JSON object。")

        kind = clean_optional_text(raw.get("kind"))
        raw_path = clean_optional_text(raw.get("path"))
        if not kind or not raw_path:
            raise ResearchDbError(f"artifact #{index} 缺少 kind 或 path。")

        path = Path(raw_path).expanduser()
        if not path.is_absolute():
            path = project_root / path
        path = path.resolve()
        if not path.is_file():
            raise ResearchDbError(f"artifact #{index} 文件不存在：{path}")

        content_type = clean_optional_text(raw.get("content_type"))
        if content_type is None:
            content_type = mimetypes.guess_type(path.name)[0]

        prepared.append(
            {
                "kind": kind,
                "source_path": path,
                "content_type": content_type,
                "version": clean_optional_text(raw.get("version")),
                "source": clean_optional_text(raw.get("source")),
                "source_url": clean_optional_text(raw.get("source_url")),
                "retrieved_at": clean_optional_text(raw.get("retrieved_at")),
            }
        )

    if require_main_text and not any(artifact["kind"] == "main_text" for artifact in prepared):
        raise ResearchDbError("ingest-paper 至少需要一个 kind=main_text 的 artifact。")
    return prepared


def _artifact_basename(kind: str, source_path: Path, content_type: str | None) -> str:
    stem = "paper" if kind == "main_text" else re.sub(r"[^a-z0-9]+", "-", kind.lower()).strip("-")
    suffix = source_path.suffix.lower()
    if not suffix and content_type:
        media_type = content_type.split(";", 1)[0].strip().lower()
        suffix = (mimetypes.guess_extension(media_type, strict=False) or "").lower()
        if suffix == ".htm":
            suffix = ".html"
    if not suffix:
        raise ResearchDbError(
            f"artifact {kind!r} 的来源文件没有扩展名，且无法从 content_type 推断：{source_path}"
        )
    return f"{stem}{suffix}"


def _materialize_artifacts(
    project_root: Path, paper_id: str, artifacts: list[PreparedArtifact]
) -> tuple[Path, list[dict[str, Any]]]:
    paper_dir = project_root / PAPER_ARTIFACT_ROOT / paper_id
    if paper_dir.exists():
        raise ResearchDbError(f"Paper artifact 目录已存在，拒绝覆盖：{paper_dir}")
    paper_dir.mkdir(parents=True)

    materialized: list[dict[str, Any]] = []
    name_counts: dict[str, int] = {}
    try:
        for artifact in artifacts:
            base = _artifact_basename(
                artifact["kind"], artifact["source_path"], artifact["content_type"]
            )
            count = name_counts.get(base, 0) + 1
            name_counts[base] = count
            if count > 1:
                candidate = Path(base)
                base = f"{candidate.stem}-{count:02d}{candidate.suffix}"
            destination = paper_dir / base
            shutil.copy2(artifact["source_path"], destination)
            materialized.append(
                {
                    "kind": artifact["kind"],
                    "path": str(destination.relative_to(project_root)),
                    "content_type": artifact["content_type"],
                    "version": artifact["version"],
                    "source": artifact["source"],
                    "source_url": artifact["source_url"],
                    "retrieved_at": artifact["retrieved_at"],
                }
            )
    except Exception:
        shutil.rmtree(paper_dir, ignore_errors=True)
        raise
    return paper_dir, materialized


def _materialize_additional_artifacts(
    project_root: Path,
    paper_id: str,
    artifacts: list[PreparedArtifact],
    *,
    existing_paths: list[str],
) -> tuple[Path, list[dict[str, Any]], list[Path], bool]:
    paper_dir = project_root / PAPER_ARTIFACT_ROOT / paper_id
    created_dir = not paper_dir.exists()
    if paper_dir.exists() and not paper_dir.is_dir():
        raise ResearchDbError(f"Paper artifact canonical path 不是目录：{paper_dir}")
    paper_dir.mkdir(parents=True, exist_ok=True)

    used_names = {Path(path).name for path in existing_paths}
    used_names.update(path.name for path in paper_dir.iterdir())
    created_paths: list[Path] = []
    materialized: list[dict[str, Any]] = []
    try:
        for artifact in artifacts:
            base = _artifact_basename(
                artifact["kind"], artifact["source_path"], artifact["content_type"]
            )
            candidate = Path(base)
            destination_name = base
            index = 1
            while destination_name in used_names:
                index += 1
                destination_name = f"{candidate.stem}-{index:02d}{candidate.suffix}"
            used_names.add(destination_name)
            destination = paper_dir / destination_name
            shutil.copy2(artifact["source_path"], destination)
            created_paths.append(destination)
            materialized.append(
                {
                    "kind": artifact["kind"],
                    "path": str(destination.relative_to(project_root)),
                    "content_type": artifact["content_type"],
                    "version": artifact["version"],
                    "source": artifact["source"],
                    "source_url": artifact["source_url"],
                    "retrieved_at": artifact["retrieved_at"],
                }
            )
    except Exception:
        for path in reversed(created_paths):
            path.unlink(missing_ok=True)
        if created_dir:
            shutil.rmtree(paper_dir, ignore_errors=True)
        raise
    return paper_dir, materialized, created_paths, created_dir


def _register_artifacts(
    connection: sqlite3.Connection,
    *,
    paper_id: str,
    artifacts: list[dict[str, Any]],
    timestamp: str,
    reason: str,
) -> list[dict[str, Any]]:
    artifact_rows: list[dict[str, Any]] = []
    for artifact in artifacts:
        cursor = connection.execute(
            """
            INSERT INTO artifacts(
                paper_id, kind, path, content_type, version,
                source, source_url, retrieved_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                paper_id,
                artifact["kind"],
                artifact["path"],
                artifact["content_type"],
                artifact["version"],
                artifact["source"],
                artifact["source_url"],
                artifact["retrieved_at"],
                timestamp,
            ),
        )
        artifact_id = int(cursor.lastrowid)
        connection.execute(
            """
            INSERT INTO change_log(
                timestamp, action, entity_type, entity_id, paper_id, reason, summary
            ) VALUES (?, 'ADD', 'artifact', ?, ?, ?, ?)
            """,
            (
                timestamp,
                str(artifact_id),
                paper_id,
                reason,
                f"Registered {artifact['kind']} artifact: {artifact['path']}",
            ),
        )
        artifact_rows.append(
            {
                "id": artifact_id,
                "kind": artifact["kind"],
                "path": artifact["path"],
                "content_type": artifact["content_type"],
                "version": artifact["version"],
                "source": artifact["source"],
                "source_url": artifact["source_url"],
                "retrieved_at": artifact["retrieved_at"],
            }
        )
    return artifact_rows


def _duplicate_identity(
    connection: sqlite3.Connection,
    *,
    doi: str | None,
    pmid: str | None,
    canonical: str | None,
) -> str | None:
    checks = (("doi", doi), ("pmid", pmid), ("canonical_identity", canonical))
    for column, value in checks:
        if not value:
            continue
        row = connection.execute(
            f"SELECT id FROM papers WHERE lower({column}) = lower(?) LIMIT 1", (value,)
        ).fetchone()
        if row:
            return str(row["id"])
    return None


def _link_discovery_candidates(
    connection: sqlite3.Connection,
    *,
    paper_id: str,
    title: str,
    doi: str | None,
    pmid: str | None,
    year: int | None,
    timestamp: str,
) -> list[int]:
    predicates: list[str] = []
    params: list[Any] = []
    if doi:
        predicates.append("lower(doi) = lower(?)")
        params.append(doi)
    if pmid:
        predicates.append("pmid = ?")
        params.append(pmid)
    if doi or pmid:
        predicates.append(
            "(lower(title) = lower(?) AND ((year IS NULL AND ? IS NULL) OR year = ?) "
            "AND (doi IS NULL OR trim(doi) = '') AND (pmid IS NULL OR trim(pmid) = ''))"
        )
        params.extend([title, year, year])
    if not predicates:
        return []

    rows = connection.execute(
        "SELECT id FROM candidates WHERE " + " OR ".join(predicates), params
    ).fetchall()
    candidate_ids = [int(row["id"]) for row in rows]
    for candidate_id in candidate_ids:
        connection.execute(
            """
            UPDATE candidates
            SET paper_id = ?, identity_status = 'resolved',
                acquisition_status = 'acquired', doi = COALESCE(NULLIF(doi, ''), ?),
                pmid = COALESCE(NULLIF(pmid, ''), ?),
                user_access_status = CASE
                    WHEN user_access_status = 'not_required' THEN 'not_required'
                    ELSE 'completed'
                END,
                updated_at = ?
            WHERE id = ?
            """,
            (paper_id, doi, pmid, timestamp, candidate_id),
        )
    return candidate_ids


def add_paper_artifacts(
    project_root: Path, bundle: PaperArtifactBundle
) -> dict[str, Any]:
    db_path = database_path(project_root)
    if not db_path.exists():
        raise ResearchDbError("research.sqlite 不存在；先运行 research-db init。")

    paper_id = clean_optional_text(bundle.get("paper_id"))
    if not paper_id:
        raise ResearchDbError("add-paper-artifacts 缺少非空 paper_id。")
    prepared = _prepare_artifacts(
        project_root, bundle.get("artifacts"), require_main_text=False
    )
    timestamp = _now()
    reason = clean_optional_text(bundle.get("reason")) or "Added paper artifacts"
    paper_dir: Path | None = None
    created_paths: list[Path] = []
    created_dir = False

    with connect(db_path) as connection:
        try:
            connection.execute("BEGIN IMMEDIATE")
            paper = connection.execute(
                "SELECT id, reading_status, critical_status FROM papers WHERE id = ?", (paper_id,)
            ).fetchone()
            if paper is None:
                raise ResearchDbError(f"Paper 不存在：{paper_id}")

            existing_paths = [
                str(row["path"])
                for row in connection.execute(
                    "SELECT path FROM artifacts WHERE paper_id = ? ORDER BY id", (paper_id,)
                )
            ]
            paper_dir, artifacts, created_paths, created_dir = _materialize_additional_artifacts(
                project_root,
                paper_id,
                prepared,
                existing_paths=existing_paths,
            )
            for artifact in artifacts:
                if not artifact["retrieved_at"]:
                    artifact["retrieved_at"] = timestamp

            artifact_rows = _register_artifacts(
                connection,
                paper_id=paper_id,
                artifacts=artifacts,
                timestamp=timestamp,
                reason=reason,
            )

            review_invalidated = (
                str(paper["reading_status"]) != "unread"
                or str(paper["critical_status"]) != "not_reviewed"
            )
            if review_invalidated:
                connection.execute(
                    """
                    UPDATE papers
                    SET reading_status = 'unread', critical_status = 'not_reviewed', updated_at = ?
                    WHERE id = ?
                    """,
                    (timestamp, paper_id),
                )
                connection.execute(
                    """
                    INSERT INTO change_log(
                        timestamp, action, entity_type, entity_id, paper_id, reason, summary
                    ) VALUES (?, 'REOPEN', 'paper', ?, ?, ?, ?)
                    """,
                    (
                        timestamp,
                        paper_id,
                        paper_id,
                        reason,
                        "New paper artifact invalidated the current Reconstruction/Critical Audit completion state.",
                    ),
                )
            else:
                connection.execute(
                    "UPDATE papers SET updated_at = ? WHERE id = ?", (timestamp, paper_id)
                )
            connection.commit()
        except Exception:
            if connection.in_transaction:
                connection.rollback()
            for path in reversed(created_paths):
                path.unlink(missing_ok=True)
            if created_dir and paper_dir is not None:
                shutil.rmtree(paper_dir, ignore_errors=True)
            raise

    return {
        "ok": True,
        "paper_id": paper_id,
        "paper_dir": str(paper_dir.relative_to(project_root)) if paper_dir else None,
        "artifacts": artifact_rows,
        "review_reopened": review_invalidated,
    }


def ingest_paper(project_root: Path, bundle: PaperIngestBundle) -> dict[str, Any]:
    db_path = database_path(project_root)
    if not db_path.exists():
        raise ResearchDbError("research.sqlite 不存在；先运行 research-db init。")

    title = clean_optional_text(bundle.get("title"))
    if not title:
        raise ResearchDbError("ingest-paper 缺少非空 title。")

    year = bundle.get("year")
    if year is not None and (not isinstance(year, int) or isinstance(year, bool)):
        raise ResearchDbError("year 必须是整数。")

    authors = bundle.get("authors")
    if authors is not None:
        if not isinstance(authors, list) or not all(
            isinstance(author, str) and author.strip() for author in authors
        ):
            raise ResearchDbError("authors 必须是非空字符串数组。")
        authors_json = json.dumps(
            [author.strip() for author in authors], ensure_ascii=False
        )
    else:
        authors_json = None

    doi = normalize_doi(bundle.get("doi"))
    pmid = normalize_identifier(bundle.get("pmid"))
    pmcid = normalize_identifier(bundle.get("pmcid"))
    canonical = canonical_identity(bundle, doi, pmid)
    if canonical is None:
        raise ResearchDbError(
            "无法建立稳定论文身份；请提供 doi、pmid 或显式 canonical_identity。"
        )

    prepared = _prepare_artifacts(project_root, bundle.get("artifacts"))
    timestamp = _now()
    reason = clean_optional_text(bundle.get("reason")) or "Registered acquired paper"
    paper_dir: Path | None = None

    with connect(db_path) as connection:
        try:
            connection.execute("BEGIN IMMEDIATE")
            duplicate = _duplicate_identity(
                connection, doi=doi, pmid=pmid, canonical=canonical
            )
            if duplicate:
                raise ResearchDbError(f"论文身份已存在：{duplicate}")

            paper_id = _paper_id(connection)
            paper_dir, artifacts = _materialize_artifacts(
                project_root, paper_id, prepared
            )
            for artifact in artifacts:
                if not artifact["retrieved_at"]:
                    artifact["retrieved_at"] = timestamp

            connection.execute(
                """
                INSERT INTO papers(
                    id, title, doi, pmid, pmcid, authors, journal, year, paper_type,
                    canonical_identity, status, sidecar_path, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'acquired', ?, ?, ?)
                """,
                (
                    paper_id,
                    title,
                    doi,
                    pmid,
                    pmcid,
                    authors_json,
                    clean_optional_text(bundle.get("journal")),
                    year,
                    clean_optional_text(bundle.get("paper_type")),
                    canonical,
                    clean_optional_text(bundle.get("sidecar_path")),
                    timestamp,
                    timestamp,
                ),
            )
            connection.execute(
                """
                INSERT INTO change_log(
                    timestamp, action, entity_type, entity_id, paper_id, reason, summary
                ) VALUES (?, 'ADD', 'paper', ?, ?, ?, ?)
                """,
                (
                    timestamp,
                    paper_id,
                    paper_id,
                    reason,
                    f"Registered acquired paper: {title}",
                ),
            )
            linked_candidate_ids = _link_discovery_candidates(
                connection,
                paper_id=paper_id,
                title=title,
                doi=doi,
                pmid=pmid,
                year=year,
                timestamp=timestamp,
            )
            for candidate_id in linked_candidate_ids:
                connection.execute(
                    """
                    INSERT INTO change_log(
                        timestamp, action, entity_type, entity_id, paper_id, reason, summary
                    ) VALUES (?, 'candidate_acquired', 'candidate', ?, ?, ?, ?)
                    """,
                    (
                        timestamp,
                        str(candidate_id),
                        paper_id,
                        reason,
                        f"Linked discovery candidate to acquired paper {paper_id}.",
                    ),
                )

            artifact_rows = _register_artifacts(
                connection,
                paper_id=paper_id,
                artifacts=artifacts,
                timestamp=timestamp,
                reason=reason,
            )

            connection.commit()
        except Exception:
            if connection.in_transaction:
                connection.rollback()
            if paper_dir is not None:
                shutil.rmtree(paper_dir, ignore_errors=True)
            raise

    return {
        "ok": True,
        "paper_id": paper_id,
        "title": title,
        "doi": doi,
        "pmid": pmid,
        "canonical_identity": canonical,
        "status": "acquired",
        "paper_dir": str(paper_dir.relative_to(project_root)) if paper_dir else None,
        "artifacts": artifact_rows,
        "linked_candidate_ids": linked_candidate_ids,
    }
