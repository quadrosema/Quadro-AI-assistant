"""
Async watchdog — monitors system and emits events.
No more callback hell — just emit events to the bus.
"""

import asyncio
import psutil
import pyperclip
from colorama import Fore
from config.settings import CPU_ALERT_THRESHOLD, CPU_ALERT_DURATION, RAM_ALERT_THRESHOLD, CLIPBOARD_MIN_LENGTH
from core.events import cpu_alert_event, clipboard_event, mode_change_event

MODE_TRIGGERS = {
    "gaming": [
        "valorant.exe", "valorant-win64-shipping.exe", "csgo.exe", "cs2.exe",
        "fortnite.exe", "minecraft.exe", "leagueclient.exe", "overwatch.exe",
        "r5apex.exe", "stremio.exe"
    ],
    "work": [
        "code.exe", "pycharm64.exe", "idea64.exe", "winword.exe",
        "excel.exe", "notion.exe", "figma.exe", "postman.exe", "obsidian.exe",
    ],
    "idle": []
}

MANUAL_LOCK_SECONDS = 120

class AsyncWatchdog:
    def __init__(self, bus):
        self.bus = bus
        
        self._stop_event = asyncio.Event()
        self._cpu_high_since = None
        self._ram_alerted = False
        self._manual_lock_until = 0
        
        self._current_mode = self._detect_mode()
        print(Fore.MAGENTA + f"   [WATCHDOG] Starting in {self._current_mode.upper()} mode")
        
        try:
            self._last_clipboard = pyperclip.paste()
        except Exception:
            self._last_clipboard = ""
        
        self.monitor_task = None
    
    def _get_running_processes(self):
        try:
            return set(p.name().lower() for p in psutil.process_iter(['name']))
        except Exception:
            return set()
    
    def _detect_mode(self):
        running = self._get_running_processes()
        for mode, triggers in MODE_TRIGGERS.items():
            if mode == "idle":
                continue
            if any(t.lower() in running for t in triggers):
                return mode
        return "idle"
    
    def set_mode_manually(self, mode):
        """Called by Brain on verbal command."""
        import time
        self._current_mode = mode
        self._manual_lock_until = time.time() + MANUAL_LOCK_SECONDS
        print(Fore.MAGENTA + f"   [WATCHDOG] Manual lock → {mode.upper()} (locked {MANUAL_LOCK_SECONDS}s)")
    
    async def _monitor_loop(self):
        """Main monitoring loop."""
        import time
        
        # Grace period on startup
        await asyncio.sleep(10)
        
        while not self._stop_event.is_set():
            try:
                # Mode detection
                if time.time() > self._manual_lock_until:
                    detected_mode = self._detect_mode()
                    if detected_mode != self._current_mode:
                        self._current_mode = detected_mode
                        await self.bus.emit(mode_change_event(detected_mode))
                        print(Fore.MAGENTA + f"   [WATCHDOG] App triggered → {detected_mode.upper()}")
                
                # CPU alert
                cpu = psutil.cpu_percent(interval=1)
                if cpu >= CPU_ALERT_THRESHOLD:
                    if self._cpu_high_since is None:
                        self._cpu_high_since = time.time()
                    elif time.time() - self._cpu_high_since >= CPU_ALERT_DURATION:
                        await self.bus.emit(cpu_alert_event(int(cpu)))
                        self._cpu_high_since = None
                else:
                    self._cpu_high_since = None
                
                # RAM alert
                ram = psutil.virtual_memory().percent
                if ram >= RAM_ALERT_THRESHOLD and not self._ram_alerted:
                    alert_text = (f"Heads up — RAM is at {int(ram)}%. "
                                  f"Things might start slowing down. Want me to kill some background processes?")
                    await self.bus.emit(clipboard_event(f"[RAM_ALERT]{alert_text}"))
                    self._ram_alerted = True
                elif ram < RAM_ALERT_THRESHOLD - 5:
                    self._ram_alerted = False
                
                # Clipboard
                current_clip = pyperclip.paste()
                if (current_clip != self._last_clipboard and
                        len(current_clip) >= CLIPBOARD_MIN_LENGTH and
                        current_clip.strip()):
                    self._last_clipboard = current_clip
                    await self.bus.emit(clipboard_event(current_clip))
                
            except Exception as e:
                print(Fore.RED + f"   [WATCHDOG] Error: {e}")
            
            await asyncio.sleep(5)
    
    async def start(self):
        """Start monitoring."""
        self.monitor_task = asyncio.create_task(self._monitor_loop())
        print(Fore.GREEN + "   ✅ Async Watchdog Online")
    
    async def stop(self):
        """Stop monitoring gracefully."""
        print(Fore.YELLOW + "   [WATCHDOG] Stopping...")
        self._stop_event.set()
        
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        
        print(Fore.GREEN + "   [WATCHDOG] Stopped")