New conversations can remain held at missing UUID grants even when a user has
authorized a resource allowance. Add native-MCP caller binding and host-delegated
objective allocations so agents can enroll without per-session provisioning.
Count fresh input plus output by default, exclude cache, and preserve cumulative
usage, deadlines, and stop/grace state across successors. Campaign pause targets
captured work turns while later operator replies remain usable.

Version1grants remain compatible; version2policies may retain their exact caller
map beside delegated allocations. Host-only initial boundaries allow first
deployment to honor an already authorized renewal without resetting its clock
or forgetting post-renewal spending. Explicit renewals retain finalized prior
charges; changed history or retry boundaries hold for reconciliation.

Validation:1,375Python tests pass with1skip in162.520s under isolated fixture
configuration;36focused tests pass;12plugin tests pass. Real native0.163and
installed0.18.0public MCP qualify original/successor spending10then30fresh after
an imported boundary, unchanged deadline and unrelated control, six localhost
Responses requests and zero external provider calls. Module hashes match source.
Compile, policy wiring, wheel build and provider-free installed surface checks
pass. Earlier failed runs remain retained, including a collection failure caused
by reinstalling its environment; the final run uses a separate immutable prefix.

Refs #289. Execution/authority:Plan0169and ADR0002. Remote Python3.11/3.12CI,
exact-main release, production policy/controller adoption and idle MCP activation
remain separate delivery gates; this PR does not itself prove live enforcement.
