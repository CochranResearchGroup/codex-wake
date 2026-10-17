"""Public accounting contract using sanitized 0.163 rollout shapes."""
import json

from codex_wake.goal_usage import observe_usage

START = '2026-10-16T22:00:00Z'
CREATED = 1792188000


def row(kind, payload, timestamp=START):
    return dict(type=kind, timestamp=timestamp, payload=payload)


def event(kind, **payload):
    return row('event_msg', dict(type=kind, **payload))


def response(thread, turn, response_id, total, root_turn=None):
    return row('token_usage_record', dict(thread_id=thread, turn_id=turn,
        session_id='root', root_turn_id=root_turn or turn, response_id=response_id,
        usage=dict(input_tokens=total-2, cached_input_tokens=total-3,
                   output_tokens=2, total_tokens=total),
        turn_token_usage={}, thread_token_usage={}))


def rollout(home, thread, rows, **meta):
    path=home/'sessions'/f'rollout-{thread}.jsonl'
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text('\n'.join(json.dumps(x) for x in [row('session_meta',
        dict(id=thread,session_id='root',source='cli',**meta))]+rows)+'\n')
    return path


def goal():
    return event('thread_goal_updated',threadId='root',goal=dict(
        threadId='root',createdAt=CREATED,status='active',tokensUsed=0))


def test_goal_start_counts_response_usage_including_cache(tmp_path):
    rollout(tmp_path,'root',[response('root','before','old',100),goal(),
        event('task_started',turn_id='work'),response('root','work','new',40),
        event('task_complete',turn_id='work')])
    result=observe_usage(tmp_path,'root',CREATED)
    assert result['state']=='qualified'
    assert result['used_tokens']==40
    assert result['sampled'] is True


def test_child_inherited_parent_records_not_double_charged(tmp_path):
    inherited=response('root','before','old',100)
    rollout(tmp_path,'root',[inherited,goal(),event('task_started',turn_id='work'),
        event('collab_agent_spawn_end',call_id='spawn',sender_thread_id='root',new_thread_id='child'),
        response('root','work','parent',40)])
    rollout(tmp_path,'child',[inherited,response('child','child-work','child-response',20,'work')],
            parent_thread_id='root',source_override='unused')
    result=observe_usage(tmp_path,'root',CREATED)
    assert result['state']=='qualified'
    assert result['used_tokens']==60


def test_reset_excludes_verified_snapshot_without_goal_reset(tmp_path):
    path=rollout(tmp_path,'root',[goal(),event('task_started',turn_id='work'),
        response('root','work','first',40),event('task_complete',turn_id='work')])
    baseline=observe_usage(tmp_path,'root',CREATED)['anchor']
    with path.open('a') as stream:
        for item in [event('task_started',turn_id='later'),response('root','later','second',25)]:
            stream.write(json.dumps(item)+'\n')
    assert observe_usage(tmp_path,'root',CREATED)['used_tokens']==65
    assert observe_usage(tmp_path,'root',CREATED,reset_anchor=baseline)['used_tokens']==25


def test_goal_creation_inside_active_turn_is_unknown(tmp_path):
    rollout(tmp_path,'root',[event('task_started',turn_id='ambiguous'),goal(),
        response('root','ambiguous','spanning',40)])
    assert observe_usage(tmp_path,'root',CREATED)['state']=='unknown'


def test_incomplete_or_unattributed_usage_never_becomes_known_zero(tmp_path):
    path=rollout(tmp_path,'root',[goal(),event('task_started',turn_id='work'),
        event('raw_response_completed',response_id='missing',token_usage={'total_tokens':10})])
    assert observe_usage(tmp_path,'root',CREATED)['state']=='unknown'
    path.write_text(path.read_text()+json.dumps(response('root','unowned','missing',10))+'\n')
    assert observe_usage(tmp_path,'root',CREATED)['state']=='unknown'


def test_missing_descendant_or_referenced_history_holds(tmp_path):
    path=rollout(tmp_path,'root',[goal(),event('task_started',turn_id='work'),
        response('root','work','r',40),event('collab_agent_spawn_end',new_thread_id='missing')])
    assert observe_usage(tmp_path,'root',CREATED)['state']=='unknown'
    rollout(tmp_path,'root',[goal()],history_base=dict(thread_id='missing',end_ordinal_exclusive=3,end_byte_offset=300))
    assert observe_usage(tmp_path,'root',CREATED)['state']=='unknown'


def test_replacement_goal_does_not_reset_and_anchor_tampering_holds(tmp_path):
    path=rollout(tmp_path,'root',[goal(),event('task_started',turn_id='one'),
        response('root','one','r1',40),event('task_complete',turn_id='one')])
    baseline=observe_usage(tmp_path,'root',CREATED)['anchor']
    with path.open('a') as stream:
        replacement=goal();replacement['payload']['goal']['createdAt']=CREATED+1
        for item in [replacement,event('task_started',turn_id='two'),
                     response('root','two','r2',25)]:
            stream.write(json.dumps(item)+'\n')
    assert observe_usage(tmp_path,'root',CREATED)['used_tokens']==65
    assert observe_usage(tmp_path,'root',CREATED,reset_anchor=baseline)['used_tokens']==25
    baseline['response_hashes']={}
    assert observe_usage(tmp_path,'root',CREATED,reset_anchor=baseline)['state']=='unknown'


def test_response_conflicts_and_truncated_json_hold(tmp_path):
    first=response('root','work','r1',40)
    path=rollout(tmp_path,'root',[goal(),event('task_started',turn_id='work'),first,
        response('root','work','r1',41)])
    assert observe_usage(tmp_path,'root',CREATED)['state']=='unknown'
    path.write_text(path.read_text()+'{"type":')
    assert observe_usage(tmp_path,'root',CREATED)['state']=='unknown'


def test_completed_response_has_matching_usage_record(tmp_path):
    record=response('root','work','r1',40)
    rollout(tmp_path,'root',[goal(),event('task_started',turn_id='work'),
        event('raw_response_completed',response_id='r1',token_usage=record['payload']['usage']),record])
    assert observe_usage(tmp_path,'root',CREATED)['used_tokens']==40


def test_wrong_goal_identity_is_not_an_accounting_boundary(tmp_path):
    boundary=goal();boundary['payload']['goal']['threadId']='other'
    rollout(tmp_path,'root',[boundary])
    assert observe_usage(tmp_path,'root',CREATED)['state']=='unknown'
