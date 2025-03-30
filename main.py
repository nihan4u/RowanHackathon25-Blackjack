# --- START OF FILE main.py ---
import cv2
import time
from collections import deque
from config import *
from card_detector import CardDetector
from blackjack_logic import BlackjackLogic
from gemini_integration import GeminiIntegration
from utils import draw_hud_element, format_hand, wrap_text

BUST_PROBABILITY_THRESHOLD = 0.50

class CasinoAI:
    # --- Indent Level 0 ---
    def __init__(self):
        # --- Indent Level 1 ---
        print("Initializing AI...")
        cam_idx = CAMERA_INDEX; num_decks = NUM_DECKS
        self.card_detector = CardDetector()
        self.blackjack_logic = BlackjackLogic(num_decks=num_decks)
        self.gemini_integration = GeminiIntegration()
        self.cap = cv2.VideoCapture(cam_idx)
        if not self.cap.isOpened():
             # --- Indent Level 2 ---
             raise IOError(f"Cannot open webcam index {cam_idx}")

        self.frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        print(f"Webcam {cam_idx} opened ({self.frame_width}x{self.frame_height}).")

        # State Variables
        self.all_player_hands = []
        self.current_player_input_index = 0
        self.dealer_hand = []
        self.game_phase = "START"
        self.status_message = "Press 'R' Reset. Then 'P' per Player Hand, 'D' for Dealer."
        self.latest_detected_cards = {'player': [], 'dealer': []}
        self.last_gemini_response = ""
        self.last_gemini_query_time = 0
        self.gemini_cooldown = 5
        self.last_analysis_state = { "player_index": 0, "recommended_move": "N/A", "bet_recommendation": 1, "bust_probability": 0.0, "override_reason": ""}
        self.action_history = deque(maxlen=10)
        self.dealer_hole_card_history = deque(maxlen=MAX_HOLE_CARD_HISTORY)
        self.dealer_anomaly_warning = ""

    def display_hud(self, frame, current_hud_state):
        # --- Indent Level 1 ---
        """Draws the Heads-Up Display with game information."""
        # Backgrounds
        hud_bg_height = 260; status_bar_height = 30; gemini_area_height = 80
        cv2.rectangle(frame, (0, 0), (self.frame_width, hud_bg_height), (0, 0, 0, 0.7), cv2.FILLED)
        cv2.rectangle(frame, (0, self.frame_height - gemini_area_height - status_bar_height), (self.frame_width, self.frame_height - status_bar_height), (0, 0, 0, 0.7), cv2.FILLED)
        cv2.rectangle(frame, (0, self.frame_height - status_bar_height), (self.frame_width, self.frame_height), (0, 0, 0, 0.9), cv2.FILLED)

        # Counts, Bet Units, Remaining A/T Vis...
        # --- Indent Level 2 ---
        draw_hud_element(frame, f"HiLo RC: {self.blackjack_logic.hi_lo_running_count}", (10, 25), HUD_COLOR_NEUTRAL)
        draw_hud_element(frame, f"HiLo TC: {self.blackjack_logic.get_hi_lo_true_count():.2f}", (10, 50), HUD_COLOR_NEUTRAL)
        draw_hud_element(frame, f"Cards Seen: {self.blackjack_logic.cards_seen_count}", (10, 75), HUD_COLOR_NEUTRAL)
        draw_hud_element(frame, f"Bet Units: {current_hud_state.get('bet_recommendation', 1)}", (10, 100), HUD_COLOR_NEUTRAL)
        rem_aces = 0; rem_tens = 0;
        if self.blackjack_logic.num_decks == 1:
            # --- Indent Level 3 --- # Around Line 57
            for card_key, count in self.blackjack_logic.remaining_cards.items():
                # --- Indent Level 4 ---
                if count > 0:
                    # --- Indent Level 5 ---
                    rank = self.blackjack_logic._get_rank_from_key_or_label(card_key) # Use helper
                    if rank == 'A': rem_aces += 1
                    elif rank in ['T','J','Q','K']: rem_tens += 1
        else:
            # --- Indent Level 3 ---
            rem_aces = self.blackjack_logic.remaining_cards.get('A', 0) # Assumes rank keys for multi-deck
            rem_tens = sum(self.blackjack_logic.remaining_cards.get(r, 0) for r in ['T','J','Q','K'])
        # --- Indent Level 2 ---
        total_rem = self.blackjack_logic.total_cards_in_shoe - self.blackjack_logic.cards_seen_count; ace_pct = (rem_aces / total_rem * 100) if total_rem > 0 else 0; ten_pct = (rem_tens / total_rem * 100) if total_rem > 0 else 0
        draw_hud_element(frame, f"Rem A/T Ranks: {rem_aces}/{rem_tens} ({ace_pct:.0f}%/{ten_pct:.0f}%)", (10, 125), HUD_COLOR_NEUTRAL)

        # Hands Display
        player_hand_str = format_hand(current_hud_state['player_hand'])
        dealer_display_hand = self.dealer_hand if len(self.dealer_hand) > 1 else ([current_hud_state['dealer_card']] if current_hud_state['dealer_card'] else [])
        dealer_hand_str = format_hand(dealer_display_hand)
        dealer_val_str = f"Val: {self.blackjack_logic.get_hand_value(dealer_display_hand)}" if dealer_display_hand else ""
        draw_hud_element(frame, f"P1: {player_hand_str} (Val: {current_hud_state['player_total']})", (10, 155), HUD_COLOR_GOOD)
        draw_hud_element(frame, f"D: {dealer_hand_str} ({dealer_val_str})", (10, 180), HUD_COLOR_BAD)

        # Strategy Recommendation & Bust Probability
        move = current_hud_state.get('recommended_move', 'N/A'); bust_prob = current_hud_state.get('bust_probability', 0.0); override_reason = current_hud_state.get('override_reason', "")
        move_text = f"P1 Move: {move} ({ {'H': 'Hit', 'S': 'Stand', 'D': 'Double', 'P': 'Split', 'Err': 'Error', 'N/A': 'N/A', 'Bust': 'Bust'}.get(move, move) })"
        if override_reason: move_text += f" ({override_reason})"
        draw_hud_element(frame, move_text, (10, 215), HUD_COLOR_TEXT)
        if current_hud_state.get('player_total', 0) < 21: draw_hud_element(frame, f"Bust on Hit: {bust_prob:.1%}", (10, 240), HUD_COLOR_NEUTRAL)

        # Instructions
        inst_x = self.frame_width - 350
        draw_hud_element(frame, "'P': Player | 'D': Dealer | 'H': P1 Hit", (inst_x, 25), HUD_COLOR_TEXT)
        draw_hud_element(frame, "'A': Analyze P1 | 'F': Final Dealer Hand", (inst_x, 50), HUD_COLOR_TEXT)
        draw_hud_element(frame, "'U': Undo Last | 'R': Reset | 'Q': Quit", (inst_x, 75), HUD_COLOR_TEXT)

        # Hole Card History & Anomaly Display
        hole_hist_str = "Hole Cards (Last {}): ".format(len(self.dealer_hole_card_history)); tens_aces_count = 0
        # --- Indent Level 2 --- # Around Line 96
        for up, hole in self.dealer_hole_card_history:
             # --- Indent Level 3 ---
             hole_hist_str += f"({up}/{hole}) "
             hole_rank = self.blackjack_logic._get_rank_from_key_or_label(hole)
             if hole_rank in ['T','J','Q','K','A']: tens_aces_count += 1
        # --- Indent Level 2 ---
        if self.dealer_hole_card_history: hole_hist_str += f" [{tens_aces_count} T/A]"
        draw_hud_element(frame, hole_hist_str, (inst_x, 100), HUD_COLOR_NEUTRAL)
        # Display Dealer Anomaly Warning
        dealer_anomaly_msg = current_hud_state.get("dealer_anomaly", "") # Safely get value
        if dealer_anomaly_msg:
             # --- Indent Level 3 --- # Around Line 123 / 125
             draw_hud_element(frame, f"DEALER ALERT: {dealer_anomaly_msg}", (inst_x, 125), HUD_COLOR_BAD) # Ensure this line is indented under the 'if'

        # Gemini Response Area
        # --- Indent Level 2 ---
        if self.last_gemini_response:
            # --- Indent Level 3 ---
            response_lines = wrap_text(f"Gemini: {self.last_gemini_response}", width=int(self.frame_width / (HUD_SCALE * 10))-5)
            y_start = self.frame_height - status_bar_height - gemini_area_height + 15; max_lines = 3
            for i, line in enumerate(response_lines[:max_lines]):
                 # --- Indent Level 4 ---
                 line_y = y_start + i * 18
                 if line_y < self.frame_height - status_bar_height - 5:
                      # --- Indent Level 5 ---
                      draw_hud_element(frame, line, (10, line_y), HUD_COLOR_NEUTRAL)

        # Status Bar
        # --- Indent Level 2 ---
        draw_hud_element(frame, current_hud_state.get("status_message", ""), (10, self.frame_height - 10), HUD_COLOR_TEXT)
        return frame

    def undo_last_action(self):
        # --- Indent Level 1 ---
        """Reverses the last card addition and count update."""
        if not self.action_history:
            self.status_message = "Nothing to undo."; print("Undo failed: History empty."); return

        last_action_type, last_card_data = self.action_history.pop()
        print(f"Attempting to undo action: {last_action_type} with data: {last_card_data}")

        cards_to_add_back = []
        action_reversed = False

        # --- Indent Level 2 ---
        try:
            # --- Indent Level 3 --- # Around Line 174 starts here
            if last_action_type == 'D': # Undo Dealer Upcard
                # --- Indent Level 4 ---
                if self.dealer_hand and self.dealer_hand[0] == last_card_data:
                    cards_to_add_back.append(self.dealer_hand.pop(0))
                    action_reversed = True; self.game_phase = "PLAYER_INPUT" if self.current_player_input_index > 0 else "START"
                else: print("Undo failed: Dealer state mismatch.")
            elif last_action_type == 'P': # Undo Player Hand Set
                 # --- Indent Level 4 ---
                 player_index = last_card_data['index']; hand_set = last_card_data['hand']
                 if player_index < len(self.all_player_hands) and self.all_player_hands[player_index] == hand_set:
                      self.all_player_hands.pop(player_index); self.current_player_input_index = max(0, self.current_player_input_index - 1)
                      cards_to_add_back.extend(hand_set); action_reversed = True
                      self.game_phase = "PLAYER_INPUT" if self.current_player_input_index > 0 else "START"
                 else: print("Undo failed: Player state mismatch.")
            elif last_action_type == 'H': # Undo Player Hit
                 # --- Indent Level 4 ---
                 player_index = last_card_data['index']; hit_card = last_card_data['card']
                 if player_index < len(self.all_player_hands) and self.all_player_hands[player_index] and self.all_player_hands[player_index][-1] == hit_card:
                      cards_to_add_back.append(self.all_player_hands[player_index].pop()); action_reversed = True
                 else: print("Undo failed: Player hit state mismatch.")
            elif last_action_type == 'F': # Undo Final Dealer Hand (Simpler version)
                 # --- Indent Level 4 ---
                 hole_card = last_card_data['hole_card']; up_card_hist = last_card_data['up_card']
                 final_hand_logged = last_card_data['final_hand']
                 # Check if current dealer hand matches the logged final hand
                 if self.dealer_hand == final_hand_logged:
                      # --- Indent Level 5 ---
                      cards_to_add_back.extend(self.dealer_hand[1:]) # Add back hole card + simulated hits
                      self.dealer_hand = [self.dealer_hand[0]] # Revert state to only upcard
                      if self.dealer_hole_card_history and self.dealer_hole_card_history[-1] == (up_card_hist, hole_card):
                           self.dealer_hole_card_history.pop()
                      action_reversed = True; self.game_phase = "DEALER_INPUT"
                      print(f"Undo 'F': Reverted state. Adding back: {cards_to_add_back}")
                 else: print("Undo F fail: state mismatch or hand changed after F.")
        except Exception as e:
             # --- Indent Level 3 ---
             print(f"Error during undo logic for {last_action_type}: {e}"); action_reversed = False

        # --- Indent Level 2 ---
        if action_reversed:
            # --- Indent Level 3 ---
            success_count = 0
            for card_label in cards_to_add_back:
                 # --- Indent Level 4 ---
                 if self.blackjack_logic.add_card_back_to_shoe(card_label): success_count += 1
            # --- Indent Level 3 ---
            if success_count == len(cards_to_add_back):
                 self.status_message = f"Undo successful: Reversed '{last_action_type}'."; print("Undo successful.")
            else: self.status_message = "Undo partially failed (count mismatch)."; print("Undo Error: Card count mismatch.")
        else:
            # --- Indent Level 3 ---
            # Put action back if undo failed to avoid breaking history sequence
            if 'last_action_type' in locals() and 'last_card_data' in locals(): # Ensure they exist
                self.action_history.append((last_action_type, last_card_data))
            self.status_message = f"Undo failed for action '{last_action_type}'."


    def run(self):
        # --- Indent Level 1 ---
        """Main application loop with key-triggered state changes."""
        print("Starting AI Assistant..."); print(self.status_message)
        while True:
            # --- Indent Level 2 ---
            ret, frame = self.cap.read()
            if not ret:
                print("Error: Failed capture..."); time.sleep(0.5); self.cap.release(); self.cap = cv2.VideoCapture(CAMERA_INDEX)
                if not self.cap.isOpened(): print("Failed reopen. Exiting."); break
                else: print("Reopened camera."); continue

            # 1. Continuous Detection
            try:
                 detected_cards_dict, annotated_frame = self.card_detector.detect(frame); self.latest_detected_cards = detected_cards_dict
            except Exception as e:
                 print(f"Error card detection: {e}"); annotated_frame = frame; self.latest_detected_cards = {'player': [], 'dealer': []}

            # 2. Handle User Input Keys
            key = cv2.waitKey(1) & 0xFF; current_time = time.time(); analysis_requested = False; override_reason = ""
            self.dealer_anomaly_warning = "" # Reset anomaly warning

            # --- State Update Keys ---
            if key == ord('r'): # Reset
                # --- Indent Level 3 ---
                self.all_player_hands = []; self.current_player_input_index = 0; self.dealer_hand = []
                self.blackjack_logic.reset_shoe(); self.last_gemini_response = ""
                self.last_analysis_state = {"player_index": 0, "recommended_move": "N/A", "bet_recommendation": 1, "bust_probability": 0.0, "override_reason": ""}
                self.game_phase = "START"; self.status_message = "Reset. 'P' for P1 Hand..., 'D' for Dealer."
                self.action_history.clear(); # Keep hole card history across resets
                print("\n--- Game Reset ---")

            elif key == ord('p') and self.game_phase in ["START", "PLAYER_INPUT"]: # Player Hand
                # --- Indent Level 3 ---
                player_labels_detected = self.latest_detected_cards.get('player', [])
                if player_labels_detected:
                    # --- Indent Level 4 ---
                    player_index_display = self.current_player_input_index + 1
                    while len(self.all_player_hands) <= self.current_player_input_index: self.all_player_hands.append([])
                    new_hand_labels = sorted([lbl.upper() for lbl in player_labels_detected])

                    valid_new_hand = True; cards_to_remove = []
                    for card_label in new_hand_labels:
                         # --- Indent Level 5 ---
                         card_key = self.blackjack_logic._get_internal_card_key(card_label)
                         if card_key is None or self.blackjack_logic.remaining_cards.get(card_key, 0) <= 0:
                              # --- Indent Level 6 ---
                              self.status_message = f"Error: Card {card_label} invalid/removed!"; print(f"Error: Card {card_label} detected but invalid/removed."); valid_new_hand = False; break
                         cards_to_remove.append(card_label) # Use original label for removal function

                    # --- Indent Level 4 ---
                    if valid_new_hand and self.all_player_hands[self.current_player_input_index] != new_hand_labels:
                        # --- Indent Level 5 ---
                        print(f"Processing P{player_index_display}: {new_hand_labels}")
                        for card_label in cards_to_remove: self.blackjack_logic.remove_card_from_shoe(card_label)
                        self.action_history.append(('P', {'index': self.current_player_input_index, 'hand': list(new_hand_labels)}))
                        self.all_player_hands[self.current_player_input_index] = new_hand_labels
                        self.current_player_input_index += 1; self.game_phase = "PLAYER_INPUT"
                        self.status_message = f"P{player_index_display} set. 'P' for next or 'D'."
                        print(f"P{player_index_display} captured: {new_hand_labels}")
                    elif self.all_player_hands[self.current_player_input_index] == new_hand_labels:
                         # --- Indent Level 5 ---
                         self.status_message = f"P{player_index_display} unchanged. 'P' or 'D'."
                    # If not valid, status message already set
                else:
                     # --- Indent Level 4 ---
                     self.status_message = f"No cards for P{self.current_player_input_index + 1}. Aim & 'P'."

            elif key == ord('d') and self.game_phase in ["START", "PLAYER_INPUT"]: # Dealer Up Card
                 # --- Indent Level 3 ---
                 dealer_labels_detected = self.latest_detected_cards.get('dealer', [])
                 if dealer_labels_detected:
                      # --- Indent Level 4 ---
                      up_card_label = dealer_labels_detected[0] # Use detected label
                      up_card_key = self.blackjack_logic._get_internal_card_key(up_card_label) # Get key for check

                      if up_card_key is None or self.blackjack_logic.remaining_cards.get(up_card_key, 0) <= 0:
                           # --- Indent Level 5 ---
                           self.status_message = f"Error: {up_card_label} invalid/removed!"; print(f"Error: {up_card_label} removed.")
                      elif not self.dealer_hand:
                           # --- Indent Level 5 ---
                           up_card_to_store = up_card_label.upper() # Store consistently
                           self.dealer_hand = [up_card_to_store]; self.blackjack_logic.remove_card_from_shoe(up_card_to_store); self.action_history.append(('D', up_card_to_store))
                           self.game_phase = "DEALER_INPUT"; self.status_message = f"Dealer: {up_card_to_store}. Press 'A' for P1."
                           print(f"Dealer upcard: {up_card_to_store}")
                      else:
                           # --- Indent Level 5 ---
                           self.status_message = f"Dealer already has {self.dealer_hand[0]}. Press 'A'."
                 else:
                      # --- Indent Level 4 ---
                      self.status_message = "No dealer card detected. Aim & 'D'."

            elif key == ord('h') and self.game_phase == "DEALER_INPUT": # Player 1 Hit
                 # --- Indent Level 3 ---
                 player_index_hitting = 0
                 if player_index_hitting < len(self.all_player_hands):
                      # --- Indent Level 4 ---
                      player_labels_detected = self.latest_detected_cards.get('player', [])
                      if player_labels_detected:
                           # --- Indent Level 5 ---
                           hit_card_label = player_labels_detected[0] # Use detected label
                           hit_card_key = self.blackjack_logic._get_internal_card_key(hit_card_label)

                           if hit_card_key is None or self.blackjack_logic.remaining_cards.get(hit_card_key, 0) <= 0:
                                # --- Indent Level 6 ---
                                self.status_message = f"Error: Hit {hit_card_label} invalid/removed!"; print(f"Error: Hit {hit_card_label} removed.")
                           else:
                                # --- Indent Level 6 ---
                                hit_card_to_store = hit_card_label.upper() # Store consistently
                                self.all_player_hands[player_index_hitting].append(hit_card_to_store); self.blackjack_logic.remove_card_from_shoe(hit_card_to_store)
                                self.action_history.append(('H', {'index': player_index_hitting, 'card': hit_card_to_store}))
                                self.status_message = f"P1 Hit: {hit_card_to_store}. Hand: {format_hand(self.all_player_hands[player_index_hitting])}. Press 'A'."
                                print(f"P{player_index_hitting+1} hit: {hit_card_to_store}")
                      else:
                           # --- Indent Level 5 ---
                           self.status_message = "No card detected for Hit ('H'). Aim clearly."
                 else:
                      # --- Indent Level 4 ---
                      self.status_message = "No P1 hand to hit. Use 'P'."

            elif key == ord('f') and self.game_phase == "DEALER_INPUT" and len(self.dealer_hand) == 1: # Final Dealer Hand
                 # --- Indent Level 3 ---
                 print("--- 'F' Pressed: Simulating Dealer Turn ---")
                 up_card_label = self.dealer_hand[0] # Already stored uppercase
                 dealer_labels_detected = self.latest_detected_cards.get('dealer', [])
                 if len(dealer_labels_detected) >= 2:
                      # --- Indent Level 4 ---
                      hole_card_label_detected = None
                      for lbl in dealer_labels_detected:
                           # --- Indent Level 5 ---
                           if lbl.upper() != up_card_label: # Find one that isn't the upcard
                                hole_card_label_detected = lbl; break
                      # --- Indent Level 4 ---
                      if hole_card_label_detected:
                           # --- Indent Level 5 ---
                           hole_card_to_store = hole_card_label_detected.upper() # Store consistently
                           hole_card_key = self.blackjack_logic._get_internal_card_key(hole_card_to_store)

                           if hole_card_key is None or self.blackjack_logic.remaining_cards.get(hole_card_key, 0) <= 0:
                                # --- Indent Level 6 ---
                                self.status_message = f"Error: Hole {hole_card_label_detected} invalid/removed!"; print(f"Error: Hole {hole_card_label_detected} removed.")
                           else:
                                # --- Indent Level 6 ---
                                print(f"Hole card detected: {hole_card_to_store}. Simulating...")
                                self.blackjack_logic.remove_card_from_shoe(hole_card_to_store) # Remove detected hole card
                                initial_dealer_hand = [up_card_label, hole_card_to_store] # Start sim with labels
                                final_dealer_hand_sim, final_outcome = self.blackjack_logic.simulate_dealer_turn(initial_dealer_hand)
                                self.dealer_hand = final_dealer_hand_sim # Update state
                                print(f"Dealer sim finished. Final: {self.dealer_hand}, Outcome: {final_outcome}")
                                self.dealer_hole_card_history.append((up_card_label, hole_card_to_store))
                                self.action_history.append(('F', {'up_card': up_card_label, 'hole_card': hole_card_to_store, 'final_hand': list(final_dealer_hand_sim)}))
                                dealer_up_rank_for_hist = self.blackjack_logic._get_rank_from_key_or_label(up_card_label)
                                self.blackjack_logic.record_dealer_outcome(dealer_up_rank_for_hist, final_outcome)
                                dealer_final_total_display = final_outcome if isinstance(final_outcome, str) else self.blackjack_logic.get_hand_value(self.dealer_hand)
                                self.status_message = f"Dealer Final (Sim): {format_hand(self.dealer_hand)} ({dealer_final_total_display}). Press 'R'."
                                self.game_phase = "ROUND_OVER"
                      else:
                           # --- Indent Level 5 ---
                           self.status_message = "Could not find distinct hole card. Aim & 'F'."
                 else:
                      # --- Indent Level 4 ---
                      self.status_message = "Need both dealer cards clearly visible. Aim & 'F'."

            elif key == ord('u'): # Undo
                 # --- Indent Level 3 ---
                 self.undo_last_action()
                 self.last_analysis_state = {"player_index": 0, "recommended_move": "N/A", "bet_recommendation": 1, "bust_probability": 0.0, "override_reason": ""}
                 self.last_gemini_response = ""

            elif key == ord('a') and self.game_phase == "DEALER_INPUT": # Analyze P1
                # --- Indent Level 3 ---
                player_index_to_analyze = 0
                if player_index_to_analyze >= len(self.all_player_hands) or not self.dealer_hand:
                    # --- Indent Level 4 ---
                    self.status_message = "Need P1 Hand ('P') & Dealer Card ('D') before analyzing ('A')."
                else:
                    # --- Indent Level 4 ---
                    analysis_requested = True
                    self.player_hand_to_analyze = self.all_player_hands[player_index_to_analyze]
                    self.dealer_up_card_to_analyze = self.dealer_hand[0] # Label like 'AS'
                    self.status_message = f"Analyzing P{player_index_to_analyze+1}... 'H' Hit, 'F' Final D, 'R' Reset."
                    print(f"--- Analyzing P{player_index_to_analyze+1}: {self.player_hand_to_analyze} vs D: {self.dealer_up_card_to_analyze} ---")
                    # Check dealer bust anomaly
                    dealer_up_rank_for_analysis = self.blackjack_logic._get_rank_from_key_or_label(self.dealer_up_card_to_analyze)
                    anomaly = self.blackjack_logic.check_dealer_bust_rate_anomaly(dealer_up_rank_for_analysis)
                    self.dealer_anomaly_warning = anomaly if anomaly else ""
                    if self.dealer_anomaly_warning: print(f"DEALER ANOMALY for upcard {dealer_up_rank_for_analysis}: {self.dealer_anomaly_warning}")


            elif key == ord('q'):
                 # --- Indent Level 3 ---
                 break # Quit

            # 3. Perform Analysis (if requested)
            # --- Indent Level 2 ---
            if analysis_requested:
                # --- Indent Level 3 ---
                player_total = self.blackjack_logic.get_hand_value(self.player_hand_to_analyze)
                dealer_up_rank = self.blackjack_logic._get_rank_from_key_or_label(self.dealer_up_card_to_analyze)
                # Handle case where dealer rank might be None if label was bad
                if dealer_up_rank is None:
                     print("Error: Cannot analyze, invalid dealer upcard rank.")
                     self.status_message = "Error: Invalid dealer upcard for analysis."
                     analysis_requested = False # Prevent further processing this cycle
                     # Maybe revert game phase?
                     # self.game_phase = "PLAYER_INPUT" # Allow re-entering dealer card?
                else:
                    dealer_up_value = self.blackjack_logic._get_card_value_numeric(dealer_up_rank)
                    final_move = "N/A"; basic_move = "N/A"; bust_probability = 0.0; override_reason = ""

                    if player_total <= 21:
                        # --- Indent Level 4 ---
                        basic_move = self.blackjack_logic.get_basic_strategy_move(self.player_hand_to_analyze, self.dealer_up_card_to_analyze); final_move = basic_move
                        hi_lo_tc = self.blackjack_logic.get_hi_lo_true_count()

                        # Check Insurance
                        if dealer_up_rank == 'A':
                             # --- Indent Level 5 ---
                             ins_key = ('Ins', 11);
                             if ins_key in INDEX_PLAYS:
                                  # --- Indent Level 6 ---
                                  rule = INDEX_PLAYS[ins_key]; threshold = rule['Threshold'];
                                  if rule['Type'] == 'ge' and hi_lo_tc >= threshold: override_reason = f"Take Insurance (TC {hi_lo_tc:+.1f})"; print(f"Index: Insurance")

                        # Check other Index Plays
                        player_ranks = [self.blackjack_logic._get_rank_from_key_or_label(lbl) for lbl in self.player_hand_to_analyze if self.blackjack_logic._get_rank_from_key_or_label(lbl) is not None]
                        is_pair_local = len(player_ranks) == 2 and player_ranks[0] == player_ranks[1]
                        player_key_for_index = tuple(sorted(player_ranks)) if is_pair_local else player_total
                        index_lookup_key = (player_key_for_index, dealer_up_value) # Line 289 area

                        if index_lookup_key in INDEX_PLAYS:
                            # --- Indent Level 5 --- Line 295 area
                            rule = INDEX_PLAYS[index_lookup_key]; threshold = rule['Threshold']; condition_met = (rule['Type'] == 'ge' and hi_lo_tc >= threshold) or (rule['Type'] == 'le' and hi_lo_tc <= threshold)
                            if condition_met:
                                # --- Indent Level 6 ---
                                index_move = rule['Action'];
                                if index_move != basic_move:
                                     # --- Indent Level 7 ---
                                     final_move = index_move;
                                     if not override_reason or not override_reason.startswith("Take Insurance"): override_reason = f"Index (TC {hi_lo_tc:+.1f})"
                                     print(f"Override: BS='{basic_move}', Index='{final_move}' at TC {hi_lo_tc:+.1f}")

                        # Check Bust Probability if still Hitting
                        if final_move == 'H':
                            # --- Indent Level 5 ---
                            bust_probability = self.blackjack_logic.calculate_bust_probability(self.player_hand_to_analyze); print(f"Bust Prob on Hit: {bust_probability:.3f}")
                            if bust_probability > BUST_PROBABILITY_THRESHOLD:
                                 # --- Indent Level 6 --- Line 314 area
                                 final_move = 'S'; override_reason = f"High Bust% ({bust_probability:.1%})"; print(f"Override: Move to 'S', bust > {BUST_PROBABILITY_THRESHOLD:.1%}")
                        else:
                             # --- Indent Level 5 ---
                             bust_probability = 0.0
                    else: # Player busted
                         # --- Indent Level 4 ---
                         final_move = 'Bust'; basic_move = 'Bust'; bust_probability = 1.0

                    # Betting
                    # --- Indent Level 4 ---
                    bet_recommendation = self.blackjack_logic.get_bet_recommendation()
                    # Store results
                    self.last_analysis_state = { "player_index": 0, "recommended_move": final_move, "bet_recommendation": bet_recommendation, "bust_probability": bust_probability, "override_reason": override_reason }

                    # Query Gemini
                    if self.gemini_integration.initialized and current_time - self.last_gemini_query_time > self.gemini_cooldown:
                        # --- Indent Level 4 ---
                        print("Querying Gemini..."); self.last_gemini_query_time = current_time;
                        total_remaining = self.blackjack_logic.total_cards_in_shoe - self.blackjack_logic.cards_seen_count; rem_aces_rank = 0; rem_tens_rank = 0
                        if self.blackjack_logic.num_decks == 1:
                             # --- Indent Level 5 ---
                             for card_key, count in self.blackjack_logic.remaining_cards.items():
                                  # --- Indent Level 6 ---
                                  if count > 0:
                                       # --- Indent Level 7 ---
                                       rank = self.blackjack_logic._get_rank_from_key_or_label(card_key)
                                       if rank == 'A': rem_aces_rank += 1;
                                       elif rank in ['T','J','Q','K']: rem_tens_rank += 1
                        else:
                             # --- Indent Level 5 ---
                             rem_aces_rank = self.blackjack_logic.remaining_cards.get('A', 0); rem_tens_rank = sum(self.blackjack_logic.remaining_cards.get(r, 0) for r in ['T','J','Q','K'])
                        composition_summary = f"Rem Cards: {total_remaining}. Rem A/T Ranks: {rem_aces_rank}/{rem_tens_rank}."
                        self.last_gemini_response = self.gemini_integration.explain_strategy_enhanced(self.player_hand_to_analyze, self.dealer_up_card_to_analyze, hi_lo_tc, basic_move, final_move, bust_probability, player_total, dealer_up_value, composition_summary, override_reason)
                        print(f"Gemini Response: {self.last_gemini_response}")
                    else:
                         # --- Indent Level 4 ---
                         self.last_gemini_response = "Gemini ready or cooldown."


            # 4. Prepare State for HUD
            # --- Indent Level 2 ---
            player_hand_display = self.all_player_hands[0] if self.all_player_hands else []
            dealer_card_display = self.dealer_hand[0] if self.dealer_hand else None
            player_total_display = self.blackjack_logic.get_hand_value(player_hand_display)
            # Display value of only upcard unless F has been pressed
            dealer_total_display = self.blackjack_logic.get_hand_value(self.dealer_hand) if len(self.dealer_hand)>1 else self.blackjack_logic.get_hand_value([dealer_card_display]) if dealer_card_display else 0

            hud_state = {
                "player_hand": player_hand_display, "dealer_card": dealer_card_display,
                "player_total": player_total_display, "dealer_total": dealer_total_display,
                "recommended_move": self.last_analysis_state["recommended_move"],
                "bet_recommendation": self.last_analysis_state["bet_recommendation"],
                "bust_probability": self.last_analysis_state["bust_probability"],
                "override_reason": self.last_analysis_state["override_reason"],
                "status_message": self.status_message,
                "dealer_anomaly": self.dealer_anomaly_warning
            }

            # 5. Display Frame
            final_frame = self.display_hud(annotated_frame, hud_state)
            cv2.imshow('Blackjack AI Assistant', final_frame)

        # Cleanup (Outside While loop)
        # --- Indent Level 1 ---
        self.cap.release(); cv2.destroyAllWindows(); print("Application terminated.")

# --- Indent Level 0 --- # Around line 388
if __name__ == "__main__":
    # --- Indent Level 1 ---
    try:
         # --- Indent Level 2 ---
         ai_assistant = CasinoAI()
         ai_assistant.run()
    except Exception as e:
         # --- Indent Level 2 ---
         print(f"An error occurred: {e}")
         import traceback
         traceback.print_exc()
         cv2.destroyAllWindows()

# --- END OF FILE main.py ---