"""JSON-file seller repository."""

import json
from pathlib import Path

from pydantic import ValidationError

from app.repositories.seller_repository import SellerDataError
from app.schemas.context import SellerContext


class JsonSellerRepository:
    """Load seller contexts from JSON files in a directory.

    Records are parsed and validated on first use, then cached on this
    instance. An unknown seller id returns None. A missing directory,
    malformed file, or invalid record raises SellerDataError instead of
    being skipped.
    """

    def __init__(self, data_dir: Path) -> None:
        self._data_dir = Path(data_dir)
        self._cache: dict[str, SellerContext] | None = None

    def get_by_id(self, seller_id: str) -> SellerContext | None:
        return self._records().get(seller_id)

    def list_ids(self) -> list[str]:
        return sorted(self._records())

    def _records(self) -> dict[str, SellerContext]:
        if self._cache is None:
            self._cache = self._read_directory()
        return self._cache

    def _read_directory(self) -> dict[str, SellerContext]:
        if not self._data_dir.is_dir():
            raise SellerDataError(
                f"Seller data directory does not exist: {self._data_dir}"
            )

        records: dict[str, SellerContext] = {}
        for path in sorted(self._data_dir.glob("*.json")):
            context = _read_seller_file(path)
            seller_id = context.seller.seller_id
            if seller_id in records:
                raise SellerDataError(
                    f"Duplicate seller_id '{seller_id}' found in {path.name}."
                )
            records[seller_id] = context
        return records


def _read_seller_file(path: Path) -> SellerContext:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SellerDataError(
            f"Unable to read seller file {path.name}: {exc.strerror}"
        ) from exc

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SellerDataError(
            f"Malformed JSON in {path.name}: {exc.msg} (line {exc.lineno})."
        ) from exc

    if not isinstance(payload, dict):
        raise SellerDataError(f"Seller file {path.name} must contain a JSON object.")

    try:
        return SellerContext.model_validate(payload)
    except ValidationError as exc:
        details = "; ".join(
            f"{_error_location(error)}: {error['msg']}" for error in exc.errors()
        )
        raise SellerDataError(f"Invalid seller record in {path.name}: {details}") from exc


def _error_location(error: dict[str, object]) -> str:
    location = error.get("loc")
    if not isinstance(location, tuple) or not location:
        return "record"
    return ".".join(str(part) for part in location)
