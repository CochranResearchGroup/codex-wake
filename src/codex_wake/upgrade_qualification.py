"""Exact-package installed qualification, distinct from fixture or auth evidence.

The executor runs inside its declared disposable environment. Remote launching
belongs to host configuration: a local process cannot attest a different WSL.
Only initialize/account/read RPCs are generated here. Pinned host acceptance
programs own capability journeys and must report observed model-request counts.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import selectors
import signal
import subprocess
import tempfile
import time

from codex_profiles.upgrades import _atomic

CAPABILITIES = frozenset(('scoped_reload','durable_notices','caller_accounting',
                         'orphan_output','tui_health'))
JOURNEYS = frozenset(('history_visibility','failed_start_recovery','compatible_rollback'))
PACKAGE_EXECUTABLES = ('bin/codex','bin/codex-code-mode-host','codex-resources/bwrap','codex-path/rg')


class QualificationError(ValueError):
    pass


class AuthenticationNeeded(QualificationError):
    pass


def content_hash(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):digest.update(chunk)
    return digest.hexdigest()


def object_hash(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def package_inventory(package):
    result={}
    for path in sorted(package.rglob('*')):
        if path.is_symlink():raise QualificationError('package links unsupported')
        if path.is_file():
            result[str(path.relative_to(package))]=dict(sha256=content_hash(path),mode=path.stat().st_mode&0o777)
    if any(name not in result or not result[name]['mode']&0o111 for name in PACKAGE_EXECUTABLES):
        raise QualificationError('complete executable package required')
    if 'codex-package.json' not in result:raise QualificationError('package manifest required')
    return result


class UpgradeQualification:
    def __init__(self, root, *, now=None):
        self.root=Path(root).resolve()
        self.now=now or time.time

    def run(self,job,config,*,guard=None):
        guard=guard or (lambda:None)
        self.owned_groups=[]
        receipt=dict(schema_version=1,job_id=job.get('id'),job_key=job.get('key'),
            target=job.get('target'),status='held',eligible_for_promotion=False,
            model_requests=0,started_at=self.now(),checks={},commands=[],executor_sha256=content_hash(__file__))
        directory=None
        try:
            if not isinstance(job.get('id'),str) or not job['id'] or '/' in job['id'] or job['id'] in ('.','..'):
                raise QualificationError('invalid job identity')
            directory=self.root/'upgrade-jobs'/job['id']/'qualification'
            directory.mkdir(parents=True,exist_ok=True,mode=0o700)
            stage=job.get('results',{}).get('stage',{})
            if stage.get('status')!='staged':raise QualificationError('staged exact package required')
            executable=Path(stage.get('build',{}).get('executable','')).resolve(strict=True)
            package=executable.parent.parent
            owned=self.root/'upgrade-jobs'/job['id']/'build-store'/'stages'
            if not package.is_relative_to(owned) or executable!=package/'bin/codex':
                raise QualificationError('package outside owned job stage')
            before=package_inventory(package)
            if before!=stage.get('files') or before['bin/codex']['sha256']!=stage['build'].get('sha256'):
                raise QualificationError('staged package digest mismatch')
            identity=stage.get('source_identity')
            if not isinstance(identity,dict) or any(not isinstance(identity.get(name),str) or not identity[name] for name in ('upstream_version','revision')):
                raise QualificationError('explicit source identity required')
            receipt.update(package_files=before,package_sha256=object_hash(before),
                source_identity=stage.get('source_identity'),candidate_sha256=object_hash(stage))
            if config.get('schema_version')!=1:raise QualificationError('qualification config schema unsupported')
            environment=self.environment(config.get('environment',{}))
            receipt['environment']=environment
            if environment['kind']!='source_fixture':
                receipt['native_version']=self.genuine_provenance(stage,package,job,guard)
            test_files=self.test_files(config)
            receipt['test_files']=test_files
            receipt['tests_sha256']=object_hash(test_files)
            receipt['configuration_sha256']=object_hash(config)
            self.check(job,guard)
            metadata=self.metadata(job,config,package,guard)
            receipt['metadata']=metadata
            required=set(JOURNEYS)
            required.update(CAPABILITIES if stage.get('channel')=='modded' else ('official_cli',))
            claimed=config.get('required_checks',[])
            if not isinstance(claimed,list) or any(not isinstance(v,str) or not v for v in claimed):
                raise QualificationError('invalid claimed capability requirements')
            required.update(claimed)
            manifest=json.loads((package/'codex-package.json').read_text())
            if not isinstance(manifest,dict):raise QualificationError('native package manifest invalid')
            capabilities=manifest.get('capabilities',{})
            if isinstance(capabilities,dict):
                if any(type(value) is not bool for value in capabilities.values()):raise QualificationError('invalid manifest capability declaration')
                required.update(name for name,value in capabilities.items() if value)
            elif isinstance(capabilities,list) and all(isinstance(name,str) and name for name in capabilities):
                required.update(capabilities)
            else:raise QualificationError('invalid manifest capability declaration')
            for declaration in (job.get('required_capabilities',[]), stage.get('required_capabilities',[]), list(stage.get('checks',{}))):
                if not isinstance(declaration,list) or any(not isinstance(v,str) or not v for v in declaration):
                    raise QualificationError('invalid candidate capability declaration')
                required.update(declaration)
            probes=config.get('probes')
            if not isinstance(probes,list) or not probes:raise QualificationError('installed capability probes required')
            for probe in probes:
                if not isinstance(probe,dict):raise QualificationError('structured qualification probe required')
                argv=probe.get('argv')
                if not isinstance(argv,list) or not argv or any(not isinstance(x,str) or not x for x in argv):
                    raise QualificationError('pinned explicit qualification argv required')
                pinned_program=str(Path(argv[0]).resolve()) in test_files
                pinned_script=len(argv)>1 and Path(argv[0]).name.startswith(('python','bash','sh')) and str(Path(argv[1]).resolve()) in test_files
                if not (pinned_program or pinned_script):
                    raise QualificationError('qualification command has no pinned test artifact')
                if self.test_files(config)!=test_files:raise QualificationError('qualification tests changed')
                report=self.probe(job,probe,config,package,directory,guard)
                receipt['commands'].append(report)
                if report['report'].get('status')=='authentication_needed':raise AuthenticationNeeded('designated test account needs authentication')
                body=report['report']
                observed=body.get('model_requests')
                if type(observed) is int and observed>=0:receipt['model_requests']+=observed
                if body.get('schema_version')!=1 or body.get('status')!='passed' or type(body.get('model_requests')) is not int or body['model_requests']!=0:
                    raise QualificationError('qualification probe failed or model-request boundary unproven')
                if body.get('owned_processes_remaining')!=[]:raise QualificationError('qualification owned-process teardown unproven')
                checks=body.get('checks')
                if not isinstance(checks,dict):raise QualificationError('qualification checks missing')
                for name,value in checks.items():
                    if type(value) is not bool:raise QualificationError('strict Boolean capability result required')
                    if name in receipt['checks'] and receipt['checks'][name] is not value:
                        raise QualificationError('contradictory capability reports')
                    receipt['checks'][name]=value
            self.check(job,guard)
            if any(receipt['checks'].get(name) is not True for name in required):
                raise QualificationError('required capability or installed journey unqualified')
            if package_inventory(package)!=before:raise QualificationError('qualification changed package bytes')
            if self.test_files(config)!=test_files:raise QualificationError('qualification tests changed')
            genuine=environment['kind'] in ('disposable_wsl','separate_test_user')
            receipt.update(status='qualified' if genuine else 'fixture_verified',eligible_for_promotion=genuine,
                evidence_scope='disposable_authenticated' if genuine else 'source_fixture',
                required_checks=sorted(required),owned_processes_remaining=[])
        except AuthenticationNeeded as error:
            receipt.update(status='authentication_needed',reason=str(error))
        except (OSError,ValueError,KeyError,TypeError) as error:
            receipt.update(status='held',reason=str(error))
        receipt['owned_processes_remaining']=self.census()
        if receipt['owned_processes_remaining']:
            receipt.update(status='held',eligible_for_promotion=False,reason='owned qualification processes remain')
        receipt['finished_at']=self.now()
        if directory:receipt['receipt_path']=str(directory/'receipt.json')
        receipt['receipt_sha256']=object_hash(receipt)
        if directory:_atomic(directory/'receipt.json',receipt)
        return receipt

    def census(self):
        remaining=[]
        if not Path('/proc').is_dir():return ['process_census_unavailable']
        for process in Path('/proc').iterdir():
            if not process.name.isdigit():continue
            try:
                fields=(process/'stat').read_text().rsplit(')',1)[1].split()
                if int(fields[2]) in self.owned_groups and fields[0]!='Z':remaining.append(int(process.name))
            except (OSError,ValueError,IndexError):continue
        return sorted(remaining)

    def check(self,job,guard):
        guard()
        deadline=job.get('deadline')
        if type(deadline) not in (int,float) or self.now()>=deadline:
            raise QualificationError('qualification deadline exhausted')

    def environment(self,declaration):
        kind=declaration.get('kind')
        if kind=='source_fixture':return dict(kind=kind,uid=os.getuid(),distro=os.environ.get('WSL_DISTRO_NAME'))
        if kind not in ('disposable_wsl','separate_test_user'):
            raise QualificationError('explicit disposable environment required')
        if type(declaration.get('uid')) is not int or os.getuid()!=declaration['uid']:
            raise QualificationError('disposable environment uid mismatch')
        distro=os.environ.get('WSL_DISTRO_NAME')
        if kind=='disposable_wsl' and (declaration.get('distribution')!='wsl-test' or distro!='wsl-test'):
            raise QualificationError('qualification must execute inside designated wsl-test')
        if kind=='separate_test_user' and os.getuid()!=1017:
            raise QualificationError('qualification must execute as designated test uid1017')
        return dict(kind=kind,uid=os.getuid(),distro=distro,shared_kernel=True)

    def genuine_provenance(self,stage,package,job,guard):
        if stage.get('evidence_scope') not in ('official_source_build','native_source_build','disposable_native_build'):
            raise QualificationError('native source-build provenance required; fixtures cannot qualify by environment location')
        if not str(stage.get('source','')).startswith('https://github.com/openai/codex/releases/download/'):
            raise QualificationError('official upstream source provenance required')
        source=stage['source_identity'].get('source_files')
        if not isinstance(source,dict) or not source:
            raise QualificationError('pinned source inventory required for genuine acceptance')
        manifest=json.loads((package/'codex-package.json').read_text())
        if not isinstance(manifest,dict):raise QualificationError('native package manifest invalid')
        with tempfile.TemporaryDirectory(prefix='wake-native-version-') as home, tempfile.TemporaryFile() as output:
            env={key:value for key,value in os.environ.items() if key in ('PATH','LANG','LC_ALL')}
            env.update(HOME=home,CODEX_HOME=home+'/.codex')
            process=subprocess.Popen([str(package/'bin/codex'),'--version'],env=env,stdin=subprocess.DEVNULL,
                stdout=output,stderr=subprocess.DEVNULL,start_new_session=True)
            self.owned_groups.append(process.pid)
            deadline=time.monotonic()+30
            try:
                while process.poll() is None:
                    self.check(job,guard)
                    if time.monotonic()>=deadline or output.tell()>4096:raise QualificationError('native version probe exceeded bound')
                    time.sleep(.05)
                output.seek(0);version=output.read(4097).decode().strip()
                expected='codex-cli '+stage['source_identity']['upstream_version']
                if process.returncode or len(version)>4096 or version!=expected:
                    raise QualificationError('native executable version differs from pinned upstream identity')
                return dict(value=version,executable_sha256=stage['build']['sha256'])
            finally:self.stop(process)

    def test_files(self,config):
        files=config.get('test_files')
        if not isinstance(files,dict) or not files:raise QualificationError('pinned acceptance test artifacts required')
        result={}
        for name,expected in files.items():
            path=Path(name).resolve(strict=True)
            if not path.is_file() or content_hash(path)!=expected:
                raise QualificationError('pinned acceptance test digest mismatch')
            result[str(path)]=expected
        return result

    def metadata(self,job,config,package,guard):
        state_root=Path(config.get('state_root','')).resolve(strict=True)
        accounts=config.get('accounts')
        if not isinstance(accounts,list) or len(accounts)!=2:raise QualificationError('two designated test accounts required')
        homes=[];aliases=[];identities=[]
        for account in accounts:
            if not isinstance(account,dict):raise QualificationError('structured test account required')
            home=Path(account['home']).resolve(strict=True)
            if not home.is_dir() or not home.is_relative_to(state_root) or home==state_root:
                raise QualificationError('account home outside designated disposable state root')
            if not isinstance(account.get('alias'),str) or not account['alias']:raise QualificationError('account alias required')
            homes.append(home);aliases.append(account['alias'])
        if len(set(homes))!=2 or len(set(aliases))!=2:raise QualificationError('distinct test homes and aliases required')
        for index in (0,1,0):
            self.check(job,guard)
            result=self.account_read(job,package,homes[index],guard)
            identities.append(result)
        if identities[0]!=identities[2]:raise QualificationError('account identity changed after A-B-A restart/reconnect')
        if identities[0]==identities[1]:raise QualificationError('test account identities are not distinct')
        return dict(sequence=[aliases[0],aliases[1],aliases[0]],
            identity_sha256=identities,restarted=True,reconnected=True,model_requests=0,
            rpc_methods=['initialize','account/read'],auth_refresh_requested=False)

    def account_read(self,job,package,home,guard):
        env={k:v for k,v in os.environ.items() if k in ('PATH','LANG','LC_ALL')}
        env.update(HOME=str(home),CODEX_HOME=str(home),XDG_CONFIG_HOME=str(home/'.config'),XDG_DATA_HOME=str(home/'.local/share'))
        process=subprocess.Popen([str(package/'bin/codex'),'app-server'],cwd=home,env=env,
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,start_new_session=True)
        self.owned_groups.append(process.pid)
        selector=selectors.DefaultSelector();selector.register(process.stdout,selectors.EVENT_READ)
        pending=b''
        local_deadline=time.monotonic()+30
        try:
            def request(identifier,method,params):
                nonlocal pending
                process.stdin.write((json.dumps(dict(id=identifier,method=method,params=params))+'\n').encode());process.stdin.flush()
                while True:
                    self.check(job,guard)
                    if time.monotonic()>=local_deadline:raise QualificationError('native metadata deadline exhausted')
                    while b'\n' in pending:
                        line,pending=pending.split(b'\n',1)
                        reply=json.loads(line)
                        if not isinstance(reply,dict):raise QualificationError('structured native metadata reply required')
                        if reply.get('id')==identifier:
                            if 'error' in reply:raise AuthenticationNeeded('native account metadata RPC unavailable')
                            return reply.get('result')
                    if not selector.select(.1):
                        if process.poll() is not None:raise QualificationError('native metadata process exited')
                        continue
                    chunk=os.read(process.stdout.fileno(),65536)
                    if not chunk:raise QualificationError('native metadata connection closed')
                    pending+=chunk
                    if len(pending)>1024*1024:raise QualificationError('native metadata response exceeds limit')
            request(1,'initialize',dict(clientInfo=dict(name='wake-upgrade-qualification',version='1'),capabilities=dict(experimentalApi=True)))
            process.stdin.write(b'{"method":"initialized","params":{}}\n');process.stdin.flush()
            result=request(2,'account/read',dict(refreshToken=False))
            account=result.get('account') if isinstance(result,dict) else None
            if not isinstance(account,dict) or account.get('type')!='chatgpt' or not isinstance(account.get('email'),str) or not account['email']:
                raise AuthenticationNeeded('designated test account has no authenticated ChatGPT identity')
            # Native account ownership observed without persisting PII or tokens.
            return hashlib.sha256(account['email'].casefold().encode()).hexdigest()
        finally:
            selector.close()
            self.stop(process)

    def stop(self,process):
        try:os.killpg(process.pid,signal.SIGTERM)
        except ProcessLookupError:pass
        try:process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            try:os.killpg(process.pid,signal.SIGKILL)
            except ProcessLookupError:pass
            process.wait()
        # The group may outlive its leader (for example a compiler/helper that
        # ignores TERM). Always fence those owned descendants as well.
        try:os.killpg(process.pid,signal.SIGKILL)
        except ProcessLookupError:pass
        for stream in (process.stdin,process.stdout):
            if stream:stream.close()

    def probe(self,job,probe,config,package,directory,guard):
        with tempfile.TemporaryDirectory(prefix='probe-',dir=directory) as home:
            env={k:v for k,v in os.environ.items() if k in ('PATH','LANG','LC_ALL')}
            env.update(HOME=home,CODEX_HOME=home+'/.codex',XDG_CONFIG_HOME=home+'/.config',XDG_DATA_HOME=home+'/.local/share',
                CODEX_UPGRADE_PACKAGE=str(package),CODEX_UPGRADE_MODEL_TURNS='forbidden')
            Path(env['CODEX_HOME']).mkdir(mode=0o700)
            timeout=probe.get('timeout_seconds',600)
            if type(timeout) is not int or not 1<=timeout<=7200:raise QualificationError('invalid qualification command timeout')
            local_deadline=time.monotonic()+timeout
            with tempfile.TemporaryFile() as output,tempfile.TemporaryFile() as errors:
                process=subprocess.Popen(probe['argv'],cwd=package,env=env,stdin=subprocess.DEVNULL,
                    stdout=output,stderr=errors,start_new_session=True)
                self.owned_groups.append(process.pid)
                try:
                    while process.poll() is None:
                        self.check(job,guard)
                        if time.monotonic()>=local_deadline:raise QualificationError('qualification command deadline exhausted')
                        if output.tell()>1024*1024 or errors.tell()>1024*1024:raise QualificationError('qualification output exceeds limit')
                        time.sleep(.05)
                    if process.returncode:raise QualificationError('qualification command failed')
                    output.seek(0);raw=output.read(1024*1024+1)
                    if len(raw)>1024*1024:raise QualificationError('qualification output exceeds limit')
                    body=json.loads(raw)
                    if not isinstance(body,dict):raise QualificationError('structured qualification report required')
                    # Do not retain arbitrary probe output: account data or
                    # private diagnostics are not part of the report contract.
                    body={key:body[key] for key in ('schema_version','status','model_requests','checks','owned_processes_remaining') if key in body}
                    return dict(id=probe.get('id'),argv_sha256=object_hash(probe['argv']),exit_code=process.returncode,
                        report=body,report_sha256=hashlib.sha256(raw).hexdigest())
                finally:self.stop(process)
