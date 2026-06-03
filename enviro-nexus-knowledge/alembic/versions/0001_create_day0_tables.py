"""Create Day 0 knowledge foundation tables."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0001_create_day0_tables"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "source_documents",
        sa.Column("doc_id", sa.Text(), primary_key=True),
        sa.Column("source_type", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("standard_code", sa.Text(), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("checksum_sha256", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "status IN ('active', 'draft', 'superseded')",
            name="ck_source_documents_status",
        ),
    )

    op.create_table(
        "method_cards",
        sa.Column("card_id", sa.Text(), primary_key=True),
        sa.Column("schema_version", sa.Text(), nullable=False),
        sa.Column("card_version", sa.Integer(), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("factor", sa.Text(), nullable=False),
        sa.Column("standard_code", sa.Text(), nullable=False),
        sa.Column("standard_name", sa.Text(), nullable=False),
        sa.Column("method_name", sa.Text(), nullable=False),
        sa.Column("review_status", sa.Text(), nullable=False),
        sa.Column("answer_visibility", sa.Text(), nullable=False),
        sa.Column("card_json", postgresql.JSONB(), nullable=False),
        sa.Column("source_doc_id", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "review_status IN ('draft', 'reviewing', 'approved', 'rejected')",
            name="ck_method_cards_review_status",
        ),
        sa.CheckConstraint(
            "answer_visibility IN ('enabled', 'disabled')",
            name="ck_method_cards_answer_visibility",
        ),
        sa.ForeignKeyConstraint(["source_doc_id"], ["source_documents.doc_id"]),
    )
    op.create_index("idx_method_cards_factor", "method_cards", ["factor"])
    op.create_index("idx_method_cards_standard_code", "method_cards", ["standard_code"])
    op.create_index("idx_method_cards_category", "method_cards", ["category"])
    op.create_index(
        "idx_method_cards_review_visibility",
        "method_cards",
        ["review_status", "answer_visibility"],
    )
    op.create_index(
        "idx_method_cards_card_json_gin",
        "method_cards",
        ["card_json"],
        postgresql_using="gin",
    )

    op.create_table(
        "factor_aliases",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("alias", sa.Text(), nullable=False),
        sa.Column("normalized_alias", sa.Text(), nullable=False),
        sa.Column("factor", sa.Text(), nullable=False),
        sa.Column("card_id", sa.Text(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default=sa.text("100")),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["card_id"], ["method_cards.card_id"]),
        sa.UniqueConstraint(
            "normalized_alias",
            "card_id",
            name="uq_factor_aliases_normalized_alias_card_id",
        ),
    )
    op.create_index("idx_factor_aliases_normalized_alias", "factor_aliases", ["normalized_alias"])
    op.create_index("idx_factor_aliases_card_id", "factor_aliases", ["card_id"])
    op.create_index("idx_factor_aliases_enabled_priority", "factor_aliases", ["enabled", "priority"])

    op.create_table(
        "knowledge_import_batches",
        sa.Column("batch_id", sa.Text(), primary_key=True),
        sa.Column("import_mode", sa.Text(), nullable=False),
        sa.Column("seed_path", sa.Text(), nullable=False),
        sa.Column("cards_count", sa.Integer(), nullable=False),
        sa.Column("aliases_count", sa.Integer(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("knowledge_import_batches")
    op.drop_index("idx_factor_aliases_enabled_priority", table_name="factor_aliases")
    op.drop_index("idx_factor_aliases_card_id", table_name="factor_aliases")
    op.drop_index("idx_factor_aliases_normalized_alias", table_name="factor_aliases")
    op.drop_table("factor_aliases")
    op.drop_index("idx_method_cards_card_json_gin", table_name="method_cards")
    op.drop_index("idx_method_cards_review_visibility", table_name="method_cards")
    op.drop_index("idx_method_cards_category", table_name="method_cards")
    op.drop_index("idx_method_cards_standard_code", table_name="method_cards")
    op.drop_index("idx_method_cards_factor", table_name="method_cards")
    op.drop_table("method_cards")
    op.drop_table("source_documents")
