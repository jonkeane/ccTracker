"""Tests for filesystem-backed transaction CSV management."""

from pathlib import Path

import pandas as pd

from benefits.transaction_csv_manager import TransactionCsvManager


class FakeUploadFile:
    """Simple UploadedFile test double."""

    def __init__(self, name, payload):
        self.name = name
        self._payload = payload

    def getvalue(self):
        return self._payload


class TestTransactionCsvManager:
    """Behavior tests for CSV upload/storage manager."""

    def test_validate_uploaded_file_rejects_missing_columns(self):
        manager = TransactionCsvManager()
        payload = b"Transaction Date,Post Date,Amount\n01/01/2026,01/02/2026,-10.00\n"
        upload = FakeUploadFile("bad.csv", payload)

        result = manager.validate_uploaded_file(upload)

        assert result["valid"] is False
        assert "Missing required columns" in result["message"]

    def test_save_uploaded_file_replace_current_overlapping_year(self, tmp_path):
        manager = TransactionCsvManager(base_path=tmp_path)
        current_year = pd.Timestamp.now().year

        root_dir = tmp_path / "transactions" / "hyatt personal"
        root_dir.mkdir(parents=True)
        old_file = root_dir / "legacy.csv"
        old_file.write_text(
            "Transaction Date,Post Date,Type,Amount\n"
            f"01/10/{current_year},01/12/{current_year},Sale,-10.00\n"
        )

        upload = FakeUploadFile(
            "new.csv",
            (
                "Transaction Date,Post Date,Type,Amount\n"
                f"02/10/{current_year},02/12/{current_year},Sale,-20.00\n"
            ).encode("utf-8"),
        )

        saved = manager.save_uploaded_file(
            uploaded_file=upload,
            card_type="personal",
            replace_overlapping_years=True,
        )

        assert Path(saved["path"]).exists()
        assert saved["name"] == "new.csv"
        assert not old_file.exists()

    def test_save_uploaded_file_normalizes_name_without_timestamp(self, tmp_path):
        manager = TransactionCsvManager(base_path=tmp_path)

        upload = FakeUploadFile(
            "2026 report (final)",
            (
                "Transaction Date,Post Date,Type,Amount\n"
                "03/10/2026,03/12/2026,Sale,-20.00\n"
            ).encode("utf-8"),
        )

        saved = manager.save_uploaded_file(
            uploaded_file=upload,
            card_type="personal",
        )

        assert saved["name"] == "2026_report__final_.csv"
        assert Path(saved["path"]).name == "2026_report__final_.csv"

    def test_active_current_year_file_prefers_newest_mtime(self, tmp_path):
        manager = TransactionCsvManager(base_path=tmp_path)
        current_year = pd.Timestamp.now().year

        card_dir = tmp_path / "transactions" / "hyatt business"
        card_dir.mkdir(parents=True)

        older_file = card_dir / "older.csv"
        older_file.write_text(
            "Transaction Date,Post Date,Type,Amount\n"
            f"01/01/{current_year},01/03/{current_year},Sale,-100.00\n"
        )

        newer_file = card_dir / "newer.csv"
        newer_file.write_text(
            "Transaction Date,Post Date,Type,Amount\n"
            f"03/01/{current_year},03/03/{current_year},Sale,-200.00\n"
        )

        older_ts = newer_ts = pd.Timestamp.now().timestamp()
        older_ts -= 100
        Path(older_file).touch()
        Path(newer_file).touch()

        # Force deterministic ordering by modified time.
        import os

        os.utime(older_file, (older_ts, older_ts))
        os.utime(newer_file, (newer_ts, newer_ts))

        active = manager.get_active_current_year_file("business")

        assert active is not None
        assert active["name"] == "newer.csv"


class TestValidateFilenameCardEnding:
    """Tests for filename card-ending validation."""

    ENDINGS = {"personal": ["4100", "1695"], "business": ["1505"]}

    def test_matching_ending_is_valid(self):
        manager = TransactionCsvManager(card_endings=self.ENDINGS)
        result = manager.validate_filename_card_ending("Chase1505_Activity.CSV", "business")
        assert result["valid"] is True

    def test_wrong_ending_is_invalid(self):
        manager = TransactionCsvManager(card_endings=self.ENDINGS)
        result = manager.validate_filename_card_ending("Chase9999_Activity.CSV", "business")
        assert result["valid"] is False
        assert "9999" in result["message"]
        assert "1505" in result["message"]

    def test_no_chase_number_in_filename_is_invalid(self):
        manager = TransactionCsvManager(card_endings=self.ENDINGS)
        result = manager.validate_filename_card_ending("export_transactions.CSV", "personal")
        assert result["valid"] is False
        assert "Chase card number" in result["message"]

    def test_personal_card_multiple_endings_match_first(self):
        manager = TransactionCsvManager(card_endings=self.ENDINGS)
        result = manager.validate_filename_card_ending("Chase4100_export.CSV", "personal")
        assert result["valid"] is True

    def test_personal_card_multiple_endings_match_second(self):
        manager = TransactionCsvManager(card_endings=self.ENDINGS)
        result = manager.validate_filename_card_ending("Chase1695_export.CSV", "personal")
        assert result["valid"] is True

    def test_no_configured_endings_skips_validation(self):
        manager = TransactionCsvManager()  # no card_endings
        result = manager.validate_filename_card_ending("anyfile.CSV", "personal")
        assert result["valid"] is True

    def test_matching_is_case_insensitive(self):
        manager = TransactionCsvManager(card_endings=self.ENDINGS)
        result = manager.validate_filename_card_ending("chase1505_Activity.CSV", "business")
        assert result["valid"] is True
