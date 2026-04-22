import pyautogui
import time
from colorama import Fore

class GamingSkills:
    def __init__(self):
        # NVIDIA typically uses Alt+F10 to save a clip
        self.save_shortcut = ['alt', 'f10']

    def clip_that(self):
        """Triggers NVIDIA ShadowPlay to save the last X minutes."""
        try:
            # Simulate the keypress
            pyautogui.hotkey(*self.save_shortcut)
            return "ShadowPlay clip saved, sir. I'll make sure it's high quality."
        except Exception as e:
            return f"I couldn't trigger the NVIDIA overlay: {e}"

    def kill_lag(self):
        """Kills common bandwidth hogs for Valorant ping stability."""
        targets = ["chrome", "steam", "epicgameslauncher", "spotify"]
        for app in targets:
            import os
            os.system(f"taskkill /f /im {app}.exe >nul 2>&1")
        return "Background bandwidth hogs terminated. Your ping should be clean now."