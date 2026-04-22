"""
Async brain — processes USER_SPEECH events and emits SPEAK responses.
Runs skills in executor to avoid blocking the event loop.
"""

import asyncio
import openai
import os
import re
from dotenv import load_dotenv
from colorama import Fore

from skills.system import SystemSkills
from skills.gaming import GamingSkills
from skills.academic import AcademicSkills
from skills.browser import BrowserSkills
from skills.spotify import SpotifySkills
from core.memory import Memory
from core.eyes import Eyes
from core.events import Event, EventType, speak_event, mode_change_event
from config.settings import PERSONALITY_MODES

load_dotenv()

AUTO_REMEMBER_PATTERNS = [
    r"my name is (.+)",
    r"i(?:'m| am) (.+)",
    r"i (?:like|love|hate|prefer|enjoy|use|play|study|work (?:at|on|with)) (.+)",
    r"my (?:favorite|favourite) (.+?) is (.+)",
    r"i(?:'ve| have) (?:a|an) (.+)",
    r"call me (.+)",
]

def is_command_not_fact(text):
    text_lower = text.lower()
    command_words = ["please", "can you", "could you", "jarvis", "tell you",
                     "want you", "need you", "asking you", "telling you"]
    profanity = ["fuck", "shit", "damn", "wtf", "dammit"]
    return any(word in text_lower for word in command_words + profanity)

def extract_auto_fact(text):
    if is_command_not_fact(text):
        return None
    text_lower = text.lower().strip()
    for pattern in AUTO_REMEMBER_PATTERNS:
        if re.search(pattern, text_lower):
            return text.strip()
    return None

class AsyncBrain:
    def __init__(self, bus):
        self.bus = bus
        self.cloud = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Skills (synchronous, will run in executor)
        self.system = SystemSkills()
        self.gaming = GamingSkills()
        self.academic = AcademicSkills()
        self.browser = BrowserSkills()
        self.spotify = SpotifySkills()
        self.memory = Memory()
        self.eyes = Eyes()
        
        self.conversation_history = []
        self.mode = "idle"
        self.watchdog = None
        
        print(Fore.GREEN + "   ✅ Async Brain Online")
    
    def set_mode(self, mode):
        if mode in PERSONALITY_MODES and mode != self.mode:
            self.mode = mode
            print(Fore.MAGENTA + f"   [BRAIN] Personality → {mode.upper()}")
    
    def _system_prompt(self):
        return PERSONALITY_MODES[self.mode]
    
    async def handle_user_speech(self, event: Event):
        """
        Main handler for USER_SPEECH events.
        Processes the text and emits SPEAK response.
        """
        text = event.data
        print(Fore.YELLOW + "🧠 Thinking...")
        
        # Get response (blocking GPT call, run in executor)
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, self.think, text)
        
        if response:
            # Emit speak event
            await self.bus.emit(speak_event(response))
    
    async def handle_mode_change(self, event: Event):
        """Handle MODE_CHANGE events from watchdog."""
        mode = event.data
        self.set_mode(mode)
    
    def think(self, text):
        """
        Synchronous think method (runs in executor).
        This is the existing logic, unchanged.
        """
        text_lower = text.lower().strip()
        
        # Mode switching
        verbal_modes = {
            "gaming": ["gaming mode", "game mode", "switch to gaming", "activate gaming", "gaming mood", "gamer mode"],
            "work":   ["work mode", "focus mode", "switch to work", "activate work", "work mood", "working mode", "study mode"],
            "idle":   ["idle mode", "chill mode", "relax mode", "go idle", "stand by", "standby mode",
                       "idle mood", "chill mood", "relaxed mode", "standard mode", "normal mode",
                       "default mode", "regular mode", "casual mode", "free mode", "off duty"],
        }
        for mode, triggers in verbal_modes.items():
            if any(t in text_lower for t in triggers):
                self.mode = mode
                if self.watchdog:
                    self.watchdog.set_mode_manually(mode)
                return {"gaming": "Gaming mode activated. Let's get it.",
                        "work":   "Work mode. I'll keep it sharp and focused.",
                        "idle":   "Idle mode. Taking it easy."}[mode]
        
        # Session & memory
        if any(p in text_lower for p in ["forget this session", "clear session", "new session"]):
            self.conversation_history = []
            return "Session memory cleared, sir. Fresh start."
        
        if any(p in text_lower for p in ["forget everything", "wipe memory", "clear all memory"]):
            self.conversation_history = []
            return self.memory.wipe_facts()
        
        # Remember
        if "remember" in text_lower:
            fact = re.sub(r'\bremember\b', '', text_lower).replace("that", "").strip()
            if fact:
                result = self.memory.save_fact(fact)
                print(Fore.CYAN + f"   [MEMORY] Saved: {fact}")
                return result
        
        # Eyes
        eye_triggers = ["look", "what's on my screen", "read this", "what do you see",
                        "check my screen", "analyze my screen", "what's this"]
        if any(t in text_lower for t in eye_triggers):
            return self.eyes.look(question=text)
        
        # Clipboard (will come from watchdog event, not direct text)
        if text_lower.startswith("[clipboard]"):
            content = text[len("[clipboard]"):].strip()
            return self.call_cloud(
                f"The user just copied this to their clipboard. Give a brief, useful reaction — "
                f"summarize it, spot issues, or offer to act on it. Content:\n\n{content}"
            )
        
        # Reflexes
        result = self.execute_reflex(text_lower)
        if result:
            return result
        
        # Auto-remember
        auto_fact = extract_auto_fact(text)
        if auto_fact:
            self.memory.save_fact(auto_fact)
            print(Fore.CYAN + f"   [MEMORY] Auto-saved: {auto_fact}")
        
        # Cloud
        return self.call_cloud(text)
    
    def execute_reflex(self, text):
        """Synchronous reflex execution (unchanged from original)."""
        # [Previous reflex code — too long to include in chat, but it's the same]
        # Just copying the Spotify section as example:
        
        if "spotify" in text and any(p in text for p in ["play", "pause", "resume"]):
            return self.spotify.play_pause()
        
        # ... rest of reflexes
        
        return None
    
    def call_cloud(self, text):
        """Synchronous GPT-4o call (runs in executor)."""
        try:
            past_facts = self.memory.get_relevant_facts(text)
            system_content = self._system_prompt()
            if past_facts:
                system_content += f"\n\nFacts you remember about the user:\n{past_facts}"
            
            self.conversation_history.append({"role": "user", "content": text})
            messages = [{"role": "system", "content": system_content}] + self.conversation_history
            
            response = self.cloud.chat.completions.create(
                model="gpt-4o",
                messages=messages
            )
            
            reply = response.choices[0].message.content
            self.conversation_history.append({"role": "assistant", "content": reply})
            
            if len(self.conversation_history) > 40:
                self.conversation_history = self.conversation_history[-40:]
            
            return reply
            
        except Exception as e:
            return f"Cloud connection lost. Error: {e}"

    def execute_reflex(self, text):
        """Full reflex routing (synchronous, runs in executor)."""
        
        # ── SPOTIFY ───────────────────────────────────────────────────────────
        if "spotify" in text and any(p in text for p in ["play", "pause", "resume"]):
            return self.spotify.play_pause()
        
        if "spotify" in text and ("skip" in text or "next" in text):
            return self.spotify.next_track()
        
        if "spotify" in text and ("previous" in text or "back" in text):
            return self.spotify.previous_track()
        
        if "spotify" in text and "volume" in text:
            numbers = re.findall(r'\d+', text)
            level = int(numbers[0]) if numbers else 50
            return self.spotify.set_volume(level)
        
        if "what's playing" in text or "what song is this" in text or "current song" in text:
            return self.spotify.current_track()
        
        if "shuffle on" in text or "turn on shuffle" in text:
            return self.spotify.shuffle(True)
        
        if "shuffle off" in text or "turn off shuffle" in text:
            return self.spotify.shuffle(False)
        
        if "repeat on" in text:
            return self.spotify.repeat("context")
        
        if "repeat off" in text:
            return self.spotify.repeat("off")
        
        if any(p in text for p in ["play song", "play track"]):
            query = re.sub(r'.*(play song|play track|on spotify)\s*', '', text).strip()
            return self.spotify.play_song(query)
        
        if "play artist" in text:
            query = re.sub(r'.*(play artist|on spotify)\s*', '', text).strip()
            return self.spotify.play_artist(query)
        
        if "play album" in text:
            query = re.sub(r'.*(play album|on spotify)\s*', '', text).strip()
            return self.spotify.play_album(query)
        
        if "play playlist" in text or ("play my" in text and "playlist" in text):
            if "play my" in text and "playlist" in text:
                query = text.replace("play my", "").replace("playlist", "").replace("on spotify", "").strip()
            elif "play playlist" in text:
                query = text.split("play playlist")[-1].replace("on spotify", "").strip()
            else:
                query = ""
            if not query:
                return "Which playlist? I need a name."
            return self.spotify.play_playlist(query)
        
        if "play my liked songs" in text or "play liked songs" in text or "play my library" in text:
            return self.spotify.play_liked_songs()
        
        if "add to queue" in text or "queue this" in text:
            query = re.sub(r'.*(add to queue|queue this|queue)\s*', '', text).strip()
            return self.spotify.add_to_queue(query)
        
        # ── VOLUME ────────────────────────────────────────────────────────────
        if "volume" in text or ("mute" in text and "unmute" not in text):
            apps = ["spotify", "discord", "chrome", "valorant"]
            target_app = next((app for app in apps if app in text), None)
            numbers = re.findall(r'\d+', text)
            level = int(numbers[0]) if numbers else (0 if "mute" in text else 50)
            if target_app:
                return self.system.set_app_volume(target_app, level)
            return self.system.set_master_volume(level)
        
        if "unmute" in text:
            return self.system.unmute_master()
        
        if "what" in text and "volume" in text:
            return self.system.get_volume()
        
        # ── MEDIA CONTROLS ────────────────────────────────────────────────────
        if any(p in text for p in ["play", "pause", "resume", "unpause", "start music",
                                   "play music", "resume music", "toggle music", "play pause"]):
            return self.system.media_play_pause()
        
        if any(p in text for p in ["next track", "next song", "skip song", "skip track", "skip", "next"]):
            return self.system.media_next()
        
        if any(p in text for p in ["previous track", "previous song", "last song", "previous", "back"]):
            return self.system.media_previous()
        
        if "stop music" in text or "stop media" in text:
            return self.system.media_stop()
        
        # ── BROWSER / SEARCH ──────────────────────────────────────────────────
        if "youtube" in text:
            query = re.sub(r'.*(youtube|search|find|look up|play|on youtube)\s*', '', text).strip()
            if query:
                return self.browser.search_youtube(query)
        
        if any(p in text for p in ["stackoverflow", "stack overflow", "stackflow"]):
            query = re.sub(r'.*(stackoverflow|stack overflow|stackflow|search)\s*', '', text).strip()
            if query:
                return self.browser.search_stackoverflow(query)
        
        if "reddit" in text and "search" in text:
            query = re.sub(r'.*(reddit|search)\s*', '', text).strip()
            return self.browser.search_reddit(query)
        
        if "github" in text and "search" in text:
            query = re.sub(r'.*(github|search)\s*', '', text).strip()
            return self.browser.search_github(query)
        
        if any(p in text for p in ["search for", "look up", "google", "search online", "search the web"]):
            for trigger in ["search for", "look up", "google", "search online", "search the web"]:
                if trigger in text:
                    query = text.split(trigger, 1)[-1].strip()
                    if query:
                        return self.browser.search_web(query)
        
        if "open" in text and any(p in text for p in [".com", ".org", ".net", ".io", "website", "site", "http"]):
            url = re.sub(r'.*(open|go to|visit)\s*', '', text).strip()
            return self.browser.open_url(url)
        
        # ── APPS & PROCESSES ──────────────────────────────────────────────────
        if "open" in text and not any(p in text for p in [".com", ".org", "http", "website"]):
            app = re.sub(r'.*open\s*', '', text).strip()
            return self.system.open_app(app)
        
        if any(word in text for word in ["kill", "close", "terminate"]):
            app = re.sub(r'.*(kill|close|terminate)\s*', '', text).strip()
            return self.system.kill_process(app)
        
        if "lag" in text or "ping" in text or "lag killer" in text:
            return self.system.lag_killer()
        
        # ── POWER ─────────────────────────────────────────────────────────────
        if "sleep" in text and ("pc" in text or "computer" in text):
            return self.system.sleep_pc()
        
        if "lock" in text and ("pc" in text or "screen" in text or "computer" in text):
            return self.system.lock_pc()
        
        if "shutdown" in text or "shut down" in text:
            numbers = re.findall(r'\d+', text)
            delay = int(numbers[0]) if numbers else 60
            return self.system.shutdown(delay)
        
        if "cancel shutdown" in text:
            return self.system.cancel_shutdown()
        
        if "restart" in text or "reboot" in text:
            return self.system.restart()
        
        if "hibernate" in text:
            return self.system.hibernate()
        
        # ── NETWORK ───────────────────────────────────────────────────────────
        if "flush dns" in text or "clear dns" in text:
            return self.system.flush_dns()
        
        if "my ip" in text or "ip address" in text:
            return self.system.get_ip()
        
        if "wifi off" in text or "turn off wifi" in text or "disable wifi" in text:
            return self.system.wifi_off()
        
        if "wifi on" in text or "turn on wifi" in text or "enable wifi" in text:
            return self.system.wifi_on()
        
        # ── GAMING ────────────────────────────────────────────────────────────
        if "clip" in text or "save that" in text:
            return self.gaming.clip_that()
        
        if "open steam" in text:
            return self.system.open_steam()
        
        # ── ACADEMIC ──────────────────────────────────────────────────────────
        if "project" in text or "janitor" in text:
            project_name = text.split("named")[-1].strip() if "named" in text else "New_Project"
            return self.academic.code_janitor(project_name)
        
        return None