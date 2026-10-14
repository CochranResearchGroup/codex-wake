"""Deterministic human-tab matching. Exact identities never use typo correction."""
import re


def normalized(value):
    return ' '.join(value.casefold().split())


def distance(left, right):
    # Bounded selector/name lengths cap cost; Levenshtein has no learned aliases.
    row = list(range(len(right) + 1))
    for i, a in enumerate(left, 1):
        following = [i]
        for j, b in enumerate(right, 1):
            following.append(min(following[-1] + 1, row[j] + 1, row[j-1] + (a != b)))
        row = following
    return row[-1]


def match_tabs(attachments, selector):
    from .sessions import SelectionError
    metadata = dict(selector=selector, normalized_selector=selector, match_method='exact', confidence=1.0)
    if selector.startswith(('pane:', 'window:', 'tab:')):
        key, value = selector.split(':', 1)
        field = {'pane': 'pane_id', 'window': 'window_id', 'tab': 'window_name'}[key]
        return [(r, p) for r, p in attachments if p[field] == value], metadata
    exact = [(r, p) for r, p in attachments if p['window_name'] == selector]
    if exact:
        return exact, metadata
    value = normalized(selector)
    value = re.sub(r'^tab\s+', '', value)
    metadata.update(normalized_selector=value, match_method='normalized')
    matches = [(r, p) for r, p in attachments if normalized(p['window_name']) == value]
    if matches:
        return matches, metadata
    parsed = re.fullmatch(r'(\d+)(?::\s*(.+?))?(?:\.(\d+))?', value)
    if parsed:
        index, name, pane = parsed.groups()
        selected = [(r, p) for r, p in attachments if p['window_index'] == str(int(index))]
        if name is not None and selected and not any(normalized(p['window_name']) == name for _, p in selected):
            error = SelectionError(3, 'tab index and name disagree', selector,
                                   sorted({p['window_index'] + ':' + p['window_name'] for _, p in selected}))
            error.condition = 'descriptor_conflict'
            raise error
        metadata['match_method'] = 'index'
        return [(r, p) for r, p in selected if (name is None or normalized(p['window_name']) == name)
                and (pane is None or p['pane_index'] == str(int(pane)))], metadata
    if len(value) < 4 or len(value) > 200 or ':' in value:
        return [], metadata
    names = {normalized(p['window_name']) for _, p in attachments if len(p['window_name']) <= 200}
    ranked = sorted((distance(value, name), name) for name in names)
    if not ranked:
        return [], metadata
    best, name = ranked[0]
    if best > (3 if len(value) >= 6 else 1) or best / max(len(value), len(name)) > .4:
        return [], metadata
    if len(ranked) > 1 and ranked[1][0] <= best + 1:
        error = SelectionError(4, 'tab spelling has multiple plausible matches', selector,
                               [n for d, n in ranked if d <= best + 1][:10])
        error.condition = 'ambiguous_target'
        raise error
    metadata.update(match_method='fuzzy', confidence=round(1 - best / max(len(value), len(name)), 3))
    return [(r, p) for r, p in attachments if normalized(p['window_name']) == name], metadata
