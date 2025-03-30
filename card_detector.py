import cv2
import numpy as np
from ultralytics import YOLO
# import random # No longer needed for simulation
from config import DETECTION_CONFIDENCE, CARD_RANKS, CARD_MODEL_PATH # Use CARD_MODEL_PATH
from utils import draw_bounding_box

class CardDetector:
    def __init__(self): # Removed model_path argument, uses config directly
        """
        Initializes the card detector using the model specified in config.py.
        """
        self.model = None
        self.model_names = {} # To store class names
        try:
            self.model = YOLO(CARD_MODEL_PATH) # Use the path to your new card model
            print(f"Card recognition model loaded successfully from {CARD_MODEL_PATH}")
            # *** IMPORTANT: Check the output of this print statement when you run the code ***
            if hasattr(self.model, 'names'):
                self.model_names = self.model.names # Store the class names map
                print("Model Class Names:", self.model_names)
                # Example output might be: {0: '10C', 1: '10D', 2: '10H', ..., 51: 'AS'}
            else:
                print("Warning: Could not access model class names. Prediction parsing might fail.")
        except Exception as e:
            print(f"Error loading card model '{CARD_MODEL_PATH}': {e}")
            # self.model remains None

    def detect(self, frame):
        """
        Detects cards in the frame and identifies their rank and suit using the loaded model.

        Args:
            frame: The input video frame.

        Returns:
            tuple: (detected_cards_dict, annotated_frame)
                   detected_cards_dict (dict): {'player': list_of_ranks, 'dealer': list_of_ranks}
                                               e.g., {'player': ['A', 'K'], 'dealer': ['7']}
                   annotated_frame: The frame with bounding boxes and labels drawn.
        """
        annotated_frame = frame.copy()
        detected_boxes = [] # Store raw detections first
        frame_height, frame_width, _ = frame.shape

        # Define detection zones (adjust percentages as needed)
        dealer_area_y_limit = frame_height * 0.4 # Top 40% for dealer
        player_area_y_start = frame_height * 0.6 # Bottom 40% for player

        if not self.model:
            return {'player': [], 'dealer': []}, annotated_frame # Return empty if model failed to load

        try:
            results = self.model(frame, verbose=False, conf=DETECTION_CONFIDENCE)
        except Exception as e:
            print(f"Error during YOLO detection: {e}")
            return {'player': [], 'dealer': []}, annotated_frame

        # --- Process Detections ---
        if results and results[0].boxes:
            for box in results[0].boxes:
                coords = box.xyxy[0].tolist()
                confidence = box.conf[0].item()
                center_x = (coords[0] + coords[2]) / 2
                center_y = (coords[1] + coords[3]) / 2

                # --- Use Real Predictions ---
                try:
                    # Ensure model loaded, has names, and prediction exists
                    if self.model_names and box.cls is not None and len(box.cls) > 0:
                        class_id = int(box.cls[0])          # Get predicted class index (e.g., 51)
                        predicted_label = self.model_names.get(class_id, None) # Get label (e.g., 'AS') safely

                        if predicted_label is None:
                             print(f"Warning: Predicted class ID {class_id} not found in model names map. Skipping.")
                             continue

                        # --- Extract Rank ('A', 'K', 'Q', 'J', 'T', '9'...'2') for game logic ---
                        # !!! Adjust this logic based on your actual model's labels (self.model_names) !!!
                        label_upper = predicted_label.upper()
                        if label_upper.startswith('10'): # Handle '10'
                            card_rank = 'T'
                        elif len(label_upper) > 0:
                            # Use first character, assuming format like 'AS', 'KH', '7D'
                            card_rank = label_upper[0]
                            # Validate rank is expected
                            if card_rank not in CARD_RANKS:
                                print(f"Warning: Extracted rank '{card_rank}' from label '{predicted_label}' not standard. Skipping.")
                                continue # Skip this detection
                        else:
                            print(f"Warning: Empty predicted label '{predicted_label}'. Skipping.")
                            continue # Skip this detection

                        card_value = card_rank         # Value used by blackjack_logic.py
                        card_label_display = predicted_label # Full label for display on box

                        # Add the accurately detected card info
                        detected_boxes.append({
                            'box': coords,
                            'center_x': center_x,
                            'center_y': center_y,
                            'label': card_label_display, # Show 'AS', 'KH', etc.
                            'value': card_value,         # Pass 'A', 'K', etc.
                            'confidence': confidence
                        })
                    else:
                        # Handle cases where prediction is missing
                        if not self.model_names:
                             print("Warning: Card model class names not available.")
                        else:
                             print(f"Warning: Box detected without class prediction: {box}")

                except KeyError:
                     print(f"Internal Error: Predicted class ID {class_id} caused KeyError (should have been caught by .get).")
                     continue
                except Exception as e:
                    print(f"Error processing prediction for box {box}: {e}")
                    continue # Skip on other errors

        # --- Assign Detections to Player/Dealer Zones ---
        # Sort by horizontal position first for somewhat stable ordering within zones
        detected_boxes.sort(key=lambda item: item['center_x'])

        player_cards_ranks = []
        dealer_cards_ranks = []

        for item in detected_boxes:
            coords = item['box']
            label = item['label'] # Full label 'AS', 'KH'
            value = item['value'] # Rank 'A', 'K'
            center_y = item['center_y']

            # Assign based on Y-coordinate zones
            if center_y < dealer_area_y_limit:
                dealer_cards_ranks.append(value)
                color = (255, 0, 0) # Red for dealer zone
                draw_bounding_box(annotated_frame, coords, f"{label}", color) # Removed (D?)
            elif center_y > player_area_y_start:
                 player_cards_ranks.append(value)
                 color = (0, 255, 0) # Green for player zone
                 draw_bounding_box(annotated_frame, coords, f"{label}", color) # Removed (P?)
            else:
                 # Card detected in the middle zone - draw gray, don't assign
                 color = (150, 150, 150) # Gray for unassigned middle zone
                 draw_bounding_box(annotated_frame, coords, f"{label}", color)

        # Return dictionary with lists of ranks found in each zone for this frame
        detected_data = {'player': player_cards_ranks, 'dealer': dealer_cards_ranks}
        return detected_data, annotated_frame