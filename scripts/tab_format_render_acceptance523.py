#!/usr/bin/env python3
"""Render Wake metadata in an owned Byobu/tmux PTY and native psmux namespace."""
import argparse
import base64
import fcntl
import hashlib
import json
import os
from pathlib import Path
import pty
import re
import select
import shutil
import signal
import struct
import subprocess
import sys
import tempfile
import termios
import time
import uuid

from codex_wake.tab_format_projection import project
from codex_wake.tab_format_expiry import expiring_options
from codex_wake.tab_format_rendering import capabilities
from codex_wake import tab_psmux_bridge
from codex_wake.controller_tab_adapters import ConfiguredBridge,PsmuxAttachmentTransport


def resource(harness,build,activity,profile,backend):
    def trait(value):return dict(value=value,status='observed',freshness='fresh',observed_at=time.time())
    return dict(target=dict(presentation=backend),traits=dict(panes=[dict(pane_id='%fixture',traits=dict(
        harness=trait(harness),build=trait(build),activity=trait(activity),account=trait(profile),model_identity=trait('#[bg=red]'),inference_provider=trait('#(echo BAD)')))]))


def plain(data):
    text=data.decode('utf-8','replace')
    text=re.sub(r'\x1b\][^\x07]*(?:\x07|\x1b\\)','',text)
    return re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]','',text)


def read_pty(master,seconds):
    until=time.monotonic()+seconds;chunks=[]
    while time.monotonic()<until:
        readable,_,_=select.select([master],[],[],min(.05,max(0,until-time.monotonic())))
        if not readable:continue
        try:value=os.read(master,65536)
        except OSError:break
        if not value:break
        chunks.append(value)
        if sum(map(len,chunks))>1048576:raise RuntimeError('owned terminal output exceeds1MiB')
    return b''.join(chunks)


def tmux_acceptance(root):
    socket=str(root/'byobu.sock');home=root/'home';home.mkdir();byobu=home/'.byobu';byobu.mkdir();run=root/'run';run.mkdir()
    env=dict(os.environ,HOME=str(home),BYOBU_CONFIG_DIR=str(byobu),BYOBU_RUN_DIR=str(run),TERM='xterm-256color')
    env.pop('TMUX',None)
    def tmux(*args,check=True):return subprocess.run(['tmux','-S',socket,*args],env=env,text=True,capture_output=True,timeout=5,check=check).stdout
    start=subprocess.run(['byobu-tmux','-S',socket,'new-session','-d','-s','render','-n','manual #{pid},界','sleep 90'],env=env,text=True,capture_output=True,timeout=10)
    assert start.returncode==0,(start.stdout,start.stderr)
    child=None;master=slave=None
    try:
        tmux('new-window','-d','-t','render:','-n','peer','sleep 90')
        windows=tmux('list-windows','-t','render','-F','#{window_id}').splitlines();assert len(windows)==2
        tmux('set-option','-t','render','status-left','');tmux('set-option','-t','render','status-right','')
        tmux('set-option','-t','render','status-interval','1');tmux('set-option','-t','render','@wake-format-clock','%s')
        cases=[resource('codex','modded','running','x,}#{pid}','byobu'),resource('grok','unknown','waiting-for-input','界'*10,'byobu')]
        rendered={}
        for mode in ('full','basic','plain'):
            rows=[]
            for wid,item in zip(windows,cases):
                shown=project(item,dict(render_mode=mode,ascii=mode!='full',show_model=True,show_provider=True),now=time.time())
                values=expiring_options(shown['options'],observed_at=time.time(),render_mode=mode)
                for key,value in values.items():tmux('set-option','-w','-t',wid,key,value)
                evaluated=tmux('display-message','-p','-t',wid,'#{E:window-status-format}')
                selected=tmux('display-message','-p','-t',wid,'#{E:window-status-current-format}')
                assert 'x,}#{pid}' in evaluated if wid==windows[0] else 'GK' in evaluated
                assert '[' in selected and '#{' not in selected.split('x,}')[0],selected
                if mode=='plain':assert 'colour' not in evaluated and 'bg=default' in evaluated
                if mode=='basic':assert 'colour' not in evaluated
                rows.append(dict(window=wid,normal=evaluated.strip(),selected=selected.strip()))
            if child is None:
                master,slave=pty.openpty();fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',30,140,0,0))
                child=subprocess.Popen(['tmux','-S',socket,'attach-session','-t','render'],stdin=slave,stdout=slave,stderr=slave,env=env,start_new_session=True)
                os.close(slave);slave=None
            tmux('select-window','-t',windows[0]);tmux('refresh-client','-S')
            initial=read_pty(master,.7)
            tmux('select-window','-t',windows[1]);tmux('refresh-client','-S')
            changed=read_pty(master,.7)
            text=plain(initial+changed)
            assert 'CX+' in text and 'GK' in text,(mode,text[-1500:])
            assert '#[bg=red]' in text and '#(echo BAD)' in text,(mode,text[-1500:])
            assert '[' in text and ']' in text,(mode,text[-1500:])
            assert b'\x1b[' in initial+changed
            rendered[mode]=dict(native_formats=rows,attached_client_bytes=len(initial+changed),
                ansi_sha256=hashlib.sha256(initial+changed).hexdigest(),selected_and_unselected_native_cues=True)
        return dict(status='passed',tmux_version=subprocess.check_output(['tmux','-V'],text=True).strip(),
            byobu_version=subprocess.check_output(['byobu','--version'],text=True).strip(),modes=rendered,
            proof='actual owned attached PTY output plus native format expansion; not screenshot or human colour perception',
            manual_name=tmux('display-message','-p','-t',windows[0],'#{window_name}').strip())
    finally:
        if child:
            child.terminate()
            try:child.wait(timeout=5)
            except subprocess.TimeoutExpired:child.kill();child.wait(timeout=5)
        if master is not None:os.close(master)
        if slave is not None:os.close(slave)
        tmux('kill-server',check=False)


def psmux_acceptance(root,windows_python):
    namespace='wake523-'+uuid.uuid4().hex[:12]
    native_directory=Path('/mnt/c/Users/ecoch/AppData/Local/codex-wake-test')/namespace
    native_directory.mkdir(parents=True,exist_ok=False)
    helper=native_directory/'fixture.py'
    helper.write_text("import json,os,subprocess,sys\nfrom pathlib import Path\np=str(Path(os.environ['LOCALAPPDATA'])/'Microsoft/WinGet/Links/psmux.exe')\nr=subprocess.run([p,'-L',sys.argv[1],*sys.argv[2:]],capture_output=True,text=True,encoding='utf-8',timeout=8)\nprint(json.dumps(dict(rc=r.returncode,out=r.stdout,err=r.stderr)))\n")
    bridge_path=native_directory/'bridge.py';shutil.copyfile(tab_psmux_bridge.__file__,bridge_path)
    capture_path=native_directory/'capture.py';shutil.copyfile(Path(__file__).with_name('tab_format_windows_capture523.py'),capture_path)
    def winpath(path):return subprocess.check_output(['wslpath','-w',str(path)],text=True).strip()
    def native(*argv,check=True):
        r=json.loads(subprocess.check_output([windows_python,winpath(helper),namespace,*argv],text=True,timeout=12))
        if check:assert r['rc']==0,r
        return r
    owned=False
    try:
        native('new-session','-d','-s','source','-n','manual #{pid},界','--','cmd.exe','/d','/k');owned=True
        native('new-window','-d','-t','source:','-n','peer','--','cmd.exe','/d','/k')
        base=[windows_python,winpath(bridge_path),'--namespace',namespace,'--session','source']
        described=json.loads(subprocess.check_output(base+['--describe'],text=True,timeout=15));identity=described['identity']
        base+=['--server-pid',str(identity['pid']),'--server-birth',str(identity['creation_filetime'])]
        transport=PsmuxAttachmentTransport(ConfiguredBridge(base),generation=described['generation'])
        before=transport.snapshot(time.monotonic()+15);windows=before['windows']
        assert windows[0]['name']=='manual #{pid},界',windows[0]['name']
        originals=transport.formatting_batch([dict(action='read',window=w['window_id']) for w in windows],time.monotonic()+15)
        session=transport.formatting('read-session',{},time.monotonic()+15)
        transport.formatting('write-session',dict(values={'@wake-format-clock':'%s','status-interval':'1'}),time.monotonic()+15)
        cases=[resource('codex','modded','running','x,}#{pid}','psmux'),resource('grok','unknown','waiting-for-input','界'*10,'psmux')]
        modes={};matrix_cases=[]
        for mode in ('full','basic','plain'):
            requests=[];values=[]
            for window,item in zip(windows,cases):
                shown=project(item,dict(render_mode=mode,ascii=mode!='full',show_model=True,show_provider=True),now=time.time())
                options=expiring_options(shown['options'],observed_at=time.time(),render_mode=mode)
                requests.append(dict(action='write',window=window['window_id'],values=options));values.append(options)
            matrix_cases.append(dict(mode=mode,requests=requests))
            actual=transport.formatting_batch(requests,time.monotonic()+15)
            assert all(not result.get('error') for result in actual),actual
            expansions=[]
            for window,options in zip(windows,values):
                target='source:'+str(window['index'])
                normal=native('display-message','-p','-t',target,options['window-status-format'])['out'].strip()
                selected=native('display-message','-p','-t',target,options['window-status-current-format'])['out'].strip()
                assert ('x,}#{pid}' in normal) if window==windows[0] else ('GK' in normal),(mode,normal)
                assert '[' in selected and ']' in selected,(mode,selected)
                if mode in ('plain','basic'):assert 'colour' not in normal,(mode,normal)
                expansions.append(dict(window=window['window_id'],normal=normal,selected=selected))
            modes[mode]=dict(native_formats=expansions,exact_write_readback=True)
        # Capture an owned attached client, but keep output absence distinct from
        # format-engine success. Never infer pixel rendering from option values.
        matrix=native_directory/'matrix.json';matrix.write_text(json.dumps(dict(identity=identity,cases=matrix_cases)))
        result=subprocess.run([windows_python,winpath(capture_path),'--namespace',namespace,'--session','source','--matrix',winpath(matrix)],text=True,capture_output=True,timeout=30)
        captured=None
        for line in result.stdout.splitlines():
            if line.startswith('{'):captured=json.loads(line)
        attached=dict(status='unqualified',reason='no attached status bar observed',returncode=result.returncode)
        if captured and captured.get('native_console'):
            screens={}
            for mode,case in captured['modes'].items():
                first=case['initial']['text'];changed=case['changed']['text']
                assert 'CX+' in first and 'GK' in first and 'CX+' in changed and 'GK' in changed
                assert '[0' in first and '[1' in changed,(mode,first[-500:],changed[-500:])
                assert '# [bg=red]' in first and '#(echo BAD)' in first,(mode,first[-500:])
                screens[mode]=dict(width=case['initial']['width'],height=case['initial']['height'],
                    selected_and_unselected_cues=True,initial_status_attributes=case['initial']['status_attributes'],
                    changed_status_attributes=case['changed']['status_attributes'],
                    initial_text_sha256=hashlib.sha256(first.encode()).hexdigest(),changed_text_sha256=hashlib.sha256(changed.encode()).hexdigest())
            attached=dict(status='passed',proof='actual owned native Windows console buffer',
                client_pid=captured['client_pid'],client_birth=captured['client_birth'],wrapper_pid=captured['wrapper_pid'],
                client_terminated_and_reaped=captured['client_terminated_and_reaped'],modes=screens)
        else:
            attached['stderr']=result.stderr[-1500:]
        after=transport.snapshot(time.monotonic()+15)
        def continuity(snapshot):return [(w['window_id'],w['name'],[(p['pid'],p['windows_creation_filetime']) for p in w['panes']]) for w in snapshot['windows']]
        assert continuity(before)==continuity(after)
        restored=transport.formatting_batch([dict(action='write',window=w['window_id'],values={k:v['value'] if v['explicit'] else None for k,v in original.items()}) for w,original in zip(windows,originals)],time.monotonic()+15)
        assert restored==originals
        restored_session=transport.formatting('write-session',dict(values={k:v['value'] if v['explicit'] else None for k,v in session.items()}),time.monotonic()+15)
        assert restored_session==session
        native('kill-server');owned=False
        census=native('list-sessions','-F','#{session_id}',check=False);assert not census['out'].strip(),census
        return dict(status='native_format_engine_passed',identity=identity,modes=modes,attached_client=attached,
            capabilities=capabilities('psmux',identity=identity),exact_originals_restored=True,process_and_name_continuity=True,
            final_owned_namespace=census,proof='installed native format expansion and style readback; attached client qualification separately reported')
    finally:
        if owned:native('kill-server',check=False)
        shutil.rmtree(native_directory)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--windows-python');args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='wake-render523-') as directory:
        report=dict(ticket=523,production_touched=False,provider_calls=0,byobu=tmux_acceptance(Path(directory)))
        if args.windows_python:report['psmux']=psmux_acceptance(Path(directory),args.windows_python)
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(status='passed',receipt=str(args.output))))


if __name__=='__main__':main()
