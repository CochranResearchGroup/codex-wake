# wakeA/wakeB live manual-inbox round trip

Verdict: PASS for live manual inbox request/read/ack/reply/sender-read only.
Automatic delivery and durable receipt suspension: NOT QUALIFIED.
Date: 2026-10-04. Work item: https://github.com/CochranResearchGroup/codex-wake/issues/181.

The operator selected Byobu wakeA and wakeB, both in the root codex-wake repo.
After bootstrap prompts, both actual agents wrote their runtime thread IDs and
were resolved against the existing shared daemon before explicit bus enrollment.
Each agent ran CLI commands in its own tool context. The controller supplied
workflow setup and helper commands; B read the request and composed the reply.
No fake daemon, substituted thread ID or controller-authored reply was used.

- wakeA thread: `01a10876-c7cf-7ae1-ad99-e9d829994e45`.
- wakeB thread: `01a10876-e53a-7322-bf68-ff43e9b2f2dc`.
- Request: `msg_02071e4c53c34984bd7561774edea49e`.
- B read: `receipt_b5911c9239ab4885bc7d9e74ca8bd740`.
- B accepted: `receipt_217c4f4a007c4548819063e9a89ad719`.
- Reply: `msg_84da70ea168047249bb155004aa4c786`, linked to the request.
- B completed: `receipt_d70d0ac1fd7f40bc81ca917fbd50e5cf`.
- A read reply: `receipt_f019aba86d2e48988062b5d24655364d`.

Actual reply:

> Challenge: e897d9c21011803c. I read a live request from wakeA in my CLI inbox
> asking me to echo this challenge and describe what I observed. The read result
> marked the peer body as untrusted, and the acknowledgement showed the request
> was accepted.

The challenge and both body SHA256s were verified against admitted envelopes.
Request admission to reply readback: 55.509 seconds. Doctor observed exactly two
admitted messages, both notifications suppressed; request completed, reply received.
Both actual threads resolved idle afterward. Each client had FD41 before/FD40
after and no direct child processes. The shared daemon runs unrelated sessions;
its census is not an isolated leak/soak verdict.

Installed Codex: 0.160.0. Source main: f104c2f86b37ac548ba1f798aa0d65abd8d37322.
Isolated wheel SHA256: f5e2bc7bfe30d2e042dfd0c8609d4ef319b0773c41906eab8ee39f1ee52dec43.
Global installation/services were not changed. Bare Python initially lacked
websockets; the properly installed wheel connected to the running shared daemon.
Fresh blank sessions had no resolvable thread until their first submitted prompt.
Tmux paste debounce required submitting Enter after the pasted input settled;
controller setup is not evidence of an automatic notification adapter.

Durable owner-private evidence directory:
`/home/ecochran76/.local/state/codex-wake/live-demos/20261004-wakeA-wakeB/`.
It contains result.json, exact CLI read/ack/send/wait receipts, runtime readbacks,
terminal captures, OS census, owned helper scripts, a SHA256 manifest and a
read-only-evidence SQLite snapshot (integrity_check: ok). No capability secrets
were copied into that evidence directory. Original owned demo bus remains paused
under `/tmp/codex-wake-live-20261004/bus`; user-owned sessions were not removed.

This supersedes the earlier statement that no live round trip had occurred.
It does not satisfy automatic wake-up, installed global service, restart or release
acceptance. Plan0119 begins with the unassisted version of this exact user flow.
