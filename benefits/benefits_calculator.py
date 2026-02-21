import json
import yaml
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List
import pandas as pd
import calendar



class BenefitsCalculator:
    """
    Loads and calculates credit card benefits, tracking posted vs. pending.
    Handles complex date logic (calendar year vs. card anniversary dates).
    """
    
    def __init__(self, config_path="benefits_config.yaml", state_path="benefits_state.json"):
        """
        Initialize the benefits calculator.
        
        Args:
            config_path: Path to benefits_config.yaml
            state_path: Path to benefits_state.json
        """
        self.config_path = Path(config_path)
        self.state_path = Path(state_path)
        self.config = self._load_config()
        self.state = self._load_state()
        self.today = date.today()
    
    def _load_config(self) -> Dict:
        """Load benefits configuration from YAML."""
        if not self.config_path.exists():
            print(f"Warning: Config file {self.config_path} not found")
            return {"cards": {}}
        
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f) or {"cards": {}}
    
    def _load_state(self) -> Dict:
        """Load benefits state from JSON."""
        if not self.state_path.exists():
            print(f"Warning: State file {self.state_path} not found")
            return {}
        
        with open(self.state_path, 'r') as f:
            return json.load(f)
    
    def save_state(self):
        """Save benefits state to JSON."""
        with open(self.state_path, 'w') as f:
            json.dump(self.state, f, indent=2)
    
    def toggle_benefit(self, benefit_id: str, period: str, anniversary_year: int = None):
        """
        Toggle the posted status of a benefit.
        
        Args:
            benefit_id: Unique benefit identifier (e.g., "schwab_platinum_2025_resy")
            period: Period identifier (e.g., "2026-Q1" or "2026")
            anniversary_year: Optional anniversary year for calendar benefits (tracks which year it was used in)
        """
        key = f"{benefit_id}|{period}"
        if key not in self.state:
            self.state[key] = {'posted': False, 'post_date': None, 'custom_amount': None, 'posted_anniversary_year': None}
        
        self.state[key]['posted'] = not self.state[key]['posted']
        if self.state[key]['posted']:
            self.state[key]['post_date'] = self.today.isoformat()
            if anniversary_year:
                self.state[key]['posted_anniversary_year'] = anniversary_year
        else:
            self.state[key]['post_date'] = None
            self.state[key]['posted_anniversary_year'] = None
        self.save_state()
    
    def set_custom_amount(self, benefit_id: str, period: str, custom_amount: float = None):
        """
        Set a custom amount for a benefit to track partial usage.
        
        Args:
            benefit_id: Benefit identifier
            period: Period identifier
            custom_amount: Custom amount used, or None to use the full amount
        """
        key = f"{benefit_id}|{period}"
        if key not in self.state:
            self.state[key] = {'posted': False, 'post_date': None, 'custom_amount': None}
        
        self.state[key]['custom_amount'] = custom_amount
        self.save_state()
    
    def get_custom_amount(self, benefit_id: str, period: str, default_amount: float = None):
        """
        Get the custom amount for a benefit if set, otherwise return the default.
        
        Args:
            benefit_id: Benefit identifier
            period: Period identifier
            default_amount: Default amount if no custom amount is set (usually the full amount)
            
        Returns:
            Custom amount if set, otherwise default_amount
        """
        key = f"{benefit_id}|{period}"
        state_entry = self.state.get(key, {})
        custom_amount = state_entry.get('custom_amount')
        
        if custom_amount is not None:
            return custom_amount
        return default_amount
    
    def set_benefit_posted(self, benefit_id: str, period: str, posted: bool, post_date: str = None):
        """
        Set a benefit's posted status explicitly.
        
        Args:
            benefit_id: Benefit identifier
            period: Period identifier
            posted: Whether the benefit has posted
            post_date: Date posted (YYYY-MM-DD format), defaults to today
        """
        key = f"{benefit_id}|{period}"
        if key not in self.state:
            self.state[key] = {'posted': False, 'post_date': None, 'custom_amount': None}
        
        self.state[key]['posted'] = posted
        if posted:
            self.state[key]['post_date'] = post_date or self.today.isoformat()
        else:
            self.state[key]['post_date'] = None
        self.save_state()
    
    def get_card_benefits(self, card_key: str) -> List[Dict]:
        """
        Get all benefits for a card with their current state.
        
        Args:
            card_key: Card identifier from config (e.g., "schwab_platinum")
            
        Returns:
            List of benefit dicts with id, category, amount, period, posted status
        """
        if card_key not in self.config.get('cards', {}):
            return []
        
        card = self.config['cards'][card_key]
        benefits_list = []
        
        for benefit in card.get('benefits', []):
            periods = self._generate_periods(benefit, card_key)
            
            for period in periods:
                # Create unique ID by combining card base name and benefit id
                # For calendar year benefits, strip the year suffix so they share state across card years
                # For anniversary benefits, include the year since they're specific to that card's anniversary
                renewal_type = benefit.get('renewal_type', 'calendar_year')
                if renewal_type == 'calendar_year':
                    # Remove _YYYY suffix for calendar year benefits (e.g., schwab_platinum_2025 -> schwab_platinum)
                    base_card_key = '_'.join(card_key.rsplit('_', 1)[:-1]) if '_' in card_key and card_key.split('_')[-1].isdigit() else card_key
                    unique_benefit_id = f"{base_card_key}_{benefit['id']}"
                else:
                    # Keep year for anniversary benefits
                    unique_benefit_id = f"{card_key}_{benefit['id']}"
                
                state_key = f"{unique_benefit_id}|{period}"
                state_entry = self.state.get(state_key, {'posted': False, 'post_date': None, 'custom_amount': None})
                
                benefits_list.append({
                    'benefit_id': unique_benefit_id,
                    'category': benefit['category'],
                    'amount': benefit['amount'],
                    'frequency': benefit['frequency'],
                    'posted_anniversary_year': state_entry.get('posted_anniversary_year'),
                    'period': period,
                    'posted': state_entry['posted'],
                    'post_date': state_entry.get('post_date'),
                    'custom_amount': state_entry.get('custom_amount'),
                    'card_key': card_key,
                    'card_name': card.get('display_name', card_key),
                })
        
        return benefits_list
    
    def get_all_benefits(self) -> List[Dict]:
        """
        Get all benefits across all cards with their current state.
        
        Returns:
            List of benefit dicts
        """
        all_benefits = []
        for card_key in self.config.get('cards', {}).keys():
            all_benefits.extend(self.get_card_benefits(card_key))
        return all_benefits
    
    def _generate_periods(self, benefit: Dict, card_key: str) -> List[str]:
        """
        Generate period identifiers for a benefit based on its frequency and renewal logic.
        
        Args:
            benefit: Benefit definition from config
            card_key: Card identifier
            
        Returns:
            List of period strings (e.g., ["2026-Q1", "2025-Q1", ...])
        """
        frequency = benefit.get('frequency', 'yearly')
        renewal_type = benefit.get('renewal_type', 'calendar_year')
        
        card = self.config['cards'][card_key]
        renewal_month = card.get('renewal_month', 1)
        renewal_day = card.get('renewal_day', 1)
        
        periods = []
        current_year = self.today.year
        current_month = self.today.month
        
        # Generate periods for current year and past years (2 years back)
        # and future years (1 year ahead)
        for year_offset in range(-2, 2):
            year = current_year + year_offset
            
            if renewal_type == 'calendar_year':
                # Calendar-based periods
                if frequency == 'yearly':
                    periods.append(str(year))
                elif frequency == 'half_yearly':
                    periods.append(f"{year}-H1")
                    periods.append(f"{year}-H2")
                elif frequency == 'quarterly':
                    periods.append(f"{year}-Q1")
                    periods.append(f"{year}-Q2")
                    periods.append(f"{year}-Q3")
                    periods.append(f"{year}-Q4")
                elif frequency == 'monthly':
                    for month in range(1, 13):
                        periods.append(f"{year}-{calendar.month_abbr[month]}")
            
            elif renewal_type == 'card_anniversary':
                # Card anniversary-based periods
                # Period format: "YYYY-AA" where AA is anniversary year
                # This allows tracking across card renewal dates
                
                if frequency == 'yearly':
                    # Yearly benefit renews on card anniversary
                    # Period should span from last renewal to next renewal
                    periods.append(f"{year}-A{renewal_month:02d}")
                
                elif frequency == 'half_yearly':
                    # H1: anniversary month to ~6 months later
                    # H2: 6 months after anniversary to anniversary
                    periods.append(f"{year}-AH1-{renewal_month:02d}")
                    periods.append(f"{year}-AH2-{renewal_month:02d}")
                
                elif frequency == 'quarterly':
                    # Quarterly periods relative to anniversary
                    for q in range(1, 5):
                        periods.append(f"{year}-AQ{q}-{renewal_month:02d}")
                
                elif frequency == 'every_4_years':
                    # Every 4 years benefit (e.g., Global Entry/TSA PreCheck)
                    # Generate periods at 4-year intervals
                    # The period represents the anniversary year when it can be used
                    periods.append(f"{year}-A{renewal_month:02d}")
        
        return periods
    
    def get_card_summary(self, card_key: str) -> Dict:
        """
        Get summary of benefits for a card.
        
        Args:
            card_key: Card identifier
            
        Returns:
            Dictionary with total annual fee, total benefits posted, total potential benefits
        """
        if card_key not in self.config.get('cards', {}):
            return {}
        
        card = self.config['cards'][card_key]
        benefits = self.get_card_benefits(card_key)
        
        # Filter to "active" periods (current year and recent)
        current_year = self.today.year
        active_benefits = [
            b for b in benefits 
            if str(current_year) in b['period'] or 
               str(current_year - 1) in b['period']
        ]
        
        total_annual_fee = card.get('annual_fee', 0)
        
        # Current year benefits
        current_year_benefits = [
            b for b in active_benefits 
            if str(current_year) in b['period']
        ]
        
        # For posted benefits, use custom_amount if set and > 0, otherwise use full amount
        total_posted = sum(
            (b['custom_amount'] if b['custom_amount'] is not None and b['custom_amount'] > 0 else b['amount']) 
            for b in current_year_benefits if b['posted']
        )
        # For potential benefits, always use the full amount
        total_potential = sum(
            b['amount'] for b in current_year_benefits
        )
        
        return {
            'card_name': card.get('display_name', card_key),
            'annual_fee': total_annual_fee,
            'total_posted': total_posted,
            'total_potential': total_potential,
            'net_value_posted': total_posted - total_annual_fee,
            'net_value_potential': total_potential - total_annual_fee,
            'roi_posted': ((total_posted - total_annual_fee) / total_annual_fee * 100) if total_annual_fee > 0 else 0,
            'roi_potential': ((total_potential - total_annual_fee) / total_annual_fee * 100) if total_annual_fee > 0 else 0,
        }
    
    def get_card_anniversary_month(self, card_key: str) -> int:
        """
        Get the renewal/anniversary month for a card (1-12).
        
        Args:
            card_key: Card identifier
            
        Returns:
            Month number (1-12)
        """
        if card_key not in self.config.get('cards', {}):
            return None
        return self.config['cards'][card_key].get('renewal_month', 1)
    
    def get_anniversary_year_range(self, card_key: str, anniversary_year: int) -> tuple:
        """
        Get the date range for an anniversary year.
        
        Args:
            card_key: Card identifier
            anniversary_year: The anniversary year label (e.g., 2025)
            
        Returns:
            Tuple of (start_date, end_date) for the anniversary year
        """
        if card_key not in self.config.get('cards', {}):
            return None, None
        
        card = self.config['cards'][card_key]
        renewal_month = card.get('renewal_month', 1)
        renewal_day = card.get('renewal_day', 1)
        
        # Anniversary year "2025" with July (7) renewal starts July 2025 and ends July 14, 2026
        # The year is associated with when the fee is paid (beginning of period)
        from datetime import timedelta
        start_date = date(anniversary_year, renewal_month, renewal_day)
        end_date = start_date + timedelta(days=364)  # 365 days total = almost 1 year
        
        return start_date, end_date
    
    def get_benefit_renewal_type(self, benefit: Dict) -> str:
        """
        Get the renewal type for a benefit from its benefit dict.
        This is extracted from the period format when the benefit was created.
        
        Args:
            benefit: Benefit dict
            
        Returns:
            'card_anniversary' or 'calendar_year'
        """
        period = benefit.get('period', '')
        # Anniversary periods contain '-A' followed by a digit or 'H' or 'Q': 
        # '2026-A12', '2026-AH1-11', '2026-AQ1-11', etc.
        # Must not match month abbreviations like '2026-Apr' or '2026-Aug'
        import re
        if re.search(r'-A[0-9HQ]', period):
            return 'card_anniversary'
        return 'calendar_year'
    
    def get_benefit_anniversary_year(self, card_key: str, benefit: Dict) -> int:
        """
        Determine which anniversary year a benefit belongs to based on its post_date.
        Only applies to benefits that have been posted.
        
        Args:
            card_key: Card identifier
            benefit: Benefit dict with post_date and posted status
            
        Returns:
            Anniversary year (int), or None if not posted or no post_date
        """
        if not benefit['posted'] or not benefit['post_date']:
            return None
        
        if card_key not in self.config.get('cards', {}):
            return None
        
        card = self.config['cards'][card_key]
        renewal_month = card.get('renewal_month', 1)
        renewal_day = card.get('renewal_day', 1)
        
        post_date = date.fromisoformat(benefit['post_date'])
        
        # Determine which anniversary year this post_date falls into
        # If renewal is July 15, then:
        #   - Anniversary year 2025 covers July 15, 2025 to July 14, 2026
        #   - Anniversary year 2026 covers July 15, 2026 to July 14, 2027
        # The year is associated with when the fee is paid (beginning of period)
        
        renewal_date_in_post_year = date(post_date.year, renewal_month, renewal_day)
        
        if post_date >= renewal_date_in_post_year:
            # Post date is on or after this year's renewal, so it's part of this anniversary year
            anniversary_year = post_date.year
        else:
            # Post date is before this year's renewal, so it's part of previous anniversary year
            anniversary_year = post_date.year - 1
        
        return anniversary_year
    
    def get_benefit_period_anniversary_year(self, benefit: Dict) -> int:
        """
        Extract the anniversary year from a benefit's period string.
        Works for both posted and pending anniversary benefits.
        
        Args:
            benefit: Benefit dict with period
            
        Returns:
            Anniversary year (int), or None if not an anniversary period
        """
        period = benefit.get('period', '')
        
        # Anniversary periods: '2026-A11', '2026-AH1-11', '2026-AQ1-11', etc.
        # Extract the first 4-digit year
        if '-A' in period:
            year_str = period.split('-')[0]
            try:
                return int(year_str)
            except ValueError:
                return None
        
        return None
    
    def get_calendar_period_date_range(self, period: str) -> tuple:
        """
        Get the date range for a calendar period string.
        
        Args:
            period: Calendar period string like '2026', '2026-H1', '2026-Q2', '2026-Jan', '2026-H2'
            
        Returns:
            Tuple of (start_date, end_date) or (None, None) if invalid
        """
        try:
            # Check for monthly period with abbreviated month name (2026-Jan, 2026-Feb, etc.)
            month_num = None
            for m in range(1, 13):
                if period.endswith(calendar.month_abbr[m]):
                    year_str = period.split('-')[0]
                    try:
                        year = int(year_str)
                        month_num = m
                        _, last_day = calendar.monthrange(year, month_num)
                        return date(year, month_num, 1), date(year, month_num, last_day)
                    except ValueError:
                        pass
            
            if '-M' in period:
                # Fallback for old format: Monthly: 2026-M01, M02, ..., M12
                year_str, month_part = period.split('-M')
                year = int(year_str)
                month = int(month_part)
                # Get the last day of the month
                _, last_day = calendar.monthrange(year, month)
                return date(year, month, 1), date(year, month, last_day)
            elif '-H' in period:
                # Half-yearly: 2026-H1 or 2026-H2
                year_str, half = period.split('-H')
                year = int(year_str)
                if half == '1':
                    return date(year, 1, 1), date(year, 6, 30)
                else:  # H2
                    return date(year, 7, 1), date(year, 12, 31)
            elif '-Q' in period:
                # Quarterly: 2026-Q1, Q2, Q3, Q4
                year_str, quarter = period.split('-Q')
                year = int(year_str)
                quarter_num = int(quarter)
                if quarter_num == 1:
                    return date(year, 1, 1), date(year, 3, 31)
                elif quarter_num == 2:
                    return date(year, 4, 1), date(year, 6, 30)
                elif quarter_num == 3:
                    return date(year, 7, 1), date(year, 9, 30)
                else:  # Q4
                    return date(year, 10, 1), date(year, 12, 31)
            else:
                # Yearly: just '2026'
                year = int(period)
                return date(year, 1, 1), date(year, 12, 31)
        except (ValueError, AttributeError):
            return None, None
    
    def calendar_period_overlaps_anniversary_year(self, card_key: str, period: str, anniversary_year: int) -> bool:
        """
        Check if a calendar period overlaps with an anniversary year.
        
        Args:
            card_key: Card identifier
            period: Calendar period string (e.g., '2026-H1', '2025-H2')
            anniversary_year: The anniversary year to check against
            
        Returns:
            True if there's overlap, False otherwise
        """
        # Get date ranges
        period_start, period_end = self.get_calendar_period_date_range(period)
        if not period_start or not period_end:
            return False
        
        anniv_start, anniv_end = self.get_anniversary_year_range(card_key, anniversary_year)
        if not anniv_start or not anniv_end:
            return False
        
        # Check for overlap: periods overlap if one starts before the other ends
        return period_start <= anniv_end and period_end >= anniv_start
    
    def get_posted_calendar_benefit_anniversary_year(self, card_key: str, benefit: Dict) -> int:
        """
        Determine which anniversary year a posted calendar benefit belongs to.
        For calendar benefits, we check which anniversary year the post_date falls within.
        
        Args:
            card_key: Card identifier
            benefit: Benefit dict with post_date
            
        Returns:
            Anniversary year (int), or None if not applicable
        """
        if not benefit['posted'] or not benefit['post_date']:
            return None
        
        post_date = date.fromisoformat(benefit['post_date'])
        
        # Check which anniversary year this post_date falls into
        # We'll check a range of possible anniversary years
        current_year = self.today.year
        for year_offset in range(-2, 3):
            anniversary_year = current_year + year_offset
            anniv_start, anniv_end = self.get_anniversary_year_range(card_key, anniversary_year)
            if anniv_start and anniv_end:
                if anniv_start <= post_date <= anniv_end:
                    return anniversary_year
        
        return None

    def get_all_cards_summary(self) -> pd.DataFrame:
        """
        Get summary for all cards in a DataFrame.
        
        Returns:
            DataFrame with card summaries
        """
        summaries = []
        for card_key in self.config.get('cards', {}).keys():
            summary = self.get_card_summary(card_key)
            if summary:
                summary['card_key'] = card_key
                summaries.append(summary)
        
        return pd.DataFrame(summaries)
    
    def get_benefits_by_category(self, card_key: str = None) -> Dict[str, List[Dict]]:
        """
        Get benefits grouped by category.
        
        Args:
            card_key: Optional card to filter by
            
        Returns:
            Dictionary mapping category to list of benefits
        """
        benefits = self.get_card_benefits(card_key) if card_key else self.get_all_benefits()
        
        grouped = {}
        for benefit in benefits:
            category = benefit['category']
            if category not in grouped:
                grouped[category] = []
            grouped[category].append(benefit)
        
        return grouped
    
    def is_every_4_years_benefit_available(self, benefit_id: str, card_key: str, period: str) -> tuple:
        """
        Check if an every_4_years benefit is available or if it was used too recently.
        
        Args:
            benefit_id: Benefit identifier
            card_key: Card identifier
            period: Current period being checked
            
        Returns:
            Tuple of (is_available, next_available_year, last_used_year)
            - is_available: True if available, False if used within last 4 years
            - next_available_year: Year when it will next be available (if not available)
            - last_used_year: Anniversary year when it was last used (if applicable)
        """
        # Get the card's anniversary information
        if card_key not in self.config.get('cards', {}):
            return True, None, None
        
        card = self.config['cards'][card_key]
        renewal_month = card.get('renewal_month', 1)
        
        # Extract the period year from the current period
        try:
            current_period_year = int(period.split('-')[0])
        except (ValueError, IndexError):
            return True, None, None
        
        # Look for any posted instances of this benefit across all periods
        last_used_year = None
        for key, state_entry in self.state.items():
            if state_entry.get('posted', False) and key.startswith(f"{benefit_id}|"):
                # Extract the period from the state key
                stored_period = key.split('|')[1]
                # Extract the year from the period (e.g., "2025-A11" -> 2025)
                try:
                    stored_year = int(stored_period.split('-')[0])
                    if last_used_year is None or stored_year > last_used_year:
                        last_used_year = stored_year
                except (ValueError, IndexError):
                    continue
        
        # If never used, it's available
        if last_used_year is None:
            return True, None, None
        
        # Check if enough time has passed (4 years)
        # The benefit is available again 4 anniversary years after it was last used
        next_available_year = last_used_year + 4
        
        if current_period_year >= next_available_year:
            return True, None, last_used_year
        else:
            return False, next_available_year, last_used_year
    
    def get_every_4_years_benefit_info(self, benefit: Dict) -> Dict:
        """
        Get information about an every_4_years benefit's availability.
        
        Args:
            benefit: Benefit dict
            
        Returns:
            Dict with keys: is_available, next_available_year, last_used_year, disabled_reason
        """
        if benefit.get('frequency') != 'every_4_years':
            return {'is_available': True, 'next_available_year': None, 'last_used_year': None, 'disabled_reason': None}
        
        is_available, next_available_year, last_used_year = self.is_every_4_years_benefit_available(
            benefit['benefit_id'],
            benefit['card_key'],
            benefit['period']
        )
        
        disabled_reason = None
        if not is_available:
            disabled_reason = f"Used in {last_used_year}, available again in {next_available_year}"
        
        return {
            'is_available': is_available,
            'next_available_year': next_available_year,
            'last_used_year': last_used_year,
            'disabled_reason': disabled_reason
        }


if __name__ == "__main__":
    # Example usage
    calculator = BenefitsCalculator()
    
    print("All cards summary:")
    print(calculator.get_all_cards_summary())
    
    print("\nSchwab platinum benefits:")
    schwab_benefits = calculator.get_card_benefits('schwab_platinum')
    for b in schwab_benefits:
        print(f"  {b['category']} {b['period']}: ${b['amount']} (posted: {b['posted']})")
    
    print("\nTotal annual benefits by card:")
    for card_key in calculator.config.get('cards', {}).keys():
        summary = calculator.get_card_summary(card_key)
        if summary:
            print(f"  {summary['card_name']}: ${summary['total_potential']} potential, "
                  f"${summary['total_posted']} posted (fee: ${summary['annual_fee']})")
