import json
from pathlib import Path

from sqlalchemy import text

from app.db.session import SessionLocal
from app.services.import_service import import_seed


def clear_business_tables() -> None:
    with SessionLocal() as session:
        session.execute(text("DELETE FROM factor_aliases"))
        session.execute(text("DELETE FROM method_cards"))
        session.execute(text("DELETE FROM source_documents"))
        session.execute(text("DELETE FROM knowledge_import_batches"))
        session.commit()


def scalar(sql: str) -> int:
    with SessionLocal() as session:
        return int(session.execute(text(sql)).scalar_one())


def scalar_text(sql: str) -> str:
    with SessionLocal() as session:
        return str(session.execute(text(sql)).scalar_one())


def test_import_seed_upserts_day1_5_method_cards_without_duplicates():
    clear_business_tables()

    first = import_seed(Path("data/seed"), mode="upsert")
    second = import_seed(Path("data/seed"), mode="upsert")

    assert first.status == "success"
    assert second.status == "success"
    assert first.cards_count == 5
    assert second.cards_count == 5
    assert first.aliases_count == 21
    assert second.aliases_count == 21
    assert scalar("SELECT count(*) FROM source_documents") == 5
    assert scalar("SELECT count(*) FROM method_cards") == 5
    assert scalar("SELECT count(*) FROM factor_aliases") == 21
    assert scalar("SELECT count(*) FROM knowledge_import_batches WHERE status = 'success'") == 2


def test_import_seed_treats_source_file_path_as_metadata_only():
    clear_business_tables()

    result = import_seed(Path("data/seed"), mode="upsert")
    stored_file_path = scalar_text("SELECT file_path FROM source_documents WHERE doc_id = 'doc_hj1147_2020'")
    metadata = json.loads(
        scalar_text("SELECT metadata::text FROM source_documents WHERE doc_id = 'doc_hj1147_2020'")
    )

    assert result.status == "success"
    assert stored_file_path == "files/poc-files/水质 pH的测定 电极法 HJ 1147-2020.md"
    assert metadata["derived_from"] == stored_file_path
    assert metadata["source_format"] == "markdown"
    assert metadata["manual_extract_status"] == "completed"
    assert metadata["needs_pdf_check"] is True
