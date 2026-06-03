from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class SourceDocument(Base):
    __tablename__ = "source_documents"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'draft', 'superseded')",
            name="ck_source_documents_status",
        ),
    )

    doc_id: Mapped[str] = mapped_column(Text, primary_key=True)
    source_type: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    standard_code: Mapped[str] = mapped_column(Text, nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    checksum_sha256: Mapped[str | None] = mapped_column(Text)
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class MethodCard(Base):
    __tablename__ = "method_cards"
    __table_args__ = (
        CheckConstraint(
            "review_status IN ('draft', 'reviewing', 'approved', 'rejected')",
            name="ck_method_cards_review_status",
        ),
        CheckConstraint(
            "answer_visibility IN ('enabled', 'disabled')",
            name="ck_method_cards_answer_visibility",
        ),
        Index("idx_method_cards_factor", "factor"),
        Index("idx_method_cards_standard_code", "standard_code"),
        Index("idx_method_cards_category", "category"),
        Index("idx_method_cards_review_visibility", "review_status", "answer_visibility"),
        Index("idx_method_cards_card_json_gin", "card_json", postgresql_using="gin"),
    )

    card_id: Mapped[str] = mapped_column(Text, primary_key=True)
    schema_version: Mapped[str] = mapped_column(Text, nullable=False)
    card_version: Mapped[int] = mapped_column(Integer, nullable=False)
    category: Mapped[str] = mapped_column(Text, nullable=False)
    factor: Mapped[str] = mapped_column(Text, nullable=False)
    standard_code: Mapped[str] = mapped_column(Text, nullable=False)
    standard_name: Mapped[str] = mapped_column(Text, nullable=False)
    method_name: Mapped[str] = mapped_column(Text, nullable=False)
    review_status: Mapped[str] = mapped_column(Text, nullable=False)
    answer_visibility: Mapped[str] = mapped_column(Text, nullable=False)
    card_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    source_doc_id: Mapped[str] = mapped_column(Text, ForeignKey("source_documents.doc_id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class FactorAlias(Base):
    __tablename__ = "factor_aliases"
    __table_args__ = (
        UniqueConstraint("normalized_alias", "card_id", name="uq_factor_aliases_normalized_alias_card_id"),
        Index("idx_factor_aliases_normalized_alias", "normalized_alias"),
        Index("idx_factor_aliases_card_id", "card_id"),
        Index("idx_factor_aliases_enabled_priority", "enabled", "priority"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    alias: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_alias: Mapped[str] = mapped_column(Text, nullable=False)
    factor: Mapped[str] = mapped_column(Text, nullable=False)
    card_id: Mapped[str] = mapped_column(Text, ForeignKey("method_cards.card_id"), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, server_default="100")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class KnowledgeImportBatch(Base):
    __tablename__ = "knowledge_import_batches"

    batch_id: Mapped[str] = mapped_column(Text, primary_key=True)
    import_mode: Mapped[str] = mapped_column(Text, nullable=False)
    seed_path: Mapped[str] = mapped_column(Text, nullable=False)
    cards_count: Mapped[int] = mapped_column(Integer, nullable=False)
    aliases_count: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    message: Mapped[str | None] = mapped_column(Text)
