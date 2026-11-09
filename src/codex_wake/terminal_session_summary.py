"""Bounded session summaries from the monitor's existing cached observations."""
from collections import Counter
from copy import deepcopy
from .tab_organization import digest


def _same_window(current, cached):
    if current.get('window_id') != cached.get('window_id'):
        return False
    keys = ('pane_id', 'pid', 'windows_creation_filetime')
    return bool(current.get('panes')) and [tuple(p.get(k) for k in keys) for p in current['panes']] == [
        tuple(p.get(k) for k in keys) for p in cached.get('panes', [])]


def _generation_matches(snapshot, rows, generation):
    # tabs.list adds cached process birth metadata to native panes before hashing.
    # Reconstruct that representation without reading processes or probing traits.
    current = deepcopy(snapshot)
    for window in current.get('windows', []):
        cached = next((row.get('window', {}) for row in rows
                       if _same_window(window, row.get('window', {}))), {})
        for pane, old in zip(window.get('panes', []), cached.get('panes', [])):
            if 'process_generation' in old:
                pane['process_generation'] = old['process_generation']
    return generation == digest(current)


def summarize(root, records, aliases, tabs):
    """Do not create monitor state or perform any trait/native/provider probe."""
    snapshot = {}
    if (root / 'tab-monitor' / 'snapshot.json').is_file():
        from .tab_monitor import TabMonitor
        from .managed_inventory import InventoryError
        try:
            snapshot = TabMonitor(root).status().get('snapshot') or {}
        except (OSError, ValueError, InventoryError):
            pass
    resources = snapshot.get('resources', [])[:16384]
    for record in records:
        counts = {name: Counter() for name in ('health', 'activity', 'error')}
        windows = (record.get('snapshot') or {}).get('windows', [])
        stale = 0
        fresh_tabs = 0
        enrolled = [row for row in resources if row.get('target', {}).get('workspace') in aliases.get(record['id'], ())]
        generations = {row.get('target', {}).get('generation') for row in enrolled}
        valid_generations = {generation for generation in generations if _generation_matches(record.get('snapshot') or {}, enrolled, generation)}
        for window in windows:
            matches = [row for row in resources
                       if row.get('target', {}).get('workspace') in aliases.get(record['id'], ())
                       and row.get('target', {}).get('generation') in valid_generations
                       and row.get('target', {}).get('host') == tabs.host
                       and row.get('target', {}).get('environment') == tabs.environment
                       and row.get('target', {}).get('presentation') == record['backend']
                       and _same_window(window, row.get('window', {}))]
            # Conflicting/duplicate cache rows are not independent evidence.
            row = matches[0] if len(matches) == 1 else {}
            fresh = row.get('monitor_freshness') == 'fresh'
            stale += bool(row and not fresh)
            fresh_tabs += fresh
            for name, values in counts.items():
                trait = row.get('traits', {}).get('traits', {}).get(name, {})
                known = fresh and trait.get('status') == 'observed' and trait.get('freshness') == 'fresh'
                value = trait.get('value') if known else 'unknown'
                values[value if isinstance(value, str) else 'unknown'] += 1
        unavailable = any(row.get('workspace') in aliases.get(record['id'], ())
                          for row in snapshot.get('unavailable', []))
        freshness = ('unavailable' if record['state'] == 'unavailable' or unavailable else
                     'empty' if not windows else 'stale' if stale else
                     'fresh' if fresh_tabs == len(windows) else 'unknown')
        for name, values in counts.items():
            record[name + '_summary'] = dict(counts=dict(values), tab_count=record.get('tab_count'),
                                            freshness=freshness, stale_tabs=stale)
    return records


def format_summary(summary):
    if not isinstance(summary, dict):
        return str(summary or 'unobserved')
    counts = ', '.join(f'{key}={value}' for key, value in sorted(summary['counts'].items()))
    return (counts or summary['freshness']) + (f" ({summary['freshness']})" if counts else '')
