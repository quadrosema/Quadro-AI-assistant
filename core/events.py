"""
Event system for JARVIS.
All communication between modules flows through typed events with priorities.
"""

from enum import IntEnum
from dataclasses import dataclass, field
from typing import Any, Optional
import time

class EventPriority(IntEnum):
    """
    Lower number = higher priority.
    Critical events (user speech, interrupts) get processed first.
    """
    CRITICAL = 0      # User speech, safety alerts
    HIGH = 1          # Interrupts, mode changes
    NORMAL = 2        # Screen changes, clipboard
    LOW = 3           # Watchdog alerts, memory writes
    BACKGROUND = 4    # Cleanup, health checks

class EventType(IntEnum):
    """All possible event types in the system."""
    # Input events
    USER_SPEECH = 1
    WAKE_WORD = 2
    
    # Output events
    SPEAK = 10
    INTERRUPT_SPEECH = 11
    
    # System events
    MODE_CHANGE = 20
    SCREEN_CHANGE = 21
    CLIPBOARD = 22
    
    # Watchdog events
    CPU_ALERT = 30
    RAM_ALERT = 31
    APP_DETECTED = 32
    
    # Control events
    SHUTDOWN = 90
    HEALTH_CHECK = 91

@dataclass(order=True)
class Event:
    """
    Base event class. All events flow through the bus as Event instances.
    
    Events are ordered by priority (lower = higher priority), then timestamp.
    This ensures user speech always processes before background tasks.
    """
    # Fields used for ordering (must come first)
    priority: EventPriority = field(compare=True)
    timestamp: float = field(default_factory=time.time, compare=True)
    
    # Fields not used for ordering (must have defaults after ordering fields)
    event_type: EventType = field(default=EventType.USER_SPEECH, compare=False)
    data: Any = field(default=None, compare=False)
    source: Optional[str] = field(default=None, compare=False)
    
    def __repr__(self):
        data_preview = self.data[:50] if isinstance(self.data, str) else self.data
        return f"Event({self.event_type.name}, pri={self.priority.name}, data={data_preview})"

# Event factory functions for clean creation
def user_speech_event(text: str) -> Event:
    return Event(
        priority=EventPriority.CRITICAL,
        event_type=EventType.USER_SPEECH,
        data=text,
        source="ears"
    )

def speak_event(text: str, interruptible: bool = True) -> Event:
    return Event(
        priority=EventPriority.HIGH,
        event_type=EventType.SPEAK,
        data={"text": text, "interruptible": interruptible},
        source="brain"
    )

def interrupt_event() -> Event:
    return Event(
        priority=EventPriority.HIGH,
        event_type=EventType.INTERRUPT_SPEECH,
        data=None,
        source="ears"
    )

def mode_change_event(mode: str) -> Event:
    return Event(
        priority=EventPriority.HIGH,
        event_type=EventType.MODE_CHANGE,
        data=mode,
        source="watchdog"
    )

def clipboard_event(content: str) -> Event:
    return Event(
        priority=EventPriority.NORMAL,
        event_type=EventType.CLIPBOARD,
        data=content,
        source="watchdog"
    )

def cpu_alert_event(usage: int) -> Event:
    return Event(
        priority=EventPriority.LOW,
        event_type=EventType.CPU_ALERT,
        data=usage,
        source="watchdog"
    )

def shutdown_event() -> Event:
    return Event(
        priority=EventPriority.CRITICAL,
        event_type=EventType.SHUTDOWN,
        data=None,
        source="main"
    )