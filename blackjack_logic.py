import math
import random
import logging
from collections import defaultdict, deque
from copy import deepcopy
from config import (NUM_DECKS, CARD_RANKS, BASIC_STRATEGY, COUNTING_SYSTEM, INDEX_PLAYS,
                    EXPECTED_DEALER_BUST_RATES_S17_SINGLE_DECK, DEALER_HISTORY_MIN_SAMPLES,
                    DEALER_BUST_RATE_THRESHOLD_MULTIPLIER, MAX_DEALER_OUTCOME_HISTORY)

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

class BlackjackLogic:
    def __init__(self, num_decks=NUM_DECKS):
        self.num_decks = num_decks
        self.hi_lo_running_count = 0
        self.reset_shoe()
        self.card_removal_history = []
        self.dealer_outcome_history = defaultdict(lambda: deque(maxlen=MAX_DEALER_OUTCOME_HISTORY))

    def _get_internal_card_key(self, full_card_label):
        """Converts detected label (e.g., '10h', 'Ac') to consistent internal key ('TH', 'AC')."""
        if not full_card_label or not isinstance(full_card_label, str):
            logging.warning(f"Invalid label type for key generation: {full_card_label}")
            return None
        label_upper = full_card_label.upper()
        if label_upper.startswith('10'):
            suit = label_upper[2:]
            if len(suit) == 1 and suit in ['S', 'H', 'D', 'C']:
                return 'T' + suit  # Use 'T' for Ten
        elif len(label_upper) == 2:  # Expect Rank+Suit
            rank = label_upper[0]
            suit = label_upper[1]
            if rank in CARD_RANKS and suit in ['S', 'H', 'D', 'C']:
                if rank == '1':  # Should not happen if model outputs 10
                    rank = 'T'
                return rank + suit
        logging.warning(f"Could not create valid internal key from label '{full_card_label}'.")
        return None

    def _get_rank_from_key_or_label(self, key_or_label):
        """Extracts rank ('A', 'K', 'T', '7', etc.) from internal key or label."""
        if not key_or_label or not isinstance(key_or_label, str):
            return None
        key_upper = key_or_label.upper()
        if key_upper.startswith('10') or key_upper.startswith('T'):
            return 'T'
        elif len(key_upper) >= 1 and key_upper[0] in CARD_RANKS:
            return key_upper[0]
        else:
            return None

    def reset_shoe(self):
        """Resets the shoe using standardized keys ('AS', 'KH', 'TS')."""
        self.total_cards_in_shoe = self.num_decks * 52
        self.remaining_cards = {}
        if self.num_decks == 1:
            suits = ['S', 'H', 'D', 'C']
            ranks_for_init = CARD_RANKS  # e.g., ['2', '3', ..., 'A']
            for rank in ranks_for_init:
                for suit in suits:
                    card_key = rank + suit
                    self.remaining_cards[card_key] = 1
        else:
            logging.warning("Multi-deck rank tracking not fully supported. Tracking by rank only.")
            for rank in CARD_RANKS:
                self.remaining_cards[rank] = 4 * self.num_decks

        self.cards_seen_count = 0
        self.hi_lo_running_count = 0
        self.card_removal_history = []
        logging.info(f"Shoe reset ({self.num_decks} deck)... Tracking unique cards.")

    def _get_card_value_numeric(self, card_rank):
        """Gets the numerical value using standard ranks ('T' for 10)."""
        rank = str(card_rank).upper()
        if rank.isdigit():
            return int(rank)
        elif rank in ['T', 'J', 'Q', 'K']:
            return 10
        elif rank == 'A':
            return 11
        else:
            logging.warning(f"Invalid rank '{rank}' in numeric value")
            return 0

    def _get_card_value_hi_lo(self, card_rank):
        """Gets the Hi-Lo value using standard ranks ('T' for 10)."""
        return COUNTING_SYSTEM.get(str(card_rank).upper(), 0)

    def remove_card_from_shoe(self, full_card_label):
        """Removes a card using a standardized key ('AS', 'KH', 'TS')."""
        card_key = self._get_internal_card_key(full_card_label)
        if card_key is None:
            return

        rank_for_counting = self._get_rank_from_key_or_label(card_key)
        if rank_for_counting is None:
            return

        if self.num_decks != 1:
            logging.error("Multi-deck removal not fully supported here.")
            return

        if card_key in self.remaining_cards:
            if self.remaining_cards[card_key] > 0:
                self.remaining_cards[card_key] -= 1
                self.cards_seen_count += 1
                self.hi_lo_running_count += self._get_card_value_hi_lo(rank_for_counting)
                self.card_removal_history.append(card_key)
                logging.info(f"Removed: {card_key}. Rem: {self.remaining_cards[card_key]}, Seen: {self.cards_seen_count}, RC: {self.hi_lo_running_count}")
            else:
                logging.error(f"Tried to remove {card_key}, already removed!")
        else:
            logging.warning(f"Card key '{card_key}' (from '{full_card_label}') not found in remaining_cards.")

    def add_card_back_to_shoe(self, full_card_label_or_key):
        """Undo removal by adding back a card using standardized key."""
        if self.num_decks != 1:
            logging.error("Undo requires NUM_DECKS=1.")
            return False
        card_key = self._get_internal_card_key(full_card_label_or_key)
        if card_key is None:
            return False

        rank_for_counting = self._get_rank_from_key_or_label(card_key)
        if rank_for_counting is None:
            return False

        if card_key in self.remaining_cards:
            if self.remaining_cards[card_key] < 1:  # For single deck, max is 1
                self.remaining_cards[card_key] += 1
                self.cards_seen_count -= 1
                self.hi_lo_running_count -= self._get_card_value_hi_lo(rank_for_counting)
                if self.card_removal_history and self.card_removal_history[-1] == card_key:
                    self.card_removal_history.pop()
                logging.info(f"UNDO: Added back {card_key}. Rem: {self.remaining_cards[card_key]}, Seen: {self.cards_seen_count}, RC: {self.hi_lo_running_count}")
                return True
            else:
                logging.error(f"Count max for {card_key}.")
        else:
            logging.warning(f"Invalid card key '{card_key}' for UNDO.")
        return False

    def get_hi_lo_true_count(self):
        total_remaining = self.total_cards_in_shoe - self.cards_seen_count
        if total_remaining <= 0:
            return 0
        decks_remaining = total_remaining / 52.0
        if decks_remaining < 0.1:
            return 0
        true_count = self.hi_lo_running_count / decks_remaining
        return round(true_count, 2)

    def get_hand_value(self, hand_labels):
        if not hand_labels:
            return 0
        ranks_in_hand = [self._get_rank_from_key_or_label(lbl) for lbl in hand_labels if self._get_rank_from_key_or_label(lbl) is not None]
        if len(ranks_in_hand) != len(hand_labels):
            logging.warning(f"Some invalid labels in get_hand_value: {hand_labels}")
        ace_count = ranks_in_hand.count('A')
        total = sum(self._get_card_value_numeric(rank) for rank in ranks_in_hand)
        while total > 21 and ace_count > 0:
            total -= 10
            ace_count -= 1
        return total

    def calculate_bust_probability(self, player_hand_labels):
        logging.debug("\n--- DEBUG: calculate_bust_probability ---")
        logging.debug(f"Input Hand Labels: {player_hand_labels}")
        current_total = self.get_hand_value(player_hand_labels)
        logging.debug(f"Current Hand Total: {current_total}")
        if current_total >= 21:
            result_str = 'Busted' if current_total > 21 else '21/Stand'
            logging.debug(f"Result: {result_str}")
            logging.debug("--- END DEBUG ---")
            return 1.0 if current_total > 21 else 0.0

        bust_card_count = 0
        total_remaining_cards = self.total_cards_in_shoe - self.cards_seen_count
        logging.debug(f"Total Remaining Cards in Shoe: {total_remaining_cards}")
        if total_remaining_cards <= 0:
            logging.warning("No cards remaining.")
            logging.debug("Result: Bust Prob = 0.0")
            logging.debug("--- END DEBUG ---")
            return 0.0

        logging.debug("Checking remaining cards for bust potential:")
        if self.num_decks == 1:
            for card_key, remaining_count in self.remaining_cards.items():
                if remaining_count <= 0:
                    continue
                potential_new_total = self.get_hand_value(player_hand_labels + [card_key])
                will_bust = potential_new_total > 21
                logging.debug(f"  - Card: {card_key}, Rem: {remaining_count}, NewTotal: {potential_new_total}, Busts?: {will_bust}")
                if will_bust:
                    bust_card_count += remaining_count
        else:
            for rank in CARD_RANKS:
                remaining_rank_count = self.remaining_cards.get(rank, 0)
                if remaining_rank_count <= 0:
                    continue
                potential_new_total = self.get_hand_value(player_hand_labels + [rank])
                will_bust = potential_new_total > 21
                logging.debug(f"  - Rank: {rank}, Rem: {remaining_rank_count}, NewTotal: {potential_new_total}, Busts?: {will_bust}")
                if will_bust:
                    bust_card_count += remaining_rank_count

        logging.debug(f"Total Count of Cards Causing Bust: {bust_card_count}")
        bust_probability = bust_card_count / total_remaining_cards if total_remaining_cards > 0 else 0
        logging.debug(f"Result: Bust Prob = {bust_card_count} / {total_remaining_cards} = {bust_probability:.3f}")
        logging.debug("--- END DEBUG ---")
        return bust_probability

    def get_basic_strategy_move(self, player_hand_labels, dealer_up_card_label):
        if not player_hand_labels or not dealer_up_card_label:
            return "N/A"
        player_ranks = []
        for label in player_hand_labels:
            rank = self._get_rank_from_key_or_label(label)
            if rank:
                player_ranks.append(rank)
            else:
                logging.warning(f"Invalid rank from '{label}' in basic strategy")
                return "Err"
        if not player_ranks:
            return "Err"

        dealer_up_rank = self._get_rank_from_key_or_label(dealer_up_card_label)
        if dealer_up_rank not in CARD_RANKS:
            logging.warning(f"Invalid dealer rank from '{dealer_up_card_label}'")
            return "Err"

        player_total = self.get_hand_value(player_hand_labels)
        dealer_value = self._get_card_value_numeric(dealer_up_rank)
        if player_total > 21:
            return 'Bust'

        is_pair = len(player_ranks) == 2 and player_ranks[0] == player_ranks[1]
        ace_present = 'A' in player_ranks
        non_ace_total = sum(self._get_card_value_numeric(r) for r in player_ranks if r != 'A')
        is_soft = ace_present and (player_total > non_ace_total + player_ranks.count('A'))

        hand_type = 'N/A'
        strat_key = None
        try:
            if is_pair:
                hand_type = 'Pair'
                pair_tuple = tuple(sorted(player_ranks))
                if dealer_value in BASIC_STRATEGY.get(hand_type, {}) and pair_tuple in BASIC_STRATEGY[hand_type].get(dealer_value, {}):
                    strat_key = pair_tuple
                else:
                    is_pair = False  # Fallback if no strategy found for pair
            if not is_pair:
                if is_soft:
                    hand_type = 'Soft'
                    strat_key = player_total
                else:
                    hand_type = 'Hard'
                    strat_key = player_total
            if hand_type == 'N/A' or strat_key is None:
                logging.debug("Could not determine hand type/key for basic strategy.")
                return "Err"

            strategy_for_dealer = BASIC_STRATEGY.get(hand_type, {}).get(dealer_value, {})
            if strat_key in strategy_for_dealer:
                return strategy_for_dealer[strat_key]
            else:
                logging.warning(f"Strategy missing for HT='{hand_type}', D='{dealer_value}', PK='{strat_key}'. Defaulting.")
                if hand_type == 'Hard':
                    return 'S' if player_total >= 17 else 'H'
                elif hand_type == 'Soft':
                    return 'S' if player_total >= 19 else 'H'
                else:
                    return 'S' if player_total >= 17 else 'H'
        except KeyError as e:
            logging.error(f"KeyError in basic strategy: {e}. HT='{hand_type}', D='{dealer_value}', PK='{strat_key}'")
            return "Err"
        except Exception as e:
            logging.error(f"Unexpected error in basic strategy: {e}")
            return "Err"

    def get_bet_recommendation(self, base_bet=1):
        true_count = self.get_hi_lo_true_count()
        bet_multiplier = 1.0
        if true_count >= 2:
            bet_multiplier = math.floor(true_count)
        bet_units = max(1, bet_multiplier)
        return int(bet_units * base_bet)

    def simulate_dealer_turn(self, current_dealer_hand_labels):
        """
        Simulate the dealer's turn without modifying the actual shoe.
        Returns a tuple (simulated_hand, final_total or 'Bust').
        """
        if not current_dealer_hand_labels:
            logging.error("Cannot simulate dealer turn with empty hand.")
            return [], 'Error'
        
        # Create a simulation copy of the current shoe state
        sim_remaining_cards = deepcopy(self.remaining_cards)
        sim_cards_seen = self.cards_seen_count
        sim_running_count = self.hi_lo_running_count
        
        dealer_hand_sim = list(current_dealer_hand_labels)
        logging.info(f"Simulating Dealer Turn with starting hand: {dealer_hand_sim}")
        
        while True:
            current_total = self.get_hand_value(dealer_hand_sim)
            logging.info(f"  Dealer Sim: Hand={dealer_hand_sim}, Total={current_total}")
            if current_total >= 17:
                logging.info(f"  Dealer Sim: Stands at {current_total}")
                return dealer_hand_sim, current_total
            logging.info(f"  Dealer Sim: Hits at {current_total}")
            
            total_remaining = self.total_cards_in_shoe - sim_cards_seen
            if total_remaining <= 0:
                logging.error("No cards left in simulation shoe!")
                return dealer_hand_sim, 'Error - No Cards'
            
            remaining_deck_list = []
            if self.num_decks == 1:
                for card_key, count in sim_remaining_cards.items():
                    if count > 0:
                        remaining_deck_list.append(card_key)
            else:
                for rank_key, count in sim_remaining_cards.items():
                    remaining_deck_list.extend([rank_key] * count)
            if not remaining_deck_list:
                logging.error("Simulation remaining deck empty!")
                return dealer_hand_sim, 'Error - Deck Empty'
            
            drawn_card_label = random.choice(remaining_deck_list)
            logging.info(f"  Dealer Sim: Draws {drawn_card_label}")
            dealer_hand_sim.append(drawn_card_label)
            # Update simulation state
            if drawn_card_label in sim_remaining_cards and sim_remaining_cards[drawn_card_label] > 0:
                sim_remaining_cards[drawn_card_label] -= 1
                sim_cards_seen += 1
                drawn_rank = self._get_rank_from_key_or_label(drawn_card_label)
                sim_running_count += self._get_card_value_hi_lo(drawn_rank)
            new_total = self.get_hand_value(dealer_hand_sim)
            if new_total > 21:
                logging.info(f"  Dealer Sim: Busts with {new_total}")
                return dealer_hand_sim, 'Bust'

    def record_dealer_outcome(self, up_card_rank, final_total_or_bust):
        outcome = final_total_or_bust
        up_card_key = str(up_card_rank).upper()
        if up_card_key in CARD_RANKS:
            self.dealer_outcome_history[up_card_key].append(outcome)
            logging.info(f"Dealer Outcome Recorded: Up={up_card_key}, Final={outcome}...")
        else:
            logging.warning(f"Invalid upcard rank for history: {up_card_key}")

    def check_dealer_bust_rate_anomaly(self, up_card_rank):
        up_card_key = str(up_card_rank).upper()
        history = self.dealer_outcome_history.get(up_card_key)
        if history is None or len(history) < DEALER_HISTORY_MIN_SAMPLES:
            return None
        num_samples = len(history)
        expected_rate = EXPECTED_DEALER_BUST_RATES_S17_SINGLE_DECK.get(up_card_key, None)
        if expected_rate is None:
            logging.warning(f"No expected bust rate for {up_card_key}.")
            return None
        bust_count = sum(1 for outcome in history if outcome == 'Bust')
        observed_rate = bust_count / num_samples
        threshold = expected_rate * DEALER_BUST_RATE_THRESHOLD_MULTIPLIER
        is_anomaly = observed_rate < threshold
        logging.info(f"Bust Rate Check (Up={up_card_key}): Obs={observed_rate:.2f} ({bust_count}/{num_samples}), Exp={expected_rate:.2f}, Thr={threshold:.2f}, Anomaly={is_anomaly}")
        if is_anomaly:
            return f"Low Bust Rate ({observed_rate:.1%})"
        else:
            return None

# End of blackjack_logic.py
