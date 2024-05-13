#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/01/21 21:12
# @Author  : shenglin.li
# @File    : app.py
# @Software: PyCharm
import subprocess
import sys

# 执行安装依赖包命令
pip_command = sys.executable + ' -m pip install -r requirements.txt'
result = subprocess.run(pip_command.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
stdout = result.stdout.decode()
stderr = result.stderr.decode()
if result.returncode == 0:
    print("Output:\n", stdout)
else:
    print("Error:\n", stderr)


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
