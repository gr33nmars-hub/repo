import os

import uvicorn
from casino.persistence.sqlite import configured_save_paths
from casino.process_lock import BackendProcessLock
from casino.session_report import SessionReportWriter

if __name__ == "__main__":
    database_path, _ = configured_save_paths()
    with BackendProcessLock(database_path):
        from casino.api import app

        server = uvicorn.Server(
            uvicorn.Config(
                app,
                host="127.0.0.1",
                port=int(os.environ.get("NOIR_CASINO_API_PORT", "8765")),
                log_level="error",
            )
        )
        app.state.request_shutdown = lambda: setattr(server, "should_exit", True)
        app.state.record_session = SessionReportWriter().record
        server.run()
