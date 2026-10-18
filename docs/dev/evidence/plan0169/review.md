# Control/accounting repair review

Fixed point: dbd37ca09f9a13f4ae54b98f8f8ea4b0888a86c5. Review of working diff,
not a committed integration result. Reviewer handle /root/control_repair_review.
One broad source review used; no new discovery loop is authorized by this note.

Standards: no candidate findings under the named repo policy and Matt smell
baseline. Spec: no candidate findings in the bounded control/accounting repair.
Primary adjudication: no accepted blockers on either reviewed axis. Reviewer
inspected source and supplied tests; no independent production acceptance claim.

Frozen contract: fresh input plus output default, cached input excluded; explicit
inclusive option; persisted basis/deadline/spend; qualified basis conversion keeps
prior evidence and does not clear stop latches. Campaign interruption captures
exact work turns; later operator messages remain usable. Qualification-loss grace
is persisted, max60seconds, capped by checkpoint reserve and original deadline.
Streaming accounting preserves all consumed attribution/lineage records and scan
bounds. Missing grant is no-effect and explicitly permits operator interaction.

Full issue289 provisioning/continuity remains incomplete and was not treated as
a newly discovered regression in this repair review. Installed isolated fixture
receipts are separate evidence. No native production or provider effects ran.
