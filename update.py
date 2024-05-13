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


if __name__ == '__main__':
    from multiprocessing import Process

    Process(target=update, args=[['manage.py', 'migrate', "workstation", "--database=data"]], daemon=False).start()
    Process(target=update, args=[['manage.py', 'migrate', "workstation"]], daemon=False).start()
