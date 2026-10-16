"""Lifecycle-owned binding of an objective to one dedicated executor service."""
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import time
import tomllib
from uuid import uuid4

from .host_execution import SystemdExecution
from .records import WakeError,parse_timestamp


def location(root, objective_id):
    return Path(root).resolve()/'strict-execution'/hashlib.sha256(objective_id.encode()).hexdigest()[:24]


def _private(path, directory=False):
    info=path.lstat()
    if path.is_symlink() or info.st_uid!=os.geteuid() or stat.S_IMODE(info.st_mode)&0o077:
        raise WakeError('strict execution paths must be private and owned')
    if directory and not path.is_dir():raise WakeError('strict execution directory unavailable')


def _save(path,value):
    from .agent_lifecycle import save
    save(path,value)


@contextmanager
def _lock(directory):
    directory.mkdir(parents=True,mode=0o700,exist_ok=True)
    _private(directory,True)
    descriptor=os.open(directory/'binding.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    with os.fdopen(descriptor,'a') as stream:
        fcntl.flock(stream,fcntl.LOCK_EX)
        yield


def read_execution(root, objective_id):
    directory=location(root,objective_id);path=directory/'binding.json'
    if not path.exists():return None
    _private(directory,True);_private(path)
    binding=json.loads(path.read_text())
    if binding.get('objective_id')!=objective_id:raise WakeError('strict execution objective binding changed')
    guard=directory/'status.json'
    if guard.exists():
        _private(guard)
        observed=json.loads(guard.read_text())
        if observed.get('generation')==binding.get('generation'):binding['guard']=observed
    if binding.get('identity'):
        binding['host']=SystemdExecution().inspect(binding['identity'])
        if not binding['host']['populated']:
            binding['state']='stopped'
            binding['reason']=binding.get('guard',{}).get('reason','executor_exited')
    return binding


def ensure_execution(root,receipt):
    """Reserve precedes this call; no shared server is adopted or replaced."""
    from .lifecycle_budget import objective_identity,configured_ledger,trusted_upper
    profile=receipt['intent']['launch'];cfg=receipt['intent']['configuration']
    policy=receipt['intent']['continuation'];objective=objective_identity(policy)
    directory=location(root,objective)
    if 'strict_execution' not in cfg:return
    with _lock(directory):
        path=directory/'binding.json'
        old=read_execution(root,objective)
        if old:
            if old['configuration_revision']!=cfg['revision']:
                # Renewal must already be recorded by the existing operator-only ledger API.
                ledger=configured_ledger(root,receipt).inspect(now=trusted_upper())
                if old.get('host',{}).get('populated') or ledger['revision']!=cfg['revision']:
                    raise WakeError('strict execution renewal requires settled prior execution and ledger authorization')
            elif old.get('state')=='running' and old.get('guard',{}).get('state')!='stopped':
                receipt['strict_execution']=old
                return
            else:
                raise WakeError('strict execution is fenced; explicit operator renewal required')
        home=Path(profile.get('codex_home','')).absolute()
        expected=directory/'home'
        endpoint='unix://'+str(directory/'app-server.sock')
        if home!=expected or profile['app_server']!=endpoint:
            raise WakeError('strict execution requires its objective-owned home and endpoint: '+str(directory))
        _private(home,True)
        if not Path(profile['codex_path']).is_absolute() or not Path(profile['codex_path']).is_file():
            raise WakeError('strict execution requires an absolute available Codex executable')
        settings=home/'config.toml'
        if settings.exists():
            # Do not expose or copy configuration contents into receipts.
            _private(settings)
            parsed=tomllib.loads(settings.read_text())
            if parsed.get('mcp_servers') or parsed.get('hooks'):
                raise WakeError('strict execution refuses unqualified external MCP or hook services')
        if not old and (directory/'app-server.sock').exists():
            raise WakeError('strict execution refuses an existing unowned endpoint')
        if not old and (home/'sessions').exists() and any((home/'sessions').rglob('*.jsonl')):
            raise WakeError('strict execution refuses a home containing unowned conversations')
        if not hasattr(time,'CLOCK_BOOTTIME') or not Path('/sys/fs/cgroup/cgroup.controllers').is_file():
            raise WakeError('strict execution requires Linux cgroup-v2 and suspend-aware BOOTTIME')
        upper=trusted_upper();limits=cfg['strict_execution']['limits']
        deadline=parse_timestamp(cfg['objective_deadline']).timestamp()
        remaining=deadline-upper-limits['stop_grace_seconds']
        if remaining<=limits['checkpoint_grace_seconds']:raise WakeError('strict execution deadline exhausted')
        generation=uuid4().hex
        binding=dict(state='preparing',objective_id=objective,generation=generation,
            configuration_revision=cfg['revision'],unit='codex-wake-objective-'+generation+'.service',
            coverage=cfg['strict_execution']['coverage'],exclusions=cfg['strict_execution']['exclusions'],
            prior_execution=old,identity=None)
        _save(path,binding)
        guard_config=dict(wake_root=str(Path(root).resolve()),objective_id=objective,endpoint=endpoint,
            codex_home=str(home),argv=[profile['codex_path'],'app-server','--listen',endpoint],cwd=profile['cwd'],
            configuration=cfg,started_upper=upper,started_boottime=time.clock_gettime(time.CLOCK_BOOTTIME),
            boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),deadline=deadline,
            status_path=str(directory/'status.json'),generation=generation)
        config_path=directory/('guard-'+generation+'.json');_save(config_path,dict(state='configured',**guard_config))
        selected={key:limits[key] for key in ('memory_max_bytes','memory_swap_max_bytes','cpu_quota_percent','tasks_max','stop_grace_seconds')}
        environment=dict(CODEX_HOME=str(home),PYTHONPATH=str(Path(__file__).resolve().parents[1]))
        try:
            identity=SystemdExecution().launch(binding['unit'],[sys.executable,'-m','codex_wake.strict_executor',str(config_path)],
                cwd=str(Path(profile['cwd']).resolve()),environment=environment,limits=selected,runtime_seconds=remaining)
            binding.update(state='running',identity=identity)
            _save(path,binding)
        except Exception:
            binding.update(state='uncertain',reason='executor_launch_unverified');_save(path,binding)
            raise
        receipt['strict_execution']=binding
        until=time.monotonic()+profile['timeout']
        while time.monotonic()<until:
            if (directory/'app-server.sock').is_socket():
                from .native_protocol import native_request
                try:
                    native_request(endpoint,profile['codex_path'],'thread/list',{'limit':1},
                        min(2,max(.1,until-time.monotonic())))
                    return
                except Exception as exc:
                    binding['readiness_error']=type(exc).__name__+': '+str(exc)[:240]
                    _save(path,binding)
                    # Read-only readiness may be retried; thread/start may not.
            observed=read_execution(root,objective)
            if observed['state']=='stopped':raise WakeError('strict executor stopped during startup')
            time.sleep(.025)
        raise WakeError('strict executor endpoint not ready; reconcile existing binding')


def guard_execution(root,receipt):
    if not receipt.get('intent',{}).get('configuration',{}).get('strict_execution'):return True
    from .lifecycle_budget import objective_identity
    identity=objective_identity(receipt['intent']['continuation'])
    observed=read_execution(root,identity)
    receipt['strict_execution']=observed
    if not observed or observed['state']!='running' or observed.get('guard',{}).get('state')=='stopped':
        receipt.update(state='blocked',reason='strict_execution_not_running');return False
    return True


def stop_execution(root,objective_id,reason='operator_stop'):
    """An exact operator/root capability selects scope; invocation selects effect."""
    directory=location(root,objective_id)
    with _lock(directory):
        binding=read_execution(root,objective_id)
        if not binding:return dict(state='unsupported',reason='strict_execution_not_enrolled')
        if not binding.get('identity'):
            return dict(state='uncertain',reason='executor_launch_unverified',unit=binding['unit'])
        binding.update(state='stopping',reason=reason)
        _save(directory/'binding.json',binding)
        try:
            observed=SystemdExecution().stop(binding['identity'])
            binding.update(state='stopped',reason=reason,host=observed)
        except Exception as exc:
            binding.update(state='uncertain',reason='executor_stop_unverified',error=type(exc).__name__)
        _save(directory/'binding.json',binding)
        return binding


def execution_command(args,root):
    from .lifecycle_configuration import effective_configuration
    from .lifecycle_budget import objective_identity
    from .sessions_cli import emit
    try:
        config=json.loads(Path(args.profiles).read_text())
        effective=effective_configuration(config,args.thread_id,args.profile)
        if not effective.get('strict_execution'):raise WakeError('strict execution not configured')
        objective=objective_identity(config['continuations'][args.thread_id])
        observed=stop_execution(root,objective) if args.stop else read_execution(root,objective)
        value=dict(objective_id=objective,execution=observed,policy=effective['strict_execution'])
        emit(value,args.as_json)
        return 5 if observed and observed['state']=='uncertain' else 0
    except (OSError,ValueError,KeyError,RuntimeError,WakeError) as exc:
        emit(dict(error=dict(code='execution_unavailable',message=str(exc))),args.as_json)
        return 2


def resolve_executor_endpoint(endpoint):
    """Resolve Codex's alias only for a proven, still-owned strict executor.

    Ordinary explicit endpoints retain their no-symlink contract. A peer PID in
    the exact invocation's cgroup proves this alias is not a shared-server route.
    """
    import socket
    import struct
    path=Path(endpoint[7:])
    if not path.is_symlink():return endpoint
    directory=path.parent;root=directory.parent.parent
    if path.name!='app-server.sock' or not (directory/'binding.json').is_file():return endpoint
    try:
        _private(directory,True)
        binding_path=directory/'binding.json';_private(binding_path)
        binding=json.loads(binding_path.read_text())
        if (path.name!='app-server.sock' or directory!=location(root,binding['objective_id'])
                or binding['state']!='running' or path.lstat().st_uid!=os.geteuid()):
            raise ValueError('alias binding unavailable')
        target=path.resolve(strict=True);info=target.lstat()
        if info.st_uid!=os.geteuid() or not stat.S_ISSOCK(info.st_mode):
            raise ValueError('alias target unavailable')
        observed=SystemdExecution().inspect(binding['identity'])
        with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as peer:
            peer.settimeout(1);peer.connect(str(target))
            pid,uid,_=struct.unpack('3i',peer.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
        if uid!=os.geteuid() or pid not in observed['members']:
            raise ValueError('alias peer outside executor')
        return 'unix://'+str(target)
    except (OSError,KeyError,ValueError,RuntimeError,WakeError) as exc:
        raise WakeError('strict executor socket alias ownership unavailable') from exc
