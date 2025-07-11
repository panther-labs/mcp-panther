import os
import sys
from typing import Union

COMPATIBILITY_MODE_FLAG = "--compat-mode"


def parse_bool(value: Union[str, bool, None]) -> bool:
    """Parse string to boolean, handling common representations."""
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    return value.lower() in ("true", "1", "yes", "on", "enabled")


USE_LEGACY_MCP = (
    bool(parse_bool(os.getenv("USE_LEGACY_MCP", "false")))
    or COMPATIBILITY_MODE_FLAG in sys.argv
)
