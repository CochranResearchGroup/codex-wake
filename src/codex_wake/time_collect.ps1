# Owned inspection collector. No clock adjustment, service control, or mailbox access.
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$request = [Console]::In.ReadToEnd() | ConvertFrom-Json
function Qpc { return [Diagnostics.Stopwatch]::GetTimestamp() }
function HostBoot { return (Get-CimInstance Win32_OperatingSystem -OperationTimeoutSec 3).LastBootUpTime.ToUniversalTime().Ticks.ToString() }
$boot = HostBoot
$frequency = [Diagnostics.Stopwatch]::Frequency
$start = Qpc
$generation = [Guid]::NewGuid().ToString()
$replies = @()
$stateDirectory = Join-Path $env:LOCALAPPDATA 'codex-wake\time-inspection'
[IO.Directory]::CreateDirectory($stateDirectory) | Out-Null
function SaveCache($path, $value) {
    $temporary = $path + '.' + [Guid]::NewGuid().ToString() + '.tmp'
    try {
        $bytes = [Text.Encoding]::UTF8.GetBytes(($value | ConvertTo-Json -Depth 8 -Compress))
        $stream = [IO.File]::Open($temporary, 'CreateNew', 'Write', 'None')
        try { $stream.Write($bytes,0,$bytes.Length); $stream.Flush($true) } finally { $stream.Dispose() }
        if ([IO.File]::Exists($path)) { [IO.File]::Replace($temporary,$path,($temporary+'.bak')); [IO.File]::Delete($temporary+'.bak') }
        else { [IO.File]::Move($temporary,$path) }
    } finally { if ([IO.File]::Exists($temporary)) { [IO.File]::Delete($temporary) } }
}
$lease = $null
try {
    # Per-user exclusive lease also serializes collectors in separate WSL distributions.
    $lease = [IO.File]::Open((Join-Path $stateDirectory 'lease'), 'OpenOrCreate', 'ReadWrite', 'None')
    $cachePath = Join-Path $stateDirectory 'cache.json'
    $cache = $null
    $invalidCache = $false
    if ([IO.File]::Exists($cachePath)) {
        try { $cache = [IO.File]::ReadAllText($cachePath) | ConvertFrom-Json } catch { $invalidCache = $true }
    }
    $now = Qpc
    if ($cache -and (-not $cache.host_boot -or -not $cache.generation -or -not $cache.frequency -or -not $cache.attempt)) { $invalidCache = $true }
    if ($cache -and $cache.host_boot -eq $boot -and ($cache.frequency -ne $frequency -or $now -lt $cache.attempt)) { throw 'elapsed_authority_changed' }
    if ($invalidCache) {
        $rejected = @($request.hosts | ForEach-Object { @{host=$_;error='cache_invalid_backoff'} })
        $cache = @{host_boot=$boot;guest_boot=$request.guest_boot;frequency=$frequency;attempt=$now;generation=$generation;replies=$rejected}
        SaveCache $cachePath $cache
    }
    $rateLimited = $cache -and $cache.host_boot -eq $boot -and $cache.frequency -eq $frequency -and $now -ge $cache.attempt -and (($now-$cache.attempt)/$frequency) -lt 64
    if ($rateLimited) {
        if ($cache.guest_boot -eq $request.guest_boot) {
            $replies = @($cache.replies)
            $generation = $cache.generation
        } else {
            foreach ($name in $request.hosts) { $replies += @{host=$name;error='rate_limited_after_guest_restart'} }
        }
    } else {
        # Persist attempt before acquisition: failure/crash cannot create a retry storm.
        $cache = @{host_boot=$boot;guest_boot=$request.guest_boot;frequency=$frequency;attempt=$now;generation=$generation;replies=@()}
        SaveCache $cachePath $cache
        foreach ($name in $request.hosts) {
            $udp = $null
            try {
                if (@('time.cloudflare.com','time.nist.gov','ntp.alastyr.com') -notcontains $name) { throw 'endpoint_not_admitted' }
                if (((Qpc)-$start)/$frequency -gt 12) { throw 'round_deadline' }
                $dns = [Net.Dns]::BeginGetHostAddresses($name, $null, $null)
                try {
                    if (-not $dns.AsyncWaitHandle.WaitOne(2000)) { throw 'dns_timeout' }
                    $addresses = [Net.Dns]::EndGetHostAddresses($dns)
                } finally { $dns.AsyncWaitHandle.Close() }
                $ip = @($addresses | Where-Object AddressFamily -eq InterNetwork)[0]
                if (-not $ip) { throw 'dns_no_ipv4' }
                $udp = [Net.Sockets.UdpClient]::new([Net.Sockets.AddressFamily]::InterNetwork)
                $udp.Connect($ip,123)
                $udp.Client.ReceiveTimeout = 2000
                $udp.Client.SendTimeout = 2000
                $token = New-Object byte[] 8
                $random = [Security.Cryptography.RandomNumberGenerator]::Create()
                try { $random.GetBytes($token) } finally { $random.Dispose() }
                $packet = New-Object byte[] 48
                $packet[0] = 0x23
                [Array]::Copy($token,0,$packet,40,8)
                $sent = Qpc
                $udp.Send($packet,48) | Out-Null
                $peer = [Net.IPEndPoint]::new([Net.IPAddress]::Any,0)
                $answer = $udp.Receive([ref]$peer)
                $received = Qpc
                $replies += @{host=$name;peer=$peer.Address.ToString();sent=$sent;received=$received;token=[Convert]::ToBase64String($token);packet=[Convert]::ToBase64String($answer)}
            } catch {
                $replies += @{host=$name;error=$_.Exception.Message}
            } finally { if ($udp) { $udp.Dispose() } }
        }
        $cache.replies = $replies
        SaveCache $cachePath $cache
    }
} catch {
    if ($_.Exception.Message -eq 'elapsed_authority_changed') { throw }
    foreach ($name in $request.hosts) { $replies += @{host=$name;error='collector_lease_unavailable'} }
} finally { if ($lease) { $lease.Dispose() } }
$window = @{service_running=$false;error='windows_unsynchronized'}
try {
    $service = Get-Service W32Time
    if ($service.Status -eq 'Running') {
        $process = [Diagnostics.Process]::new()
        $process.StartInfo.FileName = Join-Path $env:SystemRoot 'System32\w32tm.exe'
        $process.StartInfo.Arguments = '/query /status /verbose'
        $process.StartInfo.UseShellExecute = $false
        $process.StartInfo.RedirectStandardOutput = $true
        $process.StartInfo.RedirectStandardError = $true
        $process.StartInfo.CreateNoWindow = $true
        try {
            $process.Start() | Out-Null
            $stdout = $process.StandardOutput.ReadToEndAsync()
            $stderr = $process.StandardError.ReadToEndAsync()
            if (-not $process.WaitForExit(2000)) { $process.Kill(); throw 'windows_status_timeout' }
            if ($process.ExitCode -ne 0) { throw 'windows_status_unavailable' }
            $status = $stdout.Result
            # Unknown/localized formats fail closed, never guess successful synchronization.
            function Field($name) {
                $match = [regex]::Match($status, '(?m)^'+[regex]::Escape($name)+':\s*(.+)$')
                if (-not $match.Success) { throw 'windows_status_format_unqualified' }
                return $match.Groups[1].Value.Trim()
            }
            $leap = [int]([regex]::Match((Field 'Leap Indicator'), '^\d+').Value)
            $stratum = [int]([regex]::Match((Field 'Stratum'), '^\d+').Value)
            $dispersion = [double]::Parse((Field 'Root Dispersion').TrimEnd('s'), [Globalization.CultureInfo]::InvariantCulture)
            $offset = [double]::Parse((Field 'Phase Offset').TrimEnd('s'), [Globalization.CultureInfo]::InvariantCulture)
            $lastSync = [DateTime]::Parse((Field 'Last Successful Sync Time'), [Globalization.CultureInfo]::CurrentCulture).ToUniversalTime()
            $beforeUtc = Qpc
            $utc = [DateTime]::UtcNow
            $sampled = Qpc
            if (($sampled-$beforeUtc)/$frequency -gt 0.001) { throw 'windows_utc_sample_delayed' }
            $window = @{service_running=$true;utc=($utc.Ticks-621355968000000000)/10000000.0;sampled=$sampled;source=(Field 'Source');leap=$leap;stratum=$stratum;root_dispersion=$dispersion;phase_offset=$offset;sync_age=($utc-$lastSync).TotalSeconds+1}
        } finally { $process.Dispose() }
    }
} catch { $window = @{service_running=$false;error=$_.Exception.Message} }
$bootEnd = HostBoot
$end = Qpc
@{request_id=$request.request_id;guest_boot=$request.guest_boot;host_boot=$boot;host_boot_end=$bootEnd;frequency=$frequency;start=$start;end=$end;generation=$generation;replies=@($replies);windows=$window} | ConvertTo-Json -Depth 8 -Compress
