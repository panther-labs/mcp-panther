import os
import sys

from .server import main

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nGracefully exiting due to keyboard interrupt...", file=sys.stderr)
        os._exit(0)  # Force immediate exit
