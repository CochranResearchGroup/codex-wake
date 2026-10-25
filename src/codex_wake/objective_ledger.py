"""Process-safe, cumulative objective accounting independent of session lifetime."""
from contextlib import contextmanager
from datetime import datetime
import fcntl
import hashlib
import json
import math
import os
import stat
from pathlib import Path
import tempfile


def _epoch(value):
    if isinstance(value, str):
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if parsed.tzinfo is None:
            raise ValueError('timestamp must include timezone')
        value = parsed.timestamp()
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError('trusted finite timestamp required')
    return value


def _count(value):
    if type(value) is not int or value < 0:
        raise ValueError('nonnegative integer required')
    return value


def _private(path, directory=False):
    info = path.lstat()
    expected = stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)
    if (not expected or info.st_uid != os.geteuid()
            or stat.S_IMODE(info.st_mode) != (0o700 if directory else 0o600)):
        raise ValueError('ledger paths must be owned and private without symlinks')


class ObjectiveLedger:
    _lock_flags = fcntl.LOCK_EX

    def __init__(self, root, objective_id):
        if not isinstance(objective_id, str) or not objective_id.strip():
            raise ValueError('objective identity required')
        root = Path(root).absolute()
        if root != root.resolve():
            raise ValueError('ledger root cannot traverse symlinks')
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        _private(root, directory=True)
        self.directory = root / 'objective-ledgers'
        self.directory.mkdir(exist_ok=True, mode=0o700)
        _private(self.directory, directory=True)
        name = hashlib.sha256(objective_id.encode()).hexdigest()
        self.path = self.directory / (name + '.json')
        self.lock_path = self.directory / (name + '.lock')
        self.objective_id = objective_id

    @contextmanager
    def _transaction(self, *, write=True):
        _private(self.directory, directory=True)
        fd = os.open(self.lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'a+') as lock:
            _private(self.lock_path)
            fcntl.flock(lock, self._lock_flags)
            if self.path.exists() or self.path.is_symlink():
                _private(self.path)
                data_fd = os.open(self.path, os.O_RDONLY | os.O_NOFOLLOW)
                with os.fdopen(data_fd) as source:
                    state = json.load(source)
            else:
                state = {}
            yield state
            if not write:
                return
            temp_fd, temp_path = tempfile.mkstemp(dir=self.directory)
            try:
                with os.fdopen(temp_fd, 'w') as target:
                    json.dump(state, target, sort_keys=True)
                    target.flush()
                    os.fsync(target.fileno())
                os.replace(temp_path, self.path)
                directory_fd = os.open(self.directory, os.O_RDONLY)
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
            finally:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

    @staticmethod
    def _configuration(configuration):
        result = json.loads(json.dumps(configuration))
        for key in ('objective_token_limit', 'objective_time_limit_seconds',
                    'session_token_limit', 'session_time_limit_seconds', 'max_correction_cycles'):
            _count(result[key])
        if not result.get('revision') or result['max_correction_cycles'] > 2:
            raise ValueError('configuration revision or correction bound invalid')
        started, deadline = _epoch(result['started_at']), _epoch(result['objective_deadline'])
        if deadline < started:
            raise ValueError('deadline precedes start')
        return result

    def _view(self, state, now, admitted=None):
        now = _epoch(now)
        if not state:
            raise ValueError('objective not configured')
        config = state['configuration']
        actors = state['actors']
        used = state['prior_tokens'] + sum(a['used'] for a in actors.values())
        reserved = sum(max(0, a['reservation'] - a['used']) for a in actors.values() if not a['settled'])
        known = all(a['known'] for a in actors.values())
        remaining = max(0, config['objective_token_limit'] - used - reserved)
        expired = max(now, state.get('observed_at', now)) >= _epoch(config['objective_deadline'])
        status = 'accounting_unknown' if not known else 'exhausted' if expired or remaining == 0 else 'ready'
        result = dict(config, objective_id=self.objective_id, tokens_used=used,
                      tokens_reserved=reserved, remaining_tokens=remaining,
                      accounting_known=known, state=status, ready=status == 'ready',
                      exhausted=expired or used + reserved >= config['objective_token_limit'],
                      original_deadline=state['original_deadline'],
                      correction_cycles=state['correction_cycles'],
                      goal_aliases=state.get('goal_aliases',{}),
                      request_binding=state.get('request_binding'),
                      request_sessions=state.get('request_sessions',{}),
                      authorization_history=state['authorization_history'],
                      remaining_seconds=max(0, _epoch(config['objective_deadline']) - max(now, state.get('observed_at', now))),
                      actors={key: dict(value, tokens_remaining=max(0, value['reservation'] - value['used']),
                                       session_deadline=value.get('session_deadline'))
                              for key, value in actors.items()})
        if admitted is not None:
            result['admitted'] = admitted
        return result

    @staticmethod
    def _observe(state, now):
        state['observed_at'] = max(_epoch(now), state.get('observed_at', _epoch(now)))

    def configure(self, configuration, approval, prior_tokens=0, *, now):
        config = self._configuration(configuration)
        if not approval:
            raise ValueError('explicit approval required')
        _count(prior_tokens)
        with self._transaction() as state:
            if state:
                if state['configuration'] != config:
                    raise ValueError('changed configuration requires explicit extension')
            else:
                state.update(configuration=config, original_deadline=config['objective_deadline'],
                             prior_tokens=prior_tokens, actors={}, correction_cycles=0,
                             authorization_history=[dict(action='initial', configuration=config, approval=approval, at=_epoch(now))])
            self._observe(state, now)
            return self._view(state, now)

    def view(self, *, now):
        with self._transaction() as state:
            self._observe(state, now)
            return self._view(state, now)

    def inspect(self, *, now):
        """Read current accounting and deadline without rewriting the ledger."""
        with self._transaction(write=False) as state:
            return self._view(state, now)

    def reserve(self, actor_id, tokens, seconds, *, now):
        _count(tokens)
        _count(seconds)
        if not actor_id:
            raise ValueError('actor identity required')
        with self._transaction() as state:
            self._observe(state, now)
            view = self._view(state, now)
            if state.get('request_binding'):raise ValueError('request transport owns accounting; lifecycle reservation refused')
            actor = state['actors'].get(actor_id)
            if actor and actor.get('terms') is not None:
                if actor['terms'] != [tokens, seconds]:
                    raise ValueError('reservation terms are immutable')
                return self._view(state, now, admitted=(view['accounting_known']
                    and view['tokens_used'] + view['tokens_reserved'] <= state['configuration']['objective_token_limit']
                    and not actor['settled']
                    and actor['reservation'] > actor['used']
                    and state['observed_at'] < min(actor['session_deadline'], _epoch(state['configuration']['objective_deadline']))))
            config = state['configuration']
            admitted = (view['ready'] and tokens <= view['remaining_tokens']
                        and tokens <= config['session_token_limit']
                        and seconds <= config['session_time_limit_seconds']
                        and state['observed_at'] + seconds <= _epoch(config['objective_deadline']))
            if admitted:
                if actor:
                    raise ValueError('observed actor cannot acquire a new reservation')
                state['actors'][actor_id] = dict(terms=[tokens, seconds], reservation=tokens,
                                                used=0, settled=False, known=True, session_deadline=state['observed_at'] + seconds)
            return self._view(state, now, admitted=admitted)

    def record(self, actor_id, cumulative_tokens, settled=False, *, now):
        return self._record(actor_id, cumulative_tokens, settled=settled, now=now)

    def record_sampled_floor(self, actor_id, cumulative_tokens, *, now):
        """Retain a later observed floor without asserting final accounting."""
        _count(cumulative_tokens)
        with self._transaction() as state:
            self._observe(state,now)
            self._view(state,now)
            if actor_id not in state['actors']:
                raise ValueError('sampled floor requires an enrolled actor')
            actor=state['actors'][actor_id]
            actor.update(used=max(actor['used'],cumulative_tokens),known=False,settled=False)
            return self._view(state,now)

    def record_goal(self, goal_id, cumulative_tokens, settled=False, *, now):
        return self._record(goal_id, cumulative_tokens, settled=settled, goal=True, now=now)

    def adopt_active_goal(self, goal_id, token_budget, deadline, *, now):
        """Reserve an observed native parent's unchanged session quota atomically."""
        _count(token_budget)
        with self._transaction() as state:
            self._observe(state,now)
            view=self._view(state,now)
            if state.get('request_binding'):raise ValueError('request transport owns accounting; native goal reservation refused')
            alias=state.get('goal_aliases',{}).get(goal_id)
            actor_id=alias['actor_id'] if alias else goal_id
            offset=alias['preflight_tokens'] if alias else 0
            actor=state['actors'].get(actor_id)
            quota=token_budget+offset
            if (quota<=0 or quota>state['configuration']['session_token_limit']
                    or not view['accounting_known'] or _epoch(deadline)<=state['observed_at']):
                return self._view(state,now,admitted=False)
            if actor and actor.get('terms') is not None:
                valid=(actor['reservation']==quota and not actor['settled'] and actor['known']
                       and actor['used']<quota and state['observed_at']<actor['session_deadline'])
                return self._view(state,now,admitted=valid)
            used=actor['used'] if actor else 0
            if quota-used>view['remaining_tokens'] or used>=quota:
                return self._view(state,now,admitted=False)
            state['actors'][actor_id]=dict(terms=[quota,'native-goal'],reservation=quota,
                used=used,known=True,settled=False,session_deadline=min(_epoch(deadline),_epoch(state['configuration']['objective_deadline'])))
            return self._view(state,now,admitted=True)

    def bind_goal(self, goal_id, actor_id, preflight_tokens, *, now):
        _count(preflight_tokens)
        with self._transaction() as state:
            self._observe(state, now)
            if state.get('request_binding'):raise ValueError('request transport owns accounting; native alias refused')
            actor = state['actors'][actor_id]
            if actor['used'] < preflight_tokens:
                raise ValueError('preflight accounting must precede goal binding')
            binding = dict(actor_id=actor_id, preflight_tokens=preflight_tokens)
            aliases = state.setdefault('goal_aliases', {})
            if goal_id in aliases and aliases[goal_id] != binding:
                raise ValueError('native goal accounting binding changed')
            aliases[goal_id] = binding
            return self._view(state, now)

    def _record(self, actor_id, cumulative_tokens, settled=False, *, goal=False, now):
        if not actor_id:
            raise ValueError('actor identity required')
        if cumulative_tokens is not None:
            _count(cumulative_tokens)
        with self._transaction() as state:
            self._observe(state, now)
            self._view(state, now)
            if state.get('request_binding'):raise ValueError('request transport owns accounting; sampled actor charge refused')
            if goal:
                binding = state.get('goal_aliases', {}).get(actor_id)
                if binding:
                    actor_id = binding['actor_id']
                    if cumulative_tokens is not None:
                        cumulative_tokens += binding['preflight_tokens']
            actor = state['actors'].setdefault(actor_id, dict(terms=None, reservation=0, used=0, settled=False, known=True))
            if cumulative_tokens is None or cumulative_tokens < actor['used']:
                actor['known'] = False
                actor['settled'] = False
            else:
                actor['used'] = cumulative_tokens
                actor['known'] = True
                actor['settled'] = actor['settled'] or bool(settled)
            return self._view(state, now)

    def bind_requests(self, binding, thread_prior_tokens, *, now):
        """Select one authoritative request transport without adding allowance.

        Migration from live lifecycle actors is deliberately unsupported. The
        imported prior charges remain in prior_tokens, with per-session floors.
        """
        with self._transaction() as state:
            self._view(state, now)
            if state.get('request_binding') == binding:
                return self._view(state, now)
            if state.get('request_binding') or state['actors'] or state.get('goal_aliases'):
                raise ValueError('request accounting requires explicit migration from existing actor accounting')
            if sum(_count(value) for value in thread_prior_tokens.values()) != state['prior_tokens']:
                raise ValueError('request binding must import all prior usage without reset')
            state['request_binding'] = binding
            config = state['configuration']
            state['request_sessions'] = {thread: dict(prior_tokens=value,
                deadline=min(_epoch(config['objective_deadline']), _epoch(config['started_at'])+config['session_time_limit_seconds']))
                for thread, value in thread_prior_tokens.items()}
            state['request_completions'] = {}
            return self._view(state, now)

    def register_request_thread(self, thread_id, parent_thread_id, provenance, *, now):
        with self._transaction() as state:
            self._view(state,now)
            if not state.get('request_binding') or parent_thread_id not in state['request_sessions']:
                raise ValueError('qualified parent request binding required')
            config=state['configuration']
            sessions=state['request_sessions']
            if thread_id not in sessions:
                sessions[thread_id]=dict(prior_tokens=0,parent_thread_id=parent_thread_id,provenance=provenance,
                    deadline=min(_epoch(config['objective_deadline']),_epoch(now)+config['session_time_limit_seconds']))
            elif sessions[thread_id].get('parent_thread_id')!=parent_thread_id:
                raise ValueError('request thread provenance changed')
            return self._view(state,now)

    def reserve_request(self, actor_id, thread_id, tokens, seconds, *, enforce=True, now):
        _count(tokens);_count(seconds)
        with self._transaction() as state:
            self._observe(state, now)
            view = self._view(state, now)
            if not state.get('request_binding') or not actor_id.startswith('request:'):
                raise ValueError('authoritative request binding required')
            if actor_id in state['actors']:
                raise ValueError('an admitted attempt cannot be forwarded twice')
            config = state['configuration']
            session = state['request_sessions'].setdefault(thread_id, dict(prior_tokens=0,
                deadline=min(_epoch(config['objective_deadline']), _epoch(now)+config['session_time_limit_seconds'])))
            used = session['prior_tokens'] + sum(max(a['used'], a['reservation']) if not a['settled'] else a['used']
                for a in state['actors'].values() if a.get('request_thread')==thread_id)
            admitted = not enforce or (view['ready'] and tokens<=view['remaining_tokens']
                and used+tokens<=config['session_token_limit'] and seconds<=config['session_time_limit_seconds']
                and state['observed_at']+seconds<=session['deadline'])
            if admitted:
                state['actors'][actor_id]=dict(terms=[tokens,seconds],reservation=tokens,used=0,
                    settled=False,known=True,session_deadline=session['deadline'],request_thread=thread_id)
            return self._view(state, now, admitted=admitted)

    def settle_request(self, actor_id, response_id, tokens, request_fingerprint, *, now):
        """Unknown completion retains the reservation; duplicate exact proof is inert."""
        if tokens is not None:_count(tokens)
        with self._transaction() as state:
            self._observe(state, now)
            self._view(state, now)
            actor = state['actors'][actor_id]
            if not state.get('request_binding') or not actor_id.startswith('request:'):
                raise ValueError('authoritative request binding required')
            prior = state['request_completions'].get(response_id) if response_id else None
            proof = dict(actor_id=actor_id,tokens=tokens,fingerprint=request_fingerprint)
            if prior == proof:
                return self._view(state, now)
            if (tokens is None or not response_id or prior is not None or actor['settled']
                    or (actor['reservation'] and tokens>actor['reservation'])):
                actor.update(known=False,settled=False)
                if tokens is not None:actor['used']=max(actor['used'],tokens)
            else:
                state['request_completions'][response_id]=proof
                actor.update(used=tokens,settled=True,known=True)
            return self._view(state, now)

    def correction(self, *, now, key=None, actor_id=None):
        with self._transaction() as state:
            self._observe(state, now)
            view = self._view(state, now)
            decisions = state.setdefault('correction_decisions', {})
            eligible = view['ready']
            if actor_id is not None:
                actor = state['actors'].get(actor_id, {})
                eligible = (view['accounting_known'] and actor.get('known') is True
                    and actor.get('settled') is False and actor.get('reservation', 0) > actor.get('used', 0)
                    and state['observed_at'] < min(actor.get('session_deadline', 0), _epoch(state['configuration']['objective_deadline']))
                    and view['tokens_used'] + view['tokens_reserved'] <= state['configuration']['objective_token_limit'])
            if key is not None and key in decisions:
                return self._view(state, now, admitted=decisions[key] and eligible)
            admitted = eligible and state['correction_cycles'] < state['configuration']['max_correction_cycles']
            if admitted:
                state['correction_cycles'] += 1
            if key is not None:
                decisions[key] = admitted
            return self._view(state, now, admitted=admitted)

    def extend(self, configuration, approval, *, now):
        return self._authorize(configuration, approval, 'extend', now=now)

    def reset(self, configuration, approval, *, now):
        """Replace caps explicitly; retain all usage, original time and cycle history."""
        return self._authorize(configuration, approval, 'reset', now=now)

    def _authorize(self, configuration, approval, action, *, now):
        config = self._configuration(configuration)
        if not approval:
            raise ValueError('explicit extension approval required')
        with self._transaction() as state:
            self._observe(state, now)
            self._view(state, now)
            previous = state['configuration']
            last = state['authorization_history'][-1]
            if (config == previous and last.get('action') == action
                    and last['approval'] == approval):
                return self._view(state, now)
            if (config['revision'] == previous['revision'] or config['started_at'] != previous['started_at']
                    or (action == 'extend' and (config['objective_token_limit'] < previous['objective_token_limit']
                    or _epoch(config['objective_deadline']) < _epoch(previous['objective_deadline'])))):
                raise ValueError('authorization must preserve origin and use a new revision')
            if action == 'reset' and any(not actor['settled'] or not actor['known']
                                        for actor in state['actors'].values()):
                raise ValueError('reset requires settled known actor accounting')
            state['configuration'] = config
            state['authorization_history'].append(dict(action=action, configuration=config, approval=approval, at=_epoch(now)))
            return self._view(state, now)
