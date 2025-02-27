import pandas as pd
import sqlite3
import os
from datetime import datetime

class DataProcessor:
    def __init__(self, database):
        self.database = database
        # Ensure directories exist
        os.makedirs('data', exist_ok=True)
        os.makedirs('exports', exist_ok=True)
        
    def import_whatsapp_data(self, file_path, round_number):
        """Import WhatsApp SMS data from Excel sheet."""
        try:
            df = pd.read_excel(file_path)
            required_columns = ["mobile number", "Unique Code", "SMS"]
            
            # Check if required columns exist
            for col in required_columns:
                if col not in df.columns:
                    return False, f"Required column '{col}' not found in the WhatsApp sheet."
            
            # Save to database
            for _, row in df.iterrows():
                self.database.add_participant(
                    row["mobile number"],
                    row["Unique Code"],
                    row["SMS"],
                    "WhatsApp",
                    round_number
                )
                
            return True, f"Successfully imported {len(df)} WhatsApp participants for round {round_number}."
        except Exception as e:
            return False, f"Error importing WhatsApp data: {str(e)}"
    
    def import_post_winners(self, file_path, round_number):
        """Import already selected winners from Post."""
        try:
            df = pd.read_excel(file_path)
            required_columns = ["mobile number", "Unique Code", "SMS"]
            
            # Check if required columns exist
            for col in required_columns:
                if col not in df.columns:
                    return False, f"Required column '{col}' not found in the Post winners sheet."
            
            # Save to database
            for _, row in df.iterrows():
                participant_id = self.database.add_participant(
                    row["mobile number"],
                    row["Unique Code"],
                    row["SMS"],
                    "Post",
                    round_number
                )
                
                # Add to winners table
                self.database.add_winner(participant_id, round_number, "Post")
            
            return True, f"Successfully imported {len(df)} Post winners for round {round_number}."
        except Exception as e:
            return False, f"Error importing Post winners: {str(e)}"
    
    def get_all_winners(self, round_number):
        """Get all winners (WhatsApp + Post) for a specific round."""
        query = '''
            SELECT p.mobile_number, p.unique_code, p.message, p.source
            FROM participants p
            JOIN winners w ON p.id = w.participant_id
            WHERE w.round_number = ?
            ORDER BY p.source, w.selection_date
        '''
        
        conn = sqlite3.connect(self.database.db_path)
        df = pd.read_sql_query(query, conn, params=[round_number])
        conn.close()
        
        return df
    
    def export_winners_to_excel(self, round_number, output_path=None):
        """Export all winners for a round to Excel."""
        df = self.get_all_winners(round_number)
        
        if df.empty:
            return False, "No winners found for this round."
        
        if output_path is None:
            output_path = f"exports/round_{round_number}_winners_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            # Export to Excel
            df.to_excel(output_path, index=False)
            return True, output_path
        except Exception as e:
            return False, f"Error exporting winners: {str(e)}"
