# Cooper webhook ingress publication verification

Date: 2026-09-16
Issue: `CochranResearchGroup/codex-wake#108`
Plans: 0078 and 0080
Result: ACCEPTED

## Accepted boundary

The dedicated Codex Wake webhook listener remained on `127.0.0.1:8820` and the
shared ingress layers exposed only exact `POST /github/webhook` routers for
`codex-wake.localhost` and `codex-wake.ecochran.dyndns.org`. The application
accepted one frozen signed occurrence, rejected unsigned input, and remained
the final raw-path/method admission authority. The local and public proxies
rejected non-exact selectors without exposing an application diagnostic
surface. No Authelia middleware, catchall, prefix route, public HTTP route,
non-loopback listener, GitHub provider request or mutation, dispatch, release,
or global installation occurred.

## Git and configuration custody

- Codex Wake correction and successor plan passed both hosted release gates in
  PR #125 and squash-merged as
  `7c2836377eae0eb271636fcafb14c0cdd454c766`.
- The live successor was registered through PR #126; exact canonical candidate
  main was `3a4dbd44af9231848b722fbc5127affe9412bdda`.
- Cooper source/inventory is clean at canonical
  `cd0d60f91d870c1372b2d7d5f8e16602f52f1d6a`.
- Bastion commit `4e7bc6966870a592fc8b30c17889269e98134d0a`
  contains only the route snippet and its truthful `CODEX_LOG.md` entry. The
  unrelated Odoo modifications/untracked file remained outside that commit.
- Local generated and bastion-installed route artifacts both have SHA-256
  `ffcb4efabc644d9da705e3369be043de28fe5c8f3b4850681e002ca2f5a68a64`.
- Post-acceptance bastion readback remained at `4e7bc69`; Traefik was running
  with start time `2026-09-16T16:04:31.533800358Z`, restart count `0`, proving
  the successor performed no copy or restart.

## Retained first attempt

Plan 0078 consumed the one external publication and failed its first public TLS
handshake with `SSLError`; it did not retry. Raw, local, and Cooper-Host checks
had already passed. Traefik subsequently provisioned the exact hostname
certificate, but certificate-store presence was not promoted to acceptance.

- External receipt: `/tmp/codex-wake-p53-c5-ingress.json`
- Receipt SHA-256:
  `3642b316abb16cb529da095b3f4706a08b9a4cd640d4786fd1ff5339d2d2c8e9`
- Retained owner-only recovery root:
  `/home/ecochran76/.local/state/codex-wake/qualification/p53-c5-ingress-jchgj5g9`
- The unit was uninstalled and a fresh OS census later proved no matching
  process or listener. The receipt remains `cleanup_uncertain` rather than
  rewriting its immediate TIME_WAIT and unrelated failed-unit observations.

## Accepted successor receipt

- External receipt: `/tmp/codex-wake-p53-c5-retry1.json`
- Receipt SHA-256:
  `f1d38ac56623afeb3d3d66b0072a7c0117a0209c97149849f778d42b88ad8154`
- Candidate commit and canonical ref:
  `3a4dbd44af9231848b722fbc5127affe9412bdda`
- Installed wheel SHA-256:
  `ea1a20a0bc45615229e7505d7396de0d733c06d51a1323db0b870d6e49c84729`
- Request SHA-256:
  `c30cc9e2ac09670be952166fe83c70b46a603c65efedf3c36701b7d15b510b00`
- Signed delivery ID: `878a6044-f1dc-4225-a5ee-61942dbd2bff`
- Security-header fingerprint:
  `a2646e0f6b4795c24969fa1f0b263cec93a18fccf8a1c0fb130ce9ad99d6aba6`

Checkpoint results, in required order:

1. Raw loopback: signed `COMMITTED`/200, unsigned 401, wrong method 405,
   wrong path 404.
2. Local hostname: signed `DUPLICATE`/200, unsigned 401, wrong method/path
   404.
3. Cooper public Host: signed `DUPLICATE`/200, unsigned 401, wrong
   method/path 404.
4. Public certificate-verifying HTTPS: signed `DUPLICATE`/200, unsigned 401,
   wrong method/path 404.

Every checkpoint reported leak-free bounded responses. Authoritative attempt
reads advanced exactly `1, 2, 3, 4`; production provider factory calls and
dispatch calls remained `0` throughout. The durable journal remained one
pending receipt with zero matches, firing, submitted, or failed dispatch state.

## Cleanup and fresh readback

Cleanup returned `safe: true`, uninstall return code `0`, unit absent,
inactive/disabled state, PID `0`, no matching process, and port released under
the C5 production-equivalent bind check. The unrelated
`company-assets-immich-gallery-watchdog.service` failed during the window and
was retained as `noncausal_evidence`; it did not relax any exact target check.
The successor root was removed. A fresh post-cleanup `systemctl`, `ss`, `lsof`,
and process census independently confirmed unit not found, inactive/dead,
MainPID zero, no 8820 listener, and no matching process. The first failed root
remains preserved.

## Source validation

- Focused installed plus C5 tests: 49 passed.
- Comprehensive Python: 541 passed on the first retained retry. The initial
  unrelated provider-timeout timing failure passed in isolation and is retained
  in Plan 0080.
- OpenClaw plugin: 12 passed.
- Compilation, diff hygiene, active/goal planning audits, default-ref lane
  audit, and closed-world independent review passed.
- PR #125 and registration PR #126 passed Python 3.11 and 3.12 release gates.

## Retained route and rollback

The exact routes intentionally remain for issue #109. That issue must establish
its own production source/runtime and GitHub secret; it may not reuse either
canary root, fixture, secret, delivery, wake, journal, or bootstrap.

If a later authorized rollback is required, the bastion boundary is reverted
from `/var/homelabos` by reverting commit `4e7bc69`, validating the resulting
staged route removal, and restarting only `traefik-portainer`. The local Cooper
boundary is independently removed through reviewed inventory/source reversal,
deterministic regeneration, and the local Traefik workflow. No rollback was
performed during acceptance because it would remove the route required by
#109.
