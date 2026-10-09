# Plan0122 activation evidence — revision2

Goal began02:05UTC October9. Checkpoint before05:00UTC / two million tokens. Baseline7a4666a; work item224 (owner ecochran76), approved objective completion of Plan0122. Current progress is implementation repair, not activation acceptance.

## Reproduced defects

- CLI network mailbox worker exited8 on the first time_uncertain instead of holding/recovering. `/tmp/plan0122-worker-red.txt` has the meaningful public CLI failure; `/tmp/plan0122-worker-green.txt` has13 passing tests after accepting time_uncertain through the existing no-ambiguous-effects guard. Initial malformed/empty-binding harness controls were corrected before the meaningful red.
- Sender reply arm used guest wall UTC for registration/evaluation/expiry: `tests.test_a2a_reply_wake.ReplyWakeTests.test_network_bus_reply_arm_uses_network_time_despite_guest_wall_disagreement` produced0 submissions for an unexpired network-domain arm. Now all8 reply workflow tests pass, including legacy expiry refusal. Registration uses upper, evaluation lower, final expiry refusal upper, with explicit mailbox schema selection and no checkpoint mutation. Signal leases use the same declared mailbox domain.
- Final tmux transport used guest time for pointer expiry: `test_tmux_transport_checks_network_expiry_instead_of_guest_wall` returnedunsent before I/O for an unexpired network pointer. Transport now reads the declared bus domain and checks upper bounds. The combined network-mailbox/tmux23-test selection passes; no real paste is claimed by these fixtures.

## Additional-source admission

The original two-source mode loses quorum after either source outage while Windows fallback is unavailable. A public inspection-seam regression reproduced this for either missing original provider. Added Alastyr as a third distinct operator, preserving all four original candidates visibly. All8 inspection tests pass; each single-provider loss retains the other two. `three-provider-inspection.json` records actual Cloudflare/NIST/Alastyr consensus with a union about0.17s, and Netnod/PTB explicitly excluded. Network voting still caps four admitted operators; five registry entries include two disabled candidates.

[Alastyr's own measurement and policy page](https://ntp.alastyr.com/en/measurements.html) identifies its operator and endpoint, public UDP123 access, GNSS reference and standard leap announcement without smearing. This qualifies a declared UTC-step, unauthenticated plain-NTP source; it does not independently certify its accuracy or hostile-network authenticity. The same operator's [FAQ](https://ntp.alastyr.com/en/faq.html) incorrectly categorizes Cloudflare's smear policy; we do not adopt that third-party assertion. Cloudflare's [own policy](https://developers.cloudflare.com/time-services/ntp/) governs Cloudflare. Netnod/PTB profiles remain unqualified, rather than inferring policy from packet agreement. The prior failed NTS spike remains preserved; no authenticated acquisition or silent downgrade is claimed.

## Current runtime custody

Stable CLI remains0.7.1; no installation yet. Current Codex reports0.162.0, so historical0.160.0 acceptance cannot certify current UI/transport compatibility. Only recovered unrelated tmux sessions exist; historical wakeA/wakeB panes are absent. No existing client has been restarted or messaged. The historical demo mailbox remains schema2, no unfinished dispatch/uncertain attempts; native doctor reports unpaused/no recovery hold and metadata only. Doctor created an audit receipt; it did not prove the time guard healthy or reset its checkpoint. Historical store/guard is preserved; owned new sessions and a new explicitly enrolled bus will be used for current acceptance.

Fetched origin/main: three newer app-server transport/proxy commits precede current branch integration. They must be reconciled before deploy. Issue224 creation/readback verified on canonical GitHub repository with ADMIN capability, stable marker plan0122-network-time-activation and primary owner. This implements the repo's canonical issue workflow; issue181 remains separate.
