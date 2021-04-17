from collections import defaultdict
from pprint import pprint
import ast
import importlib
import jinja2
import os
import subprocess
import argparse
def update_readme():
    def get_docstring(node):
        docstring = ast.get_docstring(node)
        if not docstring:
            docstring = ''

        docstring = docstring.strip()
        return docstring

    def get_methods_body(methods, class_name=''):
        body = ''
        for method_name in methods:
            if method_name.startswith('_') and method_name != '__init__':
                print('■ 함수', method_name, '은 public이 아니기 때문에 무시했습니다.')
                continue

            method_doc = methods[method_name]['doc']
            if not method_doc:
                print('■ 함수', method_name, '은 __doc__가 없기 때문에 무시했습니다.')
                continue
            
            name = f'{class_name} - {method_name}' if class_name else method_name

            body += f"### 🌱 *(method)* `{name}`\n\n{method_doc}\n\n"
        return body

    def get_classes_body(classes):
        body = ''
        for class_name in classes:
            class_doc = classes[class_name]['doc']
            if not class_doc:
                print('■ 클래스', class_name, '은 __doc__가 없기 때문에 무시했습니다.')
                continue
            body += f"### 🌱 *(class)* `{class_name}`\n\n{class_doc}\n\n"
            body += get_methods_body(classes[class_name]['methods'], class_name)
        return body

    walk_dir = f'{args.library_name}/{args.library_name.replace("-", "_")}'
    defines = {}
    for dirpath, dirnames, filenames in os.walk(walk_dir):
        for filename in filenames:
            filepath = dirpath + '/' + filename
            if not filename.endswith('.py'):
                continue

            define = {
                'methods': {},
                'classes': {}
            }

            with open(filepath, 'r', encoding='utf-8') as fp:
                file_contents = fp.read()

            node = ast.parse(file_contents)

            functions = [n for n in node.body if isinstance(n, ast.FunctionDef)]
            classes = [n for n in node.body if isinstance(n, ast.ClassDef)]

            define['module'] = {
            'doc': get_docstring(node)
            }

            for method_node in functions:
                define['methods'][method_node.name] = {
                    'doc': get_docstring(method_node)

                }

            for class_node in classes:
                define['classes'][class_node.name] = {
                    'methods': {},
                    'doc': get_docstring(class_node)
                }
                
                methods = [n for n in class_node.body if isinstance(n, ast.FunctionDef)]
                for method_node in methods:
                    define['classes'][class_node.name]['methods'][method_node.name] = {
                        'doc': get_docstring(method_node)
                    }
            defines[f"{dirpath}/{filename}"[len(walk_dir) + 1:]] = define


    usage = {}
    for filepath in defines:
        print(f'[{filepath} 변환 중 . . .]')
        body = ''
        body += defines[filepath]['module']['doc'] + '\n\n'
        body += get_classes_body(defines[filepath]['classes'])
        body += get_methods_body(defines[filepath]['methods'])

        usage[filepath] = body
        print()
    

    with open(f'{args.library_name}/readme_template.md', 'r', encoding='utf-8') as fp:
        readme_template = fp.read()

    template = jinja2.Template(readme_template)

    with open(f'{args.library_name}/README.md', 'w', encoding='utf-8') as fp:
        fp.write(template.render(usage=usage))

    print('README.md가 업데이트 되었습니다.')
def check_output(command):
    result = ""
    print(command)
    process = subprocess.Popen(
        command, shell=True, stdout=subprocess.PIPE)
    for b_line in iter(process.stdout.readline, b''):
        try:
            line = b_line.decode("cp949")
        except:
            try:
                line = b_line.decode("utf-8")
            except:
                pass
        print(line, end="")
        result += line

    return result
parser = argparse.ArgumentParser()

parser.add_argument('kind')
parser.add_argument('library_name')
parser.add_argument('-m', '--commit-message')

args = parser.parse_args()

if args.kind == 'test' or args.kind == '1':
    check_output(f'cd {os.path.dirname(os.path.abspath(__file__))}/{args.library_name}/tests && pytest -s')

elif args.kind == 'test_and_deploy' or args.kind == '2':
    if not args.commit_message:
        print('commit message 가 없습니다.')
        exit()
    update_readme()

    setup_filepath = f'{args.library_name}/setup.py'
    lines = []
    with open(setup_filepath, 'r') as fp:
        setup_str = fp.read()
        for line in setup_str.split('\n'):

            if line.strip().startswith('version='):
                start_index = line.find('\'')
                end_index = line.rfind('\'')

                version = line[start_index + 1:end_index]
                version_numbers = version.split('.')
                version_numbers[-1] = str(int(version_numbers[-1]) + 1)
                line = line[:start_index] + '\'' + '.'.join(version_numbers) + '\','
            
            lines.append(line)

    setup_body = '\n'.join(lines)
    with open(setup_filepath, 'w') as fp:
        fp.write(setup_body)

    print('버전을 업데이트 했습니다.')

    cd_command = f'cd {os.path.dirname(os.path.abspath(__file__))}/{args.library_name}'
    pypi_deploy_command = f'python3 setup.py sdist bdist_wheel && python3 -m twine upload --skip-existing dist/*'
    test_command = f'cd tests && pytest -s && cd ..'
    git_push_command = f'git add . && git commit -m "{args.commit_message}" && git pull origin master && git push -u origin master'

    all_command = ' && '.join([cd_command, test_command, pypi_deploy_command, git_push_command])
    check_output(all_command)

    check_output(f'git add . && git commit -m "{args.library_name} {".".join(version_numbers)} released." && git pull origin master && git push -u origin master')

elif args.kind == 'readme' or args.kind == '3':
    update_readme()
