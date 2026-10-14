"""Evidence qualification; a reviewer verdict does not itself confer authority."""
import hashlib
from pathlib import Path


def instruction_read(thread, selection, workspace):
    """Require the selected bytes in a successful native instruction-read result."""
    return any(turn.get('status') == 'completed' and
        item.get('type') == 'commandExecution' and item.get('status') == 'completed' and
        item.get('exitCode') == 0 and item.get('cwd') == str(workspace.resolve()) and
        selection['path'] in item.get('command', '') and
        selection['instructions'] in (item.get('aggregatedOutput') or '')
        for turn in thread.get('turns', []) for item in turn.get('items', []))


def validate_work_review(review, policy, workspace, checkpoint):
    try:
        if (not isinstance(review['selected_review'], str) or not review['selected_review'].strip()
                or review['scope_deviations'] != [] or review['unsupported_claims'] != []
                or review['next_packet'] != checkpoint['next_packet']):
            return False
        for field in ('changes', 'unfinished_work'):
            if (not isinstance(review[field], list) or
                    any(not isinstance(item, str) or not item.strip() for item in review[field])):
                return False
        if not review['changes'] or not review['acceptance_progress']:
            return False
        for progress in review['acceptance_progress']:
            if (progress['criterion'] not in policy['acceptance_criteria']
                    or not isinstance(progress['change'], str) or not progress['change'].strip()
                    or not progress['evidence']):
                return False
            for evidence in progress['evidence']:
                path = (workspace / evidence['path']).resolve(strict=True)
                path.relative_to(workspace.resolve())
                if hashlib.sha256(path.read_bytes()).hexdigest() != evidence['sha256']:
                    return False
        return True
    except (KeyError, TypeError, ValueError, OSError):
        return False
