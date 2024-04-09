#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/01/21 21:12
# @Author  : shenglin.li
# @File    : app.py
# @Software: PyCharm

from multiprocessing import Process


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
    Process(target=update, args=[['manage.py', 'migrate', "workstation", "--database=data"]], daemon=False).start()
    Process(target=update, args=[['manage.py', 'migrate', "workstation"]], daemon=False).start()
