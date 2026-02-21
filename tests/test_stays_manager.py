"""
Tests for StaysManager - hotel stays and GOH nights tracking.

This tests:
- Adding and deleting stays
- Adding and deleting GOH nights
- Date validation
- State persistence
"""

import pytest
import json
from datetime import date
from pathlib import Path
from hyatt.stays_manager import StaysManager


@pytest.fixture
def empty_state_file(tmp_path):
    """Create an empty state file."""
    state_path = tmp_path / "test_stays.json"
    state_path.write_text(json.dumps({"stays": [], "goh_nights": []}))
    return state_path


class TestStaysOperations:
    """Test CRUD operations for stays."""

    def test_add_stay_success(self, empty_state_file):
        """Adding a valid stay should succeed."""
        manager = StaysManager(state_path=empty_state_file)

        result = manager.add_stay(
            "Hyatt Regency Chicago",
            date(2025, 3, 10),
            date(2025, 3, 13)
        )

        assert result is True
        stays = manager.get_stays()
        assert len(stays) == 1
        assert stays[0]['name'] == "Hyatt Regency Chicago"
        assert stays[0]['check_in'] == date(2025, 3, 10)
        assert stays[0]['check_out'] == date(2025, 3, 13)

    def test_add_stay_invalid_dates(self, empty_state_file):
        """Check-out before check-in should fail."""
        manager = StaysManager(state_path=empty_state_file)

        result = manager.add_stay(
            "Hotel",
            date(2025, 3, 13),
            date(2025, 3, 10)  # Before check-in
        )

        assert result is False
        assert len(manager.get_stays()) == 0

    def test_add_stay_same_date(self, empty_state_file):
        """Check-out same as check-in should fail."""
        manager = StaysManager(state_path=empty_state_file)

        result = manager.add_stay(
            "Hotel",
            date(2025, 3, 10),
            date(2025, 3, 10)  # Same date
        )

        assert result is False
        assert len(manager.get_stays()) == 0

    def test_add_stay_empty_name(self, empty_state_file):
        """Empty name should fail."""
        manager = StaysManager(state_path=empty_state_file)

        result = manager.add_stay(
            "",
            date(2025, 3, 10),
            date(2025, 3, 13)
        )

        assert result is False
        assert len(manager.get_stays()) == 0

    def test_add_stay_missing_dates(self, empty_state_file):
        """Missing dates should fail."""
        manager = StaysManager(state_path=empty_state_file)

        result = manager.add_stay("Hotel", None, date(2025, 3, 13))
        assert result is False

        result = manager.add_stay("Hotel", date(2025, 3, 10), None)
        assert result is False

    def test_add_multiple_stays(self, empty_state_file):
        """Adding multiple stays should work."""
        manager = StaysManager(state_path=empty_state_file)

        manager.add_stay("Hotel A", date(2025, 3, 10), date(2025, 3, 13))
        manager.add_stay("Hotel B", date(2025, 4, 15), date(2025, 4, 18))
        manager.add_stay("Hotel C", date(2025, 5, 20), date(2025, 5, 22))

        stays = manager.get_stays()
        assert len(stays) == 3
        assert stays[0]['name'] == "Hotel A"
        assert stays[1]['name'] == "Hotel B"
        assert stays[2]['name'] == "Hotel C"

    def test_delete_stay_success(self, empty_state_file):
        """Deleting a stay by index should work."""
        manager = StaysManager(state_path=empty_state_file)

        manager.add_stay("Hotel A", date(2025, 3, 10), date(2025, 3, 13))
        manager.add_stay("Hotel B", date(2025, 4, 15), date(2025, 4, 18))

        result = manager.delete_stay(0)  # Delete Hotel A

        assert result is True
        stays = manager.get_stays()
        assert len(stays) == 1
        assert stays[0]['name'] == "Hotel B"

    def test_delete_stay_invalid_index(self, empty_state_file):
        """Deleting with invalid index should fail."""
        manager = StaysManager(state_path=empty_state_file)

        manager.add_stay("Hotel A", date(2025, 3, 10), date(2025, 3, 13))

        # Index out of range
        result = manager.delete_stay(5)
        assert result is False

        # Negative index beyond range
        result = manager.delete_stay(-10)
        assert result is False

        # Stay should still exist
        assert len(manager.get_stays()) == 1

    def test_delete_stay_empty_list(self, empty_state_file):
        """Deleting from empty list should fail gracefully."""
        manager = StaysManager(state_path=empty_state_file)

        result = manager.delete_stay(0)

        assert result is False


class TestGOHNightsOperations:
    """Test CRUD operations for GOH nights."""

    def test_add_goh_night_success(self, empty_state_file):
        """Adding a valid GOH night should succeed."""
        manager = StaysManager(state_path=empty_state_file)

        result = manager.add_goh_night("John Smith", date(2025, 4, 15))

        assert result is True
        goh_nights = manager.get_goh_nights()
        assert len(goh_nights) == 1
        assert goh_nights[0]['name'] == "John Smith"
        assert goh_nights[0]['date'] == date(2025, 4, 15)

    def test_add_goh_night_empty_name(self, empty_state_file):
        """Empty name should fail."""
        manager = StaysManager(state_path=empty_state_file)

        result = manager.add_goh_night("", date(2025, 4, 15))

        assert result is False
        assert len(manager.get_goh_nights()) == 0

    def test_add_goh_night_missing_date(self, empty_state_file):
        """Missing date should fail."""
        manager = StaysManager(state_path=empty_state_file)

        result = manager.add_goh_night("John Smith", None)

        assert result is False
        assert len(manager.get_goh_nights()) == 0

    def test_add_multiple_goh_nights(self, empty_state_file):
        """Adding multiple GOH nights should work."""
        manager = StaysManager(state_path=empty_state_file)

        manager.add_goh_night("John Smith", date(2025, 4, 15))
        manager.add_goh_night("Jane Doe", date(2025, 5, 20))
        manager.add_goh_night("Bob Johnson", date(2025, 6, 10))

        goh_nights = manager.get_goh_nights()
        assert len(goh_nights) == 3
        assert goh_nights[0]['name'] == "John Smith"
        assert goh_nights[1]['name'] == "Jane Doe"
        assert goh_nights[2]['name'] == "Bob Johnson"

    def test_delete_goh_night_success(self, empty_state_file):
        """Deleting a GOH night by index should work."""
        manager = StaysManager(state_path=empty_state_file)

        manager.add_goh_night("John Smith", date(2025, 4, 15))
        manager.add_goh_night("Jane Doe", date(2025, 5, 20))

        result = manager.delete_goh_night(0)  # Delete John Smith

        assert result is True
        goh_nights = manager.get_goh_nights()
        assert len(goh_nights) == 1
        assert goh_nights[0]['name'] == "Jane Doe"

    def test_delete_goh_night_invalid_index(self, empty_state_file):
        """Deleting with invalid index should fail."""
        manager = StaysManager(state_path=empty_state_file)

        manager.add_goh_night("John Smith", date(2025, 4, 15))

        result = manager.delete_goh_night(5)
        assert result is False

        # GOH night should still exist
        assert len(manager.get_goh_nights()) == 1

    def test_delete_goh_night_empty_list(self, empty_state_file):
        """Deleting from empty list should fail gracefully."""
        manager = StaysManager(state_path=empty_state_file)

        result = manager.delete_goh_night(0)

        assert result is False


class TestDateConversion:
    """Test date conversion from ISO strings to date objects."""

    def test_get_stays_converts_dates(self, empty_state_file):
        """Stays should be returned with date objects, not strings."""
        manager = StaysManager(state_path=empty_state_file)

        manager.add_stay("Hotel", date(2025, 3, 10), date(2025, 3, 13))
        stays = manager.get_stays()

        assert isinstance(stays[0]['check_in'], date)
        assert isinstance(stays[0]['check_out'], date)
        assert not isinstance(stays[0]['check_in'], str)

    def test_get_goh_nights_converts_dates(self, empty_state_file):
        """GOH nights should be returned with date objects, not strings."""
        manager = StaysManager(state_path=empty_state_file)

        manager.add_goh_night("Guest", date(2025, 4, 15))
        goh_nights = manager.get_goh_nights()

        assert isinstance(goh_nights[0]['date'], date)
        assert not isinstance(goh_nights[0]['date'], str)


class TestStatePersistence:
    """Test state saving and loading."""

    def test_stays_persist_across_instances(self, tmp_path):
        """Stays should persist when saved and reloaded."""
        state_path = tmp_path / "test_stays.json"

        # Create manager and add a stay
        manager1 = StaysManager(state_path=state_path)
        manager1.add_stay("Hotel A", date(2025, 3, 10), date(2025, 3, 13))

        # Create new manager instance
        manager2 = StaysManager(state_path=state_path)
        stays = manager2.get_stays()

        assert len(stays) == 1
        assert stays[0]['name'] == "Hotel A"

    def test_goh_nights_persist_across_instances(self, tmp_path):
        """GOH nights should persist when saved and reloaded."""
        state_path = tmp_path / "test_stays.json"

        # Create manager and add a GOH night
        manager1 = StaysManager(state_path=state_path)
        manager1.add_goh_night("Guest", date(2025, 4, 15))

        # Create new manager instance
        manager2 = StaysManager(state_path=state_path)
        goh_nights = manager2.get_goh_nights()

        assert len(goh_nights) == 1
        assert goh_nights[0]['name'] == "Guest"

    def test_missing_state_file_creates_empty_state(self, tmp_path):
        """Missing state file should create empty state."""
        state_path = tmp_path / "nonexistent.json"

        manager = StaysManager(state_path=state_path)

        assert manager.get_stays() == []
        assert manager.get_goh_nights() == []

    def test_corrupted_state_file_creates_empty_state(self, tmp_path):
        """Corrupted state file should create empty state."""
        state_path = tmp_path / "corrupted.json"
        state_path.write_text("{ invalid json }")

        manager = StaysManager(state_path=state_path)

        assert manager.get_stays() == []
        assert manager.get_goh_nights() == []


class TestMixedOperations:
    """Test combinations of stays and GOH nights."""

    def test_stays_and_goh_nights_coexist(self, empty_state_file):
        """Stays and GOH nights should be independent."""
        manager = StaysManager(state_path=empty_state_file)

        manager.add_stay("Hotel A", date(2025, 3, 10), date(2025, 3, 13))
        manager.add_goh_night("Guest", date(2025, 4, 15))

        assert len(manager.get_stays()) == 1
        assert len(manager.get_goh_nights()) == 1

    def test_delete_stay_does_not_affect_goh_nights(self, empty_state_file):
        """Deleting a stay should not affect GOH nights."""
        manager = StaysManager(state_path=empty_state_file)

        manager.add_stay("Hotel A", date(2025, 3, 10), date(2025, 3, 13))
        manager.add_goh_night("Guest", date(2025, 4, 15))

        manager.delete_stay(0)

        assert len(manager.get_stays()) == 0
        assert len(manager.get_goh_nights()) == 1

    def test_delete_goh_night_does_not_affect_stays(self, empty_state_file):
        """Deleting a GOH night should not affect stays."""
        manager = StaysManager(state_path=empty_state_file)

        manager.add_stay("Hotel A", date(2025, 3, 10), date(2025, 3, 13))
        manager.add_goh_night("Guest", date(2025, 4, 15))

        manager.delete_goh_night(0)

        assert len(manager.get_stays()) == 1
        assert len(manager.get_goh_nights()) == 0


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_very_long_stay(self, empty_state_file):
        """Very long stay should work."""
        manager = StaysManager(state_path=empty_state_file)

        result = manager.add_stay(
            "Long vacation",
            date(2025, 1, 1),
            date(2025, 12, 31)
        )

        assert result is True
        stays = manager.get_stays()
        nights = (stays[0]['check_out'] - stays[0]['check_in']).days
        assert nights == 364

    def test_one_night_stay(self, empty_state_file):
        """One night stay should work."""
        manager = StaysManager(state_path=empty_state_file)

        result = manager.add_stay(
            "Quick trip",
            date(2025, 3, 10),
            date(2025, 3, 11)
        )

        assert result is True
        stays = manager.get_stays()
        nights = (stays[0]['check_out'] - stays[0]['check_in']).days
        assert nights == 1

    def test_special_characters_in_names(self, empty_state_file):
        """Names with special characters should work."""
        manager = StaysManager(state_path=empty_state_file)

        manager.add_stay(
            "Hôtel Château d'Étoile",
            date(2025, 3, 10),
            date(2025, 3, 13)
        )
        manager.add_goh_night("María José García-López", date(2025, 4, 15))

        stays = manager.get_stays()
        goh_nights = manager.get_goh_nights()

        assert stays[0]['name'] == "Hôtel Château d'Étoile"
        assert goh_nights[0]['name'] == "María José García-López"
