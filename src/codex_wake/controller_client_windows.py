"""Windows owner/DACL validation for the portable OAuth client only."""
import json
import os
from pathlib import Path
import subprocess

# Trusted fixed program; the path arrives as JSON stdin, never executable text.
ACL_SCRIPT=r'''
$ErrorActionPreference='Stop'; $ProgressPreference='SilentlyContinue'
$path=ConvertFrom-Json ([Console]::In.ReadToEnd())
$acl=Get-Acl -LiteralPath $path
$sid=[System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
$owner=$acl.GetOwner([System.Security.Principal.SecurityIdentifier]).Value
$raw=[System.Security.AccessControl.RawSecurityDescriptor]::new($acl.GetSecurityDescriptorBinaryForm(),0)
$rules=@($acl.Access | ForEach-Object { @{sid=$_.IdentityReference.Translate([System.Security.Principal.SecurityIdentifier]).Value; allow=($_.AccessControlType -eq 'Allow'); rights=[int64]$_.FileSystemRights} })
@{current_sid=$sid;owner_sid=$owner;dacl_present=($null -ne $raw.DiscretionaryAcl);rules=$rules} | ConvertTo-Json -Depth 4 -Compress
'''


def check_private_file(path):
    from .controller_client import ClientError
    executable=Path(os.environ.get('SystemRoot',r'C:\Windows'))/'System32/WindowsPowerShell/v1.0/powershell.exe'
    try:
        process=subprocess.run([str(executable),'-NoLogo','-NoProfile','-NonInteractive','-Command',ACL_SCRIPT],
            input=json.dumps(str(path)),text=True,capture_output=True,timeout=10,check=True)
        value=json.loads(process.stdout)
        current=value['current_sid']
        if not isinstance(current,str) or not current.startswith('S-1-') or value['owner_sid']!=current or value['dacl_present'] is not True:
            raise ValueError('owner or DACL unavailable')
        allowed={current,'S-1-5-18','S-1-5-32-544'}
        if not isinstance(value['rules'],list):raise ValueError('DACL unavailable')
        # Read data, generic read/all and ACL ownership changes can expose a token.
        sensitive=0x900C0001
        for rule in value['rules']:
            if rule['allow'] and rule['sid'] not in allowed and int(rule['rights'])&sensitive:
                raise ValueError('broad token read or ACL modification grant')
    except (OSError,subprocess.SubprocessError,ValueError,KeyError,TypeError):
        raise ClientError('token_file_not_private','OAuth token requires current Windows owner and a private readable DACL') from None
