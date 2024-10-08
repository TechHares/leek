#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/01/21 21:12
# @Author  : shenglin.li
# @File    : app.py
# @Software: PyCharm
import sys


def execute_cmd(cmd):
    import subprocess
    process = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                               bufsize=1, universal_newlines=True)
    while True:
        output = process.stdout.readline()
        if output == '' and process.poll() is not None:
            break
        if output:
            print(output.strip())


# 检查环境
if sys.version_info < (3, 13):
    print("请使用Python3.13及以上版本")
    print("请使用Python3.13及以上版本")
    print("请使用Python3.13及以上版本")
    sys.exit(1)

if __name__ == '__main__':
    # 执行安装依赖包命令
    pip_install_command = sys.executable + ' -m pip install -r requirements.txt'
    execute_cmd(pip_install_command)


def update(args):
    import os
    import sys
    from pathlib import Path
    from django.core.management import execute_from_command_line
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'website.settings')
    os.environ.setdefault("DISABLE_WORKER", "true")
    sys.path.append(f'{Path(__file__).resolve().parent}/web')

    sys.argv = args
    execute_from_command_line(args)


def init_superuser():
    import os
    import sys
    from pathlib import Path
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'website.settings')
    os.environ.setdefault("DISABLE_WORKER", "true")
    sys.path.append(f'{Path(__file__).resolve().parent}/web')
    import django
    django.setup()

    from django.contrib.auth.models import User
    if User.objects.filter(username='admin').exists():
        return
    User.objects.create_superuser('admin', '', '123456')


if __name__ == '__main__':
    from multiprocessing import Process
    Process(target=update, args=[['manage.py', 'migrate', "workstation", "--database=data"]], daemon=False).start()
    p = Process(target=update, args=[['manage.py', 'migrate']], daemon=False)
    p.start()
    p.join()
    init_superuser()
