
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
            st.write(f"Total Winners: {len(winners_df)}")
            st.write(f"WhatsApp Winners: {len(winners_df[winners_df['source'] == 'WhatsApp'])}")
            st.write(f"Post Winners: {len(winners_df[winners_df['source'] == 'Post'])}")
            st.dataframe(winners_df)

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
