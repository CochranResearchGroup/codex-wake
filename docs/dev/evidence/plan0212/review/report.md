# PR536 review

Fixed point fbfb41075f12b0567a714eac1d495741b31fb4ef (PR base).
Frozen tip acf263aaaf654b5135d08782a100ad21c0c891f0.
Commands: git diff fbfb410...acf263a; git log fbfb410..acf263a --oneline.
Commits bd79923,aa45088,acf263a. Both axes reviewed serially by primary.

## Standards

No accepted findings. Checked policies0005,0006,0014,0016,0017 and AGENTS,
plus Fowler smell baseline. The bounded module hides caller-specific credential
resolution, preserves the existing explicit operator/actor boundary and uses
focused public-seam regression and installed tests. No changes enforced by
lint were counted as review findings. No additional standards/contributing files
were found. Test fixture native metadata is clearly labeled as injected.

## Spec

No accepted findings. LOCAL-P212 acceptance maps to distinct/reused native actors,
private host-only operator selection, existing root scope, revoked and rotated
actors, native metadata rejection, wrong operator before runtime access,
concurrent issuance and actual stdio/CLI question/claim/correlated reply. Root
enrollment and live FigureLabs acceptance are correctly separate from fixture
qualification. One-time host activation is required; package installation alone
would not qualify the live setup.

23 focused3.12 checks and21 focused3.11 checks plus exact installed four-check
workflow are retained under plan0212; no repeated full suite or hosted CI.
Product bytes remain bd79923, wheel53f2a3ef358d16bf1fee7dcb05598170e8a0631b4435313d7817340131acc3c0.

Standards: 0 accepted findings, highest severity none; Spec: 0 accepted findings, highest severity none.
