import json
import pytest
from codex_wake.attention_queue import AttentionQueue, AttentionError, fingerprint
from codex_wake.session_permissions import Principal


def context(**changes):
    value = dict(owner='agent-one', operation_id='operation-one', attempt=1,
        task_id='task-one', allocation_id='allocation-one', runtime='codex',
        conversation_id='thread-one', account='account-one', target='thread-one',
        action='refresh.self', effect_scope='connection', policy_root='/policy',
        policy_revision=1, operation_state='blocked')
    return dict(value, **changes)


def request(store, **changes):
    value = dict(key='key-one', kind='decision', question='Continue?',
        options=['accept','decline'], evidence=['receipt:one'], priority='normal',
        expires_at=200, context=context(), permission_decision=False)
    value.update(changes)
    return store.request(Principal('agent-one',tasks=('task-one',)), value)


def test_restart_response_consumption_and_replay(tmp_path):
    store = AttentionQueue(tmp_path, now=lambda:100, context_validator=lambda row: context())
    row = request(store)
    store = AttentionQueue(tmp_path, now=lambda:110, context_validator=lambda row: context())
    assert store.inspect(Principal('agent-one'), row['request_id'])['status'] == 'open'
    responded = store.respond(Principal('operator','operator'), row['request_id'], 'accept',
        expected_revision=1, expected_fingerprint=row['fingerprint'])
    assert responded['status'] == 'responded'
    result = store.consume(Principal('agent-one'), row['request_id'], expected_revision=2,
        expected_fingerprint=row['fingerprint'])
    assert result['status'] == 'consumed'
    assert result['executes_operation'] is False
    with pytest.raises(AttentionError):
        store.consume(Principal('agent-one'), row['request_id'], expected_revision=2,
            expected_fingerprint=row['fingerprint'])
    assert len(store.inspect(Principal('agent-one'), row['request_id'])['history']) == 3


@pytest.mark.parametrize('change', [dict(account='other'),dict(attempt=2),dict(target='other'),
    dict(policy_revision=2),dict(operation_state='submitted_unknown')])
def test_stale_context_refuses_response(tmp_path,change):
    live = context()
    store = AttentionQueue(tmp_path, now=lambda:100, context_validator=lambda row:live)
    row = request(store)
    live.update(change)
    with pytest.raises(AttentionError):
        store.respond(Principal('operator','operator'),row['request_id'],'accept',
            expected_revision=1,expected_fingerprint=row['fingerprint'])
    assert store.inspect(Principal('agent-one'),row['request_id'])['status']=='open'


def test_dedup_notice_and_corruption_retention(tmp_path):
    store=AttentionQueue(tmp_path,now=lambda:100,context_validator=lambda row:context())
    row=request(store)
    assert request(store)['request_id']==row['request_id']
    with pytest.raises(AttentionError):request(store,question='Changed?')
    notice=request(store,key='notice',kind='notice',options=['acknowledge'])
    store.respond(Principal('operator','operator'),notice['request_id'],'acknowledge',
        expected_revision=1,expected_fingerprint=notice['fingerprint'])
    with pytest.raises(AttentionError):
        store.consume(Principal('agent-one'),notice['request_id'],expected_revision=2,
            expected_fingerprint=notice['fingerprint'])
    raw='{"version":999,"requests":[]}'
    store.path.write_text(raw)
    with pytest.raises(AttentionError):store.inspect(Principal('agent-one'))
    assert store.path.read_text()==raw


def test_owner_operator_expiry_and_validator_required(tmp_path):
    store=AttentionQueue(tmp_path,now=lambda:100,context_validator=lambda row:context())
    row=request(store)
    for principal in (Principal('agent-one'),Principal('other')):
        with pytest.raises(AttentionError):
            store.respond(principal,row['request_id'],'accept',expected_revision=1,
                expected_fingerprint=row['fingerprint'])
    with pytest.raises(AttentionError):store.inspect(Principal('other'),row['request_id'])
    store.now=lambda:200
    with pytest.raises(AttentionError):
        store.respond(Principal('operator','operator'),row['request_id'],'accept',
            expected_revision=1,expected_fingerprint=row['fingerprint'])
    store.now=lambda:100
    store.context_validator=None
    store.respond(Principal('operator','operator'),row['request_id'],'accept',
        expected_revision=1,expected_fingerprint=row['fingerprint'])
    with pytest.raises(AttentionError):
        store.consume(Principal('agent-one'),row['request_id'],expected_revision=2,
            expected_fingerprint=row['fingerprint'])


@pytest.mark.parametrize('change',[dict(account='changed'),dict(attempt=2),dict(policy_revision=2),dict(operation_state='submitted_unknown')])
def test_recorded_response_never_bypasses_current_operation(tmp_path,change):
    store=AttentionQueue(tmp_path,now=lambda:100)
    row=request(store)
    store.respond(Principal('operator','operator'),row['request_id'],'accept',
        expected_revision=1,expected_fingerprint=row['fingerprint'])
    store.context_validator=lambda row:context(**change)
    with pytest.raises(AttentionError):
        store.consume(Principal('agent-one'),row['request_id'],expected_revision=2,
            expected_fingerprint=row['fingerprint'])
    assert store.inspect(Principal('agent-one'),row['request_id'])['status']=='responded'


def test_permission_decision_reuses_existing_grant_and_policy_change_fences(tmp_path):
    from codex_wake.session_permissions import PermissionStore
    operator=Principal('operator','operator')
    permission=PermissionStore(tmp_path)
    policy={'version':1,'global':{'actions':{'attention.respond':'allow','refresh.self':'approval_required'}},
        'approvals':[dict(id='operation-one',action='enforcement.increase',subject='agent-one',target='thread-one',
            scope='operation',task_id='task-one',expires_at='2099-01-01T00:00:00Z',issuer='operator')]}
    permission.configure(policy,operator,expected_revision=0)
    live=context(policy_root=str(tmp_path),action='enforcement.increase')
    store=AttentionQueue(tmp_path,now=lambda:100,context_validator=lambda row:live)
    row=request(store,context=live,permission_decision=True)
    with pytest.raises(AttentionError):
        store.respond(operator,row['request_id'],'accept',expected_revision=1,expected_fingerprint=row['fingerprint'])
    store.respond(operator,row['request_id'],'accept',expected_revision=1,
        expected_fingerprint=row['fingerprint'],approval_id='operation-one')
    assert len(permission._read()['policy']['approvals'])==1
    permission.configure(policy,operator,expected_revision=1)
    with pytest.raises(AttentionError):
        store.consume(Principal('agent-one',tasks=('task-one',)),row['request_id'],expected_revision=2,
            expected_fingerprint=row['fingerprint'])


def test_malformed_response_is_held_without_rewriting(tmp_path):
    store=AttentionQueue(tmp_path,now=lambda:100)
    row=request(store)
    store.respond(Principal('operator','operator'),row['request_id'],'accept',
        expected_revision=1,expected_fingerprint=row['fingerprint'])
    state=json.loads(store.path.read_text())
    state['requests'][0]['response']['choice']='launch-another-task'
    raw=json.dumps(state);store.path.write_text(raw)
    with pytest.raises(AttentionError):store.inspect(Principal('agent-one'))
    assert store.path.read_text()==raw
