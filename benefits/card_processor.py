import os
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path

class CardProcessor:
    """
    Processes credit card CSV files and calculates bonus nights.
    Replicates logic from night-tracker.R in Python with pandas.
    """
    
    def __init__(self, base_path="."):
        """
        Initialize the card processor.
        
        Args:
            base_path: Root directory containing hyatt business/ and hyatt personal/ folders
        """
        self.base_path = Path(base_path)
        self.personal_df = None
        self.business_df = None
    
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
        
        for file in folder_path.glob("*.CSV"):
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
        
        group_cols = [
            'Transaction Date', 'Post Date', 'Description', 
            'Category', 'Type', 'Amount', 'Memo'
        ]
        # Only group on columns that exist
        group_cols = [col for col in group_cols if col in df.columns]
        
        if not group_cols:
            return df
        
        df_grouped = df.groupby(group_cols, dropna=False).agg({
            'file': lambda x: list(x)
        }).reset_index()
        
        # Mark true duplicates (appear in multiple files)
        df_grouped['true_duplicate'] = df_grouped['file'].apply(
            lambda files: len(files) > 1 and len(set(files)) > 1
        )
        
        # Expand back to original structure, keeping first occurrence of duplicates
        result = []
        for idx, row in df_grouped.iterrows():
            num_files = len(row['file'])
            if not row['true_duplicate']:
                # Not a true duplicate, keep all instances
                for _ in range(num_files):
                    result.append(row.drop('file'))
            else:
                # True duplicate, keep only first
                result.append(row.drop('file'))
        
        result_df = pd.concat([df.drop('file', axis=1)[
            [col for col in df.columns if col != 'file']
        ]] if result else [pd.DataFrame()], ignore_index=True)
        
        return result_df
    
    def process_personal_card(self):
        """
        Load and process personal card data with bonus night calculations.
        
        Returns:
            DataFrame with processed personal card data
        """
        df = self.load_csvs_from_folder("transactions/hyatt personal")
        
        if df.empty:
            print("No personal card data found")
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
        
        # Calculate cumulative spending
        df = df.sort_values('Transaction Date')
        df['cumsum'] = df['Amount'].cumsum()
        
        # Calculate year-to-date cumulative
        df['cumsum_year'] = df.groupby('year')['Amount'].cumsum()
        
        # Calculate bonus nights based on $5,000 thresholds
        df['previous_cumsum'] = df['cumsum'].shift(1)
        df['nights'] = df.apply(
            self._calculate_personal_bonus,
            axis=1
        )
        
        self.personal_df = df
        return df
    
    def process_business_card(self):
        """
        Load and process business card data with bonus night calculations.
        Business card resets annual counter by year.
        
        Returns:
            DataFrame with processed business card data
        """
        df = self.load_csvs_from_folder("transactions/hyatt business")
        
        if df.empty:
            print("No business card data found")
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
        
        # Calculate year-to-date cumulative (resets by year)
        df['cumsum_year'] = df.groupby('year')['Amount'].cumsum()
        df['previous_cumsum_year'] = df.groupby('year')['cumsum_year'].shift(1)
        
        # Calculate bonus nights based on $10,000 thresholds per year
        df['nights'] = df.apply(
            self._calculate_business_bonus,
            axis=1
        )
        
        self.business_df = df
        return df
    
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
        df = self.personal_df if card_type == 'personal' else self.business_df
        
        if df is None or df.empty:
            return {}
        
        # Get latest row for current spending
        latest = df.iloc[-1]
        current_year = pd.Timestamp.now().year
        current_year_df = df[df['year'] == current_year]
        
        if card_type == 'personal':
            total_spending = latest['cumsum']
            ytd_spending = current_year_df['cumsum_year'].iloc[-1] if not current_year_df.empty else 0
            current_tier = int(total_spending / 5000)
            next_tier_threshold = (current_tier + 1) * 5000
            spend_to_next = next_tier_threshold - total_spending
            
            # For $15k annual certificate
            ytd_to_certificate = 15000 - ytd_spending if ytd_spending < 15000 else 0
            
            return {
                'total_spending': round(total_spending, 2),
                'ytd_spending': round(ytd_spending, 2),
                'current_tier': current_tier,
                'spend_to_next_bonus': round(max(0, spend_to_next), 2),
                'spend_to_certificate': round(max(0, ytd_to_certificate), 2),
                'current_threshold': round((current_tier) * 5000, 2),
                'next_threshold': round(next_tier_threshold, 2),
            }
        else:  # business
            ytd_spending = current_year_df['cumsum_year'].iloc[-1] if not current_year_df.empty else 0
            current_tier = int(ytd_spending / 10000)
            next_tier_threshold = (current_tier + 1) * 10000
            spend_to_next = next_tier_threshold - ytd_spending
            
            return {
                'ytd_spending': round(ytd_spending, 2),
                'current_tier': current_tier,
                'spend_to_next_bonus': round(max(0, spend_to_next), 2),
                'current_threshold': round((current_tier) * 10000, 2),
                'next_threshold': round(next_tier_threshold, 2),
            }
    
    def get_bonus_nights_posted(self, card_type='personal'):
        """
        Count actual bonus nights earned (non-null nights column).
        
        Args:
            card_type: 'personal' or 'business'
            
        Returns:
            Total posted bonus nights
        """
        df = self.personal_df if card_type == 'personal' else self.business_df
        
        if df is None or df.empty:
            return 0
        
        return int(df['nights'].sum())
    
    def _get_most_recent_post_date(self):
        """
        Get the statement close date (23rd of month).
        This is typically when transactions post to the account.
        
        Returns:
            datetime for the 23rd of current month or previous month if today <= 2nd
        """
        today = pd.Timestamp.now()
        if today.day > 2:
            return today.replace(day=23)
        else:
            # If today is on the 1st or 2nd, use last month's 23rd
            return (today - pd.DateOffset(months=1)).replace(day=23)
    
    def get_yearly_bonus_nights_breakdown(self, card_type='personal'):
        """
        Get posted vs. pending bonus nights for the current calendar year.
        Posted: transactions on or before statement close date (23rd of month)
        Pending: transactions after that date
        
        Args:
            card_type: 'personal' or 'business'
            
        Returns:
            Dictionary with posted, pending, and total for current year
        """
        df = self.personal_df if card_type == 'personal' else self.business_df
        
        if df is None or df.empty:
            return {'posted': 0, 'pending': 0, 'total': 0}
        
        current_year = pd.Timestamp.now().year
        recent_post_date = self._get_most_recent_post_date()
        
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
