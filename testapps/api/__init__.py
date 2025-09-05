"""Package init for apps.api.

Ensures that `apps/api/src` is on sys.path so imports like
`realtime_api.realtime_common` work when running the FastAPI app
without test-specific path configuration.
"""

from __future__ import annotations

import os
import sys

_here = os.path.abspath(os.path.dirname(__file__))
_src = os.path.join(_here, "src")
if os.path.isdir(_src) and _src not in sys.path:
    sys.path.insert(0, _src)
