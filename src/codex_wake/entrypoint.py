"""Published CLI bootstrap: Windows callers never import POSIX execution owners."""
import os


def main(argv=None):
    if os.name=='nt':
        from .controller_client import main as run
    else:
        from .cli import main as run
    return run(argv)


if __name__=='__main__':raise SystemExit(main())
