from __future__ import annotations

import json
import mimetypes
import re
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TypedDict

from research_db_core import ResearchDbError, connect, database_path


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


def _clean_optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def normalize_doi(value: object) -> str | None:
    text = _clean_optional_text(value)
    if text is None:
        return None
    lowered = text.lower()
    for prefix in (
        "https://doi.org/",
        "http://doi.org/",
        "https://dx.doi.org/",
        "http://dx.doi.org/",
        "doi:",
    ):
        if lowered.startswith(prefix):
            lowered = lowered[len(prefix) :].strip()
            break
    return lowered or None


def normalize_identifier(value: object) -> str | None:
    return _clean_optional_text(value)


def canonical_identity(bundle: PaperIngestBundle, doi: str | None, pmid: str | None) -> str | None:
    if doi:
        return f"doi:{doi}"
    if pmid:
        return f"pmid:{pmid}"
    return _clean_optional_text(bundle.get("canonical_identity"))


def _paper_id(connection: sqlite3.Connection) -> str:
    highest = 0
    for row in connection.execute("SELECT id FROM papers WHERE id GLOB 'P[0-9]*'"):
        match = re.fullmatch(r"P(\d+)", str(row["id"]))
        if match:
            highest = max(highest, int(match.group(1)))
    return f"P{highest + 1:06d}"


def _prepare_artifacts(project_root: Path, specs: object) -> list[PreparedArtifact]:
    if not isinstance(specs, list) or not specs:
        raise ResearchDbError("ingest-paper 至少需要一个真实 artifact。")

    prepared: list[PreparedArtifact] = []
    for index, raw in enumerate(specs, start=1):
        if not isinstance(raw, dict):
            raise ResearchDbError(f"artifact #{index} 必须是 JSON object。")

        kind = _clean_optional_text(raw.get("kind"))
        raw_path = _clean_optional_text(raw.get("path"))
        if not kind or not raw_path:
            raise ResearchDbError(f"artifact #{index} 缺少 kind 或 path。")

        path = Path(raw_path).expanduser()
        if not path.is_absolute():
            path = project_root / path
        path = path.resolve()
        if not path.is_file():
            raise ResearchDbError(f"artifact #{index} 文件不存在：{path}")

        content_type = _clean_optional_text(raw.get("content_type"))
        if content_type is None:
            content_type = mimetypes.guess_type(path.name)[0]

        prepared.append(
            {
                "kind": kind,
                "source_path": path,
                "content_type": content_type,
                "version": _clean_optional_text(raw.get("version")),
                "source": _clean_optional_text(raw.get("source")),
                "source_url": _clean_optional_text(raw.get("source_url")),
                "retrieved_at": _clean_optional_text(raw.get("retrieved_at")),
            }
        )

    if not any(artifact["kind"] == "main_text" for artifact in prepared):
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
    paper_dir = project_root / "literature" / "papers" / paper_id
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


def ingest_paper(project_root: Path, bundle: PaperIngestBundle) -> dict[str, Any]:
    db_path = database_path(project_root)
    if not db_path.exists():
        raise ResearchDbError("research.sqlite 不存在；先运行 research-db init。")

    title = _clean_optional_text(bundle.get("title"))
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
    reason = _clean_optional_text(bundle.get("reason")) or "Registered acquired paper"
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
                    _clean_optional_text(bundle.get("journal")),
                    year,
                    _clean_optional_text(bundle.get("paper_type")),
                    canonical,
                    _clean_optional_text(bundle.get("sidecar_path")),
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
