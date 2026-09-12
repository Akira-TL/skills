#!/usr/bin/env python3
"""Export Akira recommended reading to Zotero or a deterministic RIS fallback."""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

DEFAULT_COLLECTION = "Akira Recommended Reading"
DEFAULT_BASE_URL = "http://localhost:23119/api"
APP_NAME = "Akira Literature Export"
BATCH_LIMIT = 50


class ExportError(RuntimeError):
    pass


@dataclass(frozen=True)
class Paper:
    candidate_id: int
    priority: str
    title: str
    doi: str | None
    pmid: str | None
    authors: tuple[str, ...]
    year: int | None
    journal: str | None
    paper_type: str | None
    source_url: str | None


def text(value: object) -> str | None:
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def normalize_doi(value: object) -> str | None:
    value = text(value)
    if not value:
        return None
    value = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", value, flags=re.I)
    value = re.sub(r"^doi:\s*", "", value, flags=re.I)
    return value.strip().lower() or None


def normalize_title(value: str) -> str:
    return " ".join(re.sub(r"[^\w]+", " ", value.casefold(), flags=re.UNICODE).split())


def parse_authors(value: object) -> tuple[str, ...]:
    raw = text(value)
    if not raw:
        return ()
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, list) and all(isinstance(item, str) for item in parsed):
        return tuple(item.strip() for item in parsed if item.strip())
    if ";" in raw:
        return tuple(part.strip() for part in raw.split(";") if part.strip())
    return (raw,)


def parse_priorities(raw: str) -> tuple[str, ...]:
    allowed = {"core", "high", "normal", "low"}
    values = tuple(dict.fromkeys(part.strip().lower() for part in raw.split(",") if part.strip()))
    if not values or any(value not in allowed for value in values):
        raise ExportError("--priorities 只能使用 core,high,normal,low。")
    return values


def candidate_columns(connection: sqlite3.Connection) -> set[str]:
    return {str(row[1]) for row in connection.execute("PRAGMA table_info(candidates)")}


def load_recommendations(db_path: Path, priorities: tuple[str, ...]) -> list[Paper]:
    if not db_path.is_file():
        raise ExportError(f"research.sqlite 不存在：{db_path}")
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        columns = candidate_columns(connection)
        required = {"reading_priority", "relevance_status", "paper_id"}
        missing = sorted(required - columns)
        if missing:
            raise ExportError(
                "当前 research.sqlite schema 不支持 Zotero 推荐阅读出口，缺少 candidates 字段："
                + ", ".join(missing)
            )
        source_expr = "c.source_url" if "source_url" in columns else "NULL"
        marks = ",".join("?" for _ in priorities)
        rows = connection.execute(
            f"""
            SELECT
                c.id AS candidate_id,
                c.reading_priority,
                COALESCE(p.title, c.title) AS title,
                COALESCE(p.doi, c.doi) AS doi,
                COALESCE(p.pmid, c.pmid) AS pmid,
                COALESCE(p.authors, c.authors) AS authors,
                COALESCE(p.year, c.year) AS year,
                p.journal,
                p.paper_type,
                {source_expr} AS source_url
            FROM candidates c
            LEFT JOIN papers p ON p.id = c.paper_id
            WHERE c.relevance_status = 'relevant'
              AND c.reading_priority IN ({marks})
            ORDER BY CASE c.reading_priority
                WHEN 'core' THEN 0 WHEN 'high' THEN 1
                WHEN 'normal' THEN 2 ELSE 3 END, c.id
            """,
            priorities,
        ).fetchall()
    finally:
        connection.close()

    return [
        Paper(
            candidate_id=int(row["candidate_id"]),
            priority=str(row["reading_priority"]),
            title=str(row["title"]),
            doi=normalize_doi(row["doi"]),
            pmid=text(row["pmid"]),
            authors=parse_authors(row["authors"]),
            year=int(row["year"]) if row["year"] is not None else None,
            journal=text(row["journal"]),
            paper_type=text(row["paper_type"]),
            source_url=text(row["source_url"]),
        )
        for row in rows
    ]


def ris_type(paper: Paper) -> str:
    kind = (paper.paper_type or "").casefold()
    if "conference" in kind or "proceeding" in kind:
        return "CPAPER"
    if "preprint" in kind:
        return "UNPB"
    return "JOUR"


def ris_lines(paper: Paper) -> Iterable[str]:
    yield f"TY  - {ris_type(paper)}"
    yield f"TI  - {paper.title}"
    for author in paper.authors:
        yield f"AU  - {author}"
    if paper.year:
        yield f"PY  - {paper.year}"
    if paper.journal:
        yield f"JF  - {paper.journal}"
    if paper.doi:
        yield f"DO  - {paper.doi}"
    if paper.pmid:
        yield f"AN  - PMID:{paper.pmid}"
    if paper.source_url:
        yield f"UR  - {paper.source_url}"
    yield "ER  -"


def write_ris(papers: list[Paper], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    content = "\n\n".join("\n".join(ris_lines(paper)) for paper in papers)
    output_path.write_text((content + "\n") if content else "", encoding="utf-8")


def zotero_item_type(paper: Paper) -> str:
    kind = (paper.paper_type or "").casefold()
    if "conference" in kind or "proceeding" in kind:
        return "conferencePaper"
    if "preprint" in kind:
        return "preprint"
    return "journalArticle"


def new_zotero_item(paper: Paper, collection_key: str) -> dict[str, Any]:
    item: dict[str, Any] = {
        "itemType": zotero_item_type(paper),
        "title": paper.title,
        "collections": [collection_key],
    }
    if paper.authors:
        item["creators"] = [
            {"creatorType": "author", "name": author} for author in paper.authors
        ]
    if paper.year:
        item["date"] = str(paper.year)
    if paper.journal:
        item["publicationTitle"] = paper.journal
    if paper.doi:
        item["DOI"] = paper.doi
    if paper.source_url:
        item["url"] = paper.source_url
    if paper.pmid:
        item["extra"] = f"PMID: {paper.pmid}"
    return item


def request_json(
    method: str,
    url: str,
    *,
    payload: object | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 3.0,
) -> tuple[Any, Any]:
    body = None
    final_headers = {"Zotero-API-Version": "3", "Accept": "application/json"}
    if headers:
        final_headers.update(headers)
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        final_headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=body, headers=final_headers, method=method)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read()
        if raw:
            try:
                parsed = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                parsed = None
        else:
            parsed = None
        return parsed, response.headers


def cache_path() -> Path:
    config_root = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return config_root / "akira" / "zotero-local.json"


def load_cached_key(server_id: str) -> str | None:
    path = cache_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None
    if data.get("server_id") != server_id:
        clear_cached_key()
        return None
    return text(data.get("key"))


def save_cached_key(server_id: str, key: str) -> None:
    path = cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.parent.chmod(0o700)
    except OSError:
        pass
    path.write_text(
        json.dumps({"server_id": server_id, "key": key}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    try:
        path.chmod(0o600)
    except OSError:
        pass


def clear_cached_key() -> None:
    try:
        cache_path().unlink()
    except FileNotFoundError:
        pass


def api_url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


def probe_local_api(base_url: str) -> str:
    _, headers = request_json("GET", api_url(base_url, "/"), timeout=2.0)
    server_id = text(headers.get("Zotero-Server-ID"))
    if not server_id:
        raise ExportError("Zotero Local API 未返回 Zotero-Server-ID；不进行写入。")
    return server_id


def authorize(base_url: str, server_id: str) -> tuple[str, bool]:
    result, _ = request_json(
        "POST",
        api_url(base_url, "local/authorize"),
        payload={"appName": APP_NAME},
        headers={"Zotero-Server-ID": server_id},
        timeout=60.0,
    )
    key = text((result or {}).get("key")) if isinstance(result, dict) else None
    if not key:
        raise ExportError("Zotero 没有授予 Local API write key。")
    remembered = bool(result.get("remember"))
    if remembered:
        save_cached_key(server_id, key)
    return key, remembered


def write_headers(server_id: str, key: str) -> dict[str, str]:
    return {
        "Zotero-Server-ID": server_id,
        "Zotero-API-Key": key,
        "Zotero-Write-Token": uuid.uuid4().hex,
    }


def data_of(value: object) -> dict[str, Any]:
    if isinstance(value, dict) and isinstance(value.get("data"), dict):
        return value["data"]
    return value if isinstance(value, dict) else {}


def collection_key_from_write(result: object) -> str | None:
    if not isinstance(result, dict):
        return None
    successful = result.get("successful")
    if not isinstance(successful, dict) or not successful:
        return None
    first = next(iter(successful.values()))
    return text(first.get("key")) if isinstance(first, dict) else None


def find_collection(collections: object, name: str) -> str | None:
    matches: list[str] = []
    if isinstance(collections, list):
        for raw in collections:
            data = data_of(raw)
            if data.get("name") == name and not data.get("parentCollection"):
                key = text(data.get("key"))
                if key:
                    matches.append(key)
    if len(matches) > 1:
        raise ExportError(f"Zotero 中存在多个同名顶层 collection：{name}；不自动选择。")
    return matches[0] if matches else None


def existing_item_maps(items: object) -> tuple[dict[str, dict[str, Any]], dict[tuple[str, int | None], dict[str, Any]]]:
    by_doi: dict[str, dict[str, Any]] = {}
    by_title_year: dict[tuple[str, int | None], dict[str, Any]] = {}
    if not isinstance(items, list):
        return by_doi, by_title_year
    for raw in items:
        data = data_of(raw)
        if data.get("itemType") in {"attachment", "note", "annotation"}:
            continue
        doi = normalize_doi(data.get("DOI"))
        if doi:
            by_doi.setdefault(doi, data)
        title = text(data.get("title"))
        if title:
            date = text(data.get("date")) or ""
            match = re.search(r"\b(\d{4})\b", date)
            year = int(match.group(1)) if match else None
            if year is not None:
                by_title_year.setdefault((normalize_title(title), year), data)
    return by_doi, by_title_year


def build_item_changes(
    papers: list[Paper],
    collection_key: str,
    items: object,
) -> tuple[list[dict[str, Any]], int, int]:
    by_doi, by_title_year = existing_item_maps(items)
    changes: list[dict[str, Any]] = []
    new_count = 0
    existing_count = 0
    seen_existing: set[str] = set()
    for paper in papers:
        existing = by_doi.get(paper.doi) if paper.doi else None
        if existing is None and paper.year is not None:
            existing = by_title_year.get((normalize_title(paper.title), paper.year))
        if existing is None:
            changes.append(new_zotero_item(paper, collection_key))
            new_count += 1
            continue
        key = text(existing.get("key"))
        if not key or key in seen_existing:
            continue
        seen_existing.add(key)
        collections = [str(value) for value in existing.get("collections", [])]
        if collection_key in collections:
            continue
        changes.append(
            {
                "key": key,
                "version": existing.get("version"),
                "collections": collections + [collection_key],
            }
        )
        existing_count += 1
    return changes, new_count, existing_count


def post_batches(
    base_url: str,
    server_id: str,
    key: str,
    changes: list[dict[str, Any]],
    reusable_key: bool,
) -> tuple[int, int]:
    if len(changes) > BATCH_LIMIT and not reusable_key:
        raise ExportError(
            f"本次有 {len(changes)} 个 Zotero write changes，超过一次性授权单批 {BATCH_LIMIT} 条上限；"
            "不自动请求第二次授权。"
        )
    success = 0
    failed = 0
    for start in range(0, len(changes), BATCH_LIMIT):
        batch = changes[start : start + BATCH_LIMIT]
        result, _ = request_json(
            "POST",
            api_url(base_url, "users/0/items"),
            payload=batch,
            headers=write_headers(server_id, key),
            timeout=10.0,
        )
        if isinstance(result, dict):
            successful = result.get("successful")
            unsuccessful = result.get("failed")
            if isinstance(successful, dict):
                success += len(successful)
            if isinstance(unsuccessful, dict):
                failed += len(unsuccessful)
        else:
            failed += len(batch)
    return success, failed


def push_local(
    papers: list[Paper],
    base_url: str,
    collection_name: str,
) -> dict[str, Any]:
    server_id = probe_local_api(base_url)
    key = load_cached_key(server_id)
    reusable = bool(key)
    authorized_this_run = False
    if not key:
        key, reusable = authorize(base_url, server_id)
        authorized_this_run = True

    collections, _ = request_json("GET", api_url(base_url, "users/0/collections?format=json"))
    collection_key = find_collection(collections, collection_name)
    if not collection_key:
        created, _ = request_json(
            "POST",
            api_url(base_url, "users/0/collections"),
            payload=[{"name": collection_name, "parentCollection": False}],
            headers=write_headers(server_id, key),
            timeout=10.0,
        )
        collection_key = collection_key_from_write(created)
        if not collection_key:
            raise ExportError("Zotero collection 创建结果无法确认；不继续写入 items。")
        if authorized_this_run and not reusable:
            return {
                "status": "collection_created_only",
                "collection": collection_name,
                "collection_key": collection_key,
                "reason": "single_use_authorization_consumed",
            }

    items, _ = request_json("GET", api_url(base_url, "users/0/items?format=json"), timeout=10.0)
    changes, new_count, existing_count = build_item_changes(papers, collection_key, items)
    if not changes:
        return {
            "status": "pushed",
            "collection": collection_name,
            "created_items": 0,
            "existing_items_added": 0,
            "unchanged": len(papers),
        }
    success, failed = post_batches(base_url, server_id, key, changes, reusable)
    return {
        "status": "pushed" if failed == 0 else "partial_write",
        "collection": collection_name,
        "requested_changes": len(changes),
        "successful_changes": success,
        "failed_changes": failed,
        "new_items_planned": new_count,
        "existing_items_planned": existing_count,
    }


def fallback_reason(exc: BaseException) -> str:
    if isinstance(exc, urllib.error.HTTPError):
        if exc.code == 401:
            clear_cached_key()
            return "local_api_unauthorized"
        if exc.code == 403:
            return "local_api_disabled_or_denied"
        if exc.code == 429:
            return "authorization_rate_limited"
        return f"local_api_http_{exc.code}"
    if isinstance(exc, urllib.error.URLError):
        return "local_api_unreachable"
    if isinstance(exc, TimeoutError):
        return "local_api_timeout"
    if isinstance(exc, ExportError):
        return str(exc)
    return f"local_api_error:{type(exc).__name__}"


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--project-root", type=Path, default=Path.cwd())
    result.add_argument("--collection", default=DEFAULT_COLLECTION)
    result.add_argument("--priorities", default="core,high")
    result.add_argument("--base-url", default=DEFAULT_BASE_URL)
    result.add_argument("--file-only", action="store_true")
    result.add_argument("--output", type=Path)
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        priorities = parse_priorities(args.priorities)
        project_root = args.project_root.resolve()
        db_path = project_root / ".research" / "research.sqlite"
        papers = load_recommendations(db_path, priorities)
        output = args.output or (
            project_root / ".research" / "exports" / "zotero" / f"{args.collection}.ris"
        )
        write_ris(papers, output)
        if not papers:
            summary = {
                "status": "no_recommendations",
                "selected": 0,
                "ris": str(output),
            }
        elif args.file_only:
            summary = {
                "status": "fallback_only",
                "reason": "file_only",
                "selected": len(papers),
                "ris": str(output),
            }
        else:
            try:
                summary = push_local(papers, args.base_url, args.collection)
            except Exception as exc:  # deterministic fallback, never retry-loop
                summary = {
                    "status": "fallback_only",
                    "reason": fallback_reason(exc),
                    "selected": len(papers),
                }
            summary["ris"] = str(output)
            summary["selected"] = len(papers)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0
    except ExportError as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
