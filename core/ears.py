"""
Async ears with deferred imports to avoid blocking startup.
"""

import asyncio
import time
import sounddevice as sd
import numpy as np
import webrtcvad
import queue
from colorama import Fore
from core.events import user_speech_event, interrupt_event

VOICE_COOLDOWN = 1.5
INTERRUPT_ENERGY_THRESHOLD = 3000

class AsyncEars:
    def __init__(self, bus, voice=None):
        self.bus = bus
        self.voice = voice
        self.sample_rate = 16000
        self.frame_duration_ms = 30
        self.frame_size = int(self.sample_rate * (self.frame_duration_ms / 1000.0))
        
        self.vad = webrtcvad.Vad(2)
        self.audio_queue = queue.Queue()
        self.stream = None
        
        self.model = None
        print(Fore.YELLOW + "   (Whisper will load on first speech detection)")
        
        self.listening = False
        self.listen_task = None
        self.interrupt_task = None
        
        print(Fore.GREEN + "   ✅ Async Ears Online")
    
    def _audio_callback(self, indata, frames, time, status):
        self.audio_queue.put(indata.copy())
    
    def is_arabic(self, text):
        return any('\u0600' <= char <= '\u06FF' for char in text)
    
    def filter_hallucinations(self, text):
        if not text:
            return None
        
        text_lower = text.lower().strip()
        hallucinations = [
            "thank you", "thanks", "thank you.", "thank you very much",
            "okay", "ok", "yeah", "yes", "mm-hmm", "uh-huh",
            "you", "bye", "goodbye", "please"
        ]
        
        if text_lower in hallucinations:
            print(Fore.RED + "   [FIREWALL] Hallucination filtered.")
            return None
        
        words = text_lower.split()
        if len(words) <= 3:
            hallucination_count = sum(1 for w in words if w in hallucinations)
            if hallucination_count >= len(words) - 1:
                print(Fore.RED + "   [FIREWALL] Hallucination filtered.")
                return None
        
        return text
    
    async def _ensure_model_loaded(self):
        if self.model is not None:
            return
        
        print(Fore.YELLOW + "   (Loading Whisper large-v3-turbo on CUDA...)")
        loop = asyncio.get_event_loop()
        self.model = await loop.run_in_executor(None, self._load_model)
        print(Fore.GREEN + "   ✅ Whisper Loaded")
    
    def _load_model(self):
        # Import here to avoid blocking startup
        from faster_whisper import WhisperModel
        
        return WhisperModel(
            "large-v3-turbo",
            device="cuda",
            compute_type="float16",
            local_files_only=True
        )
    
    async def _interrupt_monitor(self):
        while self.listening:
            try:
                if not self.voice or not self.voice.speaking:
                    await asyncio.sleep(0.1)
                    continue
                
                loop = asyncio.get_event_loop()
                try:
                    frame = await loop.run_in_executor(None, self.audio_queue.get, False)
                except queue.Empty:
                    await asyncio.sleep(0.01)
                    continue
                
                rms = np.sqrt(np.mean(frame.astype(np.float32) ** 2))
                
                if rms > INTERRUPT_ENERGY_THRESHOLD:
                    print(Fore.YELLOW + f"   [INTERRUPT] Energy={int(rms)}")
                    await self.bus.emit(interrupt_event())
                    await asyncio.sleep(0.5)
                
                await asyncio.sleep(0.01)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(Fore.RED + f"   [INTERRUPT MONITOR] Error: {e}")
                await asyncio.sleep(0.1)
    
    async def _listen_once(self):
        if self.voice and self.voice.speaking:
            await asyncio.sleep(0.1)
            return
        
        print(Fore.CYAN + "👂 LISTENING...")
        
        audio_data = []
        silent_frames = 0
        recording = False
        pre_speech_frames = []
        idle_frames = 0
        MAX_IDLE_FRAMES = 200
        
        loop = asyncio.get_event_loop()
        
        while True:
            if self.voice and self.voice.speaking:
                print(Fore.YELLOW + "   [EARS] Voice speaking, discarding audio")
                return
            
            try:
                frame = await loop.run_in_executor(None, self.audio_queue.get, True, 0.1)
            except queue.Empty:
                await asyncio.sleep(0.01)
                continue
            
            is_speech = self.vad.is_speech(frame.tobytes(), self.sample_rate)
            
            if is_speech:
                if not recording:
                    audio_data.extend(pre_speech_frames[-10:])
                recording = True
                audio_data.append(frame)
                silent_frames = 0
                idle_frames = 0
            
            elif recording:
                audio_data.append(frame)
                silent_frames += 1
                if silent_frames > 33:
                    break
            
            else:
                pre_speech_frames.append(frame)
                idle_frames += 1
                if idle_frames > MAX_IDLE_FRAMES:
                    return
        
        if not audio_data:
            return
        
        if self.voice and self.voice.speaking:
            print(Fore.YELLOW + "   [EARS] Voice started during recording, discarding")
            return
        
        await self._ensure_model_loaded()
        
        audio_np = np.concatenate(audio_data).flatten().astype(np.float32) / 32768.0
        segments, _ = await loop.run_in_executor(
            None,
            self.model.transcribe,
            audio_np,
            "en"
        )
        text = " ".join([seg.text.strip() for seg in segments]).strip()
        
        text = self.filter_hallucinations(text)
        if not text:
            return
        
        if self.is_arabic(text):
            print(Fore.RED + "   [FIREWALL] Arabic detected. Ignored.")
            return
        
        if self.voice and (time.time() - self.voice.last_spoke_at) < VOICE_COOLDOWN:
            print(Fore.YELLOW + f"   [EARS] Voice cooldown active ({VOICE_COOLDOWN}s), discarding")
            return
        
        print(Fore.GREEN + f"YOU >> {text}")
        await self.bus.emit(user_speech_event(text))
    
    async def _listen_loop(self):
        while self.listening:
            try:
                await self._listen_once()
            except asyncio.CancelledError:
                print(Fore.YELLOW + "   [EARS] Listen loop cancelled")
                break
            except Exception as e:
                print(Fore.RED + f"   [EARS] Error: {e}")
                import traceback
                traceback.print_exc()
                await asyncio.sleep(1)
    
    async def start(self):
        if self.listening:
            return
        
        self.listening = True
        
        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype='int16',
            blocksize=self.frame_size,
            callback=self._audio_callback
        )
        self.stream.start()
        
        self.listen_task = asyncio.create_task(self._listen_loop())
        self.interrupt_task = asyncio.create_task(self._interrupt_monitor())
    
    async def stop(self):
        print(Fore.YELLOW + "   [EARS] Stopping...")
        
        self.listening = False
        
        if self.listen_task:
            self.listen_task.cancel()
            try:
                await self.listen_task
            except asyncio.CancelledError:
                pass
        
        if self.interrupt_task:
            self.interrupt_task.cancel()
            try:
                await self.interrupt_task
            except asyncio.CancelledError:
                pass
        
        if self.stream:
            self.stream.stop()
            self.stream.close()
        
        print(Fore.GREEN + "   [EARS] Stopped")