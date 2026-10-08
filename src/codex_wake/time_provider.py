"""Pure time selection. Acquisition and trusted normalization belong to adapters."""
from dataclasses import dataclass
from itertools import combinations, islice
from collections import Counter
import math


@dataclass(frozen=True)
class Observation:
    source: str
    operator: str
    lower: float
    upper: float
    age: float
    boot: str
    round_id: str
    kind: str
    scale: str
    healthy: bool


@dataclass(frozen=True)
class TimeDecision:
    status: str
    sources: tuple[str, ...] = ()
    lower: float | None = None
    upper: float | None = None
    reason: str = ''


def select_time(observations, *, boot, round_id, tolerance, max_age, scale):
    if not all(type(v) in (int, float) and math.isfinite(v) and v >= 0 for v in (tolerance, max_age)):
        raise ValueError('time policy must have finite nonnegative bounds')
    if not all(isinstance(v, str) and v for v in (boot, round_id, scale)):
        raise ValueError('time policy identity must be explicit')
    observations = tuple(islice(observations, 6))
    if len(observations) > 5:
        raise ValueError('at most four network observations and one Windows observation')
    kinds = Counter(o.kind for o in observations if isinstance(o, Observation))
    if kinds['network'] > 4 or kinds['windows'] > 1:
        raise ValueError('at most four network observations and one Windows observation')
    usable = [o for o in observations if isinstance(o, Observation)
              if all(isinstance(v, str) and v for v in (o.source, o.operator, o.boot, o.round_id, o.scale))
              and all(type(v) in (int, float) and math.isfinite(v) for v in (o.lower, o.upper, o.age))
              and o.lower <= o.upper and o.upper-o.lower <= tolerance
              and 0 <= o.age <= max_age and o.boot == boot and o.round_id == round_id
              and o.scale == scale and o.healthy is True and o.kind in ('network', 'windows')]
    network = [o for o in usable if o.kind == 'network']
    fallback_evidence = tuple(network)
    counts = Counter(o.operator for o in network)
    sources = Counter(o.source for o in network)
    network = [o for o in network if counts[o.operator] == 1 and sources[o.source] == 1]
    for size in range(len(network), 1, -1):
        groups = [g for g in combinations(network, size)
                  if max(o.upper for o in g)-min(o.lower for o in g) <= tolerance]
        if len(groups) > 1:
            return TimeDecision('uncertain', reason='competing_network_consensuses')
        if groups:
            group = groups[0]
            return TimeDecision('network', tuple(sorted(o.source for o in group)),
                                min(o.lower for o in group), max(o.upper for o in group))
    windows = [o for o in usable if o.kind == 'windows']
    if len(windows) == 1:
        window = windows[0]
        if all(max(window.upper, o.upper)-min(window.lower, o.lower) <= tolerance for o in fallback_evidence):
            return TimeDecision('windows', (window.source,), window.lower, window.upper)
        return TimeDecision('uncertain', reason='windows_conflicts_with_network')
    return TimeDecision('uncertain', reason='no_network_consensus')


def deadline_status(decision: TimeDecision, deadline: float) -> str:
    if type(deadline) not in (int, float) or not math.isfinite(deadline):
        raise ValueError('deadline must be finite')
    if decision.status not in ('network', 'windows') or decision.lower is None or decision.upper is None:
        return 'uncertain'
    if not all(type(v) in (int, float) and math.isfinite(v) for v in (decision.lower, decision.upper)) or decision.lower > decision.upper:
        return 'uncertain'
    if decision.lower >= deadline:
        return 'due'
    if decision.upper < deadline:
        return 'pending'
    return 'uncertain'
