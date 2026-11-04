"""Select an explicit harness; retained handles keep their original effect owner."""
from .managed_inventory import InventoryError

HARNESS_PROPERTIES=dict(harness={'type':'string','enum':['codex','grok']},profile={'type':'string','minLength':1})


def parser_options(parser):
    parser.add_argument('--harness',choices=('codex','grok'),default='codex')
    parser.add_argument('--profile',help='owned Grok ACP transport profile')


def _grok(root):
    from .local_grok_control import LocalGrokControl
    return LocalGrokControl(root)


def _selection(arguments):
    arguments=dict(arguments);harness=arguments.pop('harness','codex');profile=arguments.pop('profile',None)
    if harness not in ('codex','grok'):raise InventoryError('unsupported_harness','select codex or grok')
    if harness=='codex' and (profile is not None or str(arguments.get('selector','')).startswith('grok:')):
        raise InventoryError('harness_mismatch','Grok profiles and selectors require --harness grok')
    if harness=='grok' and arguments.get('endpoint','unix://')!='unix://':
        raise InventoryError('harness_mismatch','Grok uses its owned ACP profile, not a Codex native endpoint')
    return harness,profile,arguments


def observation(verb,arguments,root):
    harness,profile,args=_selection(arguments)
    if harness=='grok':
        owner=_grok(root)
        if verb=='list':return owner.discover(profile=profile)
        return owner.resolve(args['selector'],args.get('expected_target'),profile=profile)
    from .local_sessions import discover,resolve
    if verb=='list':return discover(root,**args)
    return resolve(root,**args)


def health(arguments,root):
    harness,profile,args=_selection(arguments)
    if harness=='codex':
        from .local_health import execute
        return execute('local.health',args,root)
    result=_grok(root).health(args['selector'],profile=profile,expected_target=args.get('expected_target'),timeout=args.get('timeout',1))
    return dict(schema_version=1,operation='local.health',status='completed',result=result)


def _retained_grok(root,identifier):
    from .controller_runtime import ControllerRuntime
    record=ControllerRuntime(root)._load(identifier)
    # Routing metadata is not authority: each effect owner validates its custody.
    return record.get('operation','').startswith('grok.') and record.get('target',{}).get('runtime')=='grok'


def slash(verb,arguments,root):
    if verb in ('list','run'):
        harness,profile,args=_selection(arguments)
    else:
        args=dict(arguments);profile=None
        identifier=args.get('operation_id') if verb=='result' else args.get('interaction_id')
        harness='grok' if _retained_grok(root,identifier) else 'codex'
    if harness=='grok':return _grok(root).slash(verb,dict(args,**({'profile':profile} if profile else {})))
    from .local_slash_commands import execute
    return execute(root,verb,args)


class LocalSessionRouter:
    def __init__(self,root):self.root=root

    def _retained(self,identifier):
        if _retained_grok(self.root,identifier):return _grok(self.root)
        from .local_session_operations import LocalSessionControl
        return LocalSessionControl(self.root)

    def create(self,*,harness='codex',profile=None,key=None):
        harness,profile,_=_selection(dict(harness=harness,profile=profile))
        if harness!='grok':raise InventoryError('unsupported_operation','local create is supported for owned Grok ACP profiles; Codex controls existing sessions')
        return _grok(self.root).create(profile=profile,key=key)

    def load(self,selector,*,harness='codex',profile=None,key=None,expected_target=None):
        harness,profile,_=_selection(dict(selector=selector,harness=harness,profile=profile))
        if harness!='grok':raise InventoryError('unsupported_operation','local load is supported for owned Grok ACP profiles; use Codex account resume for Codex')
        return _grok(self.root).load(selector,profile=profile,key=key,expected_target=expected_target)

    def prompt(self,selector,prompt,key=None,*,endpoint='unix://',expected_target=None,harness='codex',profile=None):
        harness,profile,_=_selection(dict(selector=selector,harness=harness,profile=profile))
        if harness=='grok':return _grok(self.root).prompt(selector,prompt,key,profile=profile,expected_target=expected_target)
        from .local_session_operations import LocalSessionControl
        return LocalSessionControl(self.root).prompt(selector,prompt,key,endpoint=endpoint,expected_target=expected_target)

    def result(self,identifier,timeout=0):return self._retained(identifier).result(identifier,timeout)
    def output(self,identifier,**arguments):return self._retained(identifier).output(identifier,**arguments)
    def cancel(self,identifier):return self._retained(identifier).cancel(identifier)
