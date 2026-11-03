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
 $privateText=(& wsl.exe @bootstrap 2>$null | Out-String)
 if ($LASTEXITCODE -ne 0) { throw 'Start the WSL local controller before using this client.' }
 $connection=$privateText | ConvertFrom-Json
 $address=[Uri]$connection.url
 if ($address.Scheme -ne 'http' -or $address.Host -notin @('127.0.0.1','localhost','::1')) { throw 'Local controller endpoint must be loopback.' }
 Add-Type -AssemblyName System.Net.Http
 $handler=New-Object System.Net.Http.HttpClientHandler
 $handler.UseProxy=$false
 $client=New-Object System.Net.Http.HttpClient($handler)
 $client.Timeout=[System.Threading.Timeout]::InfiniteTimeSpan
 $client.DefaultRequestHeaders.Authorization=New-Object System.Net.Http.Headers.AuthenticationHeaderValue('Bearer',[string]$connection.token)
 $command=@($Arguments)
 if ($command.Count -gt 0 -and $command[0] -ne 'control') { $command=@('control')+$command }
 $retryKey=$null
 if ($command.Count -ge 2 -and $command[0] -eq 'control' -and $command[1] -eq 'prompt') {
  for ($index=0;$index -lt $Arguments.Count;$index++) {
   if ($Arguments[$index].StartsWith('--idempotency-key=')) { $retryKey=$Arguments[$index].Substring(18) }
   elseif ($Arguments[$index] -eq '--idempotency-key' -and $index+1 -lt $Arguments.Count) { $retryKey=$Arguments[$index+1] }
  }
  if ($null -eq $retryKey) {
   $retryKey=[Guid]::NewGuid().ToString('N');$Arguments=@($Arguments)+@('--idempotency-key',$retryKey)
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
 while (($line=$reader.ReadLine()) -ne $null) {
  $frame=$line | ConvertFrom-Json
  if ($frame.PSObject.Properties.Name -contains 'stdout') { [Console]::Out.Write([string]$frame.stdout) }
  if ($frame.PSObject.Properties.Name -contains 'stderr') { [Console]::Error.Write([string]$frame.stderr) }
  if ($frame.PSObject.Properties.Name -contains 'operation_id') { $script:LastWakeOperation=[string]$frame.operation_id }
  if ($frame.PSObject.Properties.Name -contains 'exit_code') { $code=[int]$frame.exit_code; break }
 }
 $reader.Dispose()
 exit $code
} catch {
 [Console]::Error.WriteLine('Codex Wake client: '+$_.Exception.Message)
 if ($retryKey) { [Console]::Error.WriteLine('No new intent is needed: reuse --idempotency-key '+$retryKey+' to reconcile submission.') }
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
