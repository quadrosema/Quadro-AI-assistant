"""
Central event bus for JARVIS.
All modules communicate through this bus via priority-ordered events.
"""

import asyncio
from typing import Callable, Dict, List, Optional, Set
from colorama import Fore
from core.events import Event, EventType, EventPriority

class EventBus:
    """
    Async event bus with priority queue and typed handlers.
    
    Architecture:
    - Modules emit() events to the bus
    - Bus routes events to registered handlers based on event type
    - Events are processed in priority order (user speech > background tasks)
    - Handlers run concurrently but events are dispatched sequentially
    """
    
    def __init__(self):
        self.queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self.handlers: Dict[EventType, List[Callable]] = {}
        self.running = False
        self._worker_task: Optional[asyncio.Task] = None
        self._active_handlers: Set[asyncio.Task] = set()
        
    def subscribe(self, event_type: EventType, handler: Callable):
        """
        Register a handler for a specific event type.
        
        Handler signature: async def handler(event: Event) -> None
        """
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)
        print(Fore.CYAN + f"   [BUS] Subscribed {handler.__name__} to {event_type.name}")
    
    async def emit(self, event: Event):
        """
        Emit an event to the bus.
        Events are queued and processed in priority order.
        """
        await self.queue.put(event)
        # print(Fore.YELLOW + f"   [BUS] Emitted: {event}")
    
    async def _dispatch_worker(self):
        """
        Main worker loop.
        Continuously pulls events from queue and dispatches to handlers.
        """
        print(Fore.GREEN + "   ✅ Event Bus Online")
        
        while self.running:
            try:
                # Get next event (blocks until available)
                event = await asyncio.wait_for(
                    self.queue.get(),
                    timeout=1.0  # Check running flag every second
                )
                
                # Handle shutdown
                if event.event_type == EventType.SHUTDOWN:
                    print(Fore.YELLOW + "   [BUS] Shutdown event received")
                    self.running = False
                    break
                
                # Dispatch to handlers
                await self._dispatch_event(event)
                
            except asyncio.TimeoutError:
                continue  # No events, check running flag and loop
            except Exception as e:
                print(Fore.RED + f"   [BUS] Worker error: {e}")
                import traceback
                traceback.print_exc()
    
    async def _dispatch_event(self, event: Event):
        """
        Route event to all registered handlers for its type.
        Handlers run concurrently but we await all before processing next event.
        """
        handlers = self.handlers.get(event.event_type, [])
        
        if not handlers:
            print(Fore.RED + f"   [BUS] No handlers for {event.event_type.name}")
            return
        
        # Create tasks for all handlers
        tasks = []
        for handler in handlers:
            task = asyncio.create_task(self._safe_handler_call(handler, event))
            tasks.append(task)
            self._active_handlers.add(task)
            task.add_done_callback(self._active_handlers.discard)
        
        # Wait for all handlers to complete before processing next event
        # This ensures speech completes before processing next command
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _safe_handler_call(self, handler: Callable, event: Event):
        """
        Wrap handler call with error handling.
        Handlers shouldn't crash the bus.
        """
        try:
            await handler(event)
        except Exception as e:
            print(Fore.RED + f"   [BUS] Handler {handler.__name__} failed: {e}")
            import traceback
            traceback.print_exc()
    
    async def start(self):
        """Start the event bus worker."""
        if self.running:
            print(Fore.YELLOW + "   [BUS] Already running")
            return
        
        self.running = True
        self._worker_task = asyncio.create_task(self._dispatch_worker())
    
    async def stop(self):
        """
        Graceful shutdown.
        Waits for active handlers to complete, then stops worker.
        """
        print(Fore.YELLOW + "   [BUS] Stopping...")
        
        # Stop accepting new events
        self.running = False
        
        # Wait for active handlers to finish
        if self._active_handlers:
            print(Fore.YELLOW + f"   [BUS] Waiting for {len(self._active_handlers)} active handlers...")
            await asyncio.gather(*self._active_handlers, return_exceptions=True)
        
        # Cancel worker
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        
        print(Fore.GREEN + "   [BUS] Stopped cleanly")