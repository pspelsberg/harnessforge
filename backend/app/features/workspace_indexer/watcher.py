"""Bounded change queue with deterministic debounce."""
from __future__ import annotations
from collections import deque
from time import monotonic
class ChangeQueue:
 def __init__(self,max_items:int=256,debounce_seconds:float=0.25):self.max_items=max_items;self.debounce_seconds=debounce_seconds;self._items=deque(maxlen=max_items);self._last=0.0
 def enqueue(self,path:str)->bool:
  if not path or path in self._items:return False
  if len(self._items)>=self.max_items:return False
  self._items.append(path);self._last=monotonic();return True
 def drain(self)->list[str]:
  if self._items and monotonic()-self._last<self.debounce_seconds:return []
  result=list(self._items);self._items.clear();return result
