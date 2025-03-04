
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
    st.set_page_config(page_title="Contest Winner Management System", layout="wide")
    
    st.title("Contest Winner Management System")
    
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

def import_data_page():
    st.header("Import Data")
    
    round_number = st.number_input("Round Number", min_value=1, value=1, step=1)
    
    st.subheader("Import WhatsApp Data")
    whatsapp_file = st.file_uploader("Upload WhatsApp Excel Sheet", type=["xlsx", "xls"], key="whatsapp")
    if st.button("Import WhatsApp Data"):
        if whatsapp_file:
            # Save uploaded file temporarily
            temp_file = f"data/temp_whatsapp_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
            with open(temp_file, "wb") as f:
                f.write(whatsapp_file.getbuffer())
            
            success, message = data_processor.import_whatsapp_data(temp_file, round_number)
            if success:
                st.success(message)
            else:
                st.error(message)
            
            # Clean up temp file
            if os.path.exists(temp_file):
                os.remove(temp_file)
        else:
            st.warning("Please upload a WhatsApp data file.")
    
    st.subheader("Import Post Winners")
    post_file = st.file_uploader("Upload Post Winners Excel Sheet", type=["xlsx", "xls"], key="post")
    if st.button("Import Post Winners"):
        if post_file:
            # Save uploaded file temporarily
            temp_file = f"data/temp_post_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
            with open(temp_file, "wb") as f:
                f.write(post_file.getbuffer())
            
            success, message = data_processor.import_post_winners(temp_file, round_number)
            if success:
                st.success(message)
            else:
                st.error(message)
            
            # Clean up temp file
            if os.path.exists(temp_file):
                os.remove(temp_file)
        else:
            st.warning("Please upload a Post winners file.")

def select_winners_page():
    st.header("Select WhatsApp Winners")
    
    round_number = st.number_input("Round Number", min_value=1, value=1, step=1)
    num_winners = st.number_input("Number of Winners to Select", min_value=1, value=5, step=1)
    
    if st.button("Select Random Winners"):
        success, message = winner_manager.select_whatsapp_winners(round_number, num_winners)
        if success:
            st.success(message)
        else:
            st.error(message)

def view_winners_page():
    st.header("View All Winners")
    
    round_number = st.number_input("Round Number", min_value=1, value=1, step=1)
    
    if st.button("Show Winners"):
        winners_df = data_processor.get_all_winners(round_number)
        
        if winners_df.empty:
            st.warning(f"No winners found for Round {round_number}.")
        else:
            # Identify duplicates based on both mobile_number and unique_code
            winners_df['is_duplicate'] = winners_df.duplicated(subset=['mobile_number', 'unique_code'], keep=False)
            winners_df['previous_rounds'] = winners_df.groupby(['mobile_number', 'unique_code'])['round_number'].transform(lambda x: ', '.join(map(str, x[:-1])))
            
            st.write(f"Total Winners: {len(winners_df)}")
            st.write(f"WhatsApp Winners: {len(winners_df[winners_df['source'] == 'WhatsApp'])}")
            st.write(f"Post Winners: {len(winners_df[winners_df['source'] == 'Post'])}")
            
            # Highlight duplicates in the DataFrame
            st.dataframe(
                winners_df.style.apply(
                    lambda x: ['background-color: #FFC7CE' if x['is_duplicate'] else '' for _ in x], 
                    axis=1
                )
            )
    
    else:  # All Rounds with duplicate detection
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
                    st.subheader("Clean Winners (Single Round Only)")
                    st.dataframe(clean_df)

def export_winners_page():
    st.header("Export Winners to Excel")
    
    round_number = st.number_input("Round Number", min_value=1, value=1, step=1)
    
    if st.button("Export Winners"):
        success, result = data_processor.export_winners_to_excel(round_number)
        if success:
            st.success(f"Successfully exported winners to {result}")
            
            # Provide download button
            with open(result, "rb") as file:
                st.download_button(
                    label=f"Download Round {round_number} Winners",
                    data=file,
                    file_name=os.path.basename(result),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        else:
            st.error(result)

if __name__ == "__main__":
    main()
