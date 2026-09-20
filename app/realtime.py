from __future__ import annotations

from collections import defaultdict

from fastapi import WebSocket


class RealtimeHub:
    def __init__(self) -> None:
        self._guest_connections: dict[int, list[WebSocket]] = defaultdict(list)
        self._kitchen_connections: list[WebSocket] = []
        self._reception_connections: list[WebSocket] = []

    async def connect_guest(self, room_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self._guest_connections[room_id].append(websocket)

    async def connect_kitchen(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._kitchen_connections.append(websocket)

    async def connect_reception(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._reception_connections.append(websocket)

    def disconnect_guest(self, room_id: int, websocket: WebSocket) -> None:
        self._remove(self._guest_connections.get(room_id, []), websocket)
        if not self._guest_connections.get(room_id):
            self._guest_connections.pop(room_id, None)

    def disconnect_kitchen(self, websocket: WebSocket) -> None:
        self._remove(self._kitchen_connections, websocket)

    def disconnect_reception(self, websocket: WebSocket) -> None:
        self._remove(self._reception_connections, websocket)

    async def notify_guest(self, room_id: int, event: dict[str, object]) -> None:
        await self._broadcast(self._guest_connections.get(room_id, []), event)

    async def notify_kitchen(self, event: dict[str, object]) -> None:
        await self._broadcast(self._kitchen_connections, event)

    async def notify_reception(self, event: dict[str, object]) -> None:
        await self._broadcast(self._reception_connections, event)

    @staticmethod
    def _remove(connections: list[WebSocket], websocket: WebSocket) -> None:
        if websocket in connections:
            connections.remove(websocket)

    async def _broadcast(
        self, connections: list[WebSocket], event: dict[str, object]
    ) -> None:
        stale: list[WebSocket] = []
        for websocket in list(connections):
            try:
                await websocket.send_json(event)
            except RuntimeError:
                stale.append(websocket)
        for websocket in stale:
            self._remove(connections, websocket)


realtime_hub = RealtimeHub()
