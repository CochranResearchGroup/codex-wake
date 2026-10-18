import json,tempfile,sys
from pathlib import Path
from unittest.mock import patch
from contextlib import redirect_stdout
from io import StringIO
from codex_wake.cli import run
from codex_wake.records import WakeError
caller='00000000-0000-7000-8000-000000000167'
with tempfile.TemporaryDirectory() as tmp:
 r=Path(tmp); home=r/'home';home.mkdir(mode=0o700);instruction=r/'instructions.md';instruction.write_text('Use the bounded approved task only.')
 limits=dict(memory_max_bytes=134217728,memory_swap_max_bytes=0,cpu_quota_percent=20,tasks_max=16,stop_grace_seconds=1,checkpoint_grace_seconds=1,poll_seconds=.2,accounting_max_age_seconds=2)
 cfg=dict(version=1,callers={caller:['strict-worker']},profiles={'strict-worker':dict(cwd=tmp,codex_home=str(home),codex_path=sys.executable,app_server='unix://'+tmp+'/not-started.sock',tmux_session='fixture',timeout=1,strict_execution=limits)},lifecycle_defaults=dict(handoff_writer=dict(name='writer',path=str(instruction)),preflight_reviewer=dict(name='reviewer',path=str(instruction)),session_token_limit=100,objective_token_limit=500,session_time_limit_seconds=60,objective_time_limit_seconds=120,max_correction_cycles=0),continuations={caller:dict(objective='bounded task',approval='fixture operator',started_at='2030-01-01T00:00:00Z')})
 profiles=r/'profiles.json';profiles.write_text(json.dumps(cfg)); error=None;output=StringIO()
 with patch('codex_wake.lifecycle_supervision.supervision_ready',return_value=True),patch('codex_wake.lifecycle_budget.trusted_upper',return_value=1893456001),patch('codex_wake.native_protocol.native_request',side_effect=WakeError('injected not-yet-created dedicated endpoint')) as request,patch('codex_wake.strict_runtime.ensure_execution') as launch,redirect_stdout(output):
  try:run(['--wake-root',str(r/'wake'),'sessions','spawn','--profiles',str(profiles),'--profile','strict-worker','--caller-thread-id',caller,'--intent','cold-start','--name','fixture','--task','bounded task','--expires-at','2030-01-01T00:02:00Z','--json'])
  except WakeError as e:error=str(e)
 assert request.call_count==1 and request.call_args.args[2]=='thread/goal/get'
 assert launch.call_count==0
 result=dict(surface='public CLI arguments emitted by MCP spawn',result='bootstrap gap reproduced',native_request_method=request.call_args.args[2],executor_creation_calls=launch.call_count,exception=error,qualification='Injected endpoint unavailability and monitor readiness; no native calls, services or model turns. Demonstrates ordering, not a native acceptance test.',runtime_effects=0)
 Path('docs/dev/evidence/plan0167/bootstrap-order.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
