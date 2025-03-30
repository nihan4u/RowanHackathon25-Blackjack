# --- START OF FILE main.py ---
import cv2
import time
from config import * # Imports CAMERA_INDEX, CARD_MODEL_PATH, etc.
from card_detector import CardDetector
from blackjack_logic import BlackjackLogic
from gemini_integration import GeminiIntegration
from utils import draw_hud_element, format_hand, wrap_text

# --- Configuration for Strategy Override ---
# If bust probability on hit exceeds this, consider overriding 'H' to 'S'
BUST_PROBABILITY_THRESHOLD = 0.50 # Example: 50% chance - Adjust as needed

class CasinoAI:
    def __init__(self):
        print("Initializing AI...")
        cam_idx = CAMERA_INDEX
        num_decks = NUM_DECKS

        self.card_detector = CardDetector() # Uses CARD_MODEL_PATH from config
        self.blackjack_logic = BlackjackLogic(num_decks=num_decks)
        self.gemini_integration = GeminiIntegration()

        self.cap = cv2.VideoCapture(cam_idx)
        if not self.cap.isOpened():
            raise IOError(f"Cannot open webcam index {cam_idx}")

        self.frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        print(f"Webcam {cam_idx} opened ({self.frame_width}x{self.frame_height}).")

        # --- State Variables ---
        self.all_player_hands = []
        self.current_player_input_index = 0
        self.dealer_hand = []
        self.game_phase = "START"
        self.status_message = "Press 'R' Reset. Then 'P' per Player Hand, 'D' for Dealer."
        self.latest_detected_cards = {'player': [], 'dealer': []}
        self.last_gemini_response = ""
        self.last_gemini_query_time = 0
        self.gemini_cooldown = 5
        self.last_analysis_state = {
            "player_index": 0,
            "recommended_move": "N/A",
            "bet_recommendation": 1,
            "bust_probability": 0.0,
            "override_reason": ""
        }

    def display_hud(self, frame, current_hud_state):
        """Draws the Heads-Up Display with game information."""
        # Backgrounds
        hud_bg_height = 240
        status_bar_height = 30
        gemini_area_height = 80
        cv2.rectangle(frame, (0, 0), (self.frame_width, hud_bg_height), (0, 0, 0, 0.7), cv2.FILLED)
        cv2.rectangle(frame, (0, self.frame_height - gemini_area_height - status_bar_height), (self.frame_width, self.frame_height - status_bar_height), (0, 0, 0, 0.7), cv2.FILLED)
        cv2.rectangle(frame, (0, self.frame_height - status_bar_height), (self.frame_width, self.frame_height), (0, 0, 0, 0.9), cv2.FILLED)

        # --- Top HUD Elements ---
        draw_hud_element(frame, f"HiLo RC: {self.blackjack_logic.hi_lo_running_count}", (10, 25), HUD_COLOR_NEUTRAL)
        draw_hud_element(frame, f"HiLo TC: {self.blackjack_logic.get_hi_lo_true_count():.2f}", (10, 50), HUD_COLOR_NEUTRAL)
        draw_hud_element(frame, f"Cards Seen: {self.blackjack_logic.cards_seen_count}", (10, 75), HUD_COLOR_NEUTRAL)
        draw_hud_element(frame, f"Bet Units: {current_hud_state.get('bet_recommendation', 1)}", (10, 100), HUD_COLOR_NEUTRAL)

        # Hands
        player_hand_str = format_hand(current_hud_state['player_hand'])
        dealer_hand_str = format_hand([current_hud_state['dealer_card']]) if current_hud_state['dealer_card'] else "None"
        draw_hud_element(frame, f"P1: {player_hand_str} (Val: {current_hud_state['player_total']})", (10, 135), HUD_COLOR_GOOD)
        draw_hud_element(frame, f"D: {dealer_hand_str} (Val: {current_hud_state['dealer_total']})", (10, 160), HUD_COLOR_BAD)

        # Strategy Recommendation & Bust Probability
        move = current_hud_state.get('recommended_move', 'N/A')
        bust_prob = current_hud_state.get('bust_probability', 0.0)
        override_reason = current_hud_state.get('override_reason', "")
        move_text = f"P1 Move: {move} ({ {'H': 'Hit', 'S': 'Stand', 'D': 'Double', 'P': 'Split', 'Err': 'Error', 'N/A': 'N/A', 'Bust': 'Bust'}.get(move, move) })"
        if override_reason:
             move_text += f" ({override_reason})"
        draw_hud_element(frame, move_text, (10, 195), HUD_COLOR_TEXT)
        if current_hud_state['player_total'] < 21:
             draw_hud_element(frame, f"Bust on Hit: {bust_prob:.1%}", (10, 220), HUD_COLOR_NEUTRAL)

        # Instructions
        inst_x = self.frame_width - 320
        draw_hud_element(frame, "'P': Next Player Hand | 'D': Dealer Hand", (inst_x, 25), HUD_COLOR_TEXT)
        draw_hud_element(frame, "'H': Player 1 Hit | 'A': Analyze P1", (inst_x, 50), HUD_COLOR_TEXT)
        draw_hud_element(frame, "'R': Reset Round | 'Q': Quit", (inst_x, 75), HUD_COLOR_TEXT)

        # Gemini Response Area
        if self.last_gemini_response:
            response_lines = wrap_text(f"Gemini: {self.last_gemini_response}", width=int(self.frame_width / (HUD_SCALE * 10))-5)
            y_start = self.frame_height - status_bar_height - gemini_area_height + 15
            max_lines = 3
            for i, line in enumerate(response_lines[:max_lines]):
                 line_y = y_start + i * 18
                 if line_y < self.frame_height - status_bar_height - 5:
                     draw_hud_element(frame, line, (10, line_y), HUD_COLOR_NEUTRAL)

        # Status Bar
        draw_hud_element(frame, current_hud_state.get("status_message", ""), (10, self.frame_height - 10), HUD_COLOR_TEXT)

        return frame

    def run(self):
        """Main application loop with key-triggered state changes."""
        print("Starting AI Assistant...")
        print(self.status_message)

        while True:
            ret, frame = self.cap.read()
            if not ret:
                print("Error: Failed to capture frame. Attempting to reopen...")
                time.sleep(0.5); self.cap.release(); self.cap = cv2.VideoCapture(CAMERA_INDEX)
                if not self.cap.isOpened(): print("Failed to reopen camera. Exiting."); break
                else: print("Reopened camera."); continue

            # 1. Continuous Detection
            try:
                detected_cards_dict, annotated_frame = self.card_detector.detect(frame)
                self.latest_detected_cards = detected_cards_dict
            except Exception as e:
                print(f"Error during card detection: {e}")
                annotated_frame = frame
                self.latest_detected_cards = {'player': [], 'dealer': []}

            # 2. Handle User Input Keys
            key = cv2.waitKey(1) & 0xFF
            current_time = time.time()
            analysis_requested = False
            override_reason = "" # Reset override reason each frame

            # --- State Update Keys ---
            if key == ord('r'): # 'R' = Reset Round/Shoe
                self.all_player_hands = []; self.current_player_input_index = 0; self.dealer_hand = []
                self.blackjack_logic.reset_shoe(); self.last_gemini_response = ""
                self.last_analysis_state = {"player_index": 0, "recommended_move": "N/A", "bet_recommendation": 1, "bust_probability": 0.0, "override_reason": ""}
                self.game_phase = "START"; self.status_message = "Reset. 'P' for P1 Hand..., 'D' for Dealer."
                print("\n--- Game Reset ---")

            elif key == ord('p') and self.game_phase in ["START", "PLAYER_INPUT"]: # 'P' = Capture Hand for Current Player
                player_ranks_detected = self.latest_detected_cards.get('player', [])
                if player_ranks_detected:
                    player_index_display = self.current_player_input_index + 1
                    while len(self.all_player_hands) <= self.current_player_input_index: self.all_player_hands.append([])
                    new_hand = player_ranks_detected
                    self.all_player_hands[self.current_player_input_index] = new_hand
                    print(f"Processing Player {player_index_display} hand: {new_hand}")
                    # Count cards assuming this is the full initial hand for this player this round
                    # TODO: Improve logic if 'P' can be pressed multiple times for same player's deal
                    for card_rank in new_hand: self.blackjack_logic.remove_card_from_shoe(card_rank)
                    self.current_player_input_index += 1
                    self.game_phase = "PLAYER_INPUT"
                    self.status_message = f"P{player_index_display} set. Press 'P' for P{self.current_player_input_index + 1} or 'D' for Dealer."
                    print(f"Player {player_index_display} hand captured: {new_hand}")
                else: self.status_message = f"No cards detected for Player {self.current_player_input_index + 1}. Aim & press 'P'."

            elif key == ord('d') and self.game_phase in ["START", "PLAYER_INPUT"]: # 'D' = Capture Dealer Up Card
                dealer_ranks_detected = self.latest_detected_cards.get('dealer', [])
                if dealer_ranks_detected:
                    up_card = dealer_ranks_detected[0]
                    if not self.dealer_hand:
                        self.dealer_hand = [up_card]; self.blackjack_logic.remove_card_from_shoe(up_card)
                        self.game_phase = "DEALER_INPUT"; self.status_message = f"Dealer shows: {up_card}. Press 'A' to analyze P1 hand."
                        print(f"Dealer upcard captured: {up_card}")
                    else: self.status_message = f"Dealer card already captured ({self.dealer_hand[0]}). Press 'A'."
                else: self.status_message = "No dealer card detected when 'D' pressed. Aim camera."

            # --- Player Action Keys (Simplified for Player 1) ---
            elif key == ord('h') and self.game_phase == "DEALER_INPUT": # 'H' = Player 1 Hit
                player_index_hitting = 0 # Assume Player 1
                if player_index_hitting < len(self.all_player_hands):
                    player_ranks_detected = self.latest_detected_cards.get('player', [])
                    if player_ranks_detected:
                        # Assume the first detected card in the player zone is the hit card
                        hit_card_rank = player_ranks_detected[0]

                        # Add the hit card to the hand (allows duplicates)
                        self.all_player_hands[player_index_hitting].append(hit_card_rank)
                        # Remove the card from the shoe count
                        self.blackjack_logic.remove_card_from_shoe(hit_card_rank)

                        self.status_message = f"P1 Hit: {hit_card_rank}. Hand: {format_hand(self.all_player_hands[player_index_hitting])}. Press 'A'."
                        print(f"Player {player_index_hitting+1} hit captured: {hit_card_rank}")

                    else:
                        # No card detected when 'H' was pressed
                        self.status_message = "No player card detected for Hit ('H'). Aim camera clearly at hit card."
                        print("Attempted to capture hit, none detected.")
                else:
                     # Player 1 hand doesn't exist yet
                     self.status_message = "No Player 1 hand set to hit. Use 'P' first."


            # --- Analysis Trigger Key ---
            elif key == ord('a') and self.game_phase == "DEALER_INPUT": # 'A' = Analyze (Player 1)
                player_index_to_analyze = 0
                if player_index_to_analyze >= len(self.all_player_hands) or not self.dealer_hand:
                    self.status_message = "Need P1 Hand ('P') & Dealer Card ('D') before analyzing ('A')."
                else:
                    analysis_requested = True
                    self.player_hand_to_analyze = self.all_player_hands[player_index_to_analyze]
                    self.dealer_up_card_to_analyze = self.dealer_hand[0]
                    self.status_message = f"Analyzing P{player_index_to_analyze+1}... Press 'H' for P1 Hit, 'R' for Reset."
                    print(f"--- Analyzing P{player_index_to_analyze+1}: {self.player_hand_to_analyze} vs D: {self.dealer_up_card_to_analyze} ---")

            elif key == ord('q'): # 'Q' = Quit
                print("Quitting...")
                break

            # 3. Perform Analysis (if 'A' was pressed and conditions met)
            if analysis_requested:
                player_total = self.blackjack_logic.get_hand_value(self.player_hand_to_analyze)
                dealer_total = self.blackjack_logic.get_hand_value([self.dealer_up_card_to_analyze])
                final_move = "N/A"
                bust_probability = 0.0 # Initialize bust prob
                override_reason = ""    # Initialize override reason

                if player_total <= 21: # Only analyze if player hasn't busted
                    # --- Strategy Calculation ---
                    basic_move = self.blackjack_logic.get_basic_strategy_move(
                        self.player_hand_to_analyze, self.dealer_up_card_to_analyze
                    )
                    final_move = basic_move

                    if basic_move == 'H':
                        bust_probability = self.blackjack_logic.calculate_bust_probability(self.player_hand_to_analyze)
                        print(f"Calculated Bust Probability on Hit: {bust_probability:.3f}")

                        if bust_probability > BUST_PROBABILITY_THRESHOLD:
                            final_move = 'S'
                            override_reason = f"High Bust% ({bust_probability:.1%})"
                            print(f"Override Applied: Basic='H', Changed to 'S' due to bust prob > {BUST_PROBABILITY_THRESHOLD:.1%}")

                    # TODO: Add Index Play logic here if desired

                else: # Player already busted
                     final_move = 'Bust'
                     bust_probability = 1.0

                # --- Betting Calculation ---
                bet_recommendation = self.blackjack_logic.get_bet_recommendation()

                # Store results for HUD
                self.last_analysis_state = {
                    "player_index": 0,
                    "recommended_move": final_move,
                    "bet_recommendation": bet_recommendation,
                    "bust_probability": bust_probability,
                    "override_reason": override_reason
                }

                # --- Query Gemini ---
                if self.gemini_integration.initialized and current_time - self.last_gemini_query_time > self.gemini_cooldown:
                    print("Querying Gemini for explanation...")
                    self.last_gemini_query_time = current_time
                    self.last_gemini_response = self.gemini_integration.explain_strategy_enhanced(
                        self.player_hand_to_analyze,
                        self.dealer_up_card_to_analyze,
                        self.blackjack_logic.get_hi_lo_true_count(),
                        basic_move if player_total <= 21 else 'Bust', # Pass original basic move if not busted
                        final_move,
                        bust_probability,
                        player_total,
                        dealer_total
                    )
                    print(f"Gemini Response: {self.last_gemini_response}")
                elif self.gemini_integration.initialized:
                     self.last_gemini_response = f"Cooldown... {int(self.gemini_cooldown - (current_time - self.last_gemini_query_time))}s left"
                else:
                     self.last_gemini_response = "Gemini not initialized."


            # 4. Prepare State for Continuous HUD Display
            player_hand_display = self.all_player_hands[0] if self.all_player_hands else []
            dealer_card_display = self.dealer_hand[0] if self.dealer_hand else None
            player_total_display = self.blackjack_logic.get_hand_value(player_hand_display)
            dealer_total_display = self.blackjack_logic.get_hand_value([dealer_card_display]) if dealer_card_display else 0

            hud_state = {
                "player_hand": player_hand_display,
                "dealer_card": dealer_card_display,
                "player_total": player_total_display,
                "dealer_total": dealer_total_display,
                "recommended_move": self.last_analysis_state["recommended_move"],
                "bet_recommendation": self.last_analysis_state["bet_recommendation"],
                "bust_probability": self.last_analysis_state["bust_probability"],
                "override_reason": self.last_analysis_state["override_reason"],
                "status_message": self.status_message
            }

            # 5. Display Frame with HUD
            final_frame = self.display_hud(annotated_frame, hud_state)
            cv2.imshow('Blackjack AI Assistant', final_frame)

        # Cleanup
        self.cap.release()
        cv2.destroyAllWindows()
        print("Application terminated.")

if __name__ == "__main__":
    try:
        ai_assistant = CasinoAI()
        ai_assistant.run()
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
        cv2.destroyAllWindows()

# --- END OF FILE main.py ---