"""ASGI request body size guard."""
from __future__ import annotations
from starlette.types import ASGIApp,Receive,Scope,Send,Message
class BodyTooLarge(Exception): pass
class BodyLimitMiddleware:
    def __init__(self,app:ASGIApp,max_bytes:int): self.app=app; self.max_bytes=max_bytes
    async def __call__(self,scope:Scope,receive:Receive,send:Send):
        if scope.get("type")!="http": return await self.app(scope,receive,send)
        total=0
        async def limited_receive():
            nonlocal total
            message=await receive(); body=message.get("body",b""); total+=len(body)
            if total>self.max_bytes: raise BodyTooLarge()
            return message
        try: await self.app(scope,limited_receive,send)
        except BodyTooLarge:
            await send({"type":"http.response.start","status":413,"headers":[]}); await send({"type":"http.response.body","body":b"request too large"})
