# --- START OF FILE config.py ---

import os
from dotenv import load_dotenv
import cv2

load_dotenv() # Load environment variables from .env file

# --- Camera Settings ---
CAMERA_INDEX = 0  # Usually 0 for built-in webcam, 1+ for external

# --- CV Model Settings ---
CARD_MODEL_PATH = 'card_model.pt' # Path to your card recognition model
DETECTION_CONFIDENCE = 0.4 # Adjust based on testing

# --- Blackjack Settings ---
NUM_DECKS = 1 # <<<--- CHANGED TO SINGLE DECK
SHOE_PENETRATION = 0.75 # Less relevant for single deck manual dealing simulation
# Ranks expected by the blackjack logic and used for tracking
CARD_RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
# Optional: Hi-Lo values for simple running count display
COUNTING_SYSTEM = {
    '2': 1, '3': 1, '4': 1, '5': 1, '6': 1,
    '7': 0, '8': 0, '9': 0,
    'T': -1, 'J': -1, 'Q': -1, 'K': -1, 'A': -1
}


# --- Basic Strategy Table (Single Deck, S17, DAS Allowed, Double Any 2, No Surrender) ---
# !!! COMPLETED BASED ON STANDARD SINGLE DECK CHARTS !!!
BASIC_STRATEGY = {
    # --- Hard Totals ---
    'Hard': {
        # Dealer showing 2
        2: {5:'H', 6:'H', 7:'H', 8:'H', 9:'D', 10:'D', 11:'D', 12:'H', 13:'S', 14:'S', 15:'S', 16:'S', 17:'S', 18:'S', 19:'S', 20:'S', 21:'S'},
        # Dealer showing 3
        3: {5:'H', 6:'H', 7:'H', 8:'D', 9:'D', 10:'D', 11:'D', 12:'H', 13:'S', 14:'S', 15:'S', 16:'S', 17:'S', 18:'S', 19:'S', 20:'S', 21:'S'}, # H8 vs 3 is Double
        # Dealer showing 4
        4: {5:'H', 6:'H', 7:'H', 8:'D', 9:'D', 10:'D', 11:'D', 12:'S', 13:'S', 14:'S', 15:'S', 16:'S', 17:'S', 18:'S', 19:'S', 20:'S', 21:'S'}, # H8 vs 4 is Double
        # Dealer showing 5
        5: {5:'H', 6:'H', 7:'H', 8:'D', 9:'D', 10:'D', 11:'D', 12:'S', 13:'S', 14:'S', 15:'S', 16:'S', 17:'S', 18:'S', 19:'S', 20:'S', 21:'S'}, # H8 vs 5 is Double
        # Dealer showing 6
        6: {5:'H', 6:'H', 7:'H', 8:'D', 9:'D', 10:'D', 11:'D', 12:'S', 13:'S', 14:'S', 15:'S', 16:'S', 17:'S', 18:'S', 19:'S', 20:'S', 21:'S'}, # H8 vs 6 is Double
        # Dealer showing 7
        7: {5:'H', 6:'H', 7:'H', 8:'H', 9:'H', 10:'D', 11:'D', 12:'H', 13:'H', 14:'H', 15:'H', 16:'H', 17:'S', 18:'S', 19:'S', 20:'S', 21:'S'},
        # Dealer showing 8
        8: {5:'H', 6:'H', 7:'H', 8:'H', 9:'H', 10:'D', 11:'D', 12:'H', 13:'H', 14:'H', 15:'H', 16:'H', 17:'S', 18:'S', 19:'S', 20:'S', 21:'S'},
        # Dealer showing 9
        9: {5:'H', 6:'H', 7:'H', 8:'H', 9:'H', 10:'D', 11:'D', 12:'H', 13:'H', 14:'H', 15:'H', 16:'H', 17:'S', 18:'S', 19:'S', 20:'S', 21:'S'},
        # Dealer showing T (10, J, Q, K)
        10: {5:'H', 6:'H', 7:'H', 8:'H', 9:'H', 10:'H', 11:'D', 12:'H', 13:'H', 14:'H', 15:'H', 16:'H', 17:'S', 18:'S', 19:'S', 20:'S', 21:'S'}, # H11 vs T is Double
        # Dealer showing A (Ace) - represented by 11
        11: {5:'H', 6:'H', 7:'H', 8:'H', 9:'H', 10:'H', 11:'H', 12:'H', 13:'H', 14:'H', 15:'H', 16:'H', 17:'S', 18:'S', 19:'S', 20:'S', 21:'S'} # H11 vs A is Hit
    },
    # --- Soft Totals (Contain an Ace counted as 11) ---
    'Soft': {
        # Dealer showing 2
        2: {13:'H', 14:'H', 15:'H', 16:'H', 17:'D', 18:'S', 19:'S', 20:'S', 21:'S'}, # S17 vs 2 is Double
        # Dealer showing 3
        3: {13:'D', 14:'D', 15:'D', 16:'D', 17:'D', 18:'D', 19:'S', 20:'S', 21:'S'},
        # Dealer showing 4
        4: {13:'D', 14:'D', 15:'D', 16:'D', 17:'D', 18:'D', 19:'S', 20:'S', 21:'S'},
        # Dealer showing 5
        5: {13:'D', 14:'D', 15:'D', 16:'D', 17:'D', 18:'D', 19:'D', 20:'S', 21:'S'}, # S19 vs 5 is Double
        # Dealer showing 6
        6: {13:'D', 14:'D', 15:'D', 16:'D', 17:'D', 18:'D', 19:'D', 20:'S', 21:'S'}, # S19 vs 6 is Double
        # Dealer showing 7
        7: {13:'H', 14:'H', 15:'H', 16:'H', 17:'S', 18:'S', 19:'S', 20:'S', 21:'S'},
        # Dealer showing 8
        8: {13:'H', 14:'H', 15:'H', 16:'H', 17:'S', 18:'S', 19:'S', 20:'S', 21:'S'},
        # Dealer showing 9
        9: {13:'H', 14:'H', 15:'H', 16:'H', 17:'H', 18:'H', 19:'S', 20:'S', 21:'S'},
        # Dealer showing T (10, J, Q, K)
        10: {13:'H', 14:'H', 15:'H', 16:'H', 17:'H', 18:'H', 19:'S', 20:'S', 21:'S'},
        # Dealer showing A (Ace) - represented by 11
        11: {13:'H', 14:'H', 15:'H', 16:'H', 17:'H', 18:'H', 19:'S', 20:'S', 21:'S'}
    },
    # --- Pairs ---
    'Pair': {
        # Dealer showing 2
        2: {('A','A'):'P', ('T','T'):'S', ('9','9'):'P', ('8','8'):'P', ('7','7'):'P', ('6','6'):'P', ('5','5'):'D', ('4','4'):'H', ('3','3'):'P', ('2','2'):'P'},
        # Dealer showing 3
        3: {('A','A'):'P', ('T','T'):'S', ('9','9'):'P', ('8','8'):'P', ('7','7'):'P', ('6','6'):'P', ('5','5'):'D', ('4','4'):'H', ('3','3'):'P', ('2','2'):'P'},
        # Dealer showing 4
        4: {('A','A'):'P', ('T','T'):'S', ('9','9'):'P', ('8','8'):'P', ('7','7'):'P', ('6','6'):'P', ('5','5'):'D', ('4','4'):'H', ('3','3'):'H', ('2','2'):'H'},
        # Dealer showing 5
        5: {('A','A'):'P', ('T','T'):'S', ('9','9'):'P', ('8','8'):'P', ('7','7'):'P', ('6','6'):'P', ('5','5'):'D', ('4','4'):'P', ('3','3'):'P', ('2','2'):'P'},
        # Dealer showing 6
        6: {('A','A'):'P', ('T','T'):'S', ('9','9'):'P', ('8','8'):'P', ('7','7'):'P', ('6','6'):'P', ('5','5'):'D', ('4','4'):'P', ('3','3'):'P', ('2','2'):'P'},
        # Dealer showing 7
        7: {('A','A'):'P', ('T','T'):'S', ('9','9'):'S', ('8','8'):'P', ('7','7'):'P', ('6','6'):'H', ('5','5'):'D', ('4','4'):'H', ('3','3'):'H', ('2','2'):'H'},
        # Dealer showing 8
        8: {('A','A'):'P', ('T','T'):'S', ('9','9'):'P', ('8','8'):'P', ('7','7'):'H', ('6','6'):'H', ('5','5'):'D', ('4','4'):'H', ('3','3'):'H', ('2','2'):'H'},
        # Dealer showing 9
        9: {('A','A'):'P', ('T','T'):'S', ('9','9'):'S', ('8','8'):'P', ('7','7'):'H', ('6','6'):'H', ('5','5'):'D', ('4','4'):'H', ('3','3'):'H', ('2','2'):'H'},
        # Dealer showing T (10, J, Q, K)
        10: {('A','A'):'P', ('T','T'):'S', ('9','9'):'S', ('8','8'):'P', ('7','7'):'H', ('6','6'):'H', ('5','5'):'H', ('4','4'):'H', ('3','3'):'H', ('2','2'):'H'},
        # Dealer showing A (Ace) - represented by 11
        11: {('A','A'):'P', ('T','T'):'S', ('9','9'):'S', ('8','8'):'P', ('7','7'):'H', ('6','6'):'H', ('5','5'):'H', ('4','4'):'H', ('3','3'):'H', ('2','2'):'H'}
    }
}

# --- Gemini Settings ---
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    print("Warning: GEMINI_API_KEY not found in .env file. Gemini features will be disabled.")
GEMINI_MODEL_NAME = "gemini-1.5-flash"

# --- UI Settings ---
HUD_FONT = cv2.FONT_HERSHEY_SIMPLEX
HUD_SCALE = 0.6
HUD_THICKNESS = 1
HUD_COLOR_GOOD = (0, 255, 0)  # Green
HUD_COLOR_BAD = (0, 0, 255)    # Red
HUD_COLOR_NEUTRAL = (255, 255, 0) # Cyan
HUD_COLOR_TEXT = (255, 255, 255) # White

# --- END OF FILE config.py ---