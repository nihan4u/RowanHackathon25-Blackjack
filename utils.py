# --- START OF FILE utils.py ---
import cv2
from config import *

def draw_hud_element(frame, text, position, color=HUD_COLOR_TEXT):
    cv2.putText(frame, text, position, HUD_FONT, HUD_SCALE, color, HUD_THICKNESS, cv2.LINE_AA)

def draw_bounding_box(frame, box, label, color):
    x1, y1, x2, y2 = map(int, box)
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, HUD_THICKNESS + 1)
    label_size, base_line = cv2.getTextSize(label, HUD_FONT, HUD_SCALE, HUD_THICKNESS)
    y1_label_bg = max(y1, label_size[1] + 5)
    cv2.rectangle(frame, (x1, y1_label_bg - label_size[1] - 5), (x1 + label_size[0], y1_label_bg - base_line + 5), color, cv2.FILLED)
    cv2.putText(frame, label, (x1 + 2, y1_label_bg - 3), HUD_FONT, HUD_SCALE, (0,0,0), HUD_THICKNESS, cv2.LINE_AA)

def format_hand(hand):
    return ", ".join(hand) if hand else "None"

def wrap_text(text, width=70):
    lines = []
    current_line = ""
    for paragraph in text.split('\n'):
        words = paragraph.split()
        line = ""
        for word in words:
            if len(word) > width:
                 if line: lines.append(line)
                 lines.append(word); line = ""
                 continue
            test_line = line + (" " if line else "") + word
            if len(test_line) <= width: line = test_line
            else: lines.append(line); line = word
        if line: lines.append(line)
    return lines
# --- END OF FILE utils.py ---