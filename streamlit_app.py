"""
Streamlit Community Cloud entrypoint.

In the Cloud dashboard, set **Main file path** to `streamlit_app.py` (repo root).

Local dev can still use: `streamlit run app/streamlit_app.py`
"""

from pathlib import Path
import runpy

_ROOT = Path(__file__).resolve().parent
runpy.run_path(str(_ROOT / "app" / "streamlit_app.py"), run_name="__main__")
