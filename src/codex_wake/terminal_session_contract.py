"""Portable named terminal session operation schemas shared by all transports."""

def specs():
    result={}
    fields={'session':{'type':'string','description':'Terminal session name or stable ID.'},'server':{'type':'string','description':'Terminal server qualifier when names are ambiguous.'}}
    for verb in ('list','show','create','update','open','delete'):
        readonly=verb in ('list','show')
        props=dict(fields)
        required=[] if verb=='list' else ['name'] if verb=='create' else ['session']
        if verb=='create':props.update(name={'type':'string'},backend={'type':'string','enum':['tmux','byobu','psmux']},start={'type':'boolean'})
        if verb=='update':props['changes']={'type':'object'};required+=['changes']
        if not readonly:props.update(expected_target={'type':'object'},_request={'type':'object'});required+=['expected_target','_request']
        result['wake_tabs_session_'+verb]=('controller-tabs','tabs.session.'+verb,'Manage named terminal sessions; empty definitions persist independently of running tabs.',props,required,readonly)
    return result
