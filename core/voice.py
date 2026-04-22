"""
Async voice with OpenAI TTS and HARD interrupt stop.
- Uses a controlled sounddevice.OutputStream (not sd.play).
- Interrupt sets an event AND stops the active stream immediately.
"""

import asyncio
import io
import re
import os
import time
import sounddevice as sd
import numpy as np
import soundfile as sf
import openai
from dotenv import load_dotenv
from colorama import Fore
from core.events import Event

load_dotenv()

VOICE = "onyx"
SPEED_MAP = {
    "calm":    1.0,
    "focused": 1.05,
    "urgent":  1.15,
    "gaming":  1.1,
    "curious": 0.95,
}
DEFAULT_EMOTION = "calm"


def clean_for_speech(text: str) -> str:
    text = re.sub(r"\*+([^*]+)\*+", r"\1", text)
    text = re.sub(r"#+\s+", "", text)
    text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*[-•]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"`+([^`]+)`+", r"\1", text)
    text = re.sub(r"`+", "", text)
    text = re.sub(r"\n{2,}", ". ", text)
    text = re.sub(r"\n", ", ", text)
    text = re.sub(r"  +", " ", text).strip()
    return text


class AsyncVoice:
    def __init__(self, bus):
        self.bus = bus
        self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        self.interrupted = asyncio.Event()
        self.speaking = False
        self.last_spoke_at = 0
        self._current_emotion = DEFAULT_EMOTION

        # Playback control
        self._stream = None
        self._play_lock = asyncio.Lock()

        if not os.getenv("OPENAI_API_KEY"):
            print(Fore.RED + "   ❌ OPENAI_API_KEY not found in .env")
        else:
            print(Fore.GREEN + f"   ✅ Voice (OpenAI TTS — {VOICE}) Online")

    def set_emotion(self, emotion: str):
        self._current_emotion = emotion if emotion in SPEED_MAP else DEFAULT_EMOTION

    async def handle_speak(self, event: Event):
        data = event.data
        if isinstance(data, dict):
            text = data.get("text", "")
            emotion = data.get("emotion", None)
        else:
            text = str(data)
            emotion = None

        if not text:
            return

        active_emotion = emotion if emotion else self._current_emotion
        clean_text = clean_for_speech(text)
        print(Fore.CYAN + f"🗣️ JARVIS [{active_emotion}]: {text}")

        async with self._play_lock:
            self.interrupted.clear()
            self.speaking = True

            try:
                loop = asyncio.get_event_loop()
                audio_np, sample_rate = await loop.run_in_executor(
                    None, self._synthesize, clean_text, active_emotion
                )

                # Ensure 1-D float32
                if audio_np.ndim > 1:
                    audio_np = audio_np.mean(axis=1)
                audio_np = audio_np.astype(np.float32)

                # Stream playback in chunks so interrupt is instant
                block = 1024
                idx = 0

                def callback(outdata, frames, time_info, status):
                    nonlocal idx
                    if self.interrupted.is_set():
                        outdata[:] = 0
                        raise sd.CallbackStop()

                    end = idx + frames
                    chunk = audio_np[idx:end]

                    if len(chunk) < frames:
                        outdata[:len(chunk), 0] = chunk
                        outdata[len(chunk):, 0] = 0
                        idx = end
                        raise sd.CallbackStop()

                    outdata[:, 0] = chunk
                    idx = end

                self._stream = sd.OutputStream(
                    samplerate=sample_rate,
                    channels=1,
                    dtype="float32",
                    callback=callback,
                    blocksize=block
                )

                self._stream.start()

                # Wait until finished or interrupted
                while self._stream.active:
                    if self.interrupted.is_set():
                        break
                    await asyncio.sleep(0.02)

            except sd.CallbackStop:
                pass
            except Exception as e:
                print(Fore.RED + f"❌ Speech Error: {e}")
            finally:
                try:
                    if self._stream:
                        self._stream.stop()
                        self._stream.close()
                except Exception:
                    pass
                self._stream = None
                self.speaking = False
                self.last_spoke_at = time.time()

    def _synthesize(self, text, emotion):
        speed = SPEED_MAP.get(emotion, 1.0)
        response = self.client.audio.speech.create(
            model="tts-1",
            voice=VOICE,
            input=text,
            speed=speed,
            response_format="wav"
        )
        audio_bytes = io.BytesIO(response.content)
        audio_np, sample_rate = sf.read(audio_bytes, dtype="float32")
        return audio_np, sample_rate

    async def handle_interrupt(self, event: Event):
        # HARD stop: set flag + stop active output stream immediately
        if self.speaking:
            print(Fore.YELLOW + "   [VOICE] Interrupt received -> STOPPING")
            self.interrupted.set()
            try:
                if self._stream:
                    self._stream.abort()
                    self._stream.close()
            except Exception:
                pass
            self._stream = None