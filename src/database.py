
import sqlite3
import os
from datetime import datetime

class Database:
    def __init__(self, db_path="database/contest_winners.db"):
        # Ensure directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self.initialize_database()
        
    def initialize_database(self):
        """Initialize the SQLite database with required tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Table for all participants (both WhatsApp and Post)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS participants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mobile_number TEXT,
                unique_code TEXT,
                message TEXT,
                source TEXT,
                round_number INTEGER,
                date_added TIMESTAMP
            )
        ''')
        
        # Table for winners
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS winners (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                participant_id INTEGER,
                round_number INTEGER,
                source TEXT,
                selection_date TIMESTAMP,
                FOREIGN KEY (participant_id) REFERENCES participants (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def execute_query(self, query, params=None):
        """Execute a query and return the results."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
            
        conn.commit()
        last_id = cursor.lastrowid
        
        try:
            results = cursor.fetchall()
        except sqlite3.Error:
            results = []
            
        conn.close()
        return results, last_id
    
    def add_participant(self, mobile_number, unique_code, message, source, round_number):
        """Add a new participant to the database."""
        query = '''
            INSERT INTO participants 
            (mobile_number, unique_code, message, source, round_number, date_added) 
            VALUES (?, ?, ?, ?, ?, ?)
        '''
        params = (mobile_number, unique_code, message, source, round_number, datetime.now())
        _, participant_id = self.execute_query(query, params)
        return participant_id
    
    def add_winner(self, participant_id, round_number, source):
        """Add a participant as a winner."""
        query = '''
            INSERT INTO winners
            (participant_id, round_number, source, selection_date)
            VALUES (?, ?, ?, ?)
        '''
        params = (participant_id, round_number, source, datetime.now())
        self.execute_query(query, params)
    
    def get_existing_winners(self):
        """Get mobile numbers of all existing winners."""
        query = '''
            SELECT p.mobile_number FROM participants p
            JOIN winners w ON p.id = w.participant_id
        '''
        results, _ = self.execute_query(query)
        return [row[0] for row in results]
    
    def get_eligible_participants(self, round_number, existing_winners):
        """Get eligible participants who haven't won before."""
        if not existing_winners:
            query = '''
                SELECT id, mobile_number, unique_code, message FROM participants
                WHERE source = 'WhatsApp' AND round_number = ?
            '''
            params = (round_number,)
        else:
            placeholders = ','.join(['?'] * len(existing_winners))
            query = f'''
                SELECT id, mobile_number, unique_code, message FROM participants
                WHERE source = 'WhatsApp' AND round_number = ? 
                AND mobile_number NOT IN ({placeholders})
            '''
            params = [round_number] + existing_winners
            
        results, _ = self.execute_query(query, params)
        return results
    
    def get_participants_by_round(self, round_number, source):
        """Get all participants for a specific round and source."""
        query = '''
            SELECT id, mobile_number, unique_code, message FROM participants
            WHERE round_number = ? AND source = ?
        '''
        params = (round_number, source)
        results, _ = self.execute_query(query, params)
        return results

    def get_all_winners(self):
        """Get all previous winners with their mobile numbers and unique codes."""
        query = '''
            SELECT p.mobile_number, p.unique_code 
            FROM participants p
            JOIN winners w ON p.id = w.participant_id
        '''
        results, _ = self.execute_query(query)
        
        # Convert results to a dictionary-like structure with lists
        winners = {
            'mobile_number': [row[0] for row in results],
            'unique_code': [row[1] for row in results]
        }
        return winners
