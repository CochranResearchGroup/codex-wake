"""Portable named terminal session operation schemas shared by all transports."""

def specs():
    result={}
    fields={'session':{'type':'string','description':'Terminal session name or stable ID.'},'server':{'type':'string','description':'Terminal server qualifier when names are ambiguous.'}}
    for verb in ('list','show','create','update','open','delete','ensure'):
        readonly=verb in ('list','show')
        props=dict(fields)
        required=[] if verb=='list' else ['name'] if verb in ('create','ensure') else ['session']
        if verb in ('create','ensure'):props.update(name={'type':'string'},backend={'type':'string','enum':['tmux','byobu','psmux']},start={'type':'boolean'},defaults={'type':'object'})
        if verb=='update':props['changes']={'type':'object'};required+=['changes']
        if verb=='delete':
            props.update(destination={'type':'string'},terminate={'type':'boolean'},plan_id={'type':'string'});required=[]
        if not readonly:props.update(expected_target={'type':'object'},_request={'type':'object'});required+=['expected_target','_request']
        result['wake_tabs_session_'+verb]=('controller-tabs','tabs.session.'+verb,'Manage named terminal sessions; empty definitions persist independently of running tabs.',props,required,readonly)
    for verb in ('preview','apply','status','undo'):
        readonly=verb=='status'
        props=dict(session={'type':'string'},destination={'type':'string'},selection={'type':'object'},plan_id={'type':'string'},receipt_id={'type':'string'})
        required=['destination'] if verb=='preview' else []
        if not readonly:props.update(expected_target={'type':'object'},_request={'type':'object'});required+=['expected_target','_request']
        result['wake_tabs_relocate_'+verb]=('controller-tabs','tabs.relocate.'+verb,'Preview and relocate whole tabs by selection; reconcile partial results and conditionally undo.',props,required,readonly)
    for verb in ('list','show','save','delete','enable','pause','tick','status','hold','resume','pin','unpin'):
        readonly=verb in ('list','show','status')
        props=dict(name={'type':'string'},rule_id={'type':'string'}) if verb in ('show','save','delete','enable','pause') else {}
        required=[]
        if verb=='save':
            props.update(destination={'type':'string'},selection={'type':'object'},priority={'type':'integer','minimum':-1000000,'maximum':1000000},stability_seconds={'type':'number','minimum':0,'maximum':3600})
            required=['name','destination','selection']
        if verb=='enable':props['include_existing']={'type':'boolean'}
        if verb in ('hold','resume','pin','unpin'):
            props.update(selection={'type':'object'},reason={'type':'string'});required=['selection']
        if not readonly:props.update(expected_target={'type':'object'},_request={'type':'object'});required+=['expected_target','_request']
        result['wake_tabs_route_'+verb]=('controller-tabs','tabs.route.'+verb,'Manage opt-in stable routing rules, explicit pins and manual placement holds.',props,required,readonly)
    return result


def split_selector(selector,server=None):
    """Qualified SERVER::NAME selectors keep names usable across native servers."""
    if isinstance(selector,str) and '::' in selector:
        qualifier,selector=selector.rsplit('::',1)
        if server is not None and qualifier!=server:
            from .managed_inventory import InventoryError
            raise InventoryError('invalid_argument','Qualified session and --server must select the same server.')
        server=qualifier
    return selector,server
