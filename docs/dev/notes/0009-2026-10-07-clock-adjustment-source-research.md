# Clock adjustment source research — 2026-10-07

## Question, scope and stopping criterion

What evidence identifies the source of the unusual Linux coarse clock adjustment? Research uses local service/configuration readbacks, a bounded read-only observation, official systemd source and Microsoft WSL source. Output is this one Markdown note. Stop after one observation spanning approximately a minimum NTP polling interval and source comparison of the enabled synchronization paths; return attribution gaps without changing services, clocks, mailbox state or installing tracing tools.

## Result

**The setter is not identified.** Current behavior is independently observed, and the enabled synchronization paths are documented below. Neither enabled-service status nor source capability establishes which caller last changed the coarse setting. Do not disable a service or reconcile the mailbox checkpoint on that inference.

## Local evidence

Evidence directory: `/home/ecochran76/.local/state/codex-wake/clock-research/20261007-setter/`.

- `packages.txt`: installed systemd and systemd-timesyncd version `255.4-1ubuntu8.17`.
- `timesync-unit.txt`: systemd-timesyncd running with CAP_SYS_TIME. A vendor WSL drop-in explicitly enables the service in WSL, with a comment about synchronization after host suspension.
- `timesync-config.txt`: no active custom settings in the displayed configuration; default fallback ntp.ubuntu.com.
- `timesync-status.txt`: selected NTP server ntp.ubuntu.com, minimum/current polling interval 32 seconds. The live status read in this investigation showed an offset near -1.997 seconds and fine frequency 0 ppm. This is a point-in-time NTP status, not proof of the original historical UTC error.
- `kernel-parameters.txt`: command line includes `hv_utils.timesync_implicit=1`, and the live module parameter is `Y`.
- `/etc/wsl.conf` readback: systemd enabled; no clock adjustment setting present.
- Bounded search of `/etc/cron.d`, `/etc/cron.daily`, `/etc/systemd/system`, `/etc/init.d` and `/etc/wsl.conf` found no literal ADJ_TICK, adjtimex or clock_adjtime reference. This excludes only matching text in those locations, not other programs or namespaces.
- `clock-log.txt`: journald repeatedly reports backward time jumps. The timesyncd-specific journal query returned no entries; absence is not evidence that the service never adjusted time.

## Bounded direct measurement

`observe.c` extends the preceding C probe to 46 samples and reads adjustment settings before each clock sample using zero-initialized `struct timex` with modes zero. It requests no clock changes. libc and direct kernel clock calls are both retained. Compilation with `cc -Wall -Wextra -O2` and execution returned zero. `observe.jsonl` preserves raw samples; `observation-summary.json` is derived from them.

| Quantity | Observed value |
| --- | ---: |
| Coarse tick at every sampled point | 11000 microseconds |
| Fine frequency at every sampled point | 0 ppm |
| libc monotonic elapsed | 45.013995736 seconds |
| libc raw elapsed | 40.921814289 seconds |
| libc wall elapsed | 42.282089233 seconds |
| direct syscall monotonic elapsed | 45.014000972 seconds |
| direct syscall raw elapsed | 40.921818969 seconds |
| direct syscall wall elapsed | 42.282094479 seconds |

Monotonic/raw elapsed ratio is approximately 1.100000. At sample 23, wall elapsed advanced 2.731906643 seconds less than monotonic elapsed over that interval. This is evidence of a wall-clock correction relative to monotonic time, but does not identify its caller. No coarse-tick change occurred at the sampled points; settings could change between samples. Requested sleep duration is only pacing, not a physical-time reference.

## Primary-source comparison

### systemd-timesyncd

Upstream v255 `manager_adjust_clock` uses ADJ_OFFSET for small offsets, and ADJ_SETOFFSET for larger offsets (threshold 0.4 seconds). It calls clock_adjtime and reports the returned fine frequency. This inspected routine does not request ADJ_TICK. Therefore it can explain a mechanism for wall corrections, but its upstream source does not identify a coarse-tick setter. [Official systemd v255 source](https://github.com/systemd/systemd/blob/v255/src/timesync/timesyncd-manager.c#L221)

Qualification: installed Ubuntu packaging is 255.4-1ubuntu8.17, not the unpatched upstream v255 build. An attempted Ubuntu source URL could not be retrieved through the web tool. This research therefore does not assert that every installed Ubuntu code path has been excluded.

### WSL Hyper-V integration

The matching kernel tag's hv_util.c exposes timesync_implicit. Its implicit-sync logic schedules host-time synchronization if guest wall time is at least five seconds behind. Explicit SYNC messages also schedule synchronization. The work function calls do_settimeofday64; this inspected path does not set ADJ_TICK. Enabled host synchronization is not proof it changed the coarse setting or caused the observed backward correction. [Matching Microsoft WSL kernel source](https://github.com/microsoft/WSL2-Linux-Kernel/blob/linux-msft-wsl-6.6.87.2/drivers/hv/hv_util.c#L282)

Microsoft WSL userspace init.cpp and SecCompDispatcher.cpp were also inspected at source commit `c40740d870fb6441ddbe5bb4042e1aaf0f9697b7`. The bounded literal check found no adjtimex, ADJ_TICK, clock_adjtime or clock_settime reference in those two files. This is not a repository-wide exclusion or an installed-version match. Saved copies and tree/path provenance are in the evidence directory. [Microsoft WSL source](https://github.com/microsoft/WSL/tree/c40740d870fb6441ddbe5bb4042e1aaf0f9697b7/src/linux/init)

### Meaning of the coarse setting

The matching WSL kernel's ntp_update_frequency combines coarse tick, fine frequency and boot adjustment; process_adjtimex_modes handles ADJ_TICK separately from ADJ_FREQUENCY. A zero fine-frequency report therefore does not imply zero total rate adjustment. The observed ratio is consistent with a coarse rate adjustment, but consistency does not identify its historical setter. [Matching kernel timekeeping source](https://github.com/microsoft/WSL2-Linux-Kernel/blob/linux-msft-wsl-6.6.87.2/kernel/time/ntp.c#L242)

## Attribution limits

The session runs as an unprivileged user. `sudo -n true` returned that a password is required. The perf wrapper reports no matching tool for the running WSL kernel; bpftrace is absent and perf_event_paranoid is 2. No privileged tracer was started and no packages or kernel settings were changed. Read-only WSL management queries (`--list --running` and `--version`) returned UtilAcceptVsock accept4 timeout errors, so they provided no inventory/version evidence. No reboot, shutdown or retry escalation was performed.

These limits prevent this bounded investigation from naming a live adjustment caller. They do not prove there is no caller. Existing setting plus snapshot reads cannot reconstruct when it was originally written.

## Recommended next step

Capture adjustment writes with caller identity and requested modes/tick/frequency in a privileged, bounded trace, without altering synchronization settings. Include both adjtimex and clock_adjtime, and distinguish query-only calls from requests to change state. Expand namespace/distribution inventory only if evidence points there. If no ADJ_TICK write occurs, report that result rather than inferring an owner from the active services. Do not migrate timer clocks or advance the mailbox checkpoint before the result is reconciled.

Only this note was added by this turn. Earlier research and the unrelated untracked handoff note remain intact. No product or runtime configuration was changed.

Memory disposition: unavailable; no reviewed Codex Wake Graphiti target group in established context. A non-write receipt is recorded against this note.
