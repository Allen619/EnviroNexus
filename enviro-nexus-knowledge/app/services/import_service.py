import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import ValidationError

from app.db.repositories import (
    insert_import_batch,
    upsert_factor_alias,
    upsert_method_card,
    upsert_source_document,
)
from app.db.session import SessionLocal
from app.schemas.method_card import MethodCard


VALID_SOURCE_STATUSES = {"active", "draft", "superseded"}


@dataclass(frozen=True)
class ImportResult:
    status: str
    cards_count: int
    aliases_count: int
    batch_id: str
    message: str | None = None


class SeedImportError(ValueError):
    pass


def import_seed(seed_path: Path, mode: str = "upsert") -> ImportResult:
    if mode != "upsert":
        raise SeedImportError("only upsert import mode is supported")
    if not seed_path.exists() or not seed_path.is_dir():
        raise SeedImportError(f"seed path does not exist: {seed_path}")

    sources = _load_sources(seed_path / "source_documents.json")
    cards = _load_method_cards(seed_path / "method_cards")
    aliases = _load_aliases(seed_path / "factor_aliases.json")
    _validate_cross_references(sources, cards, aliases)

    batch_id = f"seed-{uuid4()}"
    with SessionLocal() as session:
        try:
            for source in sources:
                upsert_source_document(session, source)
            for card in cards:
                upsert_method_card(session, card)
            for alias in aliases:
                upsert_factor_alias(session, alias)
            insert_import_batch(
                session,
                batch_id=batch_id,
                import_mode=mode,
                seed_path=str(seed_path),
                cards_count=len(cards),
                aliases_count=len(aliases),
                status="success",
            )
            session.commit()
        except Exception:
            session.rollback()
            raise

    return ImportResult(
        status="success",
        cards_count=len(cards),
        aliases_count=len(aliases),
        batch_id=batch_id,
    )


def _load_sources(path: Path) -> list[dict[str, Any]]:
    payload = _read_json(path)
    if not isinstance(payload, list) or not payload:
        raise SeedImportError("source_documents.json must be a non-empty list")

    for index, source in enumerate(payload):
        if not isinstance(source, dict):
            raise SeedImportError(f"source_documents[{index}] must be an object")
        _require_non_empty_string(source, "doc_id", f"source_documents[{index}]")
        _require_non_empty_string(source, "source_type", f"source_documents[{index}]")
        _require_non_empty_string(source, "title", f"source_documents[{index}]")
        _require_non_empty_string(source, "standard_code", f"source_documents[{index}]")
        _require_non_empty_string(source, "file_path", f"source_documents[{index}]")
        status = _require_non_empty_string(source, "status", f"source_documents[{index}]")
        if status not in VALID_SOURCE_STATUSES:
            raise SeedImportError(f"source_documents[{index}].status is invalid: {status}")
        if "metadata" in source and not isinstance(source["metadata"], dict):
            raise SeedImportError(f"source_documents[{index}].metadata must be an object")

    return payload


def _load_method_cards(directory: Path) -> list[MethodCard]:
    if not directory.exists() or not directory.is_dir():
        raise SeedImportError(f"method_cards directory does not exist: {directory}")

    paths = sorted(directory.glob("*.json"))
    if not paths:
        raise SeedImportError(f"method_cards directory has no json files: {directory}")

    cards: list[MethodCard] = []
    for path in paths:
        try:
            cards.append(MethodCard.model_validate(_read_json(path)))
        except ValidationError as exc:
            raise SeedImportError(f"MethodCard schema validation failed: {path}: {exc}") from exc
    return cards


def _load_aliases(path: Path) -> list[dict[str, Any]]:
    payload = _read_json(path)
    if not isinstance(payload, list):
        raise SeedImportError("factor_aliases.json must be a list")

    for index, alias in enumerate(payload):
        if not isinstance(alias, dict):
            raise SeedImportError(f"factor_aliases[{index}] must be an object")
        _require_non_empty_string(alias, "alias", f"factor_aliases[{index}]")
        _require_non_empty_string(alias, "normalized_alias", f"factor_aliases[{index}]")
        _require_non_empty_string(alias, "factor", f"factor_aliases[{index}]")
        _require_non_empty_string(alias, "card_id", f"factor_aliases[{index}]")
        if "priority" in alias and not isinstance(alias["priority"], int):
            raise SeedImportError(f"factor_aliases[{index}].priority must be an integer")
        if "enabled" in alias and not isinstance(alias["enabled"], bool):
            raise SeedImportError(f"factor_aliases[{index}].enabled must be a boolean")
    return payload


def _validate_cross_references(
    sources: list[dict[str, Any]],
    cards: list[MethodCard],
    aliases: list[dict[str, Any]],
) -> None:
    sources_by_doc_id = {source["doc_id"]: source for source in sources}
    cards_by_card_id = {card.card_id: card for card in cards}
    if len(sources_by_doc_id) != len(sources):
        raise SeedImportError("source_documents doc_id values must be unique")
    if len(cards_by_card_id) != len(cards):
        raise SeedImportError("method card card_id values must be unique")

    for card in cards:
        source = sources_by_doc_id.get(card.source_document.doc_id)
        if source is None:
            raise SeedImportError(
                f"MethodCard {card.card_id} references unknown source doc_id: "
                f"{card.source_document.doc_id}"
            )
        if source["standard_code"] != card.source_document.standard_code:
            raise SeedImportError(
                f"MethodCard {card.card_id} standard_code does not match source document"
            )

    for alias in aliases:
        if alias["card_id"] not in cards_by_card_id:
            raise SeedImportError(
                f"factor alias {alias['alias']} references unknown card_id: {alias['card_id']}"
            )


def _read_json(path: Path) -> Any:
    if not path.exists():
        raise SeedImportError(f"required seed file does not exist: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SeedImportError(f"invalid json file: {path}: {exc}") from exc


def _require_non_empty_string(payload: dict[str, Any], key: str, location: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise SeedImportError(f"{location}.{key} must be a non-empty string")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Import EnviroNexus knowledge seed data.")
    parser.add_argument("--seed", type=Path, default=Path("data/seed"))
    parser.add_argument("--mode", default="upsert")
    args = parser.parse_args(argv)

    try:
        result = import_seed(args.seed, mode=args.mode)
    except Exception as exc:
        print(f"status=error message={exc}", file=sys.stderr)
        return 1

    print(
        f"status={result.status} cards_count={result.cards_count} "
        f"aliases_count={result.aliases_count} batch_id={result.batch_id}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
