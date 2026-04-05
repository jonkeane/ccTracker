"""Filesystem-backed manager for Hyatt transaction CSV uploads and inventory."""

from __future__ import annotations

import io
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import pandas as pd


class TransactionCsvManager:
    """Manage transaction CSV files using filesystem conventions and metadata."""

    DEFAULT_CARD_FOLDERS = {
        "personal": Path("transactions/hyatt personal"),
        "business": Path("transactions/hyatt business"),
    }

    REQUIRED_COLUMNS = {
        "Transaction Date",
        "Post Date",
        "Type",
        "Amount",
    }

    def __init__(
        self,
        base_path: str | Path = ".",
        card_folders: Dict[str, str | Path] | None = None,
        card_endings: Dict[str, List[str]] | None = None,
    ):
        self.base_path = Path(base_path)
        configured_folders = card_folders or self.DEFAULT_CARD_FOLDERS
        self.card_folders = {
            card_type: Path(folder)
            for card_type, folder in configured_folders.items()
        }
        self.card_endings: Dict[str, List[str]] = card_endings or {}

    def validate_uploaded_file(self, uploaded_file) -> Dict:
        """Validate uploaded CSV shape and return parsed metadata."""
        payload = uploaded_file.getvalue()
        if not payload:
            return {
                "valid": False,
                "message": "File is empty",
                "row_count": 0,
                "years": [],
            }

        try:
            df = pd.read_csv(io.BytesIO(payload))
        except Exception as exc:
            return {
                "valid": False,
                "message": f"Could not parse CSV: {exc}",
                "row_count": 0,
                "years": [],
            }

        missing_columns = sorted(self.REQUIRED_COLUMNS - set(df.columns))
        if missing_columns:
            missing = ", ".join(missing_columns)
            return {
                "valid": False,
                "message": f"Missing required columns: {missing}",
                "row_count": len(df),
                "years": [],
            }

        years = self._extract_years_from_dataframe(df)
        if not years:
            return {
                "valid": False,
                "message": "Could not determine transaction years from Post Date",
                "row_count": len(df),
                "years": [],
            }

        return {
            "valid": True,
            "message": "Valid CSV",
            "row_count": len(df),
            "years": years,
        }

    def validate_filename_card_ending(self, filename: str, card_type: str) -> Dict:
        """Validate that the filename contains a configured card ending for the given card type."""
        expected = self.card_endings.get(card_type.lower().strip(), [])
        if not expected:
            return {"valid": True, "message": "No card endings configured"}

        match = re.search(r"Chase(\d+)", filename, re.IGNORECASE)
        if not match:
            return {
                "valid": False,
                "message": (
                    f"Filename does not contain a Chase card number. "
                    f"Expected one of: {', '.join(expected)}"
                ),
            }

        found = match.group(1)
        if found not in expected:
            return {
                "valid": False,
                "message": (
                    f"Card ending '{found}' does not match the configured "
                    f"{card_type} endings: {', '.join(expected)}"
                ),
            }

        return {"valid": True, "message": f"Card ending {found} matches configuration"}

    def save_uploaded_file(
        self,
        uploaded_file,
        card_type: str,
        replace_overlapping_years: bool = False,
    ) -> Dict:
        """Save an uploaded file into the card folder."""
        validation = self.validate_uploaded_file(uploaded_file)
        if not validation["valid"]:
            raise ValueError(validation["message"])

        years = validation["years"]
        payload = uploaded_file.getvalue()

        if replace_overlapping_years and years:
            self._delete_overlapping_year_files(card_type, years)

        destination_dir = self._get_card_root(card_type)
        destination_dir.mkdir(parents=True, exist_ok=True)

        filename = self._normalized_upload_name(uploaded_file.name)
        destination_path = destination_dir / filename
        self._atomic_write(destination_path, payload)

        return {
            "path": str(destination_path),
            "name": filename,
            "years": years,
            "row_count": validation["row_count"],
            "size_bytes": destination_path.stat().st_size,
            "modified": datetime.fromtimestamp(destination_path.stat().st_mtime),
        }

    def list_csv_files(self, card_type: str) -> List[Dict]:
        """List CSV inventory for a card type."""
        root = self._get_card_root(card_type)
        if not root.exists():
            return []

        current_year = pd.Timestamp.now().year
        inventory = []

        for file_path in root.rglob("*"):
            if not file_path.is_file() or file_path.suffix.lower() != ".csv":
                continue

            years = self._extract_years_from_file(file_path)
            stat = file_path.stat()

            inventory.append(
                {
                    "name": file_path.name,
                    "relative_path": str(file_path.relative_to(root)),
                    "full_path": str(file_path),
                    "folder": str(file_path.parent.relative_to(self.base_path)),
                    "years": years,
                    "is_current_year": current_year in years,
                    "size_bytes": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime),
                }
            )

        return sorted(inventory, key=lambda item: item["modified"], reverse=True)

    def get_active_current_year_file(self, card_type: str) -> Dict | None:
        """Return the most recently modified file touching the current year."""
        current_candidates = [
            item for item in self.list_csv_files(card_type) if item["is_current_year"]
        ]
        if not current_candidates:
            return None

        return current_candidates[0]

    def delete_csv_file(self, full_path: str | Path) -> None:
        """Delete a CSV file by absolute path."""
        path = Path(full_path)
        if path.exists():
            path.unlink()

    def _get_card_root(self, card_type: str) -> Path:
        normalized = card_type.lower().strip()
        if normalized not in self.card_folders:
            raise ValueError(f"Unsupported card type: {card_type}")
        return self.base_path / self.card_folders[normalized]

    @staticmethod
    def _normalized_upload_name(filename: str) -> str:
        base_name = Path(filename).name
        base_name = re.sub(r"[^A-Za-z0-9._-]", "_", base_name)
        if not base_name.lower().endswith(".csv"):
            base_name = f"{base_name}.csv"
        return base_name

    @staticmethod
    def _atomic_write(destination_path: Path, payload: bytes) -> None:
        temp_path = destination_path.with_suffix(destination_path.suffix + ".tmp")
        with open(temp_path, "wb") as temp_file:
            temp_file.write(payload)
        temp_path.replace(destination_path)

    def _delete_overlapping_year_files(self, card_type: str, years: List[int]) -> None:
        years_set = set(years)
        if not years_set:
            return

        root = self._get_card_root(card_type)
        if not root.exists():
            return

        for item in self.list_csv_files(card_type):
            if years_set.intersection(item["years"]):
                path = Path(item["full_path"])
                if path.exists():
                    path.unlink()

    def _extract_years_from_file(self, file_path: Path) -> List[int]:
        try:
            df = pd.read_csv(file_path, usecols=["Post Date"])
            years = self._extract_years_from_dataframe(df)
            if years:
                return years
        except Exception:
            pass

        return self._extract_years_from_name(file_path.name)

    @staticmethod
    def _extract_years_from_name(filename: str) -> List[int]:
        matches = re.findall(r"\b(20\d{2})\b", filename)
        return sorted({int(match) for match in matches})

    @staticmethod
    def _extract_years_from_dataframe(df: pd.DataFrame) -> List[int]:
        if "Post Date" not in df.columns:
            return []

        parsed = pd.to_datetime(df["Post Date"], format="%m/%d/%Y", errors="coerce")
        if parsed.isna().all():
            parsed = pd.to_datetime(df["Post Date"], errors="coerce")

        years = sorted({int(year) for year in parsed.dt.year.dropna().unique()})
        return years
