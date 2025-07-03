import os
import sys

from .server import main

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        os._exit(0)  # Force immediate exit
