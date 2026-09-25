# GitHub CLI credential backend

State: CLOSED
Lane: I166
Issue: #166
Branch: `feat/issue-166-gh-auth-backend`
Target: `main`
Integration: `squash`

## Current state

PR #167 passed both hosted Python gates and merged as canonical `8ae3a024`.
The exact canonical wheel is installed in the user tool, and the supervisor
restart left all four enrolled roots ready. Installed source hashes, credential
resolution, CLI defaults, and the two installed skill copies were read back.
Receipt 0090 records the implementation and installed rollout. The retained
#141 listener and poller continue on their prior isolated runtime and binding.

## Objective

Make the same user's configured `gh` login the default credential backend for
GitHub CI polling, signed delivery verification, and explicit webhook
administration, preserving explicit limited tokens.

## Scope

- Resolve `GH_CLI` through the fixed `gh auth token --hostname github.com`
  command at the credential resolver seam.
- Default new source and binding configuration to `GH_CLI`; preserve existing
  durable references and explicit environment credentials.
- Accept a webhook listener environment with its HMAC secret and no `GH_CLI`
  environment variable.
- Document the same-user trust model, authorization boundary, and multi-repo
  configuration.
- Validate provider free, merge through hosted gates, install the canonical
  wheel in user scope, and read back the installed command.

## Non-goals

- No automatic repository enrollment, provider mutation during tests, webhook
  redelivery, live dispatch, or migration of the retained #141 binding.
- No claim that same-user `gh` access isolates service authority.

## Acceptance criteria

- Fixed-command resolution and sanitized failure tests pass; explicit token
  resolution remains compatible.
- Poller, listener, and webhook administration use the backend through their
  existing credential resolver seams.
- The HMAC-only service environment is accepted for `GH_CLI` sources.
- Docs and skill match the installed behavior; both hosted Python gates pass.
- Canonical user install exposes the default and leaves the retained #141
  service on its existing isolated runtime until a separate migration receipt.

## Definition of done

Code, documentation, skill, tests, and receipt are canonical; user installation
and post-install readback pass; #166 closes with any live multi-repository
qualification explicitly deferred.
