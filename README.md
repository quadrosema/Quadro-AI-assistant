# JARVIS — Real-Time Multimodal AI Assistant

A fully event-driven AI assistant that integrates voice, vision, memory, and system-level automation into a single real-time architecture.

## What makes this different

This is not a chatbot.

JARVIS is designed as a modular AI system with components similar to an operating system:
- event-driven communication through a central event bus
- asynchronous real-time processing
- multimodal input using speech and vision
- persistent memory with semantic retrieval
- direct system-level automation

## Architecture

Core components:
- Event Bus — central async message system coordinating all modules
- Brain — reasoning engine combining LLM calls with skill routing
- Ears — real-time speech recognition using Whisper + VAD
- Voice — streaming text-to-speech with interrupt handling
- Eyes — screen understanding using GPT-4o vision
- Memory — long-term memory using SQLite and embedding-based retrieval
- Watchdog — system monitoring and automatic mode switching

## Capabilities

- voice-controlled system automation
- app and master volume control
- process management and power actions
- Spotify control
- browser automation
- real-time screen analysis
- clipboard monitoring and summarization
- long-term semantic memory
- personality modes such as work, gaming, and idle

## Tech Stack

- Python
- asyncio
- OpenAI API
- Faster-Whisper
- PyTorch
- OpenCV
- SQLite
- ChromaDB
- sounddevice

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