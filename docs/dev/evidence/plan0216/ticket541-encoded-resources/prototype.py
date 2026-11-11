import json, subprocess, time, statistics, hashlib
from codex_wake.json_decode import decode_json
raw=subprocess.check_output(['sudo','-n','-u','codex-daemon-test','cat','/tmp/wake547-results/62877702-private-state/snapshot.json'])
base=decode_json(raw)['resources']
for row in base:
 row.pop('monitor_observed_at',None);row.pop('monitor_unavailable',None)
frames=[]
for i in range(60):
 rows=decode_json(json.dumps(base,separators=(',',':'),allow_nan=False))
 for j,row in enumerate(rows):
  row['evidence_revision']=str(i if i%5==0 or j<2 else i-i%5)
  if j<2:row['traits']['traits']['activity']['value']='running' if i%2 else 'waiting-for-input'
 frames.append(rows)

def old():
 outputs=[]
 for i,rows in enumerate(frames):
  encoded=json.dumps(rows,separators=(',',':'),allow_nan=False)
  materialized=decode_json(encoded)
  for row in materialized:row.update(monitor_observed_at=1000.+i,monitor_unavailable=False)
  outputs.append(json.dumps(dict(schema_version=1,observed_at=1000.+i,resources=materialized),separators=(',',':'),allow_nan=False))
 return outputs

def cached():
 cache={};outputs=[]
 for i,rows in enumerate(frames):
  items=[];updated={}
  for row in rows:
   key=(row['target']['workspace'],row['window']['window_id'])
   token=(row['evidence_revision'],row['projection_revision'],row.get('projection_valid_until'))
   prior=cache.get(key)
   if prior and prior[0]==token:body=prior[1]
   else:body=json.dumps(row,separators=(',',':'),allow_nan=False)
   updated[key]=(token,body)
   items.append(body[:-1]+',"monitor_observed_at":'+str(1000.+i)+',"monitor_unavailable":false}')
  cache=updated
  encoded='['+','.join(items)+']'
  materialized=decode_json(encoded) # formatter still requires independent rows
  outputs.append('{"schema_version":1,"observed_at":'+str(1000.+i)+',"resources":'+encoded+'}')
 return outputs
expected=old();actual=cached()
assert expected==actual
samples={'old':[],'cached':[]}
for repeat in range(5):
 for name,fn in [('old',old),('cached',cached),('cached',cached),('old',old)]:
  start=time.process_time();fn();samples[name].append(time.process_time()-start)
result=dict(frames=60,resources=len(base),full_rebaseline_every_frames=5,dirty_rows_per_other_frame=2,source_artifact_sha256=hashlib.sha256(raw).hexdigest(),json_bytes_identical=True,median_cpu_seconds={name:statistics.median(values) for name,values in samples.items()},scope='component prototype; formatter decode retained in both; not installed CPU acceptance')
result['saved_cpu_seconds_per60_frames']=result['median_cpu_seconds']['old']-result['median_cpu_seconds']['cached']
print(json.dumps(result));open('/tmp/wake216-serialization-probe.json','w').write(json.dumps(result,indent=2)+'\n')
