try:
    import asyncio
    import queue
    import threading
    from contextlib import asynccontextmanager
    from datetime import datetime, UTC
    import uvicorn
    from fastapi import APIRouter, FastAPI, WebSocket, WebSocketDisconnect
    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles
    from typing import List, Dict
    from .db import get_session, EventLog, create_db_and_tables
    from sqlmodel import Session, select
    from ..base_interpreter import BaseInterpreter
    from fastapi import Depends
    import json
    import os
except ImportError:
    raise ImportError(
        "The 'inspector' feature requires additional dependencies. "
        "Please install them with 'pip install xstate-statemachine[inspector]'"
    )


class ConnectionManager:
    """Manages active WebSocket connections."""
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

# Create singleton instances for the connection manager and message queue
manager = ConnectionManager()
message_queue = queue.Queue()
active_interpreters: Dict[str, "BaseInterpreter"] = {}


def get_db():
    """FastAPI dependency to get a database session."""
    with get_session() as session:
        yield session


# --- Background Task ---
async def broadcast_from_queue():
    while True:
        try:
            message = message_queue.get_nowait()
            await manager.broadcast(message)
        except queue.Empty:
            await asyncio.sleep(0.01)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages the background task for broadcasting messages."""
    task = asyncio.create_task(broadcast_from_queue())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


def create_app(mount_static_files: bool = True) -> FastAPI:
    """Creates and configures the FastAPI application."""
    app = FastAPI(lifespan=lifespan)

    # --- WebSocket Endpoint ---
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await manager.connect(websocket)
        # When a new client connects, send them the current state of all active machines.
        for machine_id, interpreter in active_interpreters.items():
            try:
                # Reconstruct the registration message
                message = {
                    "type": "machine_registered",
                    "machine_id": interpreter.id,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "payload": {
                        "machine_id": interpreter.id,
                        "initial_state": [s.id for s in interpreter._active_state_nodes],
                        "initial_context": interpreter.context,
                        "definition": interpreter.machine.to_dict(),
                    },
                }
                await websocket.send_text(json.dumps(message, default=str))
            except Exception:
                # If something goes wrong with one machine, don't kill the connection
                pass
        try:
            while True:
                data = await websocket.receive_text()
                try:
                    message = json.loads(data)
                    command = message.get("command")
                    machine_id = message.get("machine_id")

                    if command and machine_id:
                        interpreter = active_interpreters.get(machine_id)
                        if interpreter:
                            if command == "pause":
                                interpreter.pause()
                            elif command == "resume":
                                interpreter.resume()
                except json.JSONDecodeError:
                    # Ignore non-json messages
                    pass
        except WebSocketDisconnect:
            manager.disconnect(websocket)

    # --- API Router ---
    api_router = APIRouter(prefix="/api")

    @api_router.get("/sessions")
    async def get_sessions(db: Session = Depends(get_db)):
        statement = select(EventLog.session_id).distinct()
        sessions = db.exec(statement).all()
        return sessions

    @api_router.get("/history/{session_id}")
    async def get_history(session_id: str, db: Session = Depends(get_db)):
        statement = (
            select(EventLog)
            .where(EventLog.session_id == session_id)
            .order_by(EventLog.timestamp)
        )
        history = db.exec(statement).all()
        return [json.loads(log.data) for log in history]

    app.include_router(api_router)

    # --- Static Files (Optional) ---
    if mount_static_files:
        frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")

        @app.get("/")
        async def get_index():
            return FileResponse(os.path.join(frontend_dir, "index.html"))

        app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

    return app

# The main app instance used by the running server
app = create_app()

# --- Server Singleton Management ---
_server_thread = None
_server_started = threading.Event()

def run_server():
    """The target function for the server thread."""
    create_db_and_tables()
    config = uvicorn.Config(app, host="127.0.0.1", port=8008, log_level="info")
    server = uvicorn.Server(config)

    async def new_startup(*args, **kwargs):
        # Correctly call the original startup without extra args
        await server.startup()
        _server_started.set()

    # server.startup is an awaitable list of callables
    server.startup_tasks = [new_startup]
    server.run()


def start_inspector_server():
    """Starts the inspector server in a background thread if not already running."""
    global _server_thread
    if _server_thread is None:
        _server_thread = threading.Thread(target=run_server, daemon=True)
        _server_thread.start()
        started = _server_started.wait(timeout=20)
        if not started:
            print("ERROR: Inspector server failed to start in time.")
