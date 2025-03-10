
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
        success, message = winner_manager.select_whatsapp_winners(round_number, num_winners)
        if success:
            st.success(message)
        else:
            st.error(message)

def view_winners_page():
    st.header("View All Winners")
    
    round_number = st.number_input("Drow Number", min_value=1, value=1, step=1)
    
    col1, col2 = st.columns(2)
    
    with col1:
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
                # Identify duplicates based on both mobile_number and unique_code
                # For this specific round, we need to check if these winners appeared in previous rounds
                
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
                
                # Mark as duplicate if this mobile number & code combination appears in other rounds
                winners_df['is_duplicate'] = False
                winners_df['previous_rounds'] = ''
                
                for idx, row in winners_df.iterrows():
                    # Find all occurrences of this mobile number and unique code
                    matches = all_winners[
                        (all_winners['mobile_number'] == row['mobile_number']) & 
                        (all_winners['unique_code'] == row['unique_code'])
                    ]
                    
                    # If there are occurrences in other rounds
                    other_rounds = matches[matches['round_number'] != round_number]['round_number'].tolist()
                    
                    if other_rounds:
                        winners_df.at[idx, 'is_duplicate'] = True
                        winners_df.at[idx, 'previous_rounds'] = ', '.join(map(str, other_rounds))
                
                st.write(f"Total Winners in Round {round_number}: {len(winners_df)}")
                st.write(f"WhatsApp Winners: {len(winners_df[winners_df['source'] == 'WhatsApp'])}")
                st.write(f"Post Winners: {len(winners_df[winners_df['source'] == 'Post'])}")
                
                # Highlight duplicates in the DataFrame
                st.dataframe(
                    winners_df.style.apply(
                        lambda x: ['background-color: #FFC7CE' if x['is_duplicate'] else '' for _ in x], 
                        axis=1
                    )
                )
    
    with col2:  
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
                # Find duplicates
                duplicate_mobile_numbers = all_winners_df[all_winners_df.duplicated(subset=['mobile_number'], keep=False)]['mobile_number'].unique()
                
                # Create a new DataFrame for display with color formatting
                display_df = all_winners_df.copy()
                display_df['status'] = ""
                
                # Mark duplicates and add information
                for mobile in duplicate_mobile_numbers:
                    occurrences = all_winners_df[all_winners_df['mobile_number'] == mobile].sort_values('round_number')
                    rounds = occurrences['round_number'].tolist()
                    
                    # For each occurrence, add status information
                    for index, row in occurrences.iterrows():
                        current_round = row['round_number']
                        other_rounds = [r for r in rounds if r != current_round]
                        if other_rounds:
                            duplicate_info = f"Duplicated winner from round(s): {', '.join(map(str, other_rounds))}"
                            display_df.at[index, 'status'] = duplicate_info
                
                # Display counts
                st.write(f"Total Winners Across All Rounds: {len(all_winners_df)}")
                st.write(f"Unique Winners: {len(all_winners_df['mobile_number'].unique())}")
                st.write(f"Duplicate Winners: {len(duplicate_mobile_numbers)}")
                
                # Create two dataframes - one for clean winners, one for duplicates
                clean_df = display_df[display_df['status'] == ""].drop(columns=['status'])
                duplicates_df = display_df[display_df['status'] != ""]
                
                # Show duplicates with highlighting
                if not duplicates_df.empty:
                    st.subheader("⚠️ Duplicate Winners (Appearing in Multiple Rounds)")
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
                            f"{row['mobile_number']} - {row['status']}</div>", 
                            unsafe_allow_html=True
                        )
                    
                    st.dataframe(duplicates_df)
                
                # Show clean winners
                if not clean_df.empty:
                    st.subheader("Clean Winners (Single Drow Only)")
                    st.dataframe(clean_df)

def export_winners_page():
    st.header("Export Winners to Excel")
    
    round_number = st.number_input("Drow Number", min_value=1, value=1, step=1)
    
    if st.button("Export Winners"):
        success, result = data_processor.export_winners_to_excel(round_number)
        if success:
            st.success(f"Successfully exported winners to {result}")
            
            # Provide download button
            with open(result, "rb") as file:
                st.download_button(
                    label=f"Download Drow {round_number} Winners",
                    data=file,
                    file_name=os.path.basename(result),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        else:
            st.error(result)

if __name__ == "__main__":
    main()
