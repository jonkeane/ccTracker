import pandas as pd
from pathlib import Path

class CardProcessor:
    """
    Processes credit card CSV files and calculates bonus nights.
    Replicates logic from night-tracker.R in Python with pandas.
    """

    def __init__(
        self,
        base_path=".",
        hyatt_cards=None,
    ):
        """
        Initialize the card processor.
        
        Args:
            base_path: Root directory containing hyatt business/ and hyatt personal/ folders
        """
        self.base_path = Path(base_path)

        default_hyatt_cards = {
            'personal': {
                'folder': 'transactions/hyatt personal',
                'renewal_day': None,
            },
            'business': {
                'folder': 'transactions/hyatt business',
                'renewal_day': None,
            },
        }

        source_hyatt_cards = hyatt_cards or default_hyatt_cards
        self.hyatt_cards = {}
        for card_type in ('personal', 'business'):
            card_settings = source_hyatt_cards.get(card_type, {})
            if not isinstance(card_settings, dict):
                raise ValueError(f"hyatt_cards['{card_type}'] must be a dictionary")

            folder = card_settings.get('folder', default_hyatt_cards[card_type]['folder'])
            if not isinstance(folder, str) or not folder.strip():
                raise ValueError(f"folder for '{card_type}' card must be a non-empty string")

            self.hyatt_cards[card_type] = {
                'folder': folder.strip(),
                'renewal_day': card_settings.get('renewal_day'),
            }

        self.personal_df = None
        self.business_df = None

    def _get_card_settings(self, card_type):
        """Return configuration for a card type or raise a clear error."""
        card_settings = self.hyatt_cards.get(card_type)
        if card_settings is None:
            raise ValueError("card_type must be 'personal' or 'business'")
        return card_settings

    def _get_card_dataframe(self, card_type):
        """Return in-memory dataframe for a card type."""
        if card_type == 'personal':
            return self.personal_df
        if card_type == 'business':
            return self.business_df
        raise ValueError("card_type must be 'personal' or 'business'")

    def _set_card_dataframe(self, card_type, df):
        """Set in-memory dataframe for a card type."""
        if card_type == 'personal':
            self.personal_df = df
            return
        if card_type == 'business':
            self.business_df = df
            return
        raise ValueError("card_type must be 'personal' or 'business'")

    def _process_card(self, card_type):
        """Load and process card data with card-specific bonus logic."""
        df = self.load_csvs_from_folder(self._get_card_settings(card_type)['folder'])

        if df.empty:
            print(f"No {card_type} card data found")
            return pd.DataFrame()

        # Remove duplicates across files
        df = self.remove_duplicates(df)

        # Parse dates
        df['Transaction Date'] = pd.to_datetime(df['Transaction Date'], format='%m/%d/%Y', errors='coerce')
        df['Post Date'] = pd.to_datetime(df['Post Date'], format='%m/%d/%Y', errors='coerce')
        df['year'] = df['Post Date'].dt.year

        # Sort by transaction date
        df = df.sort_values('Transaction Date')

        # Filter out payments and fees
        df = df[~df['Type'].isin(['Payment', 'Fee'])]

        # Negate amounts (they're negative in CSV)
        df['Amount'] = -df['Amount']

        # Calculate year-to-date cumulative
        df['cumsum_year'] = df.groupby('year')['Amount'].cumsum()

        if card_type == 'personal':
            # Personal card bonus tiers use lifetime cumulative spend.
            df['cumsum'] = df['Amount'].cumsum()
            df['previous_cumsum'] = df['cumsum'].shift(1)
            df['nights'] = df.apply(self._calculate_personal_bonus, axis=1)
        else:
            # Business card bonus tiers reset each calendar year.
            df['previous_cumsum_year'] = df.groupby('year')['cumsum_year'].shift(1)
            df['nights'] = df.apply(self._calculate_business_bonus, axis=1)

        self._set_card_dataframe(card_type, df)
        return df
    
    def load_csvs_from_folder(self, folder_name):
        """
        Load all CSV files from a folder and combine them.
        
        Args:
            folder_name: Name of folder (e.g., 'hyatt personal')
            
        Returns:
            DataFrame with combined CSV data
        """
        folder_path = self.base_path / folder_name
        dfs = []
        
        if not folder_path.exists():
            print(f"Warning: Folder {folder_path} does not exist")
            return pd.DataFrame()
        
        csv_files = [
            file for file in folder_path.rglob("*")
            if file.is_file() and file.suffix.lower() == ".csv"
        ]

        for file in sorted(csv_files):
            try:
                df = pd.read_csv(file)
                df['file'] = str(file)
                dfs.append(df)
            except Exception as e:
                print(f"Error reading {file}: {e}")
        
        if not dfs:
            return pd.DataFrame()
        
        return pd.concat(dfs, ignore_index=True)

    def remove_duplicates(self, df):
        """
        Remove duplicates across files.
        Keep duplicate if it appears in multiple files; otherwise remove it.
        
        Args:
            df: DataFrame with 'file' column
            
        Returns:
            Deduplicated DataFrame
        """
        if df.empty:
            return df

        if 'file' not in df.columns:
            return df
        
        group_cols = [
            'Transaction Date', 'Post Date', 'Description', 
            'Category', 'Type', 'Amount', 'Memo'
        ]
        # Only group on columns that exist
        group_cols = [col for col in group_cols if col in df.columns]
        
        if not group_cols:
            return df
        
        # Keep one row when an identical transaction appears in multiple files,
        # but preserve all rows when duplicates exist only within the same file.
        keep_indices = []
        grouped = df.groupby(group_cols, dropna=False)
        for _, group in grouped:
            if group['file'].nunique() > 1:
                keep_indices.append(group.index[0])
            else:
                keep_indices.extend(group.index.tolist())

        result_df = (
            df.loc[sorted(keep_indices)]
            .drop(columns=['file'])
            .reset_index(drop=True)
        )

        return result_df
    
    def process_personal_card(self):
        """
        Load and process personal card data with bonus night calculations.
        
        Returns:
            DataFrame with processed personal card data
        """
        return self._process_card('personal')
    
    def process_business_card(self):
        """
        Load and process business card data with bonus night calculations.
        Business card resets annual counter by year.
        
        Returns:
            DataFrame with processed business card data
        """
        return self._process_card('business')
    
    @staticmethod
    def _calculate_personal_bonus(row):
        """
        Calculate bonus nights for personal card.
        Every $5,000 spent = 2 bonus nights (plus more for higher tiers)
        """
        cumsum = row['cumsum']
        previous_cumsum = row['previous_cumsum'] if pd.notna(row['previous_cumsum']) else 0
        
        current_tier = int(cumsum / 5000)
        previous_tier = int(previous_cumsum / 5000)
        
        # Check if we crossed into a new tier
        if current_tier > previous_tier and current_tier > 0:
            tiers_crossed = current_tier - previous_tier
            if tiers_crossed == 1:
                return 2 if current_tier == 1 else 2 * tiers_crossed
            # For multi-tier crosses, use max nights for highest tier
            nights_map = {1: 2, 2: 4, 3: 6, 4: 8, 5: 10, 
                         6: 12, 7: 14, 8: 16, 9: 18, 10: 20, 11: 22}
            return nights_map.get(current_tier, 22)
        
        # Check if we dropped below a tier
        elif current_tier < previous_tier and current_tier > 0:
            tiers_dropped = previous_tier - current_tier
            nights_map = {1: 2, 2: 4, 3: 6, 4: 8, 5: 10, 
                         6: 12, 7: 14, 8: 16, 9: 18, 10: 20, 11: 22}
            return -nights_map.get(previous_tier, 22)
        
        return None
    
    @staticmethod
    def _calculate_business_bonus(row):
        """
        Calculate bonus nights for business card.
        Every $10,000 spent per year = 5 bonus nights (up to 30)
        """
        cumsum_year = row['cumsum_year']
        previous_cumsum_year = row['previous_cumsum_year'] if pd.notna(row['previous_cumsum_year']) else 0
        
        current_tier = int(cumsum_year / 10000)
        previous_tier = int(previous_cumsum_year / 10000)
        
        # Check if we crossed into a new tier
        if current_tier > previous_tier and current_tier > 0:
            nights_map = {1: 5, 2: 10, 3: 15, 4: 20, 5: 25, 6: 30}
            return nights_map.get(current_tier, 30)
        
        # Check if we dropped below a tier
        elif current_tier < previous_tier and current_tier > 0:
            nights_map = {1: 5, 2: 10, 3: 15, 4: 20, 5: 25, 6: 30}
            return -nights_map.get(previous_tier, 30)
        
        return None
    
    def get_spending_summary(self, card_type='personal'):
        """
        Get current spending summary for a card.
        
        Args:
            card_type: 'personal' or 'business'
            
        Returns:
            Dictionary with spending summary
        """
        df = self._get_card_dataframe(card_type)
        
        if df is None or df.empty:
            return {}
        
        # Get latest row for current spending
        latest = df.iloc[-1]
        current_year = pd.Timestamp.now().year
        current_year_df = df[df['year'] == current_year]
        
        ytd_spending = current_year_df['cumsum_year'].iloc[-1] if not current_year_df.empty else 0
        tier_amount = 5000 if card_type == 'personal' else 10000

        basis_spending = latest['cumsum'] if card_type == 'personal' else ytd_spending
        current_tier = int(basis_spending / tier_amount)
        next_tier_threshold = (current_tier + 1) * tier_amount
        spend_to_next = next_tier_threshold - basis_spending

        summary = {
            'ytd_spending': round(ytd_spending, 2),
            'current_tier': current_tier,
            'spend_to_next_bonus': round(max(0, spend_to_next), 2),
            'current_threshold': round((current_tier) * tier_amount, 2),
            'next_threshold': round(next_tier_threshold, 2),
        }

        if card_type == 'personal':
            ytd_to_certificate = 15000 - ytd_spending if ytd_spending < 15000 else 0
            summary.update({
                'total_spending': round(basis_spending, 2),
                'spend_to_certificate': round(max(0, ytd_to_certificate), 2),
            })

        return summary
    
    def get_bonus_nights_posted(self, card_type='personal'):
        """
        Count actual bonus nights earned (non-null nights column).
        
        Args:
            card_type: 'personal' or 'business'
            
        Returns:
            Total posted bonus nights
        """
        df = self._get_card_dataframe(card_type)
        
        if df is None or df.empty:
            return 0
        
        return int(df['nights'].sum())
    
    def _get_most_recent_post_date(self, card_type='personal'):
        """
        Get the statement cutoff date for a Hyatt card.
        Uses renewal_day from config for the selected card type.
        
        Returns:
            datetime for renewal day of current month, or previous month when today <= renewal day
        """
        card_settings = self._get_card_settings(card_type)
        renewal_day = card_settings.get('renewal_day')
        if not isinstance(renewal_day, int) or not (1 <= renewal_day <= 31):
            raise ValueError(
                f"renewal_day for '{card_type}' card must be set to an integer between 1 and 31"
            )
        today = pd.Timestamp.now()
        if today.day > renewal_day:
            return today.replace(day=renewal_day)
        else:
            return (today - pd.DateOffset(months=1)).replace(day=renewal_day)
    
    def get_yearly_bonus_nights_breakdown(self, card_type='personal'):
        """
        Get posted vs. pending bonus nights for the current calendar year.
        Posted: transactions on or before statement cutoff date (renewal_day from config)
        Pending: transactions after that date
        
        Args:
            card_type: 'personal' or 'business'
            
        Returns:
            Dictionary with posted, pending, and total for current year
        """
        df = self._get_card_dataframe(card_type)
        
        if df is None or df.empty:
            return {'posted': 0, 'pending': 0, 'total': 0}
        
        current_year = pd.Timestamp.now().year
        recent_post_date = self._get_most_recent_post_date(card_type)
        
        # Filter to current year
        year_df = df[df['year'] == current_year]
        
        if year_df.empty:
            return {'posted': 0, 'pending': 0, 'total': 0}
        
        # Posted: on or before statement close date
        posted_df = year_df[year_df['Post Date'] <= recent_post_date]
        posted = int(posted_df['nights'].sum(skipna=True))
        
        total = int(year_df['nights'].sum(skipna=True))
        pending = total - posted
        
        return {'posted': posted, 'pending': pending, 'total': total}


if __name__ == "__main__":
    # Example usage
    processor = CardProcessor()
    
    print("Processing personal card...")
    personal_df = processor.process_personal_card()
    print(f"Loaded {len(personal_df)} personal transactions")
    print(processor.get_spending_summary('personal'))
    print(f"Bonus nights: {processor.get_bonus_nights_posted('personal')}")
    
    print("\nProcessing business card...")
    business_df = processor.process_business_card()
    print(f"Loaded {len(business_df)} business transactions")
    print(processor.get_spending_summary('business'))
    print(f"Bonus nights: {processor.get_bonus_nights_posted('business')}")
