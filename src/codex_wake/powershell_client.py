"""Render a native PowerShell client with private WSL connection bootstrap."""
import os
from pathlib import Path
import sys
import subprocess

_TEMPLATE=r'''[CmdletBinding(PositionalBinding=$false)]
param(
 [string]$Distro=@@DISTRO@@,
 [string]$WakeCli=@@CLI@@,
 [string]$WakeRoot=@@ROOT@@,
 [Parameter(Position=0,ValueFromRemainingArguments=$true)][string[]]$Arguments
)
$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'
[Console]::OutputEncoding=New-Object System.Text.UTF8Encoding($false)
$OutputEncoding=[Console]::OutputEncoding
$client=$null
$retryKey=$null
try {
 # Bootstrap is captured privately; the bearer never appears in command arguments.
 $bootstrap=@('-d',$Distro,'--exec',$WakeCli,'--wake-root',$WakeRoot,'control','connection')
 # Capture both streams as private objects. PowerShell5.1 wraps native stderr
 # in ErrorRecord; letting Stop handle it would expose arbitrary native text.
 $ErrorActionPreference='Continue'
 try { $bootstrapOutput=@(& wsl.exe @bootstrap 2>&1); $bootstrapExit=$LASTEXITCODE }
 catch { throw 'WSL bootstrap failed: wsl_exit=unavailable category=launch_failed' }
 finally { $ErrorActionPreference='Stop' }
 $privateText=($bootstrapOutput | Where-Object { $_ -isnot [System.Management.Automation.ErrorRecord] } | Out-String)
 if ($bootstrapExit -ne 0) {
  $category='unknown'
  try {
   $privateError=($bootstrapOutput | Where-Object { $_ -is [System.Management.Automation.ErrorRecord] } | ForEach-Object { $_.Exception.Message }) -join "`n"
   $nativeError=$privateError | ConvertFrom-Json
   if ($nativeError.error.code -in @('controller_unavailable','invalid_argument','configuration_unavailable')) { $category=[string]$nativeError.error.code }
  } catch { $category='unknown' }
  throw ('WSL bootstrap failed: wsl_exit='+$bootstrapExit+' category='+$category)
 }

 try { $connection=$privateText | ConvertFrom-Json; $address=[Uri]$connection.url }
 catch { throw 'WSL bootstrap failed: wsl_exit=0 category=invalid_connection' }
 if ($address.Scheme -ne 'http' -or $address.Host -notin @('127.0.0.1','localhost','::1')) { throw 'Local controller endpoint must be loopback.' }
 Add-Type -AssemblyName System.Net.Http
 $handler=New-Object System.Net.Http.HttpClientHandler
 $handler.UseProxy=$false
 $client=New-Object System.Net.Http.HttpClient($handler)
 $client.Timeout=[System.Threading.Timeout]::InfiniteTimeSpan
 $client.DefaultRequestHeaders.Authorization=New-Object System.Net.Http.Headers.AuthenticationHeaderValue('Bearer',[string]$connection.token)
 $command=@($Arguments)
 if ($command.Count -gt 0 -and $command[0] -notin @('control','governor')) { $command=@('control')+$command }
 $retryKey=$null
 $keyFlag=$null
 if ($command.Count -ge 2 -and $command[0] -eq 'control' -and $command[1] -in @('prompt','create','load')) {
  $keyFlag='--idempotency-key'
 } elseif ($command.Count -ge 2 -and $command[0] -eq 'governor' -and $command[1] -ne 'status') {
  $keyFlag='--request-id'
 }
 if ($keyFlag) {
  for ($index=0;$index -lt $Arguments.Count;$index++) {
   if ($Arguments[$index].StartsWith($keyFlag+'=')) { $retryKey=$Arguments[$index].Substring($keyFlag.Length+1) }
   elseif ($Arguments[$index] -eq $keyFlag -and $index+1 -lt $Arguments.Count) { $retryKey=$Arguments[$index+1] }
  }
  if ($null -eq $retryKey) {
   $retryKey=[Guid]::NewGuid().ToString('N');$Arguments=@($Arguments)+@($keyFlag,$retryKey)
  }
 }
 $payload=@{arguments=@($Arguments)} | ConvertTo-Json -Depth 32 -Compress
 $content=New-Object System.Net.Http.ByteArrayContent(,[Text.Encoding]::UTF8.GetBytes($payload))
 $content.Headers.ContentType=New-Object System.Net.Http.Headers.MediaTypeHeaderValue('application/json')
 $request=New-Object System.Net.Http.HttpRequestMessage([System.Net.Http.HttpMethod]::Post,($connection.url+'/cli'))
 $request.Content=$content
 $response=$client.SendAsync($request,[System.Net.Http.HttpCompletionOption]::ResponseHeadersRead).GetAwaiter().GetResult()
 if (-not $response.IsSuccessStatusCode) { throw ('Local controller rejected the request: HTTP '+[int]$response.StatusCode) }
 $reader=New-Object System.IO.StreamReader($response.Content.ReadAsStreamAsync().GetAwaiter().GetResult(),[Text.Encoding]::UTF8)
 $code=3
 $terminalReceipt=$false
 while (($line=$reader.ReadLine()) -ne $null) {
  $frame=$line | ConvertFrom-Json
  if ($frame.PSObject.Properties.Name -contains 'stdout') { [Console]::Out.Write([string]$frame.stdout) }
  if ($frame.PSObject.Properties.Name -contains 'stderr') { [Console]::Error.Write([string]$frame.stderr) }
  if ($frame.PSObject.Properties.Name -contains 'operation_id') { $script:LastWakeOperation=[string]$frame.operation_id }
  if ($frame.PSObject.Properties.Name -contains 'exit_code') { $code=[int]$frame.exit_code; $terminalReceipt=$true; break }
 }
 $reader.Dispose()
 if (-not $terminalReceipt -and $retryKey) { [Console]::Error.WriteLine('Connection ended without an exit receipt; reconcile with '+$keyFlag+' '+$retryKey+'.') }
 exit $code
} catch {
 [Console]::Error.WriteLine('Codex Wake client: '+$_.Exception.Message)
 if ($retryKey) { [Console]::Error.WriteLine('No new intent is needed: reuse '+$keyFlag+' '+$retryKey+' to reconcile submission.') }
 exit 2
} finally {
 if ($null -ne $client) { $client.Dispose() }
}
'''


def render(root,cli=None,distro=None):
    def literal(value):return "'"+str(value).replace("'","''")+"'"
    if distro is None:
        distro=os.environ.get('WSL_DISTRO_NAME')
        if distro is None:
            try:
                unc=subprocess.check_output(['wslpath','-w',str(Path.home())],text=True,timeout=3).strip().split('\\')
                if len(unc)>3 and unc[2].lower() in ('wsl.localhost','wsl$'):distro=unc[3]
            except (OSError,subprocess.SubprocessError):pass
        if distro is None:raise ValueError('select the WSL distribution explicitly when rendering the PowerShell client')
    values={'@@ROOT@@':root,'@@CLI@@':cli or Path(sys.executable).with_name('codex-wake'),'@@DISTRO@@':distro}
    value=_TEMPLATE
    for key,item in values.items():value=value.replace(key,literal(item))
    return value
