"""Bounded in-process fan-out for localhost run events."""
from __future__ import annotations
import asyncio
import json
from typing import Any
from app.core.config import CAPS
class EventBroker:
    def __init__(self, *, max_queue:int=256):
        if not 1<=max_queue<=4096: raise ValueError("invalid broker queue limit")
        self.max_queue=max_queue; self._subscribers:set[asyncio.Queue[dict[str,Any]]]=set()
    def subscribe(self)->asyncio.Queue[dict[str,Any]]:
        queue:asyncio.Queue[dict[str,Any]]=asyncio.Queue(maxsize=self.max_queue)
        try: setattr(queue,"_broker_loop",asyncio.get_running_loop())
        except RuntimeError: setattr(queue,"_broker_loop",None)
        self._subscribers.add(queue); return queue
    def unsubscribe(self,queue:asyncio.Queue[dict[str,Any]])->None: self._subscribers.discard(queue)
    def close(self)->None:
        for queue in tuple(self._subscribers):
            self.unsubscribe(queue)
            try: queue.put_nowait({"type":"broker.closed"})
            except asyncio.QueueFull: pass
    def publish(self,event:dict[str,Any])->None:
        if not isinstance(event,dict) or not isinstance(event.get("type"),str): raise ValueError("invalid event")
        if len(json.dumps(event,ensure_ascii=False,separators=(",",":")).encode())>CAPS.max_event_bytes: raise ValueError("event too large")
        for queue in tuple(self._subscribers):
            def deliver(target=queue):
                if target.full():
                    try: target.get_nowait()
                    except asyncio.QueueEmpty: pass
                try: target.put_nowait(dict(event))
                except asyncio.QueueFull: pass
            loop=getattr(queue,"_broker_loop",None)
            try: current_loop=asyncio.get_running_loop()
            except RuntimeError: current_loop=None
            if loop is not None and loop is not current_loop: loop.call_soon_threadsafe(deliver)
            else: deliver()
