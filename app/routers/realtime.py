from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.repositories import DeviceRepository, UserRepository
from app.services import AuthenticationService, DeviceAuthenticationError, DeviceService
from app.realtime import realtime_hub


router = APIRouter(tags=["realtime"])


def _origin_is_allowed(websocket: WebSocket) -> bool:
    origin = websocket.headers.get("origin")
    if not origin:
        return True
    expected_http = f"http://{websocket.headers.get('host', '')}"
    expected_https = f"https://{websocket.headers.get('host', '')}"
    return origin.rstrip("/") in {expected_http, expected_https}


@router.websocket("/guest/ws")
async def guest_socket(websocket: WebSocket) -> None:
    if not _origin_is_allowed(websocket):
        await websocket.close(code=4403)
        return
    credential = websocket.cookies.get("hospitalitysync_device")
    session_factory = websocket.app.state.session_factory
    with session_factory() as session:
        try:
            device = DeviceService(DeviceRepository(session)).authenticate(credential)
        except DeviceAuthenticationError:
            await websocket.close(code=4401)
            return
        room_id = device.room_id
    await realtime_hub.connect_guest(room_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        realtime_hub.disconnect_guest(room_id, websocket)


@router.websocket("/kitchen/ws")
async def kitchen_socket(websocket: WebSocket) -> None:
    if not _origin_is_allowed(websocket):
        await websocket.close(code=4403)
        return
    user_id = websocket.session.get("user_id")
    session_factory = websocket.app.state.session_factory
    with session_factory() as session:
        user = AuthenticationService(UserRepository(session)).get_authenticated_kitchen_user(user_id) if isinstance(user_id, int) else None
    if user is None:
        await websocket.close(code=4403)
        return
    await realtime_hub.connect_kitchen(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        realtime_hub.disconnect_kitchen(websocket)


@router.websocket("/reception/ws")
async def reception_socket(websocket: WebSocket) -> None:
    if not _origin_is_allowed(websocket):
        await websocket.close(code=4403)
        return
    user_id = websocket.session.get("user_id")
    session_factory = websocket.app.state.session_factory
    with session_factory() as session:
        user = AuthenticationService(UserRepository(session)).get_authenticated_receptionist(user_id) if isinstance(user_id, int) else None
    if user is None:
        await websocket.close(code=4403)
        return
    await realtime_hub.connect_reception(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        realtime_hub.disconnect_reception(websocket)
