import sys

from .server import main

if __name__ == "__main__":
    try:
        main()  # Let Click handle the CLI, don’t wrap in sys.exit()
    except KeyboardInterrupt:
        print("\nGracefully exiting due to keyboard interrupt...", file=sys.stderr)
        sys.exit(0)  # Use sys.exit, not os._exit
