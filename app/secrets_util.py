"""
Streamlit Community Cloud injects configuration via st.secrets (TOML in the dashboard).
The rest of the app reads os.environ — map secrets into the environment without
overriding variables already set (e.g. from a local .env).
"""

from __future__ import annotations

import os
from typing import Any


def apply_streamlit_secrets_to_environ(st_module: Any) -> None:
    """Copy flat st.secrets keys into os.environ using setdefault."""
    try:
        secrets = st_module.secrets
    except Exception:
        return
    if secrets is None:
        return
    try:
        items = dict(secrets).items()
    except Exception:
        return
    for key, value in items:
        if isinstance(value, (str, int, float, bool)):
            os.environ.setdefault(str(key), str(value))
