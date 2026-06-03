from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from app.core.factor_matcher import AliasCandidate
from app.db.models import FactorAlias, KnowledgeImportBatch, MethodCard as MethodCardRow, SourceDocument
from app.schemas.method_card import MethodCard


def upsert_source_document(session: Session, source: dict[str, Any]) -> None:
    table = SourceDocument.__table__
    values = {
        "doc_id": source["doc_id"],
        "source_type": source["source_type"],
        "title": source["title"],
        "standard_code": source["standard_code"],
        "file_path": source["file_path"],
        "status": source["status"],
        "checksum_sha256": source.get("checksum_sha256"),
        "metadata": source.get("metadata", {}),
        "updated_at": func.now(),
    }
    stmt = pg_insert(table).values(values)
    excluded = stmt.excluded
    session.execute(
        stmt.on_conflict_do_update(
            index_elements=["doc_id"],
            set_={
                "source_type": excluded.source_type,
                "title": excluded.title,
                "standard_code": excluded.standard_code,
                "file_path": excluded.file_path,
                "status": excluded.status,
                "checksum_sha256": excluded.checksum_sha256,
                "metadata": excluded["metadata"],
                "updated_at": func.now(),
            },
        )
    )


def upsert_method_card(session: Session, card: MethodCard) -> None:
    table = MethodCardRow.__table__
    values = {
        "card_id": card.card_id,
        "schema_version": card.schema_version,
        "card_version": card.card_version,
        "category": card.identity.category,
        "factor": card.identity.factor,
        "standard_code": card.identity.standard_code,
        "standard_name": card.identity.standard_name,
        "method_name": card.identity.method_name,
        "review_status": card.governance.review_status,
        "answer_visibility": card.governance.answer_visibility,
        "card_json": card.model_dump(mode="json"),
        "source_doc_id": card.source_document.doc_id,
        "updated_at": func.now(),
    }
    stmt = pg_insert(table).values(values)
    excluded = stmt.excluded
    session.execute(
        stmt.on_conflict_do_update(
            index_elements=["card_id"],
            set_={
                "schema_version": excluded.schema_version,
                "card_version": excluded.card_version,
                "category": excluded.category,
                "factor": excluded.factor,
                "standard_code": excluded.standard_code,
                "standard_name": excluded.standard_name,
                "method_name": excluded.method_name,
                "review_status": excluded.review_status,
                "answer_visibility": excluded.answer_visibility,
                "card_json": excluded.card_json,
                "source_doc_id": excluded.source_doc_id,
                "updated_at": func.now(),
            },
        )
    )


def upsert_factor_alias(session: Session, alias: dict[str, Any]) -> None:
    table = FactorAlias.__table__
    values = {
        "alias": alias["alias"],
        "normalized_alias": alias["normalized_alias"],
        "factor": alias["factor"],
        "card_id": alias["card_id"],
        "priority": alias.get("priority", 100),
        "enabled": alias.get("enabled", True),
        "updated_at": func.now(),
    }
    stmt = pg_insert(table).values(values)
    excluded = stmt.excluded
    session.execute(
        stmt.on_conflict_do_update(
            index_elements=["normalized_alias", "card_id"],
            set_={
                "alias": excluded.alias,
                "factor": excluded.factor,
                "priority": excluded.priority,
                "enabled": excluded.enabled,
                "updated_at": func.now(),
            },
        )
    )


def insert_import_batch(
    session: Session,
    *,
    batch_id: str,
    import_mode: str,
    seed_path: str,
    cards_count: int,
    aliases_count: int,
    status: str,
    message: str | None = None,
) -> None:
    session.add(
        KnowledgeImportBatch(
            batch_id=batch_id,
            import_mode=import_mode,
            seed_path=seed_path,
            cards_count=cards_count,
            aliases_count=aliases_count,
            status=status,
            started_at=datetime.now(timezone.utc),
            finished_at=datetime.now(timezone.utc),
            message=message,
        )
    )


def list_alias_candidates(session: Session) -> list[AliasCandidate]:
    rows = session.execute(
        select(
            FactorAlias.alias,
            FactorAlias.normalized_alias,
            FactorAlias.factor,
            FactorAlias.card_id,
            FactorAlias.priority,
            FactorAlias.enabled,
        )
        .join(MethodCardRow, FactorAlias.card_id == MethodCardRow.card_id)
        .where(FactorAlias.enabled.is_(True))
        .where(MethodCardRow.review_status == "approved")
        .where(MethodCardRow.answer_visibility == "enabled")
    ).all()
    return [
        AliasCandidate(
            alias=row.alias,
            normalized_alias=row.normalized_alias,
            factor=row.factor,
            card_id=row.card_id,
            priority=row.priority,
            enabled=row.enabled,
        )
        for row in rows
    ]


def get_enabled_method_card_json(session: Session, card_id: str) -> dict[str, Any] | None:
    return session.execute(
        select(MethodCardRow.card_json)
        .where(MethodCardRow.card_id == card_id)
        .where(MethodCardRow.review_status == "approved")
        .where(MethodCardRow.answer_visibility == "enabled")
    ).scalar_one_or_none()


def list_public_method_card_jsons(session: Session) -> list[dict[str, Any]]:
    rows = session.execute(
        select(MethodCardRow.card_json)
        .where(MethodCardRow.review_status == "approved")
        .where(MethodCardRow.answer_visibility == "enabled")
        .order_by(
            MethodCardRow.category.asc(),
            MethodCardRow.factor.asc(),
            MethodCardRow.standard_code.asc(),
            MethodCardRow.card_id.asc(),
        )
    ).all()
    return [row.card_json for row in rows]


def get_public_method_card_json(session: Session, card_id: str) -> dict[str, Any] | None:
    return session.execute(
        select(MethodCardRow.card_json)
        .where(MethodCardRow.card_id == card_id)
        .where(MethodCardRow.review_status == "approved")
        .where(MethodCardRow.answer_visibility == "enabled")
    ).scalar_one_or_none()
