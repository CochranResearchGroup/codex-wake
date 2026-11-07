"""Parser-derived shell completion; candidates observe local registry metadata only."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shlex
import stat
import sys
import tomllib

_NAME = re.compile(r'[A-Za-z0-9_.-]{1,128}\Z')


def _accounts(root):
    """Do not resolve accounts or inspect their homes to complete a name."""
    path = Path(root) / 'controller-accounts.toml'
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, 'rb') as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > 262144:
                return []
            data = tomllib.loads(stream.read(262145).decode())
        profiles = data.get('profiles', {})
        prefix = profiles.get('account_prefix', 'codex-')
        if not isinstance(prefix, str) or not prefix:
            return []
        known = profiles.get('known_profiles', [])
        aliases = profiles.get('aliases', {})
        if not isinstance(known, list) or not isinstance(aliases, dict):
            return []
        admitted = data.get('accounts', {}).get('enabled')
        normalize = lambda value: value if value.startswith(prefix) else prefix + value
        allowed = {normalize(aliases.get(n, n)) for n in admitted if isinstance(n, str)} if isinstance(admitted, list) else None
        result = set()
        for name in known:
            if isinstance(name, str) and _NAME.fullmatch(name) and (allowed is None or normalize(name) in allowed):
                result.add(name.removeprefix(prefix))
        for name, target in aliases.items():
            if isinstance(name, str) and _NAME.fullmatch(name) and isinstance(target, str) and (allowed is None or normalize(target) in allowed):
                result.add(name)
        stores = data.get('stores', {})
        if isinstance(stores, dict):
            result.update(name for name in stores if isinstance(name, str) and _NAME.fullmatch(name))
        return sorted(result)
    except (OSError, ValueError, TypeError, AttributeError, UnicodeError):
        return []


def _unquote(value):
    try:
        tokens = shlex.split(value)
        return tokens[0] if len(tokens) == 1 else value
    except ValueError:
        return value


def candidates(words, cursor, *, parser=None):
    """Complete tokenized words excluding argv[0]; never execute a parsed command."""
    if not isinstance(cursor, int) or cursor < 0 or cursor > len(words) or len(words) > 512:
        return []
    if any(not isinstance(w, str) or len(w) > 16384 for w in words):
        return []
    if parser is None:
        from .cli import build_parser
        parser = build_parser()
    prefix = words[cursor] if cursor < len(words) else ''
    root = Path.cwd() / '.codex' / 'wake'
    try:
        from .shortcut_store import default_root
        root = default_root()
    except (ValueError, OSError):
        pass
    pending = None
    position = 0
    for word in words[:cursor]:
        if pending is not None:
            if word == '=':
                continue
            if pending.dest == 'wake_root':
                root = Path(_unquote(word)).expanduser()
            pending = None
            continue
        options = {flag: action for action in parser._actions for flag in action.option_strings}
        option, equal, value = word.partition('=')
        if option in options:
            action = options[option]
            if action.nargs != 0:
                if equal:
                    if action.dest == 'wake_root':
                        root = Path(_unquote(value)).expanduser()
                else:
                    pending = action
            continue
        sub = next((a for a in parser._actions if isinstance(a, argparse._SubParsersAction)), None)
        if sub is not None and word in sub.choices:
            parser = sub.choices[word]
            position = 0
        elif not word.startswith('-'):
            position += 1
    if prefix.startswith('-') and '=' in prefix:
        flag, unused, value_prefix = prefix.partition('=')
        action = next((a for a in parser._actions if flag in a.option_strings), None)
        values = [str(v) for v in action.choices] if action is not None and action.choices else []
        if action is not None and action.dest in ('account', 'owner', 'destination', 'owners', 'selector', 'source', 'destinations'):
            values += _accounts(root)
        return sorted({flag + '=' + v for v in values if v.startswith(value_prefix) and '\n' not in v and '\r' not in v})
    if pending is not None:
        values = [str(v) for v in pending.choices] if pending.choices else []
        if pending.dest in ('account', 'owner', 'destination', 'owners', 'selector', 'source', 'destinations'):
            values += _accounts(root)
    elif prefix.startswith('-'):
        values = [flag for a in parser._actions for flag in a.option_strings]
    else:
        sub = next((a for a in parser._actions if isinstance(a, argparse._SubParsersAction)), None)
        values = list(sub.choices) if sub is not None else []
        positional = [a for a in parser._actions if not a.option_strings and not isinstance(a, argparse._SubParsersAction)]
        if position < len(positional):
            action = positional[position]
            if action.choices:
                values += [str(v) for v in action.choices]
            if action.dest in ('account', 'owner', 'destination', 'owners', 'selector', 'source', 'destinations'):
                values += _accounts(root)
    return sorted({v for v in values if v.startswith(prefix) and '\n' not in v and '\r' not in v})


def render_script(shell):
    if shell == 'bash':
        return '''# Generated by codex-wake completion bash; no service or provider calls.
_codex_wake() {
  local candidate
  COMPREPLY=()
  while IFS= read -r candidate; do
    COMPREPLY+=("$candidate")
  done < <("${COMP_WORDS[0]}" completion _candidates --cursor "$((COMP_CWORD - 1))" -- "${COMP_WORDS[@]:1}" 2>/dev/null)
}
complete -F _codex_wake codex-wake
'''
    if shell == 'zsh':
        return '''#compdef codex-wake
# Generated by codex-wake completion zsh; no service or provider calls.
_codex_wake() {
  local -a candidates
  candidates=("${(@f)$("${words[1]}" completion _candidates --cursor "$((CURRENT - 2))" -- "${words[@]:1}" 2>/dev/null)}")
  (( ${#candidates} )) && compadd -- "${candidates[@]}"
}
compdef _codex_wake codex-wake
'''
    raise ValueError('completion supports bash and zsh')


def register_parser(subparsers):
    parser = subparsers.add_parser('completion', help='generate, install or remove Bash/Zsh completion')
    verbs = parser.add_subparsers(dest='completion_verb', required=True)
    for shell in ('bash', 'zsh'):
        verbs.add_parser(shell, help='print the generated ' + shell + ' completion script')
    for verb in ('install', 'uninstall'):
        item = verbs.add_parser(verb, help=verb + ' user-owned completion and shell activation')
        item.add_argument('--shell', choices=('bash', 'zsh', 'all'), default='all', help='shell to configure (default: all)')
        item.add_argument('--home', type=Path, default=None, help='user home to configure (default: current user home)')
    item = verbs.add_parser('_candidates', help=argparse.SUPPRESS)
    item.add_argument('--cursor', type=int, required=True)
    item.add_argument('words', nargs=argparse.REMAINDER)


def command(args, root=None):
    try:
        verb = args.completion_verb
        if verb in ('bash', 'zsh'):
            print(render_script(verb), end='')
        elif verb == '_candidates':
            words = args.words[1:] if args.words[:1] == ['--'] else args.words
            for value in candidates(words, args.cursor):
                print(value)
        else:
            from .shell_completion import configure
            print(json.dumps(configure(verb, shell=args.shell, home=args.home), sort_keys=True))
        return 0
    except (ValueError, OSError) as error:
        print('Completion unavailable: ' + str(error), file=sys.stderr)
        return 2


def main(argv=None):
    parser = argparse.ArgumentParser(prog='codex-wake')
    register_parser(parser.add_subparsers(dest='command', required=True))
    return command(parser.parse_args(['completion', *(sys.argv[1:] if argv is None else argv)]))


if __name__ == '__main__':
    raise SystemExit(main())
