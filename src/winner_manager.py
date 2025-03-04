
import random
from datetime import datetime

class WinnerManager:
    def __init__(self, database):
        self.database = database
def select_whatsapp_winners(self, round_number, num_winners):
    """Select unique winners based on both mobile_number and unique_code."""
    try:
            # Fetch all participants for the round
            participants = self.database.get_participants_by_round(round_number, "WhatsApp")
            
            # Fetch all previous winners
            previous_winners = self.database.get_all_winners()
            
            # Filter out participants who are already winners based on mobile_number and unique_code
            previous_winner_keys = set(zip(previous_winners['mobile_number'], previous_winners['unique_code']))
            eligible_participants = [p for p in participants if (p['mobile_number'], p['unique_code']) not in previous_winner_keys]
            
            if len(eligible_participants) < num_winners:
                return False, f"Not enough unique participants to select {num_winners} winners."
            
            # Randomly select winners
            selected_winners = random.sample(eligible_participants, num_winners)
            
            # Add selected winners to the database
            for winner in selected_winners:
                participant_id = winner[0]
                self.database.add_winner(participant_id, round_number, "WhatsApp")
            
            return True, f"Successfully selected {num_winners} WhatsApp winners for round {round_number}."
    except Exception as e:
        return False, f"Error selecting winners: {str(e)}"

