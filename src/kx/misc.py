def __typeof(var):
    if isinstance(var,float):
        return 'REAL'
    elif isinstance(var,bool):
        return 'BOOL'
    elif isinstance(var,int):
        return 'LONG'
    elif isinstance(var,str):
        return 'STRING'
    return f'{type(var)}'


def exports(ctx: dict,prefix:str=None):
    print('Export all available items')
    print('VAR_CONFIG')
    prefix = '' if prefix is None else f'{prefix}.'
    for i in ctx.keys():
        obj = ctx[i]
        try:
            data = obj.__data__()
            if i!='hw':
                vars = [ f'\t{prefix}{i}.{x} AT {prefix}{i}.{x}: {__typeof(data[x])};' for x in data.keys() ]
            else:
                vars = [ f'\t{prefix}{x} AT {prefix}{i}.{x}: {__typeof(data[x])};' for x in data.keys() ]
            print('\n'.join(vars))
        except:
            pass
    print('END_VAR')
