try:
    import asyncio
    import json
    import logging
    import os
    import queue
    import threading
    from contextlib import asynccontextmanager
    from datetime import datetime, UTC
    from pathlib import Path
    from typing import Dict, List

    import uvicorn
    from fastapi import (
        APIRouter,
        Depends,
        FastAPI,
        WebSocket,
        WebSocketDisconnect,
    )
    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles
    from sqlmodel import Session, select

    from ..base_interpreter import BaseInterpreter
    from .db import EventLog, create_db_and_tables, get_session

except ImportError:
    raise ImportError(
        "The 'inspector' feature requires additional dependencies. "
        "Please install them with 'pip install xstate-statemachine[inspector]'"
    )

logger = logging.getLogger(__name__)


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
        tasks = [
            connection.send_text(message)
            for connection in self.active_connections
        ]
        await asyncio.gather(*tasks, return_exceptions=True)


# --- Singleton Instances ---
manager = ConnectionManager()
message_queue = queue.Queue()
active_interpreters: Dict[str, "BaseInterpreter"] = {}
_active_interpreters_lock = threading.Lock()


def get_db():
    """FastAPI dependency to get a database session."""
    with get_session() as session:
        yield session


async def broadcast_from_queue():
    """Efficiently waits for messages from the thread-safe queue."""
    loop = asyncio.get_running_loop()
    while True:
        try:
            message = await loop.run_in_executor(None, message_queue.get)
            if message is None:
                break
            logger.info(
                f"INSPECTOR: Broadcasting message from queue: {message[:100]}..."
            )
            await manager.broadcast(message)
            message_queue.task_done()
        except asyncio.CancelledError:
            logger.info("INSPECTOR: Broadcast task cancelled.")
            break
        except Exception as e:
            logger.error(
                f"INSPECTOR: Error in broadcast queue: {e}", exc_info=True
            )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages the background broadcast task."""
    logger.info("INSPECTOR: Lifespan startup. Starting broadcast task.")
    task = asyncio.create_task(broadcast_from_queue())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        logger.info("INSPECTOR: Broadcast task cancelled on shutdown.")


def create_app(mount_static_files: bool = True) -> FastAPI:
    """Creates and configures the FastAPI application."""
    app = FastAPI(lifespan=lifespan)

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await manager.connect(websocket)
        logger.info(
            "INSPECTOR: WebSocket client connected. Sending initial state for all active machines."
        )

        with _active_interpreters_lock:
            active_ids = list(active_interpreters.keys())
            logger.info(
                f"INSPECTOR: Acquired lock. Found active interpreters: {active_ids}"
            )

            for machine_id, interpreter in active_interpreters.items():
                try:
                    logger.info(
                        f"INSPECTOR: Preparing registration message for machine '{machine_id}'..."
                    )
                    message = {
                        "type": "machine_registered",
                        "machine_id": interpreter.id,
                        "timestamp": datetime.now(UTC).isoformat(),
                        "payload": {
                            "machine_id": interpreter.id,
                            "initial_state_ids": list(
                                {
                                    s.id
                                    for s in interpreter._active_state_nodes
                                    if s.is_atomic or s.is_final
                                }
                            ),
                            "initial_context": interpreter.context,
                            "definition": interpreter.machine.to_dict(),
                        },
                    }
                    await websocket.send_text(json.dumps(message, default=str))
                    logger.info(
                        f"INSPECTOR: Successfully sent registration for '{machine_id}' to new client."
                    )
                except Exception as e:
                    logger.error(
                        f"INSPECTOR: Error sending initial state for '{machine_id}': {e}",
                        exc_info=True,
                    )

        try:
            while True:
                data = await websocket.receive_text()
                try:
                    message = json.loads(data)
                    command = message.get("command")
                    machine_id = message.get("machine_id")

                    if not command or not machine_id:
                        continue
                    with _active_interpreters_lock:
                        interpreter = active_interpreters.get(machine_id)

                    if interpreter:
                        logger.info(
                            f"INSPECTOR: Received command '{command}' for machine '{machine_id}'"
                        )
                        if command == "pause":
                            interpreter.pause()
                        elif command == "resume":
                            interpreter.resume()
                        elif command == "send_event" and "event" in message:
                            if asyncio.iscoroutinefunction(interpreter.send):
                                asyncio.create_task(
                                    interpreter.send(message["event"])
                                )
                            else:
                                interpreter.send(message["event"])
                except (json.JSONDecodeError, KeyError):
                    logger.warning(
                        f"INSPECTOR: Received invalid command message: {data}"
                    )
                except Exception as e:
                    logger.error(
                        f"INSPECTOR: Error processing command: {e}",
                        exc_info=True,
                    )
        except WebSocketDisconnect:
            logger.info("INSPECTOR: WebSocket client disconnected.")
        finally:
            manager.disconnect(websocket)

    api_router = APIRouter(prefix="/api")

    @api_router.get("/sessions")
    async def get_sessions(db: Session = Depends(get_db)):
        return db.exec(select(EventLog.session_id).distinct()).all()

    @api_router.get("/history/{session_id}")
    async def get_history(session_id: str, db: Session = Depends(get_db)):
        history = db.exec(
            select(EventLog)
            .where(EventLog.session_id == session_id)
            .order_by(EventLog.timestamp)
        ).all()
        return [json.loads(log.data) for log in history]

    app.include_router(api_router)

    if mount_static_files:
        frontend_dist_dir = Path(__file__).parent / "frontend" / "dist"
        if frontend_dist_dir.exists():
            app.mount(
                "/assets",
                StaticFiles(directory=frontend_dist_dir / "assets"),
                name="assets",
            )

            @app.get("/{full_path:path}")
            async def serve_frontend_spa(full_path: str):
                return FileResponse(frontend_dist_dir / "index.html")

        else:
            logger.error(
                f"Frontend dist directory not found at {frontend_dist_dir}"
            )

    return app


app = create_app()

_server_thread = None


def run_server():
    """The target function for the server thread."""
    try:
        logger.info("INSPECTOR: Uvicorn server thread started.")
        config = uvicorn.Config(
            app, host="127.0.0.1", port=8008, log_level="info"
        )
        server = uvicorn.Server(config)
        server.run()
    except Exception as e:
        logger.critical(
            f"INSPECTOR: Server thread crashed: {e}", exc_info=True
        )


def start_inspector_server():
    """Initializes DB and starts the inspector server in a background thread."""
    global _server_thread
    if _server_thread is None or not _server_thread.is_alive():
        # FIX: Create DB tables synchronously before starting any threads
        logger.info("INSPECTOR: Initializing database...")
        create_db_and_tables()
        logger.info("INSPECTOR: Database initialized. Starting server thread.")

        _server_thread = threading.Thread(target=run_server, daemon=True)
        _server_thread.start()
