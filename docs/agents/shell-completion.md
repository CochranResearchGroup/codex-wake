# Shell completion and installation

Use the supported user installer to install Wake and activate Bash/Zsh completion
in one step:

```sh
bash scripts/install.sh
# Select one shell, or install the package without shell configuration:
bash scripts/install.sh --shell zsh
bash scripts/install.sh --no-completion
```

The installer uses `uv tool install --force`, locates that installation through
`uv tool dir --bin`, then invokes its `codex-wake completion install`. A completion
failure returns nonzero and explains that package installation already succeeded.
Plain `pip install` and `uv tool install` cannot safely mutate a user's shell
configuration during package installation; follow either with
`codex-wake completion install`, or use the installer above. Building/importing a
wheel never changes shell configuration.

```sh
codex-wake completion bash              # print generated Bash script
codex-wake completion zsh               # print generated Zsh script
codex-wake completion install           # install/activate both shells
codex-wake completion install --shell bash
codex-wake completion uninstall         # remove unchanged Wake-owned content
```

Completion derives command names, flags and choices from the installed parser.
Account suggestions read only the selected root's `controller-accounts.toml`;
pass `--wake-root PATH` or `--wake-root=PATH` before the command. Aliases and
explicit account admission are respected. Tab completion does not read account
credentials, call providers, start daemons or invoke account operations.

Bash scripts live at `~/.local/share/bash-completion/completions/codex-wake`;
Zsh scripts at `~/.zsh/completions/_codex-wake`. Installation adds a small marked
block to `.bashrc`/`.zshrc` where an explicit source line is not already present.
Open a new shell or reload its startup file afterward; the installer cannot
change the environment of an already-running parent shell.

Installation records ownership under `~/.local/state/codex-wake/completion`.
Repeated installation refreshes unchanged owned content. Symlinked/unowned paths,
ambiguous activation markers and edited completion files are refused without
overwriting them. Uninstall retains edited content and reports its paths;
unrelated startup-file text and explicit user activation lines remain untouched.
`--home PATH` is available for explicit alternate/disposable user homes.
