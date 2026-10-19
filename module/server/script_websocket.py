# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
from typing import Iterable
import asyncio

from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState


class ScriptWSManager:
    send_timeout = 2.0
    close_timeout = 0.5

    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self._connection_owners = {}

    async def _on_owner(self, ws, operation):
        owner = self._connection_owners.get(ws)
        if owner is None:
            owner = (asyncio.get_running_loop(), asyncio.Lock())
            self._connection_owners[ws] = owner
        loop, lock = owner

        async def run():
            async with lock:
                return await operation()

        if loop is asyncio.get_running_loop():
            return await asyncio.wait_for(run(), timeout=self.send_timeout)
        # Push workers use a background event loop. ASGI sends and their locks
        # must execute on the HTTP loop that accepted this connection.
        if loop.is_closed():
            raise RuntimeError('WebSocket owner loop has closed')
        operation_coro = run()
        try:
            future = asyncio.run_coroutine_threadsafe(operation_coro, loop)
        except RuntimeError:
            operation_coro.close()
            raise
        return await asyncio.wait_for(asyncio.wrap_future(future), timeout=self.send_timeout)

    async def connect(self, ws: WebSocket):
        # 等待连接
        await ws.accept()
        self._connection_owners[ws] = (asyncio.get_running_loop(), asyncio.Lock())
        if ws not in self.active_connections:
            self.active_connections.append(ws)

    async def disconnect(self, ws: WebSocket):
        # 关闭时移除 ws 对象，重复调用也应安全
        if ws in self.active_connections:
            self.active_connections.remove(ws)
        try:
            if ws.client_state != WebSocketState.DISCONNECTED:
                async def close():
                    await asyncio.wait_for(ws.close(), timeout=self.close_timeout)
                await self._on_owner(ws, close)
        except Exception:
            pass
        finally:
            self._connection_owners.pop(ws, None)

    async def send_text(self, ws: WebSocket, message: str) -> bool:
        return await self._send(ws, ws.send_text, message)

    async def send_json(self, ws: WebSocket, data: dict) -> bool:
        return await self._send(ws, ws.send_json, data)

    async def broadcast(self, message: str):
        # 广播消息
        await self._broadcast(self.active_connections, lambda connection: connection.send_text(message))

    async def broadcast_state(self, data: dict):
        # 广播自身的状态
        await self._broadcast(self.active_connections, lambda connection: connection.send_json(data))

    async def broadcast_log(self, log: str):
        # 广播日志
        await self._broadcast(self.active_connections, lambda connection: connection.send_text(log))

    async def _send(self, ws: WebSocket, sender, payload) -> bool:
        if ws.client_state == WebSocketState.DISCONNECTED:
            await self.disconnect(ws)
            return False
        try:
            await self._on_owner(ws, lambda: sender(payload))
            return True
        except (RuntimeError, WebSocketDisconnect):
            await self.disconnect(ws)
            return False
        except Exception:
            await self.disconnect(ws)
            return False

    async def _broadcast(self, connections: Iterable[WebSocket], sender_factory) -> None:
        await asyncio.gather(*(self._send(connection, sender_factory, connection)
                               for connection in list(connections)))




