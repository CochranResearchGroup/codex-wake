"""Pinned patch replay and bounded semantic repair with independent review.

This executor consumes host configuration, never caller-supplied commands.
Workers edit an owned Git workspace. Reports live outside the candidate, and a
review is accepted only for the exact candidate and tests that were inspected.
A reviewed source snapshot is input to staging, not runtime qualification.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import tempfile
import time

from codex_profiles.upgrades import _atomic, REQUIRED_CAPABILITIES


class RepairHeld(ValueError):
    """A repair could not establish the evidence needed to proceed."""


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _digest(value):
    return _sha(json.dumps(value,sort_keys=True,separators=(',',':')).encode())


def _inventory(root):
    files={}
    for path in sorted(root.rglob('*')):
        relative=path.relative_to(root)
        if '.git' in relative.parts:
            continue
        if path.is_symlink():
            resolved=path.resolve(strict=True)
            if not resolved.is_relative_to(root) or not resolved.is_file():
                raise RepairHeld('candidate contains an escaping or directory symlink')
        if path.is_file():
            files[str(relative)]={'sha256':_sha(path.read_bytes()),'mode':path.stat().st_mode&0o777}
        elif not path.is_dir():
            raise RepairHeld('candidate contains a special file')
    return files


def _identities(files):
    tests={path:value for path,value in files.items() if 'tests' in Path(path).parts or Path(path).name.startswith('test_') or Path(path).stem.endswith('_tests')}
    return _digest(files),_digest(tests)


class UpgradeRepair:
    """Run one sealed release's replay/repair/review; result is a stage recipe.

    ``guard`` verifies the current enabled scope during command polling.
    ``checkpoint`` durably charges the job's cumulative repair_attempts before
    each worker submission. The executor's own journal independently retains the
    same high-water mark and unresolved subprocess intents across reconstruction.
    """
    def __init__(self, workspace, evidence, config, *, now=None, guard=None, checkpoint=None):
        self.workspace=Path(workspace).resolve(strict=True)
        self.evidence=Path(evidence).resolve()
        if self.evidence == self.workspace or self.evidence.is_relative_to(self.workspace):
            raise ValueError('repair evidence must be outside candidate source')
        self.config=config
        self.now=now or time.time
        self.guard=guard or (lambda: None)
        self.checkpoint=checkpoint or (lambda value: None)
        self.evidence.mkdir(parents=True,exist_ok=True,mode=0o700)
        self.state_path=self.evidence/'repair-state.json'
        self.state={}

    def _save(self):
        _atomic(self.state_path,self.state)

    def _budget(self):
        self.guard()
        current=self.now()
        if current < self.state['last_seen']:
            raise RepairHeld('clock_uncertain')
        self.state['last_seen']=current
        if current >= self.job['deadline'] or time.monotonic() >= self.monotonic_deadline:
            raise RepairHeld('deadline_exhausted')
        limit=self.job['limits'].get('temporary_bytes')
        if limit is not None:
            size=sum(p.stat().st_size for base in (self.workspace,self.evidence) for p in base.rglob('*') if p.is_file() and not p.is_symlink())
            if size>limit:
                raise RepairHeld('temporary_storage_exhausted')

    def _command(self, argv, role, *, packet=None):
        if not isinstance(argv,list) or not argv or any(not isinstance(x,str) or not x for x in argv):
            raise RepairHeld('host command must be an explicit argv array')
        self._budget()
        sequence=len(self.state['commands'])+1
        output=self.evidence/f'{sequence}-{role}.stdout'
        error=self.evidence/f'{sequence}-{role}.stderr'
        response=self.evidence/f'{sequence}-{role}-response.json'
        env={k:v for k,v in os.environ.items() if k in ('PATH','LANG','LC_ALL')}
        with tempfile.TemporaryDirectory(prefix='repair-home-',dir=self.evidence) as home:
            env.update(HOME=home,CODEX_HOME=home+'/.codex',XDG_CONFIG_HOME=home+'/.config',XDG_DATA_HOME=home+'/.local/share',
                CARGO_BUILD_JOBS=str(self.job['limits'].get('compiler_jobs',2)))
            Path(env['CODEX_HOME']).mkdir(mode=0o700)
            if packet is not None:
                packet_path=self.evidence/f'{sequence}-{role}-packet.json'
                _atomic(packet_path,packet)
                env.update(CODEX_UPGRADE_PACKET=str(packet_path),CODEX_UPGRADE_RESPONSE=str(response))
            report=dict(role=role,argv=argv,stdout=str(output),stderr=str(error),status='intent')
            self.state['commands'].append(report)
            self.state['inflight']=dict(role=role,sequence=sequence)
            self._save()
            process=None
            try:
                with output.open('wb') as out,error.open('wb') as err:
                    process=subprocess.Popen(argv,cwd=self.workspace,env=env,stdout=out,stderr=err,start_new_session=True)
                    started=time.monotonic()
                    timeout=self.config.get('command_timeout_seconds',600)
                    if type(timeout) is not int or timeout<=0:
                        raise RepairHeld('positive host command timeout required')
                    while process.poll() is None:
                        self._budget()
                        if time.monotonic()-started>=timeout:
                            raise RepairHeld(role+'_timeout')
                        time.sleep(.05)
                    self._budget()
                report.update(status='completed',exit_code=process.returncode,stdout_sha256=_sha(output.read_bytes()),stderr_sha256=_sha(error.read_bytes()))
                self.state['inflight']=None
                self._save()
                return process.returncode,output.read_text(errors='replace')+error.read_text(errors='replace'),response
            finally:
                if process is not None:
                    try:os.killpg(process.pid,signal.SIGTERM)
                    except ProcessLookupError:pass
                    try:process.wait(timeout=1)
                    except subprocess.TimeoutExpired:
                        try:os.killpg(process.pid,signal.SIGKILL)
                        except ProcessLookupError:pass
                        process.wait()

    def _git(self,*argv):
        code,output,_=self._command(['git',*argv],'git')
        return code,output

    def _unresolved(self):
        code,output=self._git('ls-files','--unmerged')
        if code or output.strip():
            return True
        code,output=self._git('diff','--check','HEAD')
        return 'conflict marker' in output.lower()

    def _validate_config(self, recipe):
        worker=self.config.get('worker',{});reviewer=self.config.get('reviewer',{})
        if not worker.get('identity') or not reviewer.get('identity') or worker['identity']==reviewer['identity']:
            raise RepairHeld('independently configured worker and reviewer identities required')
        if worker.get('argv')==reviewer.get('argv'):
            raise RepairHeld('worker and reviewer must be separately configured commands')
        for commands in ('regenerate','verify'):
            if not isinstance(self.config.get(commands),list):
                raise RepairHeld('explicit host generation and verification command lists required')
        if not self.config['verify']:
            raise RepairHeld('behavioral verification commands required')
        patches=self.config.get('patches')
        if not isinstance(patches,list):
            raise RepairHeld('pinned patch list required')
        pins=lambda items: [(str(Path(p['path']).resolve()),p['sha256']) for p in items]
        if pins(patches)!=pins(recipe.get('patches',[])):
            raise RepairHeld('original_patch_stack_mismatch')
        ids=set()
        for patch in patches:
            if not patch.get('id') or patch['id'] in ids or not patch.get('intent'):
                raise RepairHeld('unique patch identity and behavioral intent required')
            ids.add(patch['id'])
            if _sha(Path(patch['path']).read_bytes())!=patch.get('sha256'):
                raise RepairHeld('patch_pin_mismatch')

    def _packet(self,role):
        files=_inventory(self.workspace)
        candidate,tests=_identities(files)
        return dict(schema_version=1,role=role,job_id=self.job['id'],candidate_digest=candidate,tests_digest=tests,
            workspace=str(self.workspace),required_capabilities=self.required,patches=self.config['patches'],
            patch_provenance=self.state['patch_provenance'],prior_findings=self.state.get('findings',[]),
            contract='Preserve every required capability and acceptance standard. Resolve conflicts by upstream and patch intent. Return schema_version 1, status, identity, candidate_digest, tests_digest, capabilities mapping to evidence, patch_dispositions for EVERY patch ID (disposition applied/rewritten/retired plus nonempty intent evidence), and retirements mapping patch IDs to equivalence evidence. Reviewer additionally returns reviewer identity and status approved or rejected. Never weaken tests to obtain approval.')

    def _read_report(self,path,role):
        try:report=json.loads(path.read_text())
        except (OSError,ValueError) as error:raise RepairHeld(role+'_structured_report_missing') from error
        if not isinstance(report,dict) or report.get('schema_version')!=1:
            raise RepairHeld(role+'_report_schema_unsupported')
        return report

    def _replay(self):
        code,revision=self._git('rev-parse','HEAD')
        if code or not re.fullmatch(r'[a-f0-9]{40,64}',self.config.get('base_revision','')) or revision.strip()!=self.config['base_revision']:
            raise RepairHeld('upstream_source_identity_mismatch')
        self.state['base_revision']=revision.strip()
        self.state['base_files_digest']=_digest(_inventory(self.workspace))
        code,output=self._git('status','--porcelain')
        if code or output.strip():
            raise RepairHeld('initial_workspace_must_be_clean')
        self.state['patch_provenance']=[dict(id=p['id'],sha256=p['sha256'],intent=p['intent'],disposition='pending') for p in self.config['patches']]
        self._save()
        for patch,provenance in zip(self.config['patches'], self.state['patch_provenance']):
            code,_=self._git('apply','--check',str(Path(patch['path']).resolve()))
            if code==0:
                code,output=self._git('apply','--index',str(Path(patch['path']).resolve()))
            else:
                code,output=self._git('apply','--3way','--index',str(Path(patch['path']).resolve()))
            conflicted=code!=0 or 'with conflicts' in output.lower() or self._unresolved()
            provenance['disposition']='needs_repair' if conflicted else 'applied'
            self._save()
            if conflicted:
                return False
        return True

    def _verify(self):
        for role in ('regenerate','verify'):
            for argv in self.config[role]:
                code,_,_=self._command(argv,role)
                if code:
                    return False
        return not self._unresolved()

    def _review(self):
        packet=self._packet('reviewer')
        code,_,path=self._command(self.config['reviewer']['argv'],'reviewer',packet=packet)
        if code:
            raise RepairHeld('reviewer_failed')
        report=self._read_report(path,'reviewer')
        current=self._packet('reviewer')
        if current['candidate_digest']!=packet['candidate_digest'] or current['tests_digest']!=packet['tests_digest']:
            raise RepairHeld('candidate_changed_during_review')
        if report.get('reviewer')!=self.config['reviewer']['identity'] or any(report.get(k)!=packet[k] for k in ('candidate_digest','tests_digest')):
            raise RepairHeld('review_identity_or_content_mismatch')
        capabilities=report.get('capabilities',{})
        if not isinstance(capabilities,dict) or any(not isinstance(capabilities.get(c),str) or not capabilities[c].strip() for c in self.required):
            raise RepairHeld('required_capability_evidence_missing')
        for patch in self.state['patch_provenance']:
            if patch['disposition']=='retired':
                evidence=report.get('retirements',{}).get(patch['id'])
                if not isinstance(evidence,str) or not evidence.strip():
                    raise RepairHeld('retirement_equivalence_unreviewed')
        report['report_sha256']=_sha(path.read_bytes())
        return report

    def _prepared(self,recipe,review):
        before=_inventory(self.workspace)
        snapshot=self.evidence/'reviewed-source'
        if snapshot.exists():
            raise RepairHeld('reviewed_snapshot_exists_reconcile_required')
        snapshot.mkdir(mode=0o700)
        for name in before:
            source=self.workspace/name;destination=snapshot/name
            destination.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(source.resolve(strict=True),destination)
        if _inventory(self.workspace)!=before or _inventory(snapshot)!=before:
            raise RepairHeld('candidate_changed_while_snapshotting')
        if _identities(before)!=(review['candidate_digest'],review['tests_digest']):
            raise RepairHeld('candidate_changed_after_review')
        prepared=json.loads(json.dumps(recipe))
        prepared['source']=dict(prepared.get('source',{}),tree=str(snapshot),files={p:v['sha256'] for p,v in before.items()})
        prepared['patches']=[]
        prepared['repair_provenance']=dict(original_recipe_sha256=_digest(recipe),base_revision=self.state['base_revision'],base_files_digest=self.state['base_files_digest'],candidate_digest=review['candidate_digest'],tests_digest=review['tests_digest'],patches=self.state['patch_provenance'],review=review)
        path=self.evidence/'prepared-recipe.json';_atomic(path,prepared)
        return str(path)

    def run(self,job,recipe):
        self.job=job
        remaining=job['deadline']-self.now()
        self.monotonic_deadline=time.monotonic()+max(0,remaining)
        self.required=sorted(set(REQUIRED_CAPABILITIES.get(recipe.get('channel'), ())) |
            set(job.get('required_capabilities', ())) | set(self.config.get('required_capabilities', ())) |
            ({'tui_health'} if recipe.get('channel') == 'modded' else set()))
        seal=_digest(dict(job_id=job['id'],recipe=recipe,config=self.config,workspace=str(self.workspace),required=self.required))
        self.state=dict(schema_version=1,seal=seal,repair_attempts=job.get('repair_attempts',0),last_seen=self.now(),commands=[],patch_provenance=[],inflight=None,status='applying')
        if self.state_path.exists():
            self.state=json.loads(self.state_path.read_text())
            if self.state.get('seal')!=seal:
                raise RepairHeld('repair_job_input_changed')
            self.state['repair_attempts']=max(self.state['repair_attempts'],job.get('repair_attempts',0))
            if self.state.get('status')=='reviewed':
                result=self.state['result']
                prepared=json.loads(Path(result['prepared_recipe']).read_text())
                if _identities(_inventory(Path(prepared['source']['tree'])))!=(result['candidate_digest'],result['tests_digest']):
                    raise RepairHeld('reviewed_snapshot_changed')
                return result
            return dict(status='held',reason='interrupted_repair_reconcile_required',repair_attempts=self.state['repair_attempts'],evidence=str(self.state_path))
        self._save()
        try:
            self._validate_config(recipe);self._budget()
            applied=self._replay()
            limit=job['limits']['repair_attempts']
            while True:
                verified=applied and self._verify()
                if verified:
                    review=self._review()
                    if review.get('status')=='approved':
                        prepared=self._prepared(recipe,review)
                        result=dict(status='reviewed',prepared_recipe=prepared,candidate_digest=review['candidate_digest'],tests_digest=review['tests_digest'],review=review,
                            repair_attempts=self.state['repair_attempts'],patch_provenance=self.state['patch_provenance'],evidence=str(self.state_path))
                        self.state.update(status='reviewed',result=result);self._save()
                        return result
                    self.state['findings']=review.get('findings',['review rejected'])
                if self.state['repair_attempts']>=limit:
                    raise RepairHeld('repair_attempts_exhausted')
                self._budget()
                self.state['repair_attempts']+=1
                self._save()
                self.checkpoint(dict(repair_attempts=self.state['repair_attempts']))
                packet=self._packet('worker')
                code,_,path=self._command(self.config['worker']['argv'],'worker',packet=packet)
                if code:
                    self.state['findings']=['worker command failed'];applied=False
                    continue
                report=self._read_report(path,'worker')
                if report.get('identity') != self.config['worker']['identity'] or report.get('status') != 'repaired':
                    raise RepairHeld('worker_identity_or_status_mismatch')
                declarations=report.get('patch_dispositions',{})
                if not isinstance(declarations,dict) or set(declarations)!={p['id'] for p in self.config['patches']}:
                    raise RepairHeld('worker_patch_dispositions_incomplete')
                retirements=report.get('retirements',{})
                if not isinstance(retirements,dict):raise RepairHeld('invalid retirement declarations')
                known={p['id'] for p in self.config['patches']}
                if set(retirements)-known:raise RepairHeld('unknown retired patch')
                for patch in self.state['patch_provenance']:
                    declaration=declarations[patch['id']]
                    if not isinstance(declaration,dict) or declaration.get('disposition') not in ('applied','rewritten','retired') or not isinstance(declaration.get('evidence'),str) or not declaration['evidence'].strip():
                        raise RepairHeld('worker_patch_intent_evidence_missing')
                    patch.update(disposition=declaration['disposition'],evidence=declaration['evidence'])
                    if patch['disposition']=='retired':
                        if not isinstance(retirements.get(patch['id']),str) or not retirements[patch['id']].strip():
                            raise RepairHeld('retirement_equivalence_missing')
                        patch['equivalence']=retirements[patch['id']]
                self._save()
                applied=not self._unresolved()
        except (RepairHeld,OSError,ValueError,KeyError,subprocess.SubprocessError) as error:
            self.state.update(status='held',reason=str(error));self._save()
            return dict(status='held',reason=str(error),repair_attempts=self.state['repair_attempts'],evidence=str(self.state_path))
