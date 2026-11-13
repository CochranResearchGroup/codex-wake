"""Portable family commands shared by CLI, HTTP and MCP."""


def specs():
    string = {'type': 'string'}
    descriptor = {key: dict(string) for key in ('bot_id', 'parent_bot_id', 'name', 'scope_kind', 'scope_ref')}
    descriptor['temporary'] = {'type': 'boolean'}
    identity = {key: dict(string) for key in ('bot_id', 'client_id', 'environment')}
    fields = {
        'register': (descriptor, ['bot_id']),
        'list': ({'root_bot_id': dict(string)}, []),
        'show': ({'bot_id': dict(string)}, ['bot_id']),
        'bind': (dict(identity, **{key: dict(string) for key in ('workspace', 'window_id', 'pane_id', 'thread_id')}), ['bot_id', 'client_id', 'workspace', 'window_id', 'pane_id']),
        'open': (dict(identity, **{key: dict(string) for key in ('workspace', 'server', 'profile', 'cwd', 'thread_id')},
                      argv={'type': 'array', 'items': {'type': 'string'}}, placement={'type': 'string', 'enum': ['workers', 'adjacent']}), ['bot_id', 'client_id']),
        'accept': (dict(identity, parent_bot_id=dict(string), result_id=dict(string), successful={'type': 'boolean'}), ['bot_id', 'client_id', 'parent_bot_id', 'result_id', 'successful']),
        'adopt': (dict(identity), ['bot_id', 'client_id']),
        'focus': (dict(identity, relation={'type': 'string', 'enum': ['self', 'parent', 'root']}), ['bot_id', 'client_id']),
    }
    result = {}
    for verb, (properties, required) in fields.items():
        readonly = verb in ('list', 'show')
        if not readonly:
            properties.update(expected_target={'type': 'object'}, _request={'type': 'object'})
            required += ['expected_target', '_request']
        result['wake_tabs_family_' + verb] = ('controller-tabs', 'tabs.family.' + verb,
            'Organize durable bot families and exact client tabs; identity does not grant account or input authority.',
            properties, required, readonly)
    return result
