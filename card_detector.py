# --- START OF FILE card_detector.py ---
import cv2
import numpy as np
from ultralytics import YOLO
from config import DETECTION_CONFIDENCE, CARD_RANKS, CARD_MODEL_PATH
from utils import draw_bounding_box

class CardDetector:
    def __init__(self):
        self.model = None
        self.model_names = {}
        try:
            self.model = YOLO(CARD_MODEL_PATH)
            print(f"Card recognition model loaded successfully from {CARD_MODEL_PATH}")
            if hasattr(self.model, 'names'):
                self.model_names = self.model.names
                print("--- IMPORTANT: Verify these Model Class Names match your rank extraction logic below ---")
                print("Model Class Names:", self.model_names) # <<<--- USER MUST CHECK THIS OUTPUT
            else:
                print("Warning: Could not access model class names.")
        except Exception as e:
            print(f"Error loading card model '{CARD_MODEL_PATH}': {e}")

    def detect(self, frame):
        annotated_frame = frame.copy()
        detected_boxes = []
        frame_height, frame_width, _ = frame.shape
        dealer_area_y_limit = frame_height * 0.4
        player_area_y_start = frame_height * 0.6

        if not self.model:
            return {'player': [], 'dealer': []}, annotated_frame

        try:
            results = self.model(frame, verbose=False, conf=DETECTION_CONFIDENCE)
        except Exception as e:
            print(f"Error during YOLO detection: {e}")
            return {'player': [], 'dealer': []}, annotated_frame

        if results and results[0].boxes:
            for box in results[0].boxes:
                coords = box.xyxy[0].tolist()
                confidence = box.conf[0].item()
                center_x = (coords[0] + coords[2]) / 2
                center_y = (coords[1] + coords[3]) / 2

                try:
                    if self.model_names and box.cls is not None and len(box.cls) > 0:
                        class_id = int(box.cls[0])
                        predicted_label = self.model_names.get(class_id, None) # Full label 'AS', 'KH', '10d' etc.

                        if predicted_label is None: continue

                        # --- Extract Rank ---
                        # !!! USER MUST VERIFY/ADJUST THIS LOGIC based on printed "Model Class Names" !!!
                        label_upper = predicted_label.upper()
                        card_rank = None
                        if label_upper.startswith('10'): card_rank = 'T'
                        elif len(label_upper) >= 1:
                            first_char = label_upper[0]
                            if first_char in CARD_RANKS: card_rank = first_char
                        # Add elif conditions here if model uses non-standard labels like 'Ace', 'King'

                        if card_rank is None or card_rank not in CARD_RANKS:
                            print(f"Warning: Could not extract valid rank from label '{predicted_label}'. Skipping.")
                            continue
                        # !!! END OF VERIFICATION BLOCK !!!

                        card_value_full_label = predicted_label # Use original case for tracking
                        card_label_display = predicted_label # Label for display box

                        detected_boxes.append({
                            'box': coords, 'center_x': center_x, 'center_y': center_y,
                            'label': card_label_display, # Show 'Ac', '10d', etc.
                            'value': card_value_full_label, # <<<--- VALUE IS FULL LABEL ('Ac', '10d')
                            'rank': card_rank,        # Extracted rank ('A', 'T', 'K')
                            'confidence': confidence
                        })
                    # ... (handle missing prediction/names) ...
                except Exception as e:
                    print(f"Error processing prediction for box {box}: {e}")
                    continue

        detected_boxes.sort(key=lambda item: item['center_x'])
        player_card_labels = []
        dealer_card_labels = []

        for item in detected_boxes:
            coords = item['box']; display_label = item['label']; full_label = item['value']; center_y = item['center_y']
            if center_y < dealer_area_y_limit:
                dealer_card_labels.append(full_label)
                color = (255, 0, 0); draw_bounding_box(annotated_frame, coords, display_label, color)
            elif center_y > player_area_y_start:
                 player_card_labels.append(full_label)
                 color = (0, 255, 0); draw_bounding_box(annotated_frame, coords, display_label, color)
            else:
                 color = (150, 150, 150); draw_bounding_box(annotated_frame, coords, display_label, color)

        # Return dictionary with lists of FULL LABELS found in each zone
        detected_data = {'player': player_card_labels, 'dealer': dealer_card_labels}
        return detected_data, annotated_frame

# --- END OF FILE card_detector.py ---