"""
Runner script for Secure Online Code Execution Platform.
Starts the FastAPI application with Uvicorn.
"""

import uvicorn
import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting Secure Online Code Execution Platform on http://127.0.0.1:{port}")
    uvicorn.run("app.main:app", host="127.0.0.1", port=port, reload=False)
