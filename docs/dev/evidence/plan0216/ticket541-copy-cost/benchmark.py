"""Opt-in synthetic public-cache microbenchmark; not resource acceptance.

Run from the repository root. Remove explicit_checks=True in both observe calls
to reproduce the retained cached-read variant. Frozen base is available in Git.
"""
import importlib.util,json,statistics,tempfile,time,subprocess
from pathlib import Path
source=subprocess.check_output(['git','show','e5beb4c7:src/codex_wake/tab_observation.py'],text=True)
candidate=source.replace('from copy import deepcopy','from copy import deepcopy\nimport json',1).replace('                return deepcopy(prior[2])','                observed,rows=json.loads(prior[2])\n                return observed,rows',1).replace('now+self.ttl,deepcopy(result),digest(self._processes)','now+self.ttl,json.dumps(result,separators=(\',\',\':\'),allow_nan=False),digest(self._processes)',1)
assert candidate!=source
with tempfile.TemporaryDirectory() as directory:
 def load(label,code):
  p=Path(directory)/(label+'.py');p.write_text(code)
  spec=importlib.util.spec_from_file_location('codex_wake.cache_bench_'+label,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m.ObservationCache
 classes={'baseline':load('baseline',source),'candidate':load('candidate',candidate)}
 windows=[dict(window_id='@'+str(i),name='fixture',panes=[dict(pane_id='%'+str(i),pid=10000+i)]) for i in range(100)]
 snapshot=dict(server='fixture',session_id='$0',socket_identity=[1,2],windows=windows)
 def identity(pid):return dict(start_time_ticks=10,boot_id='fixture')
 def processes(pid,deadline):return [dict(process=dict(pid=pid,start_ticks=10,boot_id='fixture'),executable='/fixture/worker',argv=['worker'],cwd='/fixture')],True
 receipt=dict(mode='refresh microbenchmark, NOT installed resource acceptance',tabs=100,frames_per_sample=60,samples=[])
 for label in ('baseline','candidate','candidate','baseline'):
  owner=classes[label](directory,process_probe=processes,identity_probe=identity,monotonic=lambda:0)
  owner.observe('fixture',snapshot,deadline=time.monotonic()+120,explicit_checks=True)
  start=time.perf_counter();cpu=time.process_time()
  for i in range(60):
   result,_=owner.observe('fixture',snapshot,deadline=time.monotonic()+120,explicit_checks=True)
   assert result['@0']['traits']['harness']['value']=='unknown'
   result['@0']['traits']['harness']['value']='caller mutation'
  receipt['samples'].append(dict(label=label,cpu_seconds=time.process_time()-cpu,wall_seconds=time.perf_counter()-start))
 receipt['means']={label:statistics.mean(s['cpu_seconds'] for s in receipt['samples'] if s['label']==label) for label in classes}
 receipt['candidate_ratio']=receipt['means']['candidate']/receipt['means']['baseline']
 Path('/tmp/wake216-cache-copy-refresh-reproduction.json').write_text(json.dumps(receipt,indent=2)+'\n')
 print(json.dumps(receipt))
