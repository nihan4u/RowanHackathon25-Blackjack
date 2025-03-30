# --- START OF FILE blackjack_ai/utils.py ---
import cv2
from config import * # This imports variables defined in config.py

# ... the rest of the functions (draw_hud_element, etc.) should follow ...

def draw_hud_element(frame, text, position, color=HUD_COLOR_TEXT):
    """Draws a single line of text on the HUD."""
    cv2.putText(frame, text, position, HUD_FONT, HUD_SCALE, color, HUD_THICKNESS, cv2.LINE_AA)

def draw_bounding_box(frame, box, label, color):
    """Draws a bounding box and label on the frame."""
    x1, y1, x2, y2 = map(int, box)
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, HUD_THICKNESS + 1) # Make box slightly thicker
    # Put label above the box
    label_size, base_line = cv2.getTextSize(label, HUD_FONT, HUD_SCALE, HUD_THICKNESS)
    # Ensure label background doesn't go above image top
    y1_label_bg = max(y1, label_size[1] + 5) # Position background based on text size
    cv2.rectangle(frame, (x1, y1_label_bg - label_size[1] - 5), (x1 + label_size[0], y1_label_bg - base_line + 5), color, cv2.FILLED)
    cv2.putText(frame, label, (x1 + 2, y1_label_bg - 3), HUD_FONT, HUD_SCALE, (0,0,0), HUD_THICKNESS, cv2.LINE_AA) # Black text on colored background

def format_hand(hand):
    """Formats a list of cards into a readable string."""
    return ", ".join(hand) if hand else "None"

def wrap_text(text, width=70):
    """Wraps text to a specified width for display."""
    lines = []
    current_line = ""
    for paragraph in text.split('\n'):
        words = paragraph.split()
        line = ""
        for word in words:
            # If the word itself is longer than width, just put it on its own line (or split it if necessary)
            if len(word) > width:
                 if line: # Add the current line before the long word
                     lines.append(line)
                 lines.append(word) # Add the long word
                 line = ""
                 continue

            # Check if adding the next word exceeds width
            test_line = line + (" " if line else "") + word
            if len(test_line) <= width:
                line = test_line
            else:
                lines.append(line) # Add the completed line
                line = word # Start new line with the current word
        if line:
            lines.append(line) # Add the last line of the paragraph
    return lines