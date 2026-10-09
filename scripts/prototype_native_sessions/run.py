#!/usr/bin/env python3
"""PROTOTYPE: two independent TUI clients; never use on production sessions."""
import json, os, pathlib, shlex, subprocess, sys
ROOT=pathlib.Path.home()/".local/state/codex-wake/native-session-prototype-20261008"
SOCKET="native-session-prototype-20261008"
def tmux(*args):
    return subprocess.run(["tmux","-L",SOCKET,*args],capture_output=True,text=True,check=True).stdout
if sys.argv[1]=="start":
    ROOT.mkdir(parents=True,exist_ok=True,mode=0o700)
    for actor in ("A","B"):
        target=ROOT/(actor+".id")
        prompt=(f"Authorized disposable native-communication prototype actor {actor}. "
                f"Run printenv CODEX_THREAD_ID and save only that ID to {target}. "
                f"Then reply exactly READY_INDEPENDENT_{actor} and end your turn. "
                "Do not edit repository files, create tasks, or message anyone until a later test instruction.")
        cmd=shlex.join(["env","-u","CODEX_THREAD_ID","-u","TMUX_PANE","codex",
                        "--no-alt-screen","-C",str(pathlib.Path.cwd()),prompt])
        tmux("new-session","-d","-s",actor,"-x","180","-y","45",cmd)
    print(json.dumps({"socket":SOCKET,"root":str(ROOT)}))
elif sys.argv[1]=="status":
    for actor in ("A","B"):
        print(actor,(ROOT/(actor+".id")).read_text().strip() if (ROOT/(actor+".id")).exists() else "starting")
        print(tmux("capture-pane","-p","-t",actor,"-S","-25"))
elif sys.argv[1]=="stop":
    tmux("kill-server")
else:
    raise SystemExit("Usage: run.py start|status|stop")
