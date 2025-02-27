
import random
from datetime import datetime

class WinnerManager:
    def __init__(self, database):
        self.database = database
    
    def select_whatsapp_winners(self, round_number, num_winners):
        """Select random winners from WhatsApp participants, excluding previous winners."""
        # Get all mobile numbers that have already won in any round
        existing_winners = self.database.get_existing_winners()
        
        # Get eligible WhatsApp participants for this round who haven't won before
        eligible_participants = self.database.get_eligible_participants(round_number, existing_winners)
        
        if len(eligible_participants) < num_winners:
            return False, f"Not enough eligible participants. Found {len(eligible_participants)}, needed {num_winners}."
        
        # Select random winners
        selected_winners = random.sample(eligible_participants, num_winners)
        
        # Add to winners table
        for winner in selected_winners:
            participant_id = winner[0]
            self.database.add_winner(participant_id, round_number, "WhatsApp")
        
        return True, f"Successfully selected {num_winners} WhatsApp winners for round {round_number}."
