# Revision-qualified encoded resource reuse

The exact wheel6 owner still failed active CPU at5.112%, while child costs fell.
The producer encoded all100rows on every native change, and publication encoded
the same rows again. A bounded cache now retains strict stdlib JSON per row,
qualified by existing evidence/projection revisions and expiry boundary. The
cache keeps at most512entries/1MiB. Each current frame adds its checked observation
clock and availability, then materializes independent containers only when needed.
A trusted encoded-frame interface allows publication to reuse that same JSON.

Component probe: actual469KB synthetic snapshot,60frames,2dirtyrows/frame and a
full rebaseline every5frames. Formatter decoding remains in both arms. FiveABBA
repeats gave median CPU0.58478s old versus0.28196s cached, saving0.30282s. All
modeled output bytes match. This is a component prototype, not installed acceptance.
The input SHA and limits are in prototype.json; raw synthetic input stays private.

Public native observer test now has two independently bound conversations. One
status change increments resource_serializations by1 and reuses the other row;
its evidence revision stays unchanged. Initial red lacked these cost records.
A second regression caught numeric frame-cache collision between0 and0.0; the
encoded clock now qualifies the frame cache, preserving type and signed zero.
Caller mutation, source loss, redaction and lifecycle checks remain in the same
public selection.

Commands: PYTHONPATH=src /tmp/wake216-py{311,312}/bin/python -m unittest discover
-s tests -p test_tab_observer.py . Both pass5tests (2.533s/3.11,2.289s/3.12).
Original red logs are retained. The publisher integration and exact installed
resource qualification remain separate gates.
