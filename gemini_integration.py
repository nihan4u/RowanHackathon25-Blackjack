# --- START OF FILE gemini_integration.py ---
import google.generativeai as genai
import time
from config import GEMINI_API_KEY, GEMINI_MODEL_NAME
from utils import format_hand

class GeminiIntegration:
    def __init__(self):
        self.initialized = False
        if not GEMINI_API_KEY: print("Gemini API Key not configured."); return
        try:
            genai.configure(api_key=GEMINI_API_KEY)
            self.generation_config = genai.types.GenerationConfig(max_output_tokens=300)
            self.safety_settings = [ {"category": c, "threshold": "BLOCK_MEDIUM_AND_ABOVE"} for c in ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]]
            self.model = genai.GenerativeModel(GEMINI_MODEL_NAME, generation_config=self.generation_config, safety_settings=self.safety_settings)
            self.initialized = True; print(f"Gemini initialized successfully with model {GEMINI_MODEL_NAME}.")
        except Exception as e: print(f"Error initializing Gemini: {e}")

    def _generate(self, prompt):
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

    def explain_strategy_enhanced(self, player_hand_labels, dealer_up_card_label,
                                  hi_lo_true_count, basic_strategy_move,
                                  final_recommended_move, bust_probability,
                                  player_total, dealer_up_card_value, # Use numeric dealer value for context
                                  deck_composition_summary, override_reason):
        """Asks Gemini to explain the recommended move, considering multiple factors."""
        if not self.initialized: return "Gemini N/A"

        player_hand_str = format_hand(player_hand_labels)
        dealer_card_str = dealer_up_card_label if dealer_up_card_label else "N/A"
        move_map = {'H': 'Hit', 'S': 'Stand', 'D': 'Double Down', 'P': 'Split', 'Bust': 'Bust', 'Err': 'Error', 'N/A': 'N/A'}
        basic_move_desc = move_map.get(basic_strategy_move, basic_strategy_move)
        final_move_desc = move_map.get(final_recommended_move, final_recommended_move)

        prompt = f"""
        Analyze the Blackjack situation and explain the final recommendation considering all factors:

        Player Hand: {player_hand_str} (Total Value: {player_total})
        Dealer Shows: {dealer_card_str} (Numeric Value: {dealer_up_card_value})
        Deck Status: {deck_composition_summary}
        Hi-Lo True Count: {hi_lo_true_count:+.1f}
        Basic Strategy Suggestion: {basic_strategy_move} ({basic_move_desc})
        Calculated Bust Probability on Hit: {bust_probability:.1%}
        Final Recommended Move: {final_recommended_move} ({final_move_desc})
        Reason for Deviation (if any): {override_reason if override_reason else "None"}

        Task: Explain concisely (2-4 sentences) the reasoning behind the "{final_move_desc}" recommendation.
        1. State the standard Basic Strategy move.
        2. If the Final Move differs, explain *why* it deviates. Mention the specific reason provided (e.g., "Index Play triggered by True Count", "High Bust Probability").
        3. Briefly incorporate the deck composition summary or True Count context into the explanation where relevant (e.g., "...standing is safer, especially given the {deck_composition_summary.lower()}" or "...hitting is correct by basic strategy, and the neutral count doesn't suggest deviating.").
        4. Keep the tone advisory and informative.
        """
        return self._generate(prompt)

# --- END OF FILE gemini_integration.py ---