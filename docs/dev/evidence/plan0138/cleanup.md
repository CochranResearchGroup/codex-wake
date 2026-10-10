# Plan0138 owned-runtime cleanup

Both acceptance actors completed their relevant turns. Recipient pane%213/window
@201 was already closed; its original history and seed remain readable. Sender
pane%212/window@200 was independently read back idle with original PID87563/start
ticks27331886 and one exact attachment. Its ordinary close returned a guard error;
public pending_thread_work inspection reported inventory_unavailable. No affected
wake was found by the final close operation. Under the user's explicit owned-test
tab cleanup instruction, public sessions close pane:%212 --force closed only that
verified pane and preserved the conversation and all mailbox/wake records.
Private sender-close-forced.json records the inventory warning, exact attachment
and conversation=preserved. No failed mailbox result was fabricated or discarded.

Worker4 finished normally: submitted1/ticks4. Workers1/2/3 were already stopped
at their owned checkpoints. Disposable native supervisor50807 was verified by
its private Plan0138 argv/process group and stopped with SIGTERM. Fresh OS
readback found none of PIDs50807,87563,98188,36338,15781,28907,72816 remaining;
fresh tmux inventory found neither test pane/window. Bus is paused. Private
cleanup-stopped.json,cleanup-pause.json and worker4.log preserve the receipts.
Other Byobu tabs, the stock shared Codex daemon and LitScout services were not
stopped or changed. Installed global entrypoints remain v0.10.1 until release.
