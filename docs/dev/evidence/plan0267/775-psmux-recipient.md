# #775 native Windows psmux recipient recovery

The Windows owner ran under its normal Windows account with native Python
3.14.3, psmux 3.4.0 build `20aa1d7`, and the installed stock Codex CLI
0.169.1. The candidate Python files came from `f6c1d11e` for tab loss and
busy detachment, and `2a27b2c4` for the slot and server-loss cases. The
fixture recorded the exact Windows account SID digest, Codex profile
directory identity, harness and psmux hashes, app-server listener PID and
creation time, model provider and original thread. A loopback Responses
fixture served the real Codex runtime without an external model call.

WSL admitted each scheduled message via the public `message-owner send`
command and shared PostgreSQL. The Windows owner dispatched through the
documented native psmux adapter. For each case, PostgreSQL retained the
original eligibility, expiry, recipient and one submitted receipt. The
original Codex thread's native history had one matching user item and its
Windows rollout retained that exact message UUID as `client_id`.

| Case | Observed result |
| --- | --- |
| Tab-only loss with a later window | Thread `01a21136-cb1c-73b1-ade8-361ddb035de7` resumed at index 2 in the same psmux server. Anchor index 0 and later index 4 retained their names, panes, processes and focus state. Message `c4dc34db-20cf-49c5-8653-01292b399ae2` had receipt `01a21137-e8ea-75b0-b1b1-5b106296e03e`. |
| Busy detached turn | Once the scheduled message was eligible, Windows reported `held_recipient/busy` and the psmux presentation remained absent. The original turn ran to completion. The same thread then resumed at index 2 and accepted message `191e962e-fded-4369-b283-3edd1f072012` once, with receipt `01a21139-92d1-7193-9b1c-13a9cbc4a3b4`. |
| Matching idle placeholder | Thread `01a2113d-018a-7652-ae77-d72727907135` took index 2. The prior shell in window `@4`, PID 86976, creation time 134400591556666620, moved intact to index 5. Unrelated panes and focus stayed pinned. Message `6d9f21f8-b2d6-4079-bde8-bf7d582c60c8` had receipt `01a2113e-2a95-78b0-ab2d-184fca62e6eb`. |
| Unrelated occupant | The unrelated shell in index 2 and the prior shell, anchor and later windows remained unchanged. The original same thread resumed at spare index 6. Message `0ce41a14-dd30-4c32-8695-f99470f32efa` had receipt `01a2113f-4ba3-7d41-bd7a-0cf0378a15ea`. |
| Complete psmux server loss | The server creation time changed from 134400591422013280 to 134400593315799526. The pinned Codex app server remained the same, the original same thread resumed at index 2, and the independent guard namespace's window and pane snapshot matched exactly. Message `9cb50da7-8649-4219-a858-44e3859ef7c4` had receipt `01a2113f-fbd8-76f3-95a8-48e3ffedd216`. |

An earlier native placeholder run observed a focus change after
`swap-window -d`. The adapter held before submission. The follow-up
restored the previous exact focus and rechecked the displaced shell.

Local validation used disposable PostgreSQL with
`CODEX_WAKE_TEST_MESSAGE_DB_DSN` set in the test process environment.

```sh
PYTHONPATH=src:tests python -m unittest test_tab_psmux test_tab_reattach \
  test_tab_recovery_restored_slots test_message_owner -q
```

All 13 focused tests passed. Ruff 0.14.2 passed the undefined-name checks
and the full F checks for the two new modules. Qualification used a
temporary native stock Codex profile and private candidate source
prefix, with production credentials and services outside the fixture.
Codex app-server loss and Windows reboot were separate from the psmux
server-loss case.

The final native process readback covered 16 fixture namespaces. It found
no fixture psmux server, no marked fixture Codex process and no listener
on the fixture app-server port 57475.
