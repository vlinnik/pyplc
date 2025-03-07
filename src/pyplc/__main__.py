import logging,os,importlib,shutil,re
import argparse,importlib.resources as resources

def file_template(src: str,dst: str,env = {}):
    """Файл по шаблону.

    Заменяет ${var} на значение env['var']

    Параметры:
        src (str): имя файла из ресурсов
        dst (str): путь до создаваемого файла
        env (dict, optional): словарь переменных. Defaults to {}.
    """
    data = resources.files('pyplc.resources')
    with open(dst,'w') as output:
        content = data.joinpath(src).read_text()
        var = re.compile(r'\${([^}]+)}')
        for m in re.findall(var,content):
            what = r'\${' + f'{m}' + '}'
            content = re.sub(what,env[m] if m in env else f'<{m} not set>',content)
        output.write(content)


logging.info(f'PYPLC project generator tool')

parser = argparse.ArgumentParser(
                    prog='PYPLC Project generator tool',
                    description='Генерирует скелет проекта по шаблону',
                    epilog='Пример: python -m pyplc')

parser.add_argument('-c','--create',required=False,default=False,action='store_true',help='Создать новый проект')
parser.add_argument('-n','--name',required=False,default='PROJECT',action='store',help='Имя проекта')
parser.add_argument('-d','--destination',required=False,action='store',default='.',help='Путь где создать проект')

args = parser.parse_args()

if args.create:
    os.makedirs(f'{args.destination}/{args.name}',exist_ok = True )
    os.makedirs(f'{args.destination}/{args.name}/src',exist_ok = True )
    for f in ['board.py','krax.py','krax.csv','krax.json']:
        file_template(f,f'{args.destination}/{args.name}/src/{f}',vars(args))
