
import os
import sqlite3
import streamlit as st
import pandas as pd
from datetime import datetime

# Import our modules
from src.database import Database
from src.data_processor import DataProcessor
from src.winner_manager import WinnerManager

# Initialize the system
database = Database()
data_processor = DataProcessor(database)
winner_manager = WinnerManager(database)

# Fix missing import in data_processor.py
import sqlite3

def main():
    st.set_page_config(page_title="Raththi Winner Management System", layout="wide")
    
    st.title("Raththi Winner Management System")
    
    # Sidebar for navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Go to", [
        "Import Data", 
        "Select Winners", 
        "View Winners", 
        "Export Winners"
    ])
    
    if page == "Import Data":
        import_data_page()
    
    elif page == "Select Winners":
        select_winners_page()
    
    elif page == "View Winners":
        view_winners_page()
    
    elif page == "Export Winners":
        export_winners_page()

def get_latest_draw_number():
    """Get the latest draw number from the database."""
    try:
        conn = sqlite3.connect(database.db_path)
        cursor = conn.cursor()
        
        # Query to find the highest round_number in participants
        query = "SELECT MAX(round_number) FROM participants"
        cursor.execute(query)
        result = cursor.fetchone()[0]
        
        conn.close()
        return result if result else 0
    except Exception as e:
        print(f"Error getting latest draw number: {str(e)}")
        return 0

def import_data_page():
    st.header("Import Data")
    
    # Get the latest draw number from the database
    latest_draw = get_latest_draw_number()
    suggested_draw = latest_draw + 1 if latest_draw else 1
    
    # Display suggested draw number with option to change
    st.info(f"Suggested Draw Number: {suggested_draw} (based on previous imports)")
    
    # Allow manual override - this is a SINGLE round_number for BOTH imports
    round_number = st.number_input("Draw Number", min_value=1, value=suggested_draw, step=1)
    
    # Draw a line to separate the round number from the import sections
    st.markdown("---")
    
    # First import section - SMS data
    st.subheader("Import SMS Data")
    whatsapp_file = st.file_uploader("Upload SMS Excel Sheet", type=["xlsx", "xls"], key="sms")
    
    # Second import section - Post winners
    st.subheader("Import Post Winners")
    post_file = st.file_uploader("Upload Post Winners Excel Sheet", type=["xlsx", "xls"], key="post")
    
    if st.button("Import Data"):
        if not whatsapp_file or not post_file:
            st.warning("Please upload both SMS data and Post winners files.")
        else:
            # Save uploaded files temporarily
            temp_sms_file = f"data/temp_sms_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
            temp_post_file = f"data/temp_post_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
            
            with open(temp_sms_file, "wb") as f:
                f.write(whatsapp_file.getbuffer())
            with open(temp_post_file, "wb") as f:
                f.write(post_file.getbuffer())
            
            # Import SMS data
            sms_success, sms_message = data_processor.import_whatsapp_data(temp_sms_file, round_number)
            if not sms_success:
                st.error(f"SMS Data Import Failed: {sms_message}")
                # Clean up temp files
                if os.path.exists(temp_sms_file):
                    os.remove(temp_sms_file)
                if os.path.exists(temp_post_file):
                    os.remove(temp_post_file)
                return
            
            # Import Post winners
            post_success, post_message = data_processor.import_post_winners(temp_post_file, round_number)
            if not post_success:
                st.error(f"Post Winners Import Failed: {post_message}")
                # Clean up temp files
                if os.path.exists(temp_sms_file):
                    os.remove(temp_sms_file)
                if os.path.exists(temp_post_file):
                    os.remove(temp_post_file)
                return
            
            # If both imports are successful, show success message
            st.success(f"SMS Data Import: {sms_message}")
            st.success(f"Post Winners Import: {post_message}")
            
            # Increment the Draw number for the next round
            next_draw = round_number + 1
            st.info(f"Next Draw Number: {next_draw} (for the next import)")
            
            # Clean up temp files
            if os.path.exists(temp_sms_file):
                os.remove(temp_sms_file)
            if os.path.exists(temp_post_file):
                os.remove(temp_post_file)


def select_winners_page():
    st.header("Select SMS Winners")
    
    round_number = st.number_input("Drow Number", min_value=1, value=1, step=1)
    num_winners = st.number_input("Number of Winners to Select", min_value=1, value=5, step=1)
    
    if st.button("Select Random Winners"):
        # Show loading message with spinner
        with st.spinner("Please wait, selecting winners. This may take a few minutes..."):
            # You can add a small delay here to ensure the spinner is visible
            # even if the operation is quick
            import time
            time.sleep(6)  # This gives users time to see the loading message
            
            # Original winner selection code
            success, message = winner_manager.select_whatsapp_winners(round_number, num_winners)
        
        # Show the result after the spinner is done
        if success:
            st.success(message)
        else:
            st.error(message)

def view_winners_page():
    st.header("View All Winners")
    
    round_number = st.number_input("Drow Number", min_value=1, value=1, step=1)
    
    # Using rows instead of columns for better table visibility
    if st.button("Show Winners"):
        # Modified query to get only winners from the specified round
        query = '''
            SELECT p.mobile_number, p.unique_code, p.message, p.source, w.round_number
            FROM participants p
            JOIN winners w ON p.id = w.participant_id
            WHERE w.round_number = ?
            ORDER BY p.source
        '''
        
        conn = sqlite3.connect(database.db_path)
        winners_df = pd.read_sql_query(query, conn, params=[round_number])
        conn.close()
        
        if winners_df.empty:
            st.warning(f"No winners found for Round {round_number}.")
        else:
            # Get all winners from all rounds to check for duplicates
            all_rounds_query = '''
                SELECT p.mobile_number, p.unique_code, w.round_number
                FROM participants p
                JOIN winners w ON p.id = w.participant_id
                ORDER BY w.round_number
            '''
            conn = sqlite3.connect(database.db_path)
            all_winners = pd.read_sql_query(all_rounds_query, conn)
            conn.close()
            
            # Add columns for duplicate tracking
            winners_df['is_duplicate'] = False
            winners_df['previous_rounds'] = ''
            winners_df['duplicate_reason'] = ''
            
            for idx, row in winners_df.iterrows():
                # Check for mobile number duplicates (same mobile, different code)
                mobile_matches = all_winners[
                    (all_winners['mobile_number'] == row['mobile_number']) & 
                    (all_winners['round_number'] != round_number)
                ]
                
                # Check for unique code duplicates (same code, different mobile)
                code_matches = all_winners[
                    (all_winners['unique_code'] == row['unique_code']) & 
                    (all_winners['round_number'] != round_number)
                ]
                
                # If there are occurrences in other rounds
                mobile_dup_rounds = mobile_matches['round_number'].tolist()
                code_dup_rounds = code_matches['round_number'].tolist()
                
                # Combine all duplicate rounds
                all_dup_rounds = sorted(list(set(mobile_dup_rounds + code_dup_rounds)))
                
                if all_dup_rounds:
                    winners_df.at[idx, 'is_duplicate'] = True
                    winners_df.at[idx, 'previous_rounds'] = ', '.join(map(str, all_dup_rounds))
                    
                    # Add reason for duplication
                    reasons = []
                    if mobile_dup_rounds:
                        reasons.append(f"Same mobile in rounds: {', '.join(map(str, mobile_dup_rounds))}")
                    if code_dup_rounds:
                        reasons.append(f"Same code in rounds: {', '.join(map(str, code_dup_rounds))}")
                    
                    winners_df.at[idx, 'duplicate_reason'] = "; ".join(reasons)
            
            st.write(f"Total Winners in Round {round_number}: {len(winners_df)}")
            st.write(f"WhatsApp Winners: {len(winners_df[winners_df['source'] == 'WhatsApp'])}")
            st.write(f"Post Winners: {len(winners_df[winners_df['source'] == 'Post'])}")
            st.write(f"Duplicate Winners: {len(winners_df[winners_df['is_duplicate']])}")
            
            # Highlight duplicates in the DataFrame
            st.dataframe(
                winners_df.style.apply(
                    lambda x: ['background-color: #FFC7CE' if x['is_duplicate'] else '' for _ in x], 
                    axis=1
                )
            )
    
    # Add a separator line
    st.markdown("---")
    
    # All Winners section below
    if st.button("Show All Winners"):
        # Get winners from all rounds
        query = '''
            SELECT p.mobile_number, p.unique_code, p.message, p.source, w.round_number
            FROM participants p
            JOIN winners w ON p.id = w.participant_id
            ORDER BY w.round_number, p.source
        '''
        
        conn = sqlite3.connect(database.db_path)
        all_winners_df = pd.read_sql_query(query, conn)
        conn.close()
        
        if all_winners_df.empty:
            st.warning("No winners found in any round.")
        else:
            # Create a duplicate detection DataFrame
            display_df = all_winners_df.copy()
            display_df['is_duplicate'] = False
            display_df['duplicate_reason'] = ""
            
            # Check for mobile number duplicates
            mobile_duplicates = display_df[display_df.duplicated(subset=['mobile_number'], keep=False)]
            mobile_groups = mobile_duplicates.groupby('mobile_number')
            
            # Check for unique code duplicates
            code_duplicates = display_df[display_df.duplicated(subset=['unique_code'], keep=False)]
            code_groups = code_duplicates.groupby('unique_code')
            
            # Mark mobile number duplicates
            for mobile, group in mobile_groups:
                rounds = group['round_number'].tolist()
                for index in group.index:
                    display_df.at[index, 'is_duplicate'] = True
                    current_round = display_df.at[index, 'round_number']
                    other_rounds = [r for r in rounds if r != current_round]
                    
                    if other_rounds:
                        reason = f"Same mobile in round(s): {', '.join(map(str, other_rounds))}"
                        if display_df.at[index, 'duplicate_reason']:
                            display_df.at[index, 'duplicate_reason'] += "; " + reason
                        else:
                            display_df.at[index, 'duplicate_reason'] = reason
            
            # Mark unique code duplicates
            for code, group in code_groups:
                rounds = group['round_number'].tolist()
                for index in group.index:
                    display_df.at[index, 'is_duplicate'] = True
                    current_round = display_df.at[index, 'round_number']
                    other_rounds = [r for r in rounds if r != current_round]
                    
                    if other_rounds:
                        reason = f"Same code in round(s): {', '.join(map(str, other_rounds))}"
                        if display_df.at[index, 'duplicate_reason']:
                            display_df.at[index, 'duplicate_reason'] += "; " + reason
                        else:
                            display_df.at[index, 'duplicate_reason'] = reason
            
            # Display counts
            st.write(f"Total Winners Across All Rounds: {len(all_winners_df)}")
            st.write(f"Duplicate Winners (same mobile or same code): {len(display_df[display_df['is_duplicate']])}")
            
            # Create two dataframes - one for clean winners, one for duplicates
            clean_df = display_df[~display_df['is_duplicate']].drop(columns=['is_duplicate', 'duplicate_reason'])
            duplicates_df = display_df[display_df['is_duplicate']]
            
            # Show duplicates with highlighting
            if not duplicates_df.empty:
                st.subheader("⚠️ Duplicate Winners (Same Mobile Number OR Same Unique Code)")
                st.markdown("""
                <style>
                .duplicate-winner {
                    color: red;
                    font-weight: bold;
                }
                </style>
                """, unsafe_allow_html=True)
                
                # Display duplicates with HTML formatting for red text
                for _, row in duplicates_df.iterrows():
                    st.markdown(
                        f"<div class='duplicate-winner'>Round {row['round_number']} - "
                        f"{row['mobile_number']} (Code: {row['unique_code']}) - {row['duplicate_reason']}</div>", 
                        unsafe_allow_html=True
                    )
                
                st.dataframe(duplicates_df)
            
            # Show clean winners
            if not clean_df.empty:
                st.subheader("Clean Winners (No Duplications)")
                st.dataframe(clean_df)
def export_winners_page():
    st.header("Export Winners to Excel")
    
    round_number = st.number_input("Drow Number", min_value=1, value=1, step=1)
    
    if st.button("Export Winners"):
        # Use the updated data_processor method to export
        success, result = data_processor.export_winners_to_excel(round_number)
        
        if success:
            # Get summary statistics
            conn = sqlite3.connect(database.db_path)
            
            # Count total, WhatsApp, and Post winners
            stats_query = """
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN p.source = 'WhatsApp' THEN 1 ELSE 0 END) as whatsapp,
                    SUM(CASE WHEN p.source = 'Post' THEN 1 ELSE 0 END) as post,
                    SUM(CASE 
                        WHEN p.mobile_number IN (
                            SELECT p2.mobile_number 
                            FROM participants p2
                            JOIN winners w2 ON p2.id = w2.participant_id
                            WHERE w2.round_number != ?
                        ) OR p.unique_code IN (
                            SELECT p2.unique_code 
                            FROM participants p2
                            JOIN winners w2 ON p2.id = w2.participant_id
                            WHERE w2.round_number != ?
                        ) THEN 1 ELSE 0 END
                    ) as duplicates
                FROM participants p
                JOIN winners w ON p.id = w.participant_id
                WHERE w.round_number = ?
            """
            
            cursor = conn.cursor()
            cursor.execute(stats_query, [round_number, round_number, round_number])
            stats = cursor.fetchone()
            conn.close()
            
            if stats and stats[0] > 0:  # If we have winners
                total, whatsapp, post, duplicates = stats
                
                st.success(f"Successfully exported winners to {result}")
                
                # Display summary with attractive formatting
                st.markdown(f"""
                <div style="padding: 10px; background-color: #f0f8ff; border-radius: 5px; margin-bottom: 10px;">
                    <h3>Round {round_number} Winners Summary</h3>
                    <ul>
                        <li><b>Total Winners:</b> {total}</li>
                        <li><b>WhatsApp Winners:</b> {whatsapp}</li>
                        <li><b>Post Winners:</b> {post}</li>
                        <li><b>Duplicate Winners:</b> {duplicates} (same mobile or code in other rounds)</li>
                    </ul>
                </div>
                """, unsafe_allow_html=True)
                
                # Provide download button
                with open(result, "rb") as file:
                    st.download_button(
                        label=f"Download Round {round_number} Winners",
                        data=file,
                        file_name=os.path.basename(result),
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
            else:
                st.warning(f"No winners found for Round {round_number}.")
        else:
            st.error(result)  # Display the error message

if __name__ == "__main__":
    main()
