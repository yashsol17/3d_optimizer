"""
Mesh Optimizer — Windows desktop launcher.

Runs the FastAPI service in-process on a free local port and shows the existing
web interface in a native window, so the desktop build and the web build are
the same application with a different shell around it.

Build a standalone .exe with: python desktop/build.py
"""
import os
import socket
import sys
import threading
import time
import traceback
import urllib.request

APP_NAME = "Mesh Optimizer"

# A --windowed build has no console: sys.stdout and sys.stderr are None, and any
# library that touches them (uvicorn's log formatter calls .isatty()) blows up.
for _stream in ("stdout", "stderr"):
    if getattr(sys, _stream, None) is None:
        setattr(sys, _stream, open(os.devnull, "w", encoding="utf-8"))

# A windowed build has no console, so anything that goes wrong has to be written
# down somewhere the user (and we) can find it.
LOG_DIR = os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"), "MeshOptimizer")
LOG_FILE = os.path.join(LOG_DIR, "startup.log")


def log(message: str) -> None:
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as fh:
            fh.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}  {message}\n")
    except OSError:
        pass

# Make `backend` importable both from the repo and from inside a PyInstaller bundle
BASE = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(BASE, "backend"))

import config  # noqa: E402


def free_port() -> int:
    """Ask the OS for an unused port so two copies can run side by side."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def start_server(port: int) -> threading.Thread:
    """Run uvicorn on a daemon thread; it dies with the window."""
    import uvicorn
    from main import app

    # log_config=None keeps uvicorn from installing its console-oriented logging
    server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning", log_config=None)
    )

    def run():
        try:
            server.run()
        except Exception:
            log("server thread crashed:\n" + traceback.format_exc())

    thread = threading.Thread(target=run, daemon=True, name="mesh-optimizer-server")
    thread.start()
    return thread


def wait_until_ready(port: int, timeout: float = 30.0) -> bool:
    """Poll the health route so the window never opens on a blank page."""
    deadline = time.time() + timeout
    url = f"http://127.0.0.1:{port}/api/v1/health"
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2):
                return True
        except Exception:
            time.sleep(0.25)
    return False


def blender_warning() -> str | None:
    """Mesh processing needs Blender installed; say so plainly if it is missing."""
    path = config.BLENDER_PATH
    if path and os.path.isfile(path):
        return None
    return (
        f"{APP_NAME} could not find Blender on this computer.\n\n"
        "The interface will still open, but optimizing a model will fail.\n\n"
        "Install Blender from blender.org, or set the BLENDER_PATH environment "
        "variable to blender.exe if it is installed somewhere unusual."
    )


def show_message(text: str) -> None:
    """Native message box on Windows, console elsewhere."""
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, text, APP_NAME, 0x40)
    except Exception:
        print(text)


def main() -> int:
    log(f"--- starting {APP_NAME} (frozen={getattr(sys, 'frozen', False)})")
    log(f"blender: {config.BLENDER_PATH}")
    log(f"frontend: {config.FRONTEND_DIR}")
    log(f"storage: {config.STORAGE_DIR}")

    warning = blender_warning()
    if warning:
        show_message(warning)

    port = free_port()
    start_server(port)

    if not wait_until_ready(port):
        show_message(f"{APP_NAME} could not start its local service. Please try again.")
        return 1

    url = f"http://127.0.0.1:{port}/"

    try:
        import webview  # pywebview: a real window, no browser chrome
        window = webview.create_window(
            APP_NAME, url,
            width=1280, height=860, min_size=(900, 600),
            background_color="#050506",
        )
        webview.start()
        return 0
    except ImportError:
        # No pywebview available — fall back to the default browser
        import webbrowser
        webbrowser.open(url)
        print(f"{APP_NAME} is running at {url}")
        print("Close this window to quit.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:
        details = traceback.format_exc()
        log("fatal:\n" + details)
        show_message(f"{APP_NAME} failed to start.\n\nDetails were written to:\n{LOG_FILE}\n\n{details[-600:]}")
        raise SystemExit(1)
