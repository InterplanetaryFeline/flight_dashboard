"""Marks FlightEvents as occurred once sim time passes their scheduled time."""
from __future__ import annotations

from typing import List, Optional

from data_interface import FlightEvent


class EventManager:
    def __init__(self, events: List[FlightEvent]):
        # keep sorted by time; work on our own copies so dataset stays pristine
        self.events = sorted(
            [FlightEvent(e.name, e.t) for e in events], key=lambda e: e.t
        )

    def update(self, t: float) -> Optional[FlightEvent]:
        """Update occurred flags for time t. Returns the most-recently-fired
        event if any newly fired this call, else None."""
        newly_fired = None
        for ev in self.events:
            should_have_occurred = t >= ev.t
            if should_have_occurred and not ev.occurred:
                ev.occurred = True
                newly_fired = ev
            elif not should_have_occurred and ev.occurred:
                ev.occurred = False  # rewinding (e.g. reset/scrub backward)
        return newly_fired

    def reset(self):
        for ev in self.events:
            ev.occurred = False

    def most_recent(self, t: float) -> Optional[FlightEvent]:
        candidates = [e for e in self.events if e.t <= t]
        return candidates[-1] if candidates else None
