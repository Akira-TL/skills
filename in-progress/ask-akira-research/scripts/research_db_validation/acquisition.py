from __future__ import annotations

from research_db_ops.acquisition import acquired_main_text_access_blockers, unavailable_candidate_blockers


def check_acquisition(connection, errors: list[str]) -> None:
    for attempt in connection.execute(
        """
        SELECT id, candidate_id, paper_id, target_kind, validity_status,
               superseded_by_attempt_id, supersession_reason
        FROM acquisition_attempts ORDER BY id
        """
    ):
        attempt_id = int(attempt["id"])
        validity = attempt["validity_status"]
        superseded_by = attempt["superseded_by_attempt_id"]
        reason = attempt["supersession_reason"]
        if validity == "active" and (superseded_by is not None or reason):
            errors.append(
                f"acquisition attempt {attempt_id} 仍为 active，但携带 supersession metadata。"
            )
        if validity == "superseded":
            if superseded_by is None or not (reason and str(reason).strip()):
                errors.append(
                    f"acquisition attempt {attempt_id} 标记 superseded，但缺少 superseded_by_attempt_id/supersession_reason。"
                )
                continue
            replacement = connection.execute(
                """
                SELECT id, candidate_id, paper_id, target_kind, validity_status
                FROM acquisition_attempts WHERE id = ?
                """,
                (superseded_by,),
            ).fetchone()
            if replacement is None:
                errors.append(
                    f"acquisition attempt {attempt_id} 指向不存在的 superseding attempt {superseded_by}。"
                )
            else:
                if int(replacement["id"]) == attempt_id:
                    errors.append(
                        f"acquisition attempt {attempt_id} 不能 supersede 自身。"
                    )
                if int(replacement["id"]) <= attempt_id:
                    errors.append(
                        f"acquisition attempt {attempt_id} 的 superseding attempt {superseded_by} 必须是后续新记录。"
                    )
                if replacement["target_kind"] != attempt["target_kind"]:
                    errors.append(
                        f"acquisition attempt {attempt_id} 与 superseding attempt {superseded_by} target_kind 不一致。"
                    )
                if attempt["candidate_id"] is not None and replacement["candidate_id"] != attempt["candidate_id"]:
                    errors.append(
                        f"acquisition attempt {attempt_id} 与 superseding attempt {superseded_by} Candidate 不一致。"
                    )
                if attempt["paper_id"] is not None and replacement["paper_id"] != attempt["paper_id"]:
                    errors.append(
                        f"acquisition attempt {attempt_id} 与 superseding attempt {superseded_by} Paper 不一致。"
                    )

    for row in connection.execute(
        """
        SELECT id, identity_status, relevance_status, exclusion_reason,
               acquisition_status, reading_priority, paper_id, doi, pmid,
               user_access_status, user_access_reason
        FROM candidates ORDER BY id
        """
    ):
        candidate_id = int(row["id"])
        doi = str(row["doi"]).strip().lower() if row["doi"] else None
        pmid = str(row["pmid"]).strip() if row["pmid"] else None
        if row["relevance_status"] == "excluded" and not (
            row["exclusion_reason"] and str(row["exclusion_reason"]).strip()
        ):
            errors.append(
                f"candidate {candidate_id} 标记为 excluded，但缺少 exclusion_reason。"
            )
        if row["user_access_status"] != "not_required" and not (
            row["user_access_reason"] and str(row["user_access_reason"]).strip()
        ):
            errors.append(
                f"candidate {candidate_id} 的 user_access_status={row['user_access_status']}，"
                "但缺少 user_access_reason。"
            )
        if row["acquisition_status"] == "unavailable":
            for blocker in unavailable_candidate_blockers(connection, row):
                errors.append(
                    f"candidate {candidate_id} unavailable provenance 不完整：{blocker['reason']}。"
                )
        if row["acquisition_status"] == "acquired":
            for blocker in acquired_main_text_access_blockers(connection, candidate_id):
                errors.append(
                    f"candidate {candidate_id} acquired provenance 不完整：{blocker['reason']}。"
                )
        if row["acquisition_status"] == "acquired" and not row["paper_id"]:
            errors.append(
                f"candidate {candidate_id} 标记为 acquired，但没有关联 Paper。"
            )
        if row["paper_id"] and row["acquisition_status"] != "acquired":
            errors.append(
                f"candidate {candidate_id} 已关联 {row['paper_id']}，但 acquisition_status 不是 acquired。"
            )
        if row["identity_status"] == "resolved" and not (doi or pmid or row["paper_id"]):
            errors.append(
                f"candidate {candidate_id} 标记为 resolved，但没有 DOI/PMID/Paper identity。"
            )
        if row["identity_status"] == "unresolved" and (doi or pmid or row["paper_id"]):
            errors.append(
                f"candidate {candidate_id} 已有稳定身份，但 identity_status 仍为 unresolved。"
            )
        if row["paper_id"]:
            paper = connection.execute(
                "SELECT doi, pmid FROM papers WHERE id = ?", (row["paper_id"],)
            ).fetchone()
            if paper is not None:
                paper_doi = str(paper["doi"]).strip().lower() if paper["doi"] else None
                paper_pmid = str(paper["pmid"]).strip() if paper["pmid"] else None
                if doi and paper_doi and doi != paper_doi:
                    errors.append(
                        f"candidate {candidate_id} DOI 与关联 Paper {row['paper_id']} 不一致。"
                    )
                if pmid and paper_pmid and pmid != paper_pmid:
                    errors.append(
                        f"candidate {candidate_id} PMID 与关联 Paper {row['paper_id']} 不一致。"
                    )

    for field, expression, where in (
        ("DOI", "lower(doi)", "doi IS NOT NULL AND trim(doi) <> ''"),
        ("PMID", "pmid", "pmid IS NOT NULL AND trim(pmid) <> ''"),
    ):
        duplicates = connection.execute(
            f"SELECT {expression} AS identity, GROUP_CONCAT(id) AS ids "
            f"FROM candidates WHERE {where} GROUP BY {expression} HAVING COUNT(*) > 1"
        ).fetchall()
        for duplicate in duplicates:
            errors.append(
                f"Candidate 存在重复稳定身份 {field}={duplicate['identity']!r}："
                f"{duplicate['ids']}；请使用 merge-candidates 合并。"
            )
