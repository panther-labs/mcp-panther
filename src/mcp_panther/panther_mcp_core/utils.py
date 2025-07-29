from typing import Union


def parse_bool(value: Union[str, bool, None]) -> bool:
    """Parse string to boolean, handling common representations."""
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    return value.lower() in ("true", "1", "yes", "on", "enabled")
