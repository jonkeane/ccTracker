import json
from datetime import date
from pathlib import Path
from typing import Dict, List
import pandas as pd


class StaysManager:
    """
    Manages persistent storage of hotel stays and guest-of-honor (GOH) nights.
    Stores data in JSON format, mirroring the benefits_calculator pattern.
    """

    def __init__(self, state_path="stays_state.json"):
        """
        Initialize the stays manager.

        Args:
            state_path: Path to stays_state.json
        """
        self.state_path = Path(state_path)
        self.state = self._load_state()

    def _load_state(self) -> Dict:
        """Load stays state from JSON."""
        if not self.state_path.exists():
            return {"stays": [], "goh_nights": []}

        try:
            with open(self.state_path, 'r') as f:
                content = json.load(f)
                # Ensure both keys exist
                if "stays" not in content:
                    content["stays"] = []
                if "goh_nights" not in content:
                    content["goh_nights"] = []
                return content
        except (json.JSONDecodeError, IOError):
            return {"stays": [], "goh_nights": []}

    def save_state(self):
        """Save stays state to JSON."""
        with open(self.state_path, 'w') as f:
            json.dump(self.state, f, indent=2)

    def add_stay(self, name: str, check_in: date, check_out: date) -> bool:
        """
        Add a new stay.

        Args:
            name: Hotel/location name
            check_in: Check-in date
            check_out: Check-out date

        Returns:
            True if added successfully, False otherwise
        """
        if not name or not check_in or not check_out or check_out <= check_in:
            return False

        stay = {
            "name": name,
            "check_in": check_in.isoformat() if isinstance(check_in, date) else str(check_in),
            "check_out": check_out.isoformat() if isinstance(check_out, date) else str(check_out),
        }
        self.state["stays"].append(stay)
        self.save_state()
        return True

    def delete_stay(self, index: int) -> bool:
        """
        Delete a stay by index.

        Args:
            index: Index of stay to delete

        Returns:
            True if deleted successfully, False if index out of range
        """
        if 0 <= index < len(self.state["stays"]):
            self.state["stays"].pop(index)
            self.save_state()
            return True
        return False

    def get_stays(self) -> List[Dict]:
        """
        Get all stays with dates converted to date objects.

        Returns:
            List of stay dicts with check_in/check_out as date objects
        """
        stays = []
        for stay in self.state["stays"]:
            stays.append({
                "name": stay["name"],
                "check_in": pd.Timestamp(stay["check_in"]).date(),
                "check_out": pd.Timestamp(stay["check_out"]).date(),
            })
        return stays

    def add_goh_night(self, name: str, goh_date: date) -> bool:
        """
        Add a new GOH (guest-of-honor) night.

        Args:
            name: Guest name or description
            goh_date: Date of GOH night

        Returns:
            True if added successfully, False otherwise
        """
        if not name or not goh_date:
            return False

        goh = {
            "name": name,
            "date": goh_date.isoformat() if isinstance(goh_date, date) else str(goh_date),
        }
        self.state["goh_nights"].append(goh)
        self.save_state()
        return True

    def delete_goh_night(self, index: int) -> bool:
        """
        Delete a GOH night by index.

        Args:
            index: Index of GOH night to delete

        Returns:
            True if deleted successfully, False if index out of range
        """
        if 0 <= index < len(self.state["goh_nights"]):
            self.state["goh_nights"].pop(index)
            self.save_state()
            return True
        return False

    def get_goh_nights(self) -> List[Dict]:
        """
        Get all GOH nights with dates converted to date objects.

        Returns:
            List of GOH night dicts with date as date object
        """
        goh_nights = []
        for goh in self.state["goh_nights"]:
            goh_nights.append({
                "name": goh["name"],
                "date": pd.Timestamp(goh["date"]).date(),
            })
        return goh_nights
