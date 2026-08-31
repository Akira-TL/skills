from __future__ import annotations

from research_db_support.checks import source_locator_is_specific
from research_db_support.schema import ENTITY_TABLES, entity_exists


def check_knowledge(connection, errors: list[str]) -> None:
    for row in connection.execute(
        "SELECT id, subject_type, subject_id, object_type, object_id FROM relations"
    ):
        if row["subject_type"] not in ENTITY_TABLES:
            errors.append(f"relation {row['id']} 使用未知 subject_type={row['subject_type']!r}。")
        elif not entity_exists(connection, row["subject_type"], row["subject_id"]):
            errors.append(f"relation {row['id']} 的 subject 不存在。")
        if row["object_type"] not in ENTITY_TABLES:
            errors.append(f"relation {row['id']} 使用未知 object_type={row['object_type']!r}。")
        elif not entity_exists(connection, row["object_type"], row["object_id"]):
            errors.append(f"relation {row['id']} 的 object 不存在。")

    for row in connection.execute(
        "SELECT id, target_type, target_id FROM issues WHERE target_type IS NOT NULL OR target_id IS NOT NULL"
    ):
        if not row["target_type"] or not row["target_id"]:
            errors.append(f"issue {row['id']} 的 target_type/target_id 必须同时存在。")
            continue
        if row["target_type"] not in ENTITY_TABLES:
            errors.append(f"issue {row['id']} 使用未知 target_type={row['target_type']!r}。")
        elif not entity_exists(connection, row["target_type"], row["target_id"]):
            errors.append(f"issue {row['id']} 指向不存在的 target。")

    for row in connection.execute(
        "SELECT id, basis, basis_rationale FROM issues ORDER BY id"
    ):
        if not row["basis_rationale"] or not str(row["basis_rationale"]).strip():
            errors.append(
                f"issue {row['id']} 缺少 basis_rationale；无法审计 basis={row['basis']!r} 的证据状态判断。"
            )

    not_reported_without_locator = connection.execute(
        """
        SELECT id FROM issues
        WHERE basis = 'not_reported'
          AND artifact_id IS NULL
          AND (source_locator IS NULL OR trim(source_locator) = '')
        """
    ).fetchall()
    for row in not_reported_without_locator:
        errors.append(f"issue {row['id']} 为 not_reported，但没有 artifact/source locator。")

    for entity, table in (
        ("method", "methods"),
        ("experiment", "experiments"),
        ("observation", "observations"),
        ("claim", "claims"),
        ("issue", "issues"),
        ("lead", "leads"),
    ):
        for row in connection.execute(
            f"SELECT id, paper_id, source_locator FROM {table} ORDER BY id"
        ):
            if not source_locator_is_specific(row["source_locator"]):
                errors.append(
                    f"{entity} {row['id']} ({row['paper_id']}) 的 source_locator="
                    f"{row['source_locator']!r} 过于模糊；需要具体 subsection/page/figure/table/supplement 定位。"
                )
