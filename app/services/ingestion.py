"""Pandas-based CSV/JSON ingestion and schema validation for transactions."""

import math
from io import BytesIO
from typing import Any, Dict, List, Optional, Union

import pandas as pd

from app.config import FX_RATES_TO_USD

REQUIRED_FIELDS = [
    "transactionId",
    "transactionDate",
    "transactionType",
    "amount",
    "currency",
    "senderName",
    "senderCountry",
    "receiverName",
    "receiverCountry",
]

OPTIONAL_FIELDS = [
    "senderDOB",
    "senderPlaceOfBirth",
    "senderNationality",
    "senderAccount",
    "receiverDOB",
    "receiverPlaceOfBirth",
    "receiverNationality",
    "receiverAccount",
]

ALLOWED_FIELDS = set(REQUIRED_FIELDS + OPTIONAL_FIELDS)


class IngestionError(ValueError):
    """Raised when ingested data fails schema or content validation."""

    pass


class IngestionService:
    """Load, clean and validate transaction records from CSV or JSON sources."""

    @classmethod
    def from_csv(cls, file_storage) -> List[Dict[str, Any]]:
        """Read and validate a CSV upload (Flask FileStorage or path)."""
        df = cls._read_dataframe(file_storage)
        records = cls._dataframe_to_records(df)
        return cls.from_records(records)

    @classmethod
    def from_csv_path(cls, path: str) -> List[Dict[str, Any]]:
        """Read and validate a CSV file from disk."""
        df = pd.read_csv(path, dtype=str, keep_default_na=False)
        records = cls._dataframe_to_records(df)
        return cls.from_records(records)

    @classmethod
    def from_records(cls, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate and clean a list of transaction dictionaries."""
        if not isinstance(records, list):
            raise IngestionError("Request body must be a list of transactions")
        if not records:
            raise IngestionError("No transaction records provided")

        errors: List[str] = []
        cleaned: List[Dict[str, Any]] = []
        for index, record in enumerate(records):
            record_errors = cls.validate_record(record)
            if record_errors:
                errors.append(f"Row {index + 1}: " + "; ".join(record_errors))
            else:
                cleaned.append(cls.clean_record(record))

        if errors:
            raise IngestionError("Validation failed:\n" + "\n".join(errors))

        return cleaned

    @classmethod
    def validate_records(cls, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Return a validation summary without raising."""
        summary = {"total": len(records), "valid": 0, "invalid": 0, "errors": []}
        for index, record in enumerate(records):
            record_errors = cls.validate_record(record)
            if record_errors:
                summary["invalid"] += 1
                summary["errors"].append(
                    {"row": index + 1, "errors": record_errors}
                )
            else:
                summary["valid"] += 1
        return summary

    @classmethod
    def validate_record(cls, record: Dict[str, Any]) -> List[str]:
        """Validate a single record. Returns a list of human-readable errors."""
        errors: List[str] = []
        if not isinstance(record, dict):
            errors.append("Record is not an object")
            return errors

        missing = [field for field in REQUIRED_FIELDS if field not in record]
        if missing:
            errors.append(f"Missing required fields: {', '.join(missing)}")

        for field in REQUIRED_FIELDS:
            if field in record and record[field] in (None, ""):
                errors.append(f"{field} is required")

        if "amount" in record and record["amount"] not in (None, ""):
            try:
                amount = float(record["amount"])
                if not math.isfinite(amount) or amount < 0:
                    errors.append("amount must be a non-negative finite number")
            except (TypeError, ValueError):
                errors.append("amount must be a number")

        if "currency" in record and record["currency"] not in (None, ""):
            currency = str(record["currency"]).upper()
            if currency not in FX_RATES_TO_USD:
                errors.append(
                    f"currency '{currency}' is not supported (use one of: "
                    f"{', '.join(sorted(FX_RATES_TO_USD))})"
                )

        unknown = [key for key in record if key not in ALLOWED_FIELDS]
        if unknown:
            errors.append(f"Unknown fields: {', '.join(unknown)}")

        return errors

    @classmethod
    def clean_record(cls, record: Dict[str, Any]) -> Dict[str, Any]:
        """Return a JSON-safe record with known fields and cleaned values."""
        cleaned: Dict[str, Any] = {}
        for field in ALLOWED_FIELDS:
            value = record.get(field)
            if isinstance(value, float) and value != value:  # NaN from pandas
                value = None
            if value is None:
                cleaned[field] = None
                continue

            if field == "amount":
                try:
                    cleaned[field] = float(value)
                except (TypeError, ValueError):
                    cleaned[field] = None
            elif field == "currency":
                cleaned[field] = str(value).upper().strip()
            else:
                text = str(value).strip()
                cleaned[field] = text if text else None

        return cleaned

    @classmethod
    def _read_dataframe(cls, source: Union[Any, str]) -> pd.DataFrame:
        try:
            if isinstance(source, str):
                return pd.read_csv(source, dtype=str, keep_default_na=False)
            content = source.read()
            if isinstance(content, str):
                content = content.encode("utf-8")
            return pd.read_csv(BytesIO(content), dtype=str, keep_default_na=False)
        except pd.errors.EmptyDataError as exc:
            raise IngestionError("CSV file is empty") from exc
        except pd.errors.ParserError as exc:
            raise IngestionError(f"Could not parse CSV: {exc}") from exc
        except Exception as exc:
            raise IngestionError(f"Could not read CSV: {exc}") from exc

    @classmethod
    def _dataframe_to_records(cls, df: pd.DataFrame) -> List[Dict[str, Any]]:
        df.columns = [str(c).strip() for c in df.columns]
        return df.where(pd.notnull(df), None).to_dict(orient="records")
