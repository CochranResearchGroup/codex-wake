# Clock measurement research — 2026-10-07

## Question and research boundary

Does the saved discrepancy prove that the workstation is hours wrong, and can the observed clock-rate difference be reproduced independently of Python and Windows interop?

Primary sources: official Python documentation, Linux man-pages, Microsoft’s source for the installed WSL kernel version, and direct read-only measurements. Output: this single findings note. Stop after checking clock semantics and one independent C/kernel-call replication; do not investigate setters, change clock settings, reset the mailbox checkpoint, or migrate timers in this task.

## Findings

The claim that the workstation’s current civil time is hours wrong is **not established**. A difference between accumulated wall-clock and monotonic intervals is not a measurement of current UTC accuracy. My earlier wording conflated these quantities.

A current difference between Linux adjusted and raw elapsed clocks **is reproduced** independently of Python and Windows interop. The C program uses the system headers, calls both libc `clock_gettime` and direct `syscall(SYS_clock_gettime, ...)`, and reads `adjtimex` with `modes = 0`. The latter reads settings without requesting changes. [Linux adjtimex documentation](https://man7.org/linux/man-pages/man2/adjtimex.2.html)

| Measurement | libc elapsed seconds | direct syscall elapsed seconds |
| --- | ---: | ---: |
| CLOCK_REALTIME | 10.002684355 | 10.002691269 |
| CLOCK_MONOTONIC | 10.002684294 | 10.002690967 |
| CLOCK_MONOTONIC_RAW | 9.116799093 | 9.116804773 |

Eleven samples were collected. Maximum differences between nearby libc and syscall readings were below 9 microseconds. Monotonic elapsed divided by raw elapsed was 1.097170640, about 9.717% greater during this sample. Reads are sequential, not simultaneous; their microsecond spacing cannot account for the approximately 0.886-second endpoint discrepancy. `nanosleep` only paces samples: its requested duration is not used as a reference for elapsed-time accuracy. This comparison does not independently certify either counter against physical UTC.

Private reproducible evidence: `/home/ecochran76/.local/state/codex-wake/clock-research/20261007/probe.c`, compiled `probe`, raw `probe.jsonl`, and derived `summary.json`. Compilation with `cc -Wall -Wextra -O2` and execution returned zero without warnings. No clock-setting operation is present.

## What the primary sources establish

Linux CLOCK_MONOTONIC cannot jump backward, but its rate can be adjusted. CLOCK_MONOTONIC_RAW omits frequency adjustment. Both exclude suspension; CLOCK_BOOTTIME includes suspension and otherwise follows monotonic semantics. Choosing a timer therefore requires an explicit suspension contract. [Linux clock_gettime documentation](https://man7.org/linux/man-pages/man2/clock_gettime.2.html)

Python’s `get_clock_info().adjustable = False` concerns discontinuous clock changes; it does not exclude gradual NTP rate adjustments. Treating that flag as proof of an unadjusted rate would be incorrect. [Python time documentation](https://docs.python.org/3/library/time.html#time.get_clock_info)

The running kernel identifies as `6.6.87.2-microsoft-standard-WSL2`. In Microsoft’s matching source tag, `ntp_update_frequency` combines the coarse `tick_usec` setting with the separate fine frequency component and boot adjustment. `ADJ_TICK` changes `tick_usec`; the fine-frequency clamp does not clamp this separate coarse setting. Consequently a small reported fine-frequency value alone does not establish a small total rate adjustment. This is a supported mechanism, not evidence of a particular caller. [Matching WSL kernel ntp.c](https://github.com/microsoft/WSL2-Linux-Kernel/blob/linux-msft-wsl-6.6.87.2/kernel/time/ntp.c)

The kernel defines nominal `USER_TICK_USEC` from `USER_HZ`; this software accounting quantity must not be described as a CPU oscillator tick. [Matching kernel jiffies.h](https://github.com/microsoft/WSL2-Linux-Kernel/blob/linux-msft-wsl-6.6.87.2/include/linux/jiffies.h)

## Configuration observations and limits

The C/system-header query reported `tick = 11000` microseconds and fine frequency `0 ppm` at the beginning of the new sample. Its struct size was 208 bytes and tick field offset 88. Yesterday’s saved Python/ctypes query reported `tick = 10288` microseconds and fine frequency approximately `-10.355 ppm`. These are different observations at different times. The new result establishes that the unusual tick value is not solely an artifact of the earlier hand-declared Python struct. It does not establish a constant setting throughout either sample or the original failure interval. The approximately 9.717% measured difference should not be rounded into an exact 10% model.

Yesterday’s saved streaming comparison reported Windows QPC elapsed 35.410899 seconds, Linux raw 35.344703, and Linux monotonic 36.315090. Interop transport and scheduling affect the endpoint comparisons. The new same-process libc/syscall comparison removes that dependency when establishing the adjusted/raw discrepancy.

Earlier records are preserved in `/home/ecochran76/.local/state/codex-wake/clock-diagnosis/20261006/windows-export/`, specifically `simultaneous-clock-summary.json` and `linux-adjtimex-readonly.json`, both read in this research turn.

**Unknown:** who changed the adjustment setting; when it changed; the complete history of adjustments, suspension and time steps; and how much each contributed to the original stored-checkpoint discrepancy. This task does not establish the original historical root cause or current absolute Windows UTC error.

## Consequence for Codex Wake

The current counter discrepancy is real under an independent measurement method. It does not justify presenting the full historical discrepancy as proved clock-rate drift. My earlier recommendation to migrate timers to RAW was premature: suspension behavior, persisted deadlines and restart semantics must be evaluated first. Keep runtime behavior unchanged while these facts are reviewed.

Only this research note was added to the repo. No runtime, mailbox, clock, service or installed command was changed. The existing untracked Plan0101 handoff note was preserved.

Memory disposition: unavailable; no reviewed Codex Wake Graphiti target group is available in this task’s established context. Record a non-write receipt against this note.
