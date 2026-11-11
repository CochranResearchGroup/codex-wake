"""Fixed palettes matching the operator-approved compact preview; no native I/O."""
PALETTES = {
    'slate': dict(base='#171c24',text='#aeb9ca',bright='#edf2fa',selected='#2b3544',
                  codex='#8eadd9',modded='#86bdb5',grok='#b09bc8',ssh='#a6b0bf',waiting='#d3b178',error='#d18b8b'),
    'dusk': dict(base='#201e29',text='#bdb7cb',bright='#f0eafa',selected='#373245',
                 codex='#9baed7',modded='#94bfb0',grok='#b6a0ce',ssh='#b9b1c5',waiting='#ceb184',error='#d0919c'),
    'graphite': dict(base='#242321',text='#bebdb5',bright='#eeeae0',selected='#3c3b35',
                     codex='#a4b7c9',modded='#a0b9a7',grok='#b7aec6',ssh='#bdb8aa',waiting='#cdb886',error='#cb9a8d'),
}
PRESETS = ('slate','dusk','graphite','legacy')


def preset_options(name,kind,label,state):
    """Color the short badge, retain soft native name and subtle selection."""
    palette=PALETTES[name]
    key={'codex:stock':'codex','codex:modded':'modded','codex':'codex','grok':'grok','ssh':'ssh'}.get(kind)
    badge=label if key else (label if kind not in ('shell','unknown') else '')
    cue={'running':'*','waiting':'?','error':'!','health-warning':'!'}.get(state,'')
    cue_color=palette['error'] if state in ('error','health-warning') else palette['waiting'] if state=='waiting' else palette.get(key,palette['text'])
    result={}
    for selected in (False,True):
        background=palette['selected'] if selected else palette['base']
        foreground=palette['bright'] if selected else palette['text']
        style=f'fg={foreground},bg={background}'+(',bold' if selected else '')
        prefix='window-status-current-' if selected else 'window-status-'
        # Only constant palette colors enter style expressions. Labels were escaped
        # by projection; native #W remains the user's literal name expansion.
        parts=[]
        if badge:parts.append(f'#[fg={palette.get(key,foreground)}]{badge}')
        if cue:parts.append(f'#[fg={cue_color}]{cue}')
        badges=''.join(parts)
        separator=' ' if badge and not cue else ''
        content='#I:'+badges+separator+f'#[fg={foreground}]#W'
        result[prefix+'style']=style
        result[prefix+'format']=' '+('['+content+']' if selected else content)+' '
    return result
