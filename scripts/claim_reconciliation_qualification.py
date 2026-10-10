"""Opt-in installed claim observation; native metadata reads only, no turns sent."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import codex_wake
from codex_wake.a2a_bus import BusStore
from codex_wake.a2a_identity import BusError, RuntimeIdentity
from codex_wake.a2a_mailbox import Mailbox
from codex_wake.shared_app_server import SharedAppServerReader, locate_shared_endpoint


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--thread', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not Path(codex_wake.__file__).is_relative_to(Path(sys.prefix)):
        raise SystemExit('Use an immutable installed candidate with PYTHONPATH unset')
    endpoint = locate_shared_endpoint()
    with SharedAppServerReader(endpoint) as reader:
        identity = RuntimeIdentity.from_metadata(reader.read_thread(args.thread), reader.server_metadata)
    repo = Path(identity.cwd)
    cli = Path(sys.executable).with_name('codex-wake')
    env = dict(os.environ, CODEX_THREAD_ID=args.thread)
    env.pop('PYTHONPATH', None)
    count = lambda: len(list(Path('/proc/self/fd').iterdir()))
    report = dict(version=codex_wake.__version__, prefix=sys.prefix, thread=identity.thread_id,
                  namespace=identity.namespace, root=identity.cwd, fd_before=count(), checks=[],
                  notification_effects=0, business_task_effects=0,
                  clock_basis='fixed1000 setup; reconciliation time not observed')
    try:
        with tempfile.TemporaryDirectory(prefix='wake-claim-reconciliation-') as directory:
            root = Path(directory)
            bus, operator = BusStore.configure(root / 'bus')
            Mailbox.migrate(bus, operator)
            bus.enroll(repo, operator)
            sender = RuntimeIdentity('owned-fixture', 'sender', identity.cwd)
            caps = [bus.issue_actor(item, repo, operator)[0] for item in [sender, identity]]
            actors = [bus.authenticate(cap, item, invoking_cwd=repo) for cap, item in zip(caps, [sender, identity])]
            mailbox = Mailbox(bus, clock=lambda: 1000.0, monotonic=lambda: 1000.0)
            messages = []
            for key in ['unknown', 'completed']:
                identifier = mailbox.send(actors[0], identity, body='Disposable owned fixture',
                    idempotency_key=key, delivery='inbox')['message']['message_id']
                claim = mailbox.ack(actors[1], identifier, outcome='accepted')
                terminal = mailbox.ack(actors[1], identifier, outcome='completed') if key == 'completed' else None
                messages.append((identifier, claim, terminal))
            def command(identifier, cap, *, expected=0, cwd=repo, operator_mode=False):
                argv = [str(cli), 'messages', 'reconcile', identifier, '--bus-root', str(bus.root), '--json']
                argv += ['--as-operator', '--operator-capability', str(operator)] if operator_mode else ['--capability', str(cap), '--app-server', endpoint]
                completed = subprocess.run(argv, env=env, cwd=cwd, capture_output=True, text=True, timeout=10)
                value = json.loads(completed.stdout)
                if completed.returncode != expected:
                    raise RuntimeError(dict(code=completed.returncode, value=value))
                return value
            initial = command(messages[0][0], caps[1])
            assert initial['processing_reconciliation']['state'] == 'already_claimed'
            cap, _ = bus.rotate_actor(actors[1].actor_id, operator)
            current = bus.authenticate(cap, identity, invoking_cwd=repo)
            for identifier, claim, terminal in messages:
                value = command(identifier, cap)
                processing = value['processing_reconciliation']
                assert processing['state'] == ('known_terminal' if terminal else 'held_for_original_claim')
                assert processing['claim_receipt_id'] == claim['receipt_id']
                assert processing['owner_generation'] == 1 and processing['current_generation'] == 2
                assert not value['grants_new_processing'] and value['time_status'] == 'not_observed'
                assert 'Disposable owned fixture' not in json.dumps(value)
                if terminal:
                    assert processing['terminal_receipt_id'] == terminal['receipt_id']
                report['checks'].append(dict(message_id=identifier, processing=processing))
            for outcome in ['accepted', 'completed', 'failed', 'declined']:
                try:
                    mailbox.ack(current, messages[0][0], outcome=outcome)
                except BusError as error:
                    assert error.code == 'claim_fenced'
                else:
                    raise AssertionError('new generation acquired original claim')
            assert command(messages[0][0], caps[1], expected=7)['error']['code'] == 'authorization_denied'
            assert command(messages[0][0], cap, expected=7, cwd=root)['error']['code'] == 'authorization_denied'
            inspected = command(messages[0][0], cap, operator_mode=True)
            assert inspected['receipt_id'] and not inspected['grants_new_processing']
            report['checks'].append('stale capability/wrong invoking root refused; operator audit committed; no new start')
        report.update(fd_after=count(), children=Path('/proc/self/task/' + str(os.getpid()) + '/children').read_text().strip(), owned_root_removed=not root.exists())
        assert report['fd_after'] <= report['fd_before'] + 2 and not report['children'] and report['owned_root_removed']
        report['status'] = 'PASS'
    except Exception as error:
        report.update(status='FAIL', error=str(error))
        raise
    finally:
        args.output.write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
