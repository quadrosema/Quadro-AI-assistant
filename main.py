"""
Async JARVIS — event-driven architecture.
"""

import asyncio
import signal
from colorama import Fore, init

from core.bus import EventBus
from core.events import EventType, shutdown_event
from core.ears import AsyncEars
from core.voice import AsyncVoice
from core.brain import AsyncBrain
from core.watchdog import AsyncWatchdog

init(autoreset=True)

class JarvisAsync:
    def __init__(self):
        # Create event bus
        self.bus = EventBus()
        
        # Create modules
        self.voice = AsyncVoice(self.bus)
        self.ears = AsyncEars(self.bus, voice=self.voice)  # Pass voice reference
        self.brain = AsyncBrain(self.bus)
        self.watchdog = AsyncWatchdog(self.bus)
        
        # Wire watchdog to brain
        self.brain.watchdog = self.watchdog
        
        # Subscribe handlers to events
        self.bus.subscribe(EventType.USER_SPEECH, self.brain.handle_user_speech)
        self.bus.subscribe(EventType.SPEAK, self.voice.handle_speak)
        self.bus.subscribe(EventType.INTERRUPT_SPEECH, self.voice.handle_interrupt)
        self.bus.subscribe(EventType.MODE_CHANGE, self.brain.handle_mode_change)
        
        self.shutdown_event = asyncio.Event()
    
    def handle_signal(self, sig, frame):
        """Handle Ctrl+C gracefully."""
        print(Fore.YELLOW + "\n\n⚠️  Shutdown signal received...")
        self.shutdown_event.set()
    
    async def run(self):
        """Main async run loop."""
        print(Fore.CYAN + "🛡️  INITIALIZING JARVIS PROTOCOLS (ASYNC)...\n")
        
        try:
            # Start event bus
            await self.bus.start()
            
            # Start all modules
            await self.ears.start()
            await self.watchdog.start()
            
            print(Fore.GREEN + "\n🤖 JARVIS ASYNC ONLINE. WAITING FOR EVENTS...\n")
            
            # Wait for shutdown signal
            await self.shutdown_event.wait()
            
        finally:
            # Graceful shutdown
            print(Fore.YELLOW + "\n🛑 SHUTTING DOWN JARVIS...\n")
            
            # Emit shutdown event
            await self.bus.emit(shutdown_event())
            
            # Stop modules in reverse order
            await self.watchdog.stop()
            await self.ears.stop()
            
            # Stop bus last
            await self.bus.stop()
            
            print(Fore.GREEN + "\n✅ JARVIS SHUTDOWN COMPLETE\n")

def main():
    """Entry point."""
    jarvis = JarvisAsync()
    
    # Register signal handler
    signal.signal(signal.SIGINT, jarvis.handle_signal)
    
    # Run async event loop
    try:
        asyncio.run(jarvis.run())
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()