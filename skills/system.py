import os
import subprocess
import ctypes
import webbrowser
from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume, IAudioEndpointVolume
from colorama import Fore

class SystemSkills:
    def __init__(self):
        try:
            devices = AudioUtilities.GetSpeakers()
            self.master_volume = devices.EndpointVolume
            print(Fore.GREEN + "✅ System Skills: Master Volume Linked")
        except Exception as e:
            print(Fore.RED + f"❌ System Skills Init Error: {e}")

    # ── VOLUME ──────────────────────────────────────────────────────────────

    def set_master_volume(self, level):
        self.master_volume.SetMasterVolumeLevelScalar(level / 100.0, None)
        return f"Master volume set to {level}%."

    def set_app_volume(self, app_name, level):
        sessions = AudioUtilities.GetAllSessions()
        found = False
        for session in sessions:
            if session.Process and app_name.lower() in session.Process.name().lower():
                volume = session._ctl.QueryInterface(ISimpleAudioVolume)
                volume.SetMasterVolume(level / 100.0, None)
                found = True
        return f"Set {app_name} volume to {level}%." if found else f"{app_name} not found in audio sessions."

    def mute_master(self):
        self.master_volume.SetMute(1, None)
        return "Muted, sir."

    def unmute_master(self):
        self.master_volume.SetMute(0, None)
        return "Unmuted, sir."

    def get_volume(self):
        level = round(self.master_volume.GetMasterVolumeLevelScalar() * 100)
        return f"Master volume is at {level}%."

    # ── MEDIA CONTROLS (no keyboard sim — uses Windows WM_APPCOMMAND) ────────

    def _send_media_key(self, command_id):
        """
        Sends a media command via WM_APPCOMMAND to the foreground window.
        No actual keypress — this is a system message.
        APPCOMMAND values: 14=play/pause, 11=next, 12=prev, 13=stop
        """
        APPCOMMAND_MEDIA_PLAY_PAUSE = 14
        APPCOMMAND_MEDIA_NEXTTRACK  = 11
        APPCOMMAND_MEDIA_PREVTRACK  = 12
        APPCOMMAND_MEDIA_STOP       = 13
        WM_APPCOMMAND = 0x0319

        hwnd = ctypes.windll.user32.GetForegroundWindow()
        ctypes.windll.user32.SendMessageW(hwnd, WM_APPCOMMAND, 0, command_id * 65536)

    def media_play_pause(self):
        self._send_media_key(14)
        return "Toggled play/pause."

    def media_next(self):
        self._send_media_key(11)
        return "Skipped to next track."

    def media_previous(self):
        self._send_media_key(12)
        return "Going back a track."

    def media_stop(self):
        self._send_media_key(13)
        return "Media stopped."

    # ── APPS & PROCESSES ────────────────────────────────────────────────────

    def open_app(self, app_name):
        subprocess.Popen(f"start {app_name}", shell=True)
        return f"Opening {app_name}, sir."

    def kill_process(self, app_name):
        os.system(f"taskkill /f /im {app_name}.exe >nul 2>&1")
        return f"Terminated {app_name}."

    def lag_killer(self):
        hogs = ["chrome", "msedge", "steam", "epicgameslauncher", "discord"]
        for app in hogs:
            os.system(f"taskkill /f /im {app}.exe >nul 2>&1")
        return "Background processes cleared. Network should be cleaner now."

    # ── POWER & SESSION ──────────────────────────────────────────────────────

    def sleep_pc(self):
        os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
        return "Going to sleep, sir."

    def lock_pc(self):
        ctypes.windll.user32.LockWorkStation()
        return "Workstation locked."

    def shutdown(self, delay=60):
        os.system(f"shutdown /s /t {delay}")
        return f"Shutdown scheduled in {delay} seconds. Say 'cancel shutdown' to abort."

    def cancel_shutdown(self):
        os.system("shutdown /a")
        return "Shutdown cancelled."

    def restart(self, delay=60):
        os.system(f"shutdown /r /t {delay}")
        return f"Restart scheduled in {delay} seconds."

    def hibernate(self):
        os.system("shutdown /h")
        return "Hibernating, sir."

    # ── DISPLAY ──────────────────────────────────────────────────────────────

    def set_brightness(self, level):
        """Set screen brightness via WMI (works on laptops, some monitors)."""
        try:
            import wmi
            c = wmi.WMI(namespace='wmi')
            methods = c.WmiMonitorBrightnessMethods()[0]
            methods.WmiSetBrightness(level, 0)
            return f"Brightness set to {level}%."
        except Exception as e:
            return f"Brightness control unavailable on this display: {e}"

    def turn_off_monitors(self):
        """Turn off monitors without sleeping the PC."""
        ctypes.windll.user32.SendMessageW(0xFFFF, 0x0112, 0xF170, 2)
        return "Monitors off."

    # ── NETWORK ─────────────────────────────────────────────────────────────

    def flush_dns(self):
        os.system("ipconfig /flushdns >nul 2>&1")
        return "DNS cache flushed."

    def get_ip(self):
        result = subprocess.check_output("ipconfig", shell=True).decode()
        for line in result.split('\n'):
            if "IPv4" in line:
                return f"Your IP is {line.split(':')[-1].strip()}."
        return "Could not determine IP address."

    def wifi_off(self):
        os.system("netsh interface set interface Wi-Fi disabled >nul 2>&1")
        return "Wi-Fi disabled."

    def wifi_on(self):
        os.system("netsh interface set interface Wi-Fi enabled >nul 2>&1")
        return "Wi-Fi enabled."

    # ── NOTIFICATIONS ────────────────────────────────────────────────────────

    def notify(self, title, message):
        """Send a Windows toast notification."""
        try:
            from win10toast import ToastNotifier
            toaster = ToastNotifier()
            toaster.show_toast(title, message, duration=5, threaded=True)
            return f"Notification sent: {title}"
        except ImportError:
            return "win10toast not installed. Run: pip install win10toast"

    # ── STEAM ────────────────────────────────────────────────────────────────

    def launch_steam_game(self, game_id):
        """Launch a Steam game by its app ID without opening Steam UI."""
        webbrowser.open(f"steam://rungameid/{game_id}")
        return f"Launching Steam game {game_id}."

    def open_steam(self):
        subprocess.Popen("start steam://open/main", shell=True)
        return "Opening Steam."

    # ── CLIPBOARD ────────────────────────────────────────────────────────────

    def get_clipboard(self):
        import pyperclip
        content = pyperclip.paste()
        return content if content else "Clipboard is empty."

    def set_clipboard(self, text):
        import pyperclip
        pyperclip.copy(text)
        return "Copied to clipboard."