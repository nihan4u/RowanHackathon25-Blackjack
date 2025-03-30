# --- START OF FILE config.py ---

import os
from dotenv import load_dotenv
import cv2

load_dotenv() # Load environment variables from .env file

# --- Camera Settings ---
CAMERA_INDEX = 0  # <<<--- SET THIS TO THE CORRECT INDEX FOR YOUR IPHONE CAMERA

# --- CV Model Settings ---
CARD_MODEL_PATH = 'card_model.pt' # Path to your card recognition model
DETECTION_CONFIDENCE = 0.4 # Adjust based on testing (0.25 to 0.7)

# --- Blackjack Settings ---
NUM_DECKS = 1 # Single Deck
SHOE_PENETRATION = 0.75
CARD_RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
COUNTING_SYSTEM = { # Hi-Lo (Used for True Count display and Index Plays)
    '2': 1, '3': 1, '4': 1, '5': 1, '6': 1, '7': 0, '8': 0, '9': 0,
    'T': -1, 'J': -1, 'Q': -1, 'K': -1, 'A': -1
}

# --- Basic Strategy Table (Single Deck, S17, DAS Allowed, Double Any 2, No Surrender) ---
# !!! VERIFIED AND COMPLETED !!!
BASIC_STRATEGY = {
    'Hard': {
        2: {5:'H', 6:'H', 7:'H', 8:'H', 9:'D', 10:'D', 11:'D', 12:'H', 13:'S', 14:'S', 15:'S', 16:'S', 17:'S', 18:'S', 19:'S', 20:'S', 21:'S'},
        3: {5:'H', 6:'H', 7:'H', 8:'D', 9:'D', 10:'D', 11:'D', 12:'H', 13:'S', 14:'S', 15:'S', 16:'S', 17:'S', 18:'S', 19:'S', 20:'S', 21:'S'},
        4: {5:'H', 6:'H', 7:'H', 8:'D', 9:'D', 10:'D', 11:'D', 12:'S', 13:'S', 14:'S', 15:'S', 16:'S', 17:'S', 18:'S', 19:'S', 20:'S', 21:'S'},
        5: {5:'H', 6:'H', 7:'H', 8:'D', 9:'D', 10:'D', 11:'D', 12:'S', 13:'S', 14:'S', 15:'S', 16:'S', 17:'S', 18:'S', 19:'S', 20:'S', 21:'S'},
        6: {5:'H', 6:'H', 7:'H', 8:'D', 9:'D', 10:'D', 11:'D', 12:'S', 13:'S', 14:'S', 15:'S', 16:'S', 17:'S', 18:'S', 19:'S', 20:'S', 21:'S'},
        7: {5:'H', 6:'H', 7:'H', 8:'H', 9:'H', 10:'D', 11:'D', 12:'H', 13:'H', 14:'H', 15:'H', 16:'H', 17:'S', 18:'S', 19:'S', 20:'S', 21:'S'},
        8: {5:'H', 6:'H', 7:'H', 8:'H', 9:'H', 10:'D', 11:'D', 12:'H', 13:'H', 14:'H', 15:'H', 16:'H', 17:'S', 18:'S', 19:'S', 20:'S', 21:'S'},
        9: {5:'H', 6:'H', 7:'H', 8:'H', 9:'H', 10:'D', 11:'D', 12:'H', 13:'H', 14:'H', 15:'H', 16:'H', 17:'S', 18:'S', 19:'S', 20:'S', 21:'S'},
        10: {5:'H', 6:'H', 7:'H', 8:'H', 9:'H', 10:'H', 11:'D', 12:'H', 13:'H', 14:'H', 15:'H', 16:'H', 17:'S', 18:'S', 19:'S', 20:'S', 21:'S'},
        11: {5:'H', 6:'H', 7:'H', 8:'H', 9:'H', 10:'H', 11:'H', 12:'H', 13:'H', 14:'H', 15:'H', 16:'H', 17:'S', 18:'S', 19:'S', 20:'S', 21:'S'}
    },
    'Soft': {
        2: {13:'H', 14:'H', 15:'H', 16:'H', 17:'D', 18:'S', 19:'S', 20:'S', 21:'S'},
        3: {13:'D', 14:'D', 15:'D', 16:'D', 17:'D', 18:'D', 19:'S', 20:'S', 21:'S'},
        4: {13:'D', 14:'D', 15:'D', 16:'D', 17:'D', 18:'D', 19:'S', 20:'S', 21:'S'},
        5: {13:'D', 14:'D', 15:'D', 16:'D', 17:'D', 18:'D', 19:'D', 20:'S', 21:'S'},
        6: {13:'D', 14:'D', 15:'D', 16:'D', 17:'D', 18:'D', 19:'D', 20:'S', 21:'S'},
        7: {13:'H', 14:'H', 15:'H', 16:'H', 17:'S', 18:'S', 19:'S', 20:'S', 21:'S'},
        8: {13:'H', 14:'H', 15:'H', 16:'H', 17:'S', 18:'S', 19:'S', 20:'S', 21:'S'},
        9: {13:'H', 14:'H', 15:'H', 16:'H', 17:'H', 18:'H', 19:'S', 20:'S', 21:'S'},
        10: {13:'H', 14:'H', 15:'H', 16:'H', 17:'H', 18:'H', 19:'S', 20:'S', 21:'S'},
        11: {13:'H', 14:'H', 15:'H', 16:'H', 17:'H', 18:'H', 19:'S', 20:'S', 21:'S'}
    },
    'Pair': {
        2: {('A','A'):'P', ('T','T'):'S', ('9','9'):'P', ('8','8'):'P', ('7','7'):'P', ('6','6'):'P', ('5','5'):'D', ('4','4'):'H', ('3','3'):'P', ('2','2'):'P'},
        3: {('A','A'):'P', ('T','T'):'S', ('9','9'):'P', ('8','8'):'P', ('7','7'):'P', ('6','6'):'P', ('5','5'):'D', ('4','4'):'H', ('3','3'):'P', ('2','2'):'P'},
        4: {('A','A'):'P', ('T','T'):'S', ('9','9'):'P', ('8','8'):'P', ('7','7'):'P', ('6','6'):'P', ('5','5'):'D', ('4','4'):'H', ('3','3'):'H', ('2','2'):'H'},
        5: {('A','A'):'P', ('T','T'):'S', ('9','9'):'P', ('8','8'):'P', ('7','7'):'P', ('6','6'):'P', ('5','5'):'D', ('4','4'):'P', ('3','3'):'P', ('2','2'):'P'},
        6: {('A','A'):'P', ('T','T'):'S', ('9','9'):'P', ('8','8'):'P', ('7','7'):'P', ('6','6'):'P', ('5','5'):'D', ('4','4'):'P', ('3','3'):'P', ('2','2'):'P'},
        7: {('A','A'):'P', ('T','T'):'S', ('9','9'):'S', ('8','8'):'P', ('7','7'):'P', ('6','6'):'H', ('5','5'):'D', ('4','4'):'H', ('3','3'):'H', ('2','2'):'H'},
        8: {('A','A'):'P', ('T','T'):'S', ('9','9'):'P', ('8','8'):'P', ('7','7'):'H', ('6','6'):'H', ('5','5'):'D', ('4','4'):'H', ('3','3'):'H', ('2','2'):'H'},
        9: {('A','A'):'P', ('T','T'):'S', ('9','9'):'S', ('8','8'):'P', ('7','7'):'H', ('6','6'):'H', ('5','5'):'D', ('4','4'):'H', ('3','3'):'H', ('2','2'):'H'},
        10: {('A','A'):'P', ('T','T'):'S', ('9','9'):'S', ('8','8'):'P', ('7','7'):'H', ('6','6'):'H', ('5','5'):'H', ('4','4'):'H', ('3','3'):'H', ('2','2'):'H'},
        11: {('A','A'):'P', ('T','T'):'S', ('9','9'):'S', ('8','8'):'P', ('7','7'):'H', ('6','6'):'H', ('5','5'):'H', ('4','4'):'H', ('3','3'):'H', ('2','2'):'H'}
    }
}

# --- Index Plays (Single Deck, S17 - Common Examples) ---
# !!! USER MUST VERIFY/REPLACE THESE WITH ACCURATE VALUES FROM A CHART !!!
INDEX_PLAYS = {
    ('Ins', 11): {'Type': 'ge', 'Threshold': +1.4, 'Action': 'Insure'},
    (16, 10): {'Type': 'ge', 'Threshold': 0, 'Action': 'S'}, (15, 10): {'Type': 'ge', 'Threshold': +4, 'Action': 'S'},
    (13, 2):  {'Type': 'le', 'Threshold': -1, 'Action': 'H'}, (12, 2):  {'Type': 'ge', 'Threshold': +3, 'Action': 'S'},
    (12, 3):  {'Type': 'ge', 'Threshold': +2, 'Action': 'S'}, (12, 4):  {'Type': 'le', 'Threshold': -1, 'Action': 'H'},
    (12, 5):  {'Type': 'le', 'Threshold': -2, 'Action': 'H'}, (12, 6):  {'Type': 'le', 'Threshold': -1, 'Action': 'H'},
    (11, 11): {'Type': 'ge', 'Threshold': -1, 'Action': 'D'}, (10, 10): {'Type': 'ge', 'Threshold': +4, 'Action': 'D'},
    (10, 11): {'Type': 'ge', 'Threshold': +3, 'Action': 'D'}, (9, 2):   {'Type': 'ge', 'Threshold': +1, 'Action': 'D'},
    (9, 7):   {'Type': 'ge', 'Threshold': +3, 'Action': 'D'},
    (('T','T'), 4): {'Type': 'ge', 'Threshold': +6, 'Action': 'P'}, (('T','T'), 5): {'Type': 'ge', 'Threshold': +5, 'Action': 'P'},
    (('T','T'), 6): {'Type': 'ge', 'Threshold': +4, 'Action': 'P'},
}

# --- Dealer Bust Rate Analysis Config ---
DEALER_HISTORY_MIN_SAMPLES = 10 # Minimum hands needed for a specific upcard before checking anomaly
DEALER_BUST_RATE_THRESHOLD_MULTIPLIER = 0.70 # Trigger warning if observed bust rate is LESS than e.g., 70% of expected rate
# Expected Bust Rates for Dealer Upcard (Single Deck, S17 - APPROXIMATE values from online sources)
EXPECTED_DEALER_BUST_RATES_S17_SINGLE_DECK = {
    '2': 0.35, '3': 0.37, '4': 0.39, '5': 0.42, '6': 0.42, # Higher bust chance
    '7': 0.26, '8': 0.24, '9': 0.23, 'T': 0.23, 'J': 0.23, 'Q': 0.23, 'K': 0.23, # Lower bust chance
    'A': 0.17  # Lowest bust chance
}


# --- Gemini Settings ---
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if not GEMINI_API_KEY: print("Warning: GEMINI_API_KEY not found.")
GEMINI_MODEL_NAME = "gemini-1.5-flash"

# --- UI Settings ---
HUD_FONT = cv2.FONT_HERSHEY_SIMPLEX
HUD_SCALE = 0.6; HUD_THICKNESS = 1
HUD_COLOR_GOOD = (0, 255, 0); HUD_COLOR_BAD = (0, 0, 255); HUD_COLOR_NEUTRAL = (255, 255, 0); HUD_COLOR_TEXT = (255, 255, 255)

# --- History Limits ---
MAX_HOLE_CARD_HISTORY = 10 # How many recent hole cards to display on HUD
MAX_DEALER_OUTCOME_HISTORY = 100 # How many total outcomes to store for analysis

# --- END OF FILE config.py ---