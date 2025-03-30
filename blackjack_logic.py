# --- START OF FILE blackjack_logic.py ---
import math
# Use CARD_RANKS for initialization, COUNTING_SYSTEM for optional Hi-Lo display
from config import NUM_DECKS, CARD_RANKS, BASIC_STRATEGY, COUNTING_SYSTEM

class BlackjackLogic:
    def __init__(self, num_decks=NUM_DECKS):
        self.num_decks = num_decks
        # Optional: Keep Hi-Lo count for simple display/betting alongside exact tracking
        self.hi_lo_running_count = 0
        self.reset_shoe()

    def reset_shoe(self):
        """Resets the shoe, tracking individual card ranks remaining."""
        self.total_cards_in_shoe = self.num_decks * 52
        # Dictionary to store remaining counts of each rank
        self.remaining_cards = {}
        # Initialize shoe composition: 4 of each rank (2-9, T, J, Q, K, A) per deck
        for rank in CARD_RANKS: # Uses the list ['2', '3', ..., 'K', 'A']
            self.remaining_cards[rank] = 4 * self.num_decks

        self.cards_seen_count = 0
        self.hi_lo_running_count = 0 # Reset simple count too
        print("Shoe reset. Tracking remaining ranks.")
        # print(f"Initial Deck: {self.remaining_cards}") # Debugging

    def _get_card_value_numeric(self, card_rank):
        """Gets the numerical value for adding hand totals (T,J,Q,K=10, A=11 initially)."""
        rank = str(card_rank).upper()
        if rank.isdigit():
            return int(rank)
        elif rank in ['T', 'J', 'Q', 'K']:
            return 10
        elif rank == 'A':
            return 11 # Ace is 11 initially
        else:
            print(f"Warning: Invalid rank '{rank}' encountered in _get_card_value_numeric.")
            return 0

    def _get_card_value_hi_lo(self, card_rank):
        """Gets the Hi-Lo value for optional simple counting display."""
        return COUNTING_SYSTEM.get(str(card_rank).upper(), 0)

    def remove_card_from_shoe(self, card_rank):
        """Decrements the count of a specific rank remaining in the shoe."""
        rank_upper = str(card_rank).upper()
        if rank_upper in self.remaining_cards:
            if self.remaining_cards[rank_upper] > 0:
                self.remaining_cards[rank_upper] -= 1
                self.cards_seen_count += 1
                # Optional: Update simple Hi-Lo count as well
                self.hi_lo_running_count += self._get_card_value_hi_lo(rank_upper)
                print(f"Removed: {rank_upper}. Remaining {rank_upper}'s: {self.remaining_cards[rank_upper]}. Seen: {self.cards_seen_count}. HiLo RC: {self.hi_lo_running_count}")
            else:
                print(f"Error: Tried to remove {rank_upper}, but none remaining according to tracker!")
        else:
            print(f"Warning: Tried to remove invalid rank '{rank_upper}'.")

    def get_hi_lo_true_count(self):
        """Calculates the traditional Hi-Lo true count for display/basic betting."""
        total_remaining = self.total_cards_in_shoe - self.cards_seen_count
        if total_remaining <= 0: return 0 # Avoid division by zero

        decks_remaining = total_remaining / 52.0
        min_decks_for_calc = 0.25 # Use a smaller minimum for single deck
        if decks_remaining < min_decks_for_calc:
             decks_remaining = min_decks_for_calc

        true_count = self.hi_lo_running_count / decks_remaining
        return round(true_count, 2)

    def get_hand_value(self, hand):
        """Calculates the Blackjack value of a hand (list of card ranks)."""
        if not hand: return 0
        ace_count = hand.count('A')
        total = 0
        for card in hand:
            total += self._get_card_value_numeric(card)

        while total > 21 and ace_count > 0:
            total -= 10
            ace_count -= 1
        return total

    # --- ADDED: Calculate Bust Probability on Next Hit ---
    def calculate_bust_probability(self, player_hand):
        """
        Calculates the probability of busting if the player hits their current hand,
        based on the exact cards remaining in the shoe.
        """
        current_total = self.get_hand_value(player_hand)
        if current_total >= 21: # Already busted or 21, can't hit
            return 1.0 if current_total > 21 else 0.0

        bust_card_count = 0
        total_remaining_cards = self.total_cards_in_shoe - self.cards_seen_count

        if total_remaining_cards <= 0:
            print("Warning: No cards remaining to calculate bust probability.")
            return 0.0 # Or handle as error

        # Iterate through each possible rank that could be drawn
        for rank in CARD_RANKS:
            # Check how many of this rank are left
            remaining_count = self.remaining_cards.get(rank, 0)
            if remaining_count <= 0:
                continue # No cards of this rank left

            # Simulate adding this card to the hand
            potential_new_hand = player_hand + [rank]
            potential_new_total = self.get_hand_value(potential_new_hand)

            # If drawing this rank leads to a bust
            if potential_new_total > 21:
                bust_card_count += remaining_count # Add the number of remaining cards of this rank

        # Probability is the number of cards that cause a bust divided by total remaining cards
        bust_probability = bust_card_count / total_remaining_cards
        # print(f"Debug: Bust prob calc: BustCards={bust_card_count}, TotalRemaining={total_remaining_cards}, Prob={bust_probability:.3f}") # Debugging
        return bust_probability

    # --- Basic Strategy Lookup (Remains the same, relies on config.py) ---
    def get_basic_strategy_move(self, player_hand, dealer_up_card):
        """Determines the basic strategy move using the table in config.py."""
        # ... (Keep the existing implementation from the previous version) ...
        if not player_hand or not dealer_up_card: return "N/A"
        player_total = self.get_hand_value(player_hand)
        dealer_value = self._get_card_value_numeric(dealer_up_card)
        if player_total > 21: return 'Bust'
        if player_total < 5: return 'H'
        is_pair = len(player_hand) == 2 and player_hand[0] == player_hand[1]
        is_soft = 'A' in player_hand and self.get_hand_value([c for c in player_hand if c != 'A']) + 11 * player_hand.count('A') == player_total
        hand_type = 'N/A'; strat_key = None
        try:
            if is_pair:
                hand_type = 'Pair'; pair_tuple = tuple(sorted(player_hand))
                if dealer_value in BASIC_STRATEGY.get(hand_type, {}) and pair_tuple in BASIC_STRATEGY[hand_type].get(dealer_value, {}): strat_key = pair_tuple
                else: is_pair = False
            if not is_pair:
                if is_soft: hand_type = 'Soft'; strat_key = player_total
                else: hand_type = 'Hard'; strat_key = player_total
            if hand_type == 'N/A' or strat_key is None: return "Err"
            strategy_for_dealer = BASIC_STRATEGY.get(hand_type, {}).get(dealer_value, {})
            if strat_key in strategy_for_dealer: return strategy_for_dealer[strat_key]
            else: # Fallback
                 print(f"Warning: Strategy missing for HandType='{hand_type}', Dealer='{dealer_value}', PlayerKey='{strat_key}'. Defaulting.")
                 if hand_type == 'Hard': return 'S' if player_total >= 17 else 'H'
                 elif hand_type == 'Soft': return 'S' if player_total >= 19 else 'H'
                 else: return 'S' if player_total >= 17 else 'H'
        except KeyError as e: print(f"KeyError BS: {e}. HT='{hand_type}', D='{dealer_value}', PK='{strat_key}'"); return "Err"
        except Exception as e: print(f"Unexpected error BS: {e}"); return "Err"


    # --- Betting Recommendation (Still uses simple Hi-Lo True Count) ---
    def get_bet_recommendation(self, base_bet=1):
        """Recommends a bet size based on Hi-Lo true count."""
        # ... (Keep the existing implementation) ...
        true_count = self.get_hi_lo_true_count()
        bet_multiplier = 1.0
        if true_count >= 2: bet_multiplier = math.floor(true_count)
        bet_units = max(1, bet_multiplier)
        return int(bet_units * base_bet)

# --- END OF FILE blackjack_logic.py ---