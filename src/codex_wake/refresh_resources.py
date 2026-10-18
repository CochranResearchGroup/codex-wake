"""Read actual MCP process identity and catalog, independently of tool behavior."""


def catalog_ready(check, request, thread):
    value=request('mcpServerStatus/list',dict(threadId=thread,serverName=check['server'],detail='toolsAndAuthOnly'))
    try:
        servers=[row for row in value['data'] if row['name']==check['server']]
        if len(servers)!=1 or servers[0]['serverInfo']['version']!=check['version']:
            return False
        tools=servers[0]['tools']
        return all(name in tools and set(fields)<=set(tools[name]['inputSchema']['properties'])
                   for name,fields in check['tools'].items())
    except (KeyError,TypeError):
        return False
