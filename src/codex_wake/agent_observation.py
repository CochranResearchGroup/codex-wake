"""Read-only semantic observations for exact managed conversations."""
from __future__ import annotations

from dataclasses import dataclass
import time
import math

from .managed_inventory import ManagedInventory

STATES = ('working', 'ready', 'awaiting-human', 'auth-required', 'disconnected', 'unknown')


def _number(value, name, low, high):
    if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(name + ' is outside its supported bounds')
    return value


@dataclass(frozen=True)
class StateEvidence:
    runtime: str
    namespace: str
    conversation_id: str
    root: str
    process: dict | None
    observed_at: float
    state: str
    source: str
    reason: str
    complete: bool = True


class AgentObservation:
    def __init__(self, root, *, observer, now=time.time, monotonic=time.monotonic, sleep=time.sleep):
        self.inventory = ManagedInventory(root, now=now)
        self.observer, self.now, self.monotonic, self.sleep = observer, now, monotonic, sleep

    def observe(self, managed_agent_id, *, freshness=30, timeout=10):
        _number(freshness, 'freshness', .1, 300)
        _number(timeout, 'source timeout', .001, 60)
        agent = self.inventory.inspect(managed_agent_id)['agent']
        supported = {'ready', 'unknown'}
        if agent['runtime'] == 'codex':
            supported |= {'working', 'awaiting-human', 'disconnected'}
        expected_source = 'native_metadata' if agent['runtime'] == 'codex' else 'host_bound_runtime'
        result = dict(schema_version=1, managed_agent_id=managed_agent_id, runtime=agent['runtime'],
                      conversation_id=agent['conversation_id'], state='unknown', evidence_kind=expected_source,
                      observed_at=None, fresh=False, reason='evidence_unavailable', grants_operations=False,
                      capabilities={state: 'supported' if state in supported else 'unsupported' for state in STATES})
        if agent['enrollment'] != 'enrolled' or not agent['process']:
            result['reason'] = 'binding_unavailable'
            return result
        try:
            sample = self.observer(agent, timeout)
        except Exception:
            return result
        if (not isinstance(sample, StateEvidence) or sample.complete is not True
                or any(getattr(sample, key) != agent[key] for key in
                       ('runtime', 'namespace', 'conversation_id', 'root', 'process'))
                or sample.source != expected_source or sample.state not in supported
                or type(sample.observed_at) not in (int, float) or not math.isfinite(sample.observed_at)
                or not sample.observed_at <= self.now() <= sample.observed_at + freshness):
            result['reason'] = 'evidence_stale_partial_or_mismatched'
            return result
        result.update(state=sample.state, observed_at=sample.observed_at, fresh=True, reason=sample.reason)
        return result

    def wait(self, managed_agent_id, *, state, freshness=30, timeout=60, interval=1):
        _number(freshness, 'freshness', .1, 300)
        _number(timeout, 'wait timeout', 0, 300)
        _number(interval, 'poll interval', .05, 5)
        if state not in STATES:
            raise ValueError('unsupported semantic state')
        deadline = self.monotonic() + timeout
        last = None
        while self.monotonic() < deadline:
            remaining = deadline - self.monotonic()
            if remaining < .001:
                break
            last = self.observe(managed_agent_id, freshness=freshness, timeout=min(remaining, 60))
            if self.monotonic() < deadline and last['fresh'] and last['state'] == state:
                return dict(status='matched', requested_state=state, observation=last)
            remaining = deadline - self.monotonic()
            if remaining <= 0:
                break
            self.sleep(min(interval, remaining))
        return dict(status='unknown' if last and not last['fresh'] else 'timeout',
                    requested_state=state, observation=last)


class RuntimeStateObserver:
    """Use existing runtime metadata routes, never resume or submit a turn."""
    def __init__(self, *, endpoint='unix://', now=time.time, monotonic=time.monotonic, grok_source=None):
        self.endpoint, self.now, self.monotonic = endpoint, now, monotonic
        self.grok_source = grok_source

    def __call__(self, agent, timeout):
        if agent['runtime'] == 'grok' and self.grok_source is not None:
            return self._grok(agent, timeout)
        if agent['runtime'] != 'codex':
            raise ValueError('runtime observation is not configured')
        from .a2a_identity import RuntimeIdentity
        from .process import process_identity
        from .shared_app_server import SharedAppServerReader, locate_shared_endpoint
        deadline = self.monotonic() + timeout
        def remaining():
            value = deadline - self.monotonic()
            if value <= 0:
                raise TimeoutError('observation deadline reached')
            return value
        expected = agent['process']
        before = process_identity(expected['pid'])
        if not before:
            raise ValueError('process unavailable')
        process = dict(pid=expected['pid'], start_ticks=before['start_time_ticks'], boot_id=before['boot_id'])
        if process != expected:
            raise ValueError('process generation changed')
        endpoint = locate_shared_endpoint(timeout=remaining()) if self.endpoint == 'unix://' else self.endpoint
        with SharedAppServerReader(endpoint, timeout=remaining()) as reader:
            thread = reader.read_thread(agent['conversation_id'])
            identity = RuntimeIdentity.from_metadata(thread, reader.server_metadata)
            repeated = reader.read_thread(agent['conversation_id'])
            if RuntimeIdentity.from_metadata(repeated, reader.server_metadata) != identity:
                raise ValueError('runtime identity changed')
        if process_identity(expected['pid']) != before:
            raise ValueError('process changed during observation')
        remaining()
        status = repeated.get('status')
        state, reason = 'unknown', 'unsupported_native_status'
        if type(status) is dict:
            kind = status.get('type')
            flags = status.get('activeFlags', None if kind == 'active' else [])
            if type(flags) is list and all(type(flag) is str for flag in flags):
                if kind == 'idle' and not flags:
                    state, reason = 'ready', 'native_idle'
                elif kind == 'active' and not flags:
                    state, reason = 'working', 'native_active'
                elif (kind == 'active' and flags
                      and set(flags) <= {'waitingOnApproval', 'waitingOnUserInput'}):
                    state, reason = 'awaiting-human', 'native_waiting_for_human'
                elif kind == 'notLoaded' and not flags:
                    state, reason = 'disconnected', 'native_not_loaded'
        return StateEvidence('codex', identity.namespace, identity.thread_id, identity.cwd,
                             process, self.now(), state, 'native_metadata', reason)


    def _grok(self, agent, timeout):
        from .grok_runtime import GrokRuntimeAdapter
        from .runtime_delivery import RuntimeRecipient
        deadline = self.monotonic() + timeout
        runtime, binding_id, binding_sha256 = self.grok_source(timeout)
        identity, binding = runtime.resolve(binding_id, binding_sha256)
        observation = GrokRuntimeAdapter(runtime.host).observe(RuntimeRecipient('grok', identity.thread_id, binding))
        if self.monotonic() >= deadline:
            raise TimeoutError('observation deadline reached')
        process = {key: binding[key] for key in ('pid', 'start_ticks', 'boot_id')}
        return StateEvidence('grok', identity.namespace, identity.thread_id, identity.cwd, process,
                             self.now(), 'ready' if observation.state == 'ready' else 'unknown',
                             'host_bound_runtime', observation.reason)


def grok_state_source(runtime_root, binding_id, binding_sha256):
    """Bind host configuration to an independently deadline-bounded read-only host."""
    def source(timeout):
        from .grok_terminal import GrokTerminalHost
        from .runtime_a2a import GrokMailboxRuntime
        host = GrokTerminalHost(runtime_root, deadline=time.monotonic() + timeout)
        return GrokMailboxRuntime(runtime_root, host=host), binding_id, binding_sha256
    return source


def grok_source_from_actor(bus_root, capability):
    from .a2a_bus import BusStore, read_capability
    from .runtime_a2a import GrokMailboxRuntime
    bus = BusStore(bus_root)
    runtime = GrokMailboxRuntime.from_actor(bus, capability)
    actor_id = read_capability(capability)['actor_id']
    profile = read_capability(bus.root / 'runtime-actors' / (actor_id + '.json'))
    return grok_state_source(runtime.root, profile['binding_id'], profile['binding_sha256'])
