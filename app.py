"""
CRICFIT AI - Root Streamlit Entrypoint Shim
===========================================
For convenience and backward-compatibility, running:
    streamlit run app.py
from the project root will forward execution to `frontend/app.py`.

You can also run directly:
    streamlit run frontend/app.py
"""

import sys
from pathlib import Path

# Setup path so frontend package can be resolved
ROOT_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = ROOT_DIR / "frontend"
FRONTEND_APP = FRONTEND_DIR / "app.py"

if str(FRONTEND_DIR) not in sys.path:
    sys.path.insert(0, str(FRONTEND_DIR))

if __name__ == "__main__" or "streamlit" in sys.modules:
    # Execute frontend/app.py in this scope
    with open(FRONTEND_APP, "r", encoding="utf-8") as f:
        code = compile(f.read(), str(FRONTEND_APP), "exec")
        exec(code, globals())
