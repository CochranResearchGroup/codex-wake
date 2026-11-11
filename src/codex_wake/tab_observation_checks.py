"""Bounded independent responsiveness and visible-error schedules.

Only already classified, redacted traits enter this cache. Callbacks own exact
protocol and capture privacy; scheduling never upgrades missing evidence.
"""
from copy import deepcopy
import math
import time


class TieredChecks:
    def __init__(self, *, monotonic=time.monotonic, max_entries=1024):
        self.monotonic=monotonic
        self.max_entries=max(1,min(4096,int(max_entries)))
        self.enabled={'health':True,'errors':True}
        self.intervals={'health':60.0,'errors':5.0}
        self._entries={}
        self._counts={'health':0,'errors':0}

    def configure(self, *, health=True, errors=True, health_interval=60, error_interval=5):
        for value,minimum in ((health_interval,60),(error_interval,5)):
            if type(value) not in (int,float) or not math.isfinite(value) or value < minimum:
                raise ValueError('health_interval must be >=60 and error_interval >=5 seconds')
        if type(health) is not bool or type(errors) is not bool:
            raise ValueError('check switches must be booleans')
        self.enabled=dict(health=health,errors=errors)
        self.intervals=dict(health=float(health_interval),errors=float(error_interval))

    def is_due(self, kind, key, *, force=False, eligible=True):
        if kind not in self.enabled:
            raise ValueError('unknown observation tier')
        if not self.enabled[kind]:
            return False
        entry=self._entries.get((kind,key))
        interval=self.intervals[kind] if eligible or kind=='health' else max(60,self.intervals[kind])
        return force or entry is None or self.monotonic()>=entry[0]+interval

    def run(self, kind, key, callback, *, force=False, eligible=True):
        if kind not in self.enabled:
            raise ValueError('unknown observation tier')
        if not self.enabled[kind]:
            return dict(value='unknown',status='unknown',source='none',observed_at=None,
                        freshness='unknown',reason='check_disabled')
        now=self.monotonic(); entry=self._entries.get((kind,key))
        if not self.is_due(kind,key,force=force,eligible=eligible):
            return deepcopy(entry[1])
        result=deepcopy(callback())
        if kind=='errors':
            # Even fixture/privacy-safe transports cannot persist literal screen text.
            if 'message' in result:
                result['message']='Terminal error (content redacted)'
            if result.get('value')=='unknown' and entry:
                previous=entry[1]
                retained=previous.get('last_observation',previous)
                if retained.get('value')=='present':
                    result['last_observation']={name:deepcopy(retained[name]) for name in
                        ('value','status','source','observed_at','message','location','reason','confidence') if name in retained}

        if result.get('reason')=='observation_deadline':
            # A deferred check did not contact its source; do not consume cadence.
            return result
        self._counts[kind]+=1
        if len(self._entries)>=self.max_entries and (kind,key) not in self._entries:
            self._entries.pop(next(iter(self._entries)))
        self._entries[(kind,key)]=(now,deepcopy(result))
        return result

    def invalidate(self):
        self._entries.clear()

    def status(self):
        return dict(enabled=dict(self.enabled),intervals=dict(self.intervals),
                    retained_checks=len(self._entries),checks=dict(self._counts))
