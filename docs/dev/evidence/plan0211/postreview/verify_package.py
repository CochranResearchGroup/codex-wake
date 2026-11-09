"""Verify exact git-tree inputs, wheel, Linux install and Windows equality receipt."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile
import zipfile

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--build',type=Path,required=True);p.add_argument('--windows',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
v=json.loads(a.build.read_text());windows=json.loads(a.windows.read_text());prefix=Path(v['linux_prefix'])
archive=subprocess.check_output(['git','archive',v['source_commit'],'src','README.md','pyproject.toml'])
with tarfile.open(fileobj=io.BytesIO(archive)) as tree,zipfile.ZipFile(v['wheel']) as wheel:
 names=[n for n in wheel.namelist() if '.dist-info/' not in n]
 for name in names:
  source=tree.extractfile('src/'+name).read();actual=wheel.read(name)
  assert source==actual==(prefix/'lib/python3.12/site-packages'/name).read_bytes(),name
  assert hashlib.sha256(actual).hexdigest()==v['package_member_sha256'][name]
 for name,expected in v['build_inputs_sha256'].items():assert hashlib.sha256(tree.extractfile(name).read()).hexdigest()==expected,name
assert hashlib.sha256(Path(v['wheel']).read_bytes()).hexdigest()==v['wheel_sha256']==windows['wheel_sha256']
assert len(names)==windows['all_package_members_verified']==304
assert sum(n.endswith('.py') for n in names)==windows['python_members']==302
r=dict(status='PASS',source_commit=v['source_commit'],wheel_sha256=v['wheel_sha256'],all_members=304,python_members=302,linux_prefix=str(prefix),windows_prefix=windows['prefix'],source='git archive exact frozen commit',windows_evidence=str(a.windows))
a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
