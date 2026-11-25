"""Published CLI bootstrap: Windows callers never import POSIX execution owners."""
import os
import sys


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if args and args[0] == 'ssh-views':
        from .ssh_views import main as run
        return run(args[1:])
    if os.name=='nt':
        if args and args[0] == 'windows-scope':
            from .windows_scope import main as run
            return run(args[1:])
        if args and args[0]=='message-owner':
            from .message_owner import main as run
            return run(args[1:])
        from .controller_client import main as run
    else:
        from .cli import main as run
    return run(argv)


if __name__=='__main__':raise SystemExit(main())
