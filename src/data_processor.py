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
        """Get all winners (WhatsApp + Post) for a specific round, including previous rounds."""
        query = '''
            SELECT p.mobile_number, p.unique_code, p.message, p.source, w.round_number
            FROM participants p
            JOIN winners w ON p.id = w.participant_id
            WHERE w.round_number <= ?
            ORDER BY w.round_number, p.source, w.selection_date
        '''
        
        conn = sqlite3.connect(self.database.db_path)
        df = pd.read_sql_query(query, conn, params=[round_number])
        conn.close()
        
        return df
        
    def get_winners_all_rounds(self):
        """Get winners from all rounds with round information."""
        query = '''
            SELECT p.mobile_number, p.unique_code, p.message, p.source, w.round_number
            FROM participants p
            JOIN winners w ON p.id = w.participant_id
            ORDER BY w.round_number, p.source
        '''
        
        conn = sqlite3.connect(self.database.db_path)
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        return df
    
    def export_winners_to_excel(self, round_number, output_path=None):
        """Export only the winners for the specified round to Excel."""
        # Modified query to get ONLY winners from the specific round
        query = '''
            SELECT p.mobile_number, p.unique_code, p.message, p.source, w.round_number
            FROM participants p
            JOIN winners w ON p.id = w.participant_id
            WHERE w.round_number = ?  -- Changed from <= to = to get only the specific round
            ORDER BY p.source, w.selection_date
        '''
        
        conn = sqlite3.connect(self.database.db_path)
        df = pd.read_sql_query(query, conn, params=[round_number])
        conn.close()
        
        if df.empty:
            return False, f"No winners found for round {round_number}."
        
        # Now check for duplicates across all rounds
        all_winners_query = '''
            SELECT p.mobile_number, p.unique_code, w.round_number
            FROM participants p
            JOIN winners w ON p.id = w.participant_id
        '''
        conn = sqlite3.connect(self.database.db_path)
        all_winners = pd.read_sql_query(all_winners_query, conn)
        conn.close()
        
        # Add duplicate status
        df['duplicate_status'] = 'Clean'
        df['duplicate_details'] = ''
        
        for idx, row in df.iterrows():
            # Check for mobile duplicates (same mobile in other rounds)
            mobile_matches = all_winners[
                (all_winners['mobile_number'] == row['mobile_number']) & 
                (all_winners['round_number'] != round_number)
            ]
            
            # Check for code duplicates (same code in other rounds)
            code_matches = all_winners[
                (all_winners['unique_code'] == row['unique_code']) & 
                (all_winners['round_number'] != round_number)
            ]
            
            mobile_dup_rounds = mobile_matches['round_number'].tolist()
            code_dup_rounds = code_matches['round_number'].tolist()
            
            # Mark duplicates with details
            if mobile_dup_rounds or code_dup_rounds:
                df.at[idx, 'duplicate_status'] = 'Duplicate'
                
                details = []
                if mobile_dup_rounds:
                    details.append(f"Same mobile in Round(s): {', '.join(map(str, mobile_dup_rounds))}")
                if code_dup_rounds:
                    details.append(f"Same code in Round(s): {', '.join(map(str, code_dup_rounds))}")
                
                df.at[idx, 'duplicate_details'] = '; '.join(details)
        
        if output_path is None:
            # Make sure we have both data and exports directories
            os.makedirs('data', exist_ok=True)
            os.makedirs('data/exports', exist_ok=True)
            output_path = f"data/exports/round_{round_number}_winners_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Create a Pandas Excel writer using XlsxWriter as the engine
            with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
                # Write the main data to Excel
                df.to_excel(writer, sheet_name=f'Round {round_number} Winners', index=False)
                
                # Access the workbook and the worksheet
                workbook = writer.book
                worksheet = writer.sheets[f'Round {round_number} Winners']
                
                # Add formats
                header_format = workbook.add_format({
                    'bold': True,
                    'text_wrap': True,
                    'valign': 'top',
                    'bg_color': '#D9E1F2',
                    'border': 1
                })
                
                duplicate_format = workbook.add_format({
                    'bg_color': '#FFC7CE',  # Light red fill
                    'font_color': '#9C0006'  # Dark red text
                })
                
                # Apply header format
                for col_num, value in enumerate(df.columns.values):
                    worksheet.write(0, col_num, value, header_format)
                
                # Apply conditional formatting to highlight duplicates
                for row_num, value in enumerate(df['duplicate_status']):
                    if value == 'Duplicate':
                        worksheet.set_row(row_num + 1, None, duplicate_format)
                
                # Auto-adjust columns' width
                for col_num, column in enumerate(df.columns):
                    column_width = max(
                        df[column].astype(str).map(len).max(),
                        len(column)
                    )
                    worksheet.set_column(col_num, col_num, column_width + 2)
            
            return True, output_path
        except Exception as e:
            return False, f"Error exporting winners: {str(e)}"
