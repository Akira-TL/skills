from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

from research_db_core import connect, database_path, validate
from research_db_ops.acquisition import acquired_main_text_access_blockers
from research_db_ops.candidates import discovery_readiness


SCIENTIFIC_RELATION_PREDICATES = {
    "DIRECTLY_SUPPORTS",
    "INDIRECTLY_SUPPORTS",
    "QUALIFIES",
    "CONTRADICTS",
    "DOES_NOT_TEST",
    "LIMITS",
    "CHALLENGES",
    "WEAKENS",
}
RELATION_ENTITY_TABLES = {
    "method": "methods",
    "experiment": "experiments",
    "observation": "observations",
    "claim": "claims",
    "issue": "issues",
    "lead": "leads",
}


def _git(project_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(project_root), *args],
        text=True,
        capture_output=True,
        check=False,
    )


def _canonical_paths(project_root: Path) -> list[str]:
    paths = {"RESEARCH.md", ".research/research.sqlite"}
    db_path = database_path(project_root)
    if not db_path.exists():
        return sorted(paths)

    with connect(db_path) as connection:
        tables = {
            str(row["name"])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            )
        }
        for row in connection.execute("SELECT path FROM artifacts ORDER BY id"):
            path = Path(str(row["path"]))
            if path.is_absolute():
                try:
                    path = path.resolve().relative_to(project_root.resolve())
                except ValueError:
                    continue
            paths.add(path.as_posix())
        for row in connection.execute(
            "SELECT sidecar_path FROM papers WHERE sidecar_path IS NOT NULL AND trim(sidecar_path) <> ''"
        ):
            path = Path(str(row["sidecar_path"]))
            if path.is_absolute():
                try:
                    path = path.resolve().relative_to(project_root.resolve())
                except ValueError:
                    continue
            paths.add(path.as_posix())
        if "datasets" in tables:
            for row in connection.execute("SELECT provenance_path FROM datasets ORDER BY id"):
                paths.add(Path(str(row["provenance_path"])).as_posix())
        if "dataset_artifacts" in tables:
            for row in connection.execute(
                """
                SELECT location FROM dataset_artifacts
                WHERE storage_kind = 'local' AND git_tracking = 'required'
                ORDER BY id
                """
            ):
                paths.add(Path(str(row["location"])).as_posix())
        if "analysis_runs" in tables:
            for row in connection.execute("SELECT analysis_path, code_path FROM analysis_runs ORDER BY id"):
                paths.add(Path(str(row["analysis_path"])).as_posix())
                paths.add(Path(str(row["code_path"])).as_posix())
        if "analysis_artifacts" in tables:
            for row in connection.execute(
                "SELECT path FROM analysis_artifacts WHERE git_tracking = 'required' ORDER BY id"
            ):
                paths.add(Path(str(row["path"])).as_posix())
    return sorted(paths)


def _academic_language_paths(project_root: Path) -> list[Path]:
    paths = [project_root / "RESEARCH.md"]
    db_path = database_path(project_root)
    if not db_path.exists():
        return paths
    with connect(db_path) as connection:
        tables = {
            str(row["name"])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            )
        }
        for row in connection.execute(
            "SELECT sidecar_path FROM papers WHERE sidecar_path IS NOT NULL AND trim(sidecar_path) <> ''"
        ):
            path = Path(str(row["sidecar_path"]))
            if not path.is_absolute():
                path = project_root / path
            paths.append(path)
        if "datasets" in tables:
            for row in connection.execute("SELECT provenance_path FROM datasets ORDER BY id"):
                path = Path(str(row["provenance_path"]))
                paths.append(path if path.is_absolute() else project_root / path)
        if "analysis_runs" in tables:
            for row in connection.execute("SELECT analysis_path FROM analysis_runs ORDER BY id"):
                path = Path(str(row["analysis_path"]))
                paths.append(path if path.is_absolute() else project_root / path)
    return paths


def academic_language_readiness(project_root: Path) -> dict[str, Any]:
    research_path = project_root / "RESEARCH.md"
    if not research_path.exists():
        return {"ready": True, "checked": False, "blockers": []}
    research_text = research_path.read_text(encoding="utf-8", errors="ignore")
    if len(re.findall(r"[\u3400-\u9fff]", research_text)) < 50:
        return {"ready": True, "checked": False, "blockers": []}

    blockers: list[dict[str, Any]] = []
    for path in _academic_language_paths(project_root):
        if not path.exists() or path.suffix.casefold() not in {".md", ".txt"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
        for index, paragraph in enumerate(re.split(r"\n\s*\n", text), start=1):
            stripped = paragraph.strip()
            if not stripped or stripped.startswith("#") and "\n" not in stripped:
                continue
            prose_for_language_check = re.sub(r"`[^`]*`", "", stripped)
            prose_for_language_check = re.sub(r"https?://\S+", "", prose_for_language_check)
            cjk_count = len(re.findall(r"[\u3400-\u9fff]", prose_for_language_check))
            english_words = re.findall(r"\b[A-Za-z][A-Za-z'-]{1,}\b", prose_for_language_check)
            if len(english_words) >= 30 and cjk_count < 5:
                blockers.append(
                    {
                        "reason": "english_prose_in_chinese_research_text",
                        "path": str(path.relative_to(project_root)),
                        "paragraph": index,
                        "english_word_count": len(english_words),
                        "preview": " ".join(stripped.split())[:180],
                    }
                )
    return {"ready": not blockers, "checked": True, "blockers": blockers}


def _entity_paper_id(connection, entity_type: str, entity_id: str) -> str | None:
    if entity_type == "paper":
        row = connection.execute("SELECT id FROM papers WHERE id = ?", (entity_id,)).fetchone()
        return str(row["id"]) if row else None
    table = RELATION_ENTITY_TABLES.get(entity_type)
    if table is None:
        return None
    row = connection.execute(
        f'SELECT paper_id FROM "{table}" WHERE CAST(id AS TEXT) = ?', (entity_id,)
    ).fetchone()
    return str(row["paper_id"]) if row else None


def literature_completion_readiness(
    project_root: Path, discovery: dict[str, Any] | None = None
) -> dict[str, Any]:
    blockers: list[dict[str, Any]] = []
    core_acquired_count = 0
    relevant_acquired_count = 0
    critically_reviewed_count = 0
    cross_paper_scientific_relations: list[int] = []
    db_path = database_path(project_root)
    if not db_path.exists():
        return {
            "ready": False,
            "blockers": [{"reason": "database_missing"}],
            "core_acquired_count": 0,
            "relevant_acquired_count": 0,
            "critically_reviewed_count": 0,
            "cross_paper_scientific_relation_count": 0,
        }

    with connect(db_path) as connection:
        acquired = connection.execute(
            """
            SELECT c.id AS candidate_id, c.title, c.reading_priority, c.paper_id,
                   p.read_depth, p.reading_status, p.critical_status
            FROM candidates c
            LEFT JOIN papers p ON p.id = c.paper_id
            WHERE c.relevance_status = 'relevant'
              AND c.acquisition_status = 'acquired'
            ORDER BY c.id
            """
        ).fetchall()
        relevant_acquired_count = len(acquired)
        for row in acquired:
            paper_id = row["paper_id"]
            if not paper_id:
                continue
            blockers.extend(acquired_main_text_access_blockers(connection, int(row["candidate_id"])))
            if row["reading_status"] != "extracted" or row["critical_status"] != "critically_reviewed":
                blockers.append(
                    {
                        "reason": "relevant_acquired_not_fully_reviewed",
                        "candidate_id": int(row["candidate_id"]),
                        "paper_id": paper_id,
                        "title": row["title"],
                    }
                )
            else:
                critically_reviewed_count += 1
            if row["reading_priority"] == "core":
                core_acquired_count += 1
                deep_run = connection.execute(
                    """
                    SELECT 1 FROM reading_runs
                    WHERE paper_id = ? AND pass = 'reconstruction'
                      AND depth = 'deep_extraction' AND completed_at IS NOT NULL
                    LIMIT 1
                    """,
                    (paper_id,),
                ).fetchone()
                if row["read_depth"] != "deep_extraction" or deep_run is None:
                    blockers.append(
                        {
                            "reason": "core_acquired_not_deep_extraction",
                            "candidate_id": int(row["candidate_id"]),
                            "paper_id": paper_id,
                            "title": row["title"],
                            "read_depth": row["read_depth"],
                            "deep_reconstruction_run": deep_run is not None,
                        }
                    )

        for relation in connection.execute(
            """
            SELECT id, subject_type, subject_id, predicate, object_type, object_id
            FROM relations ORDER BY id
            """
        ):
            if relation["predicate"] not in SCIENTIFIC_RELATION_PREDICATES:
                continue
            subject_paper = _entity_paper_id(
                connection, str(relation["subject_type"]), str(relation["subject_id"])
            )
            object_paper = _entity_paper_id(
                connection, str(relation["object_type"]), str(relation["object_id"])
            )
            if subject_paper and object_paper and subject_paper != object_paper:
                cross_paper_scientific_relations.append(int(relation["id"]))

    discovery = discovery or discovery_readiness(project_root)
    topical_discovery = (
        int(discovery.get("relevant_candidate_count", 0)) >= 2
        and bool(set(discovery.get("discovery_families", [])) & {"query_search", "related_work"})
    )
    if topical_discovery and critically_reviewed_count >= 2 and not cross_paper_scientific_relations:
        blockers.append(
            {
                "reason": "cross_paper_scientific_relation_missing",
                "reviewed_paper_count": critically_reviewed_count,
            }
        )

    return {
        "ready": not blockers,
        "blockers": blockers,
        "core_acquired_count": core_acquired_count,
        "relevant_acquired_count": relevant_acquired_count,
        "critically_reviewed_count": critically_reviewed_count,
        "cross_paper_scientific_relation_count": len(cross_paper_scientific_relations),
        "cross_paper_scientific_relation_ids": cross_paper_scientific_relations,
    }


def _git_commit_has_path(project_root: Path, commit: str, path: str) -> bool:
    result = _git(project_root, "cat-file", "-e", f"{commit}:{path}")
    return result.returncode == 0


def downstream_completion_readiness(project_root: Path) -> dict[str, Any]:
    blockers: list[dict[str, Any]] = []
    db_path = database_path(project_root)
    if not db_path.exists():
        return {
            "ready": False,
            "blockers": [{"reason": "database_missing"}],
            "dataset_count": 0,
            "analysis_count": 0,
            "completed_analysis_count": 0,
        }

    with connect(db_path) as connection:
        tables = {
            str(row["name"])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            )
        }
        required = {
            "datasets",
            "dataset_artifacts",
            "analysis_runs",
            "analysis_inputs",
            "analysis_artifacts",
            "analysis_amendments",
            "project_observations",
        }
        missing = sorted(required - tables)
        if missing:
            return {
                "ready": False,
                "blockers": [{"reason": "downstream_schema_missing", "tables": missing}],
                "dataset_count": 0,
                "analysis_count": 0,
                "completed_analysis_count": 0,
            }

        dataset_count = int(connection.execute("SELECT COUNT(*) FROM datasets").fetchone()[0])
        analysis_count = int(connection.execute("SELECT COUNT(*) FROM analysis_runs").fetchone()[0])
        completed_analysis_count = int(
            connection.execute("SELECT COUNT(*) FROM analysis_runs WHERE status = 'completed'").fetchone()[0]
        )

        tracked = _git(project_root, "ls-files", "--", "data", "analysis")
        tracked_paths = {line.strip() for line in tracked.stdout.splitlines() if line.strip()}
        registered_paths = set(_canonical_paths(project_root))
        orphaned = sorted(tracked_paths - registered_paths)
        if orphaned:
            blockers.append(
                {
                    "reason": "tracked_downstream_artifacts_unregistered",
                    "paths": orphaned,
                }
            )

        data_dir = project_root / "data"
        if data_dir.exists() and any(path.is_file() for path in data_dir.rglob("*")) and dataset_count == 0:
            blockers.append({"reason": "data_assets_present_without_dataset_record"})
        analysis_dir = project_root / "analysis"
        if analysis_dir.exists() and any(path.is_file() for path in analysis_dir.rglob("*")) and analysis_count == 0:
            blockers.append({"reason": "analysis_assets_present_without_analysis_record"})

        for run in connection.execute(
            "SELECT * FROM analysis_runs WHERE status = 'completed' ORDER BY id"
        ):
            analysis_id = int(run["id"])
            slug = str(run["slug"])
            input_rows = connection.execute(
                """
                SELECT d.id, d.slug, d.provenance_path
                FROM analysis_inputs ai
                JOIN datasets d ON d.id = ai.dataset_id
                WHERE ai.analysis_id = ? ORDER BY d.id
                """,
                (analysis_id,),
            ).fetchall()
            if not input_rows:
                blockers.append(
                    {"reason": "completed_analysis_missing_dataset_input", "analysis": slug}
                )
            estimate_count = int(
                connection.execute(
                    "SELECT COUNT(*) FROM analysis_artifacts WHERE analysis_id = ? AND role = 'estimate'",
                    (analysis_id,),
                ).fetchone()[0]
            )
            if estimate_count == 0:
                blockers.append(
                    {"reason": "completed_analysis_missing_estimate_artifact", "analysis": slug}
                )
            observation_count = int(
                connection.execute(
                    "SELECT COUNT(*) FROM project_observations WHERE analysis_id = ?",
                    (analysis_id,),
                ).fetchone()[0]
            )
            if observation_count == 0:
                blockers.append(
                    {"reason": "completed_analysis_missing_project_observation", "analysis": slug}
                )

            if run["analysis_mode"] != "confirmatory":
                continue
            freeze_commit = str(run["freeze_commit"] or "").strip()
            if not freeze_commit:
                blockers.append(
                    {"reason": "confirmatory_analysis_missing_freeze_commit", "analysis": slug}
                )
                continue
            commit_exists = _git(project_root, "cat-file", "-e", f"{freeze_commit}^{{commit}}")
            if commit_exists.returncode != 0:
                blockers.append(
                    {
                        "reason": "analysis_freeze_commit_missing",
                        "analysis": slug,
                        "freeze_commit": freeze_commit,
                    }
                )
                continue
            ancestor = _git(project_root, "merge-base", "--is-ancestor", freeze_commit, "HEAD")
            if ancestor.returncode != 0:
                blockers.append(
                    {
                        "reason": "analysis_freeze_commit_not_ancestor",
                        "analysis": slug,
                        "freeze_commit": freeze_commit,
                    }
                )

            freeze_required_paths = [str(run["analysis_path"]), str(run["code_path"])]
            for dataset in input_rows:
                freeze_required_paths.append(str(dataset["provenance_path"]))
                freeze_required_paths.extend(
                    str(row["location"])
                    for row in connection.execute(
                        """
                        SELECT location FROM dataset_artifacts
                        WHERE dataset_id = ? AND storage_kind = 'local' AND git_tracking = 'required'
                        ORDER BY id
                        """,
                        (dataset["id"],),
                    )
                )
            missing_at_freeze = sorted(
                path
                for path in dict.fromkeys(freeze_required_paths)
                if not _git_commit_has_path(project_root, freeze_commit, path)
            )
            if missing_at_freeze:
                blockers.append(
                    {
                        "reason": "analysis_plan_or_input_missing_at_freeze",
                        "analysis": slug,
                        "freeze_commit": freeze_commit,
                        "paths": missing_at_freeze,
                    }
                )

            result_paths = [
                str(row["path"])
                for row in connection.execute(
                    "SELECT path FROM analysis_artifacts WHERE analysis_id = ? ORDER BY id",
                    (analysis_id,),
                )
            ]
            result_present_at_freeze = sorted(
                path for path in result_paths if _git_commit_has_path(project_root, freeze_commit, path)
            )
            if result_present_at_freeze:
                blockers.append(
                    {
                        "reason": "analysis_result_artifact_present_at_freeze",
                        "analysis": slug,
                        "freeze_commit": freeze_commit,
                        "paths": result_present_at_freeze,
                    }
                )

    return {
        "ready": not blockers,
        "blockers": blockers,
        "dataset_count": dataset_count,
        "analysis_count": analysis_count,
        "completed_analysis_count": completed_analysis_count,
    }


def validate_completion(project_root: Path) -> dict[str, Any]:
    base = validate(project_root)
    errors = list(base["errors"])
    warnings = list(base["warnings"])

    readiness = discovery_readiness(project_root)
    if readiness["has_discovery"] and not readiness["ready_for_saturation"]:
        reasons = ", ".join(
            str(blocker.get("reason", "unknown")) for blocker in readiness["blockers"]
        )
        errors.append(
            "Discovery Candidate 队列尚未闭合，不能作为完成状态或声称 practical conceptual saturation："
            + reasons
        )

    literature = literature_completion_readiness(project_root, readiness)
    for blocker in literature["blockers"]:
        reason = str(blocker.get("reason", "unknown"))
        if reason == "relevant_acquired_not_fully_reviewed":
            errors.append(
                f"相关已获取论文 {blocker.get('paper_id')} 尚未完成 Reconstruction + Critical Audit。"
            )
        elif reason == "core_acquired_not_deep_extraction":
            errors.append(
                f"core + acquired 论文 {blocker.get('paper_id')} 未完成 DEEP_EXTRACTION Reconstruction。"
            )
        elif reason == "acquired_candidate_missing_main_text_access_attempt":
            errors.append(
                f"相关已获取 Candidate {blocker.get('candidate_id')} 缺少可审计的正文获取记录。"
            )
        elif reason == "acquired_main_text_access_basis_unverified":
            errors.append(
                f"相关已获取 Candidate {blocker.get('candidate_id')} 的正文来源依据未核验；"
                "来源不明的网络镜像不能闭合为正式全文。"
            )
        elif reason == "acquired_main_text_access_basis_detail_missing":
            errors.append(
                f"相关已获取 Candidate {blocker.get('candidate_id')} 的正文获取记录缺少来源依据说明。"
            )
        elif reason == "cross_paper_scientific_relation_missing":
            errors.append(
                "主题型 Literature Discovery 已有多篇完成审阅的论文，但 canonical relation graph "
                "缺少跨论文 scientific relation；SHARES_*/CITES 不能替代 Evidence Synthesis 关系。"
            )
        elif reason == "database_missing":
            errors.append("research.sqlite 不存在；不能完成 Literature completion gate。")

    downstream = downstream_completion_readiness(project_root)
    for blocker in downstream["blockers"]:
        reason = str(blocker.get("reason", "unknown"))
        if reason == "tracked_downstream_artifacts_unregistered":
            errors.append(
                "data/analysis 下存在已被 Git 跟踪但未登记到 research.sqlite 的科研 artifact："
                + ", ".join(str(path) for path in blocker.get("paths", []))
            )
        elif reason == "data_assets_present_without_dataset_record":
            errors.append("项目存在 data/ 科研资产，但 research.sqlite 尚未登记 Dataset。")
        elif reason == "analysis_assets_present_without_analysis_record":
            errors.append("项目存在 analysis/ 科研资产，但 research.sqlite 尚未登记 Analysis Run。")
        elif reason == "completed_analysis_missing_dataset_input":
            errors.append(f"已完成 Analysis {blocker.get('analysis')} 没有关联输入 Dataset。")
        elif reason == "completed_analysis_missing_estimate_artifact":
            errors.append(f"已完成 Analysis {blocker.get('analysis')} 没有登记主要 estimate artifact。")
        elif reason == "completed_analysis_missing_project_observation":
            errors.append(f"已完成 Analysis {blocker.get('analysis')} 没有登记项目自身 Observation。")
        elif reason == "confirmatory_analysis_missing_freeze_commit":
            errors.append(f"确认性 Analysis {blocker.get('analysis')} 缺少结果可见前 freeze commit。")
        elif reason == "analysis_freeze_commit_missing":
            errors.append(
                f"Analysis {blocker.get('analysis')} 记录的 freeze commit 不存在：{blocker.get('freeze_commit')}。"
            )
        elif reason == "analysis_freeze_commit_not_ancestor":
            errors.append(
                f"Analysis {blocker.get('analysis')} 的 freeze commit 不是当前 HEAD 的祖先：{blocker.get('freeze_commit')}。"
            )
        elif reason == "analysis_plan_or_input_missing_at_freeze":
            errors.append(
                f"Analysis {blocker.get('analysis')} 的 freeze commit 未冻结全部主要计划/代码/输入："
                + ", ".join(str(path) for path in blocker.get("paths", []))
            )
        elif reason == "analysis_result_artifact_present_at_freeze":
            errors.append(
                f"Analysis {blocker.get('analysis')} 的结果 artifact 已存在于所声明的 pre-result freeze："
                + ", ".join(str(path) for path in blocker.get("paths", []))
            )
        elif reason == "downstream_schema_missing":
            errors.append(
                "下游科研 provenance schema 尚未迁移完成："
                + ", ".join(str(name) for name in blocker.get("tables", []))
            )

    academic_language = academic_language_readiness(project_root)
    for blocker in academic_language["blockers"]:
        errors.append(
            f"中文科研项目的人类可读科研文本存在大段英文叙述：{blocker.get('path')} "
            f"第 {blocker.get('paragraph')} 段。应改为规范中文学术表述；英文仅作为标准术语首次出现时的括注或必要书目信息。"
        )

    git_info: dict[str, Any] = {
        "repository_root": None,
        "head": None,
        "canonical_paths": [],
        "dirty_canonical_paths": [],
    }
    top = _git(project_root, "rev-parse", "--show-toplevel")
    if top.returncode != 0:
        errors.append("科研项目尚不是 Git repository；不能完成科研 provenance gate。")
    else:
        repo_root = Path(top.stdout.strip()).resolve()
        git_info["repository_root"] = str(repo_root)
        if repo_root != project_root.resolve():
            errors.append(
                f"科研项目根目录不是独立 Git repository top-level：{repo_root}。"
            )

        head = _git(project_root, "rev-parse", "--verify", "HEAD")
        if head.returncode != 0:
            errors.append("科研项目尚无任何 Git commit；研究状态没有形成版本历史。")
        else:
            git_info["head"] = head.stdout.strip()

        canonical_paths = _canonical_paths(project_root)
        git_info["canonical_paths"] = canonical_paths
        for path in canonical_paths:
            tracked = _git(project_root, "ls-files", "--error-unmatch", "--", path)
            if tracked.returncode != 0:
                errors.append(f"canonical research artifact 尚未被 Git 跟踪：{path}")

        if canonical_paths:
            status = _git(
                project_root,
                "status",
                "--porcelain",
                "--untracked-files=all",
                "--",
                *canonical_paths,
            )
            dirty = [line for line in status.stdout.splitlines() if line.strip()]
            git_info["dirty_canonical_paths"] = dirty
            if dirty:
                errors.append("canonical research artifacts 仍有未提交修改：" + " | ".join(dirty))

    return {
        "ok": not errors,
        "completion": True,
        "database": base["database"],
        "errors": errors,
        "warnings": warnings,
        "discovery": readiness,
        "literature": literature,
        "downstream": downstream,
        "academic_language": academic_language,
        "git": git_info,
    }
