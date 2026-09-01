# Quadro — Real-Time Multimodal AI Assistant

Quadro is an in-progress personal AI assistant built around an event-driven architecture.

The system integrates voice input, screen understanding, memory, and desktop automation into a modular local pipeline. The focus of this project is system design, real-time interaction, and integration of multiple AI components — not UI polish or production deployment.

---

## Overview

JARVIS is structured as a set of independent modules that communicate through a central event bus.

Instead of direct function calls between components, the system uses asynchronous events to coordinate behavior, allowing real-time interaction without blocking execution.

This design enables:
- modular development
- easier debugging
- real-time responsiveness
- separation of concerns across subsystems

---

## Architecture

Core components:

- **Event Bus**  
  Central async message system that routes events between all modules

- **Brain**  
  Decision-making layer that combines LLM reasoning with skill execution

- **Ears**  
  Real-time speech recognition using Whisper and VAD (voice activity detection)

- **Voice**  
  Text-to-speech output with streaming playback and interrupt handling

- **Eyes**  
  Screen capture and analysis using vision models for context-aware responses

- **Memory**  
  Persistent memory using SQLite and embedding-based semantic retrieval

- **Watchdog**  
  System monitoring (CPU, RAM, processes, clipboard) and automatic mode switching

---

## Capabilities

Currently implemented features:

- voice-based interaction (real-time, interruptible)
- system control (volume, processes, power actions)
- per-application audio control
- browser automation (Google, YouTube, GitHub, Reddit, StackOverflow)
- Spotify integration (playback, search, queue, shuffle, repeat)
- screen understanding via AI vision
- clipboard monitoring and response triggering
- long-term memory with semantic search
- automatic mode switching (work / gaming / idle)
- gaming utilities (clip capture, background process cleanup)

---

## Tech Stack

- Python (asyncio, event-driven design)
- OpenAI API (LLM, TTS, Vision)
- Faster-Whisper (speech recognition)
- PyTorch (GPU acceleration)
- OpenCV + screen capture
- SQLite + ChromaDB (memory system)
- sounddevice (real-time audio streaming)
- psutil (system monitoring)

---

## Project Structure

```text
jarvis-ai-assistant/
├─ config/
├─ core/
├─ skills/
├─ utils/
├─ main.py
├─ requirements.txt
├─ README.md
├─ .gitignore
