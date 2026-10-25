import argparse
import json
import pytest
from codex_wake import attention_commands as commands
from codex_wake.attention_queue import AttentionError
from codex_wake.session_permissions import Principal
from test_attention_queue import context


def payload():
    return dict(key='one',kind='decision',question='Continue?',options=['accept','decline'],
        evidence=['receipt:one'],priority='normal',expires_at=200,context=context(),permission_decision=False)


def test_real_command_adapter_and_restart(tmp_path,capsys,monkeypatch):
    parser=argparse.ArgumentParser()
    commands.register_parser(parser.add_subparsers(dest='command'))
    principal=Principal('agent-one')
    monkeypatch.setattr(commands,'verified_cli_principal',lambda args:principal)
    file=tmp_path/'request.json'
    file.write_text(json.dumps(payload()))
    def run(words):
        args=parser.parse_args(words)
        code=commands.run(args,tmp_path/'wake',context_validator=lambda row:context(),now=lambda:100)
        return code,json.loads(capsys.readouterr().out)
    code,row=run(['attention','request','--file',str(file),'--bus-root',str(tmp_path)])
    assert code==0
    principal=Principal('operator','operator')
    code,response=run(['attention','respond','--request-id',row['request_id'],
        '--choice','accept','--expected-revision','1','--fingerprint',row['fingerprint'],
        '--bus-root',str(tmp_path)])
    assert code==0 and response['status']=='responded'
    principal=Principal('agent-one')
    code,result=run(['attention','consume','--request-id',row['request_id'],
        '--expected-revision','2','--fingerprint',row['fingerprint'],'--bus-root',str(tmp_path)])
    assert code==0 and result['executes_operation'] is False
    code,result=run(['attention','show','--request-id',row['request_id'],'--bus-root',str(tmp_path)])
    assert code==0 and result['status']=='consumed'


def test_mcp_response_and_role_arguments_cannot_self_approve(tmp_path):
    for action,args in [('respond',{}),('consume',{}),('close',{}),('request',{'operator':True}),('request',{'role':'operator'})]:
        with pytest.raises(AttentionError):
            commands.execute(action,args,tmp_path,principal=Principal('agent-one'),mcp=True)


def test_cli_request_without_host_validator_records_only(tmp_path,capsys,monkeypatch):
    monkeypatch.setattr(commands,'verified_cli_principal',lambda args:Principal('agent-one'))
    parser=argparse.ArgumentParser()
    commands.register_parser(parser.add_subparsers(dest='command'))
    file=tmp_path/'request.json'
    file.write_text(json.dumps(payload()))
    args=parser.parse_args(['attention','request','--file',str(file),'--bus-root',str(tmp_path)])
    assert commands.run(args,tmp_path/'wake',now=lambda:100)==0
    assert json.loads(capsys.readouterr().out)['status']=='open'


def test_real_operator_capability_cli_records_response_without_validator(tmp_path,capsys):
    from codex_wake.a2a_bus import BusStore
    bus,capability=BusStore.configure(tmp_path/'bus')
    parser=argparse.ArgumentParser()
    commands.register_parser(parser.add_subparsers(dest='command'))
    packet=payload()
    packet['context']=context(owner='local-operator')
    file=tmp_path/'request.json';file.write_text(json.dumps(packet))
    common=['--bus-root',str(bus.root),'--operator-capability',str(capability)]
    args=parser.parse_args(['attention','request','--file',str(file)]+common)
    assert commands.run(args,tmp_path/'wake',now=lambda:100)==0
    row=json.loads(capsys.readouterr().out)
    args=parser.parse_args(['attention','respond','--request-id',row['request_id'],
        '--choice','accept','--expected-revision','1','--fingerprint',row['fingerprint']]+common)
    assert commands.run(args,tmp_path/'wake',now=lambda:100)==0
    assert json.loads(capsys.readouterr().out)['status']=='responded'
