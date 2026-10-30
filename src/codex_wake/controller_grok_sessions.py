"""Session/flow facade over negotiated Grok ACP owner, not a second executor."""
from .controller_grok import ControllerGrok
from .managed_inventory import InventoryError


class ControllerGrokSessions:
    def __init__(self,root,*,owner=None):self.owner=owner or ControllerGrok(root)

    def target(self,name):return dict(self.owner.profile(name)['target'])

    def _context(self,actor,name,target,authorize,capability):
        return self.owner._context(actor,dict(profile=name,expected_target=target),capability,authorize,conversation='conversation_id' in target)

    def execute(self,actor,operation,arguments,*,authorize):
        mapping={'sessions.capabilities':'grok.capabilities','sessions.create':'grok.create','sessions.prompt':'grok.prompt',
            'sessions.wait':'grok.wait','sessions.cancel':'grok.cancel','sessions.checkpoint':'grok.checkpoint','sessions.fork':'grok.fork'}
        if operation not in mapping:raise InventoryError('unsupported_operation','unsupported Grok session facade operation')
        value=self.owner.execute(actor,mapping[operation],arguments,authorize=authorize)
        if operation=='sessions.capabilities':
            value['result'].update(target=arguments['expected_target'],modes=['new_session','sequential'],max_parallelism=1,
                metering='estimate_opt_in_only',native_exact_enforcement=False,tool_policy='inherited_native_only')
        record=value.get('result',{}).get('operation')
        if isinstance(record,dict):
            result=record.get('result')
            if record['operation']=='grok.prompt' and record['phase']=='terminal' and isinstance(result,dict) and isinstance(result.get('text'),str):
                record['execution']=result.get('execution',record['execution'])
                record['answer']=dict(text=result['text'],source='original_grok_acp_reply',native_request_id=record['operation_id'],truncated=result.get('output_truncated',False),peer_content_trust='untrusted')
        value['operation']=operation
        return value
