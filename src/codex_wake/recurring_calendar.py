"""Explicit local-clock cadence over the host's IANA timezone database."""
from datetime import datetime, timedelta, timezone
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .network_wakes import precise_deadline
from .records import WakeError

FIELDS = {'kind', 'times', 'timezone', 'start_at', 'gap_policy', 'fold_policy'}


def validate_cadence(cadence):
    if not isinstance(cadence, dict) or set(cadence) != FIELDS or cadence.get('kind') != 'clock':
        raise WakeError('explicit_clock_fields_required')
    times = cadence['times']
    if (not isinstance(times, list) or not 1 <= len(times) <= 1440
            or any(not isinstance(value, str) or re.fullmatch(r'(?:[01][0-9]|2[0-3]):[0-5][0-9]', value) is None for value in times)
            or len(set(times)) != len(times)):
        raise WakeError('invalid_clock_times')
    if not isinstance(cadence['timezone'], str) or not cadence['timezone']:
        raise WakeError('invalid_clock_timezone')
    try:
        ZoneInfo(cadence['timezone'])
    except (ZoneInfoNotFoundError, ValueError):
        raise WakeError('invalid_clock_timezone') from None
    precise_deadline(cadence['start_at'])
    if cadence['gap_policy'] not in ('skip', 'shift_forward'):
        raise WakeError('explicit_clock_gap_policy_required')
    if cadence['fold_policy'] not in ('first', 'second', 'both'):
        raise WakeError('explicit_clock_fold_policy_required')
    return cadence


def _instants(local, zone, cadence):
    result = set()
    for fold in (0, 1):
        utc = local.replace(tzinfo=zone, fold=fold).astimezone(timezone.utc)
        if utc.astimezone(zone).replace(tzinfo=None) == local:
            result.add(utc)
    if not result and cadence['gap_policy'] == 'shift_forward':
        # Round-trip the pre-transition offset: 02:30 in a one-hour gap becomes
        # 03:30, preserving its position within the skipped interval.
        for fold in (0, 1):
            utc = local.replace(tzinfo=zone, fold=fold).astimezone(timezone.utc)
            if utc.astimezone(zone).replace(tzinfo=None) > local:
                result.add(utc)
    ordered = sorted(result)
    if cadence["fold_policy"] == "both":
        return ordered
    return ordered[-1:] if cadence["fold_policy"] == "second" else ordered[:1]


def _after(cadence, lower, *, inclusive):
    zone = ZoneInfo(cadence['timezone'])
    start = precise_deadline(cadence['start_at']).astimezone(timezone.utc)
    day = max(lower, start).astimezone(zone).date()
    if day.toordinal() > 1:
        day -= timedelta(days=1)
    while True:
        candidates = set()
        # Include the next local date before choosing: an explicit forward gap
        # shift may cross midnight, and must not jump over an earlier clock time.
        dates = [day]
        if day.toordinal() < datetime.max.date().toordinal():
            dates.append(day + timedelta(days=1))
        for date in dates:
            for value in cadence['times']:
                hour, minute = map(int, value.split(':'))
                local = datetime(date.year, date.month, date.day, hour, minute)
                candidates.update(_instants(local, zone, cadence))
        for candidate in sorted(candidates):
            if candidate >= start and (candidate >= lower if inclusive else candidate > lower):
                return candidate.isoformat().replace('+00:00', 'Z')
        try:
            day += timedelta(days=1)
        except OverflowError:
            raise WakeError('clock_outside_supported_calendar') from None


def first_due(cadence):
    validate_cadence(cadence)
    return _after(cadence, precise_deadline(cadence['start_at']), inclusive=True)


def next_due(cadence, after):
    validate_cadence(cadence)
    return _after(cadence, precise_deadline(after), inclusive=False)
