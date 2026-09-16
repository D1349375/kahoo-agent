"""
Screen capture and coordinate mapping utilities.
"""

import logging
from typing import List, Optional, Tuple
from PIL import Image

logger = logging.getLogger("kahoo_agent.utils.screen")


def capture_screen(roi: Optional[List[int]] = None) -> Image.Image:
    """
    Captures a screenshot of the display or specific ROI.
    roi: [top, left, width, height]
    """
    try:
        import mss
        with mss.mss() as sct:
            if roi and len(roi) == 4:
                monitor = {
                    "top": int(roi[0]),
                    "left": int(roi[1]),
                    "width": int(roi[2]),
                    "height": int(roi[3]),
                }
            else:
                monitor = sct.monitors[1]  # Primary monitor

            sct_img = sct.grab(monitor)
            return Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
    except Exception as e:
        logger.debug(f"mss failed ({e}), falling back to PIL.ImageGrab")
        from PIL import ImageGrab
        if roi and len(roi) == 4:
            bbox = (roi[1], roi[0], roi[1] + roi[2], roi[0] + roi[3])
            return ImageGrab.grab(bbox=bbox)
        return ImageGrab.grab()


def click_color_button(
    index: int,
    player_window_rect: Optional[Tuple[int, int, int, int]] = None,
):
    """
    Clicks the corresponding Kahoot answer quadrant using PyAutoGUI.
    Default quadrant layout on Kahoot player screen:
    - Top-Left: Red / Triangle (0)
    - Top-Right: Blue / Diamond (1)
    - Bottom-Left: Yellow / Circle (2)
    - Bottom-Right: Green / Square (3)
    """
    try:
        import pyautogui

        if player_window_rect:
            left, top, width, height = player_window_rect
        else:
            # Assume full screen or right-half if not specified
            screen_w, screen_h = pyautogui.size()
            left, top, width, height = 0, 0, screen_w, screen_h

        # Calculate quadrant center points
        col = index % 2
        row = index // 2

        x = left + int(width * (0.25 if col == 0 else 0.75))
        y = top + int(height * (0.4 if row == 0 else 0.75))

        logger.info(f"Simulating mouse click on option [{index}] at ({x}, {y})")
        pyautogui.click(x, y)
    except Exception as e:
        logger.error(f"PyAutoGUI click failed: {e}")
