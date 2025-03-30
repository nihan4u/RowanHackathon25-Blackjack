# --- START OF FILE gemini_integration.py ---
import google.generativeai as genai
import time
from config import GEMINI_API_KEY, GEMINI_MODEL_NAME
from utils import format_hand

class GeminiIntegration:
    def __init__(self):
        self.initialized = False
        if not GEMINI_API_KEY:
            print("Gemini API Key not configured. Skipping initialization.")
            return

        try:
            genai.configure(api_key=GEMINI_API_KEY)
            self.generation_config = genai.types.GenerationConfig(max_output_tokens=250) # Slightly longer allowed response
            self.safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            ]
            self.model = genai.GenerativeModel(
                GEMINI_MODEL_NAME,
                generation_config=self.generation_config,
                safety_settings=self.safety_settings
                )
            self.initialized = True
            print(f"Gemini initialized successfully with model {GEMINI_MODEL_NAME}.")
        except Exception as e:
            print(f"Error initializing Gemini: {e}")

    def _generate(self, prompt):
        """Internal helper to call Gemini API with error handling and retries."""
        # ... (Keep _generate method same as previous version) ...
        if not self.initialized: return "Gemini not initialized."
        retries = 2; delay = 1
        for i in range(retries + 1):
            try:
                response = self.model.generate_content(prompt)
                if response.parts:
                    if response.prompt_feedback.block_reason: return f"Gemini blocked: {response.prompt_feedback.block_reason}"
                    return response.text.strip()
                elif response.prompt_feedback.block_reason: return f"Gemini blocked: {response.prompt_feedback.block_reason}"
                else: print("Warning: Gemini empty response."); return "Gemini returned empty."
            except Exception as e:
                print(f"Error Gemini API (Try {i+1}): {e}")
                if i < retries: time.sleep(delay); delay *= 2
                else: return f"Error Gemini: {e}"
        return "Gemini failed after retries."

    # --- OLD METHOD (Can keep or remove) ---
    def explain_strategy(self, player_hand, dealer_up_card, true_count, recommended_move, player_total, dealer_value):
        # ... (Original implementation) ...
        pass # Or keep for basic explanations if needed elsewhere

    # --- NEW METHOD with Bust Probability ---
    def explain_strategy_enhanced(self, player_hand, dealer_up_card, hi_lo_true_count,
                                  basic_strategy_move, final_recommended_move, bust_probability,
                                  player_total, dealer_value):
        """Asks Gemini to explain the recommended move, considering bust probability."""
        if not self.initialized: return "Gemini N/A"

        player_hand_str = format_hand(player_hand)
        move_map = {'H': 'Hit', 'S': 'Stand', 'D': 'Double Down', 'P': 'Split', 'Bust': 'Bust', 'Err': 'Error', 'N/A': 'N/A'}
        basic_move_desc = move_map.get(basic_strategy_move, basic_strategy_move)
        final_move_desc = move_map.get(final_recommended_move, final_recommended_move)

        prompt = f"""
        Analyze the Blackjack situation and explain the final recommendation:

        Player Hand: {player_hand_str} (Total: {player_total})
        Dealer Shows: {dealer_up_card} (Value: {dealer_value})
        Hi-Lo True Count: {hi_lo_true_count:+.1f} (Context for deviations, higher favors player)
        Basic Strategy Move: {basic_strategy_move} ({basic_move_desc})
        Calculated Bust Probability on Hit: {bust_probability:.1%}
        Final Recommended Move: {final_recommended_move} ({final_move_desc})

        Task: Explain concisely (2-3 sentences) why "{final_move_desc}" is the final recommended action.
        - Start by stating the Basic Strategy move.
        - If the final move differs from Basic Strategy (e.g., Basic said Hit, final is Stand), explain that the recommendation was adjusted, mentioning the high bust probability ({bust_probability:.1%}) as the likely reason.
        - If the final move matches Basic Strategy, simply explain the Basic Strategy reason.
        - Briefly mention the True Count context if relevant (e.g., "even with a neutral count..." or "especially with a positive count...").
        """
        return self._generate(prompt)

    # --- Keep other methods like answer_question, get_situational_analysis if needed ---
    # def answer_question(...): ...
    # def get_situational_analysis(...): ...

# --- END OF FILE gemini_integration.py ---