import os

import uvicorn
from casino.process_lock import BackendProcessLock
from casino.storage import configured_save_paths


if __name__ == "__main__":
    database_path, _ = configured_save_paths()
    with BackendProcessLock(database_path):
        from casino.api import app

        uvicorn.run(
            app,
            host="127.0.0.1",
            port=int(os.environ.get("NOIR_CASINO_API_PORT", "8765")),
            log_level="error",
        )
