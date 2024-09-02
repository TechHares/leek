#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/01/21 21:12
# @Author  : shenglin.li
# @File    : app.py
# @Software: PyCharm
import os
import sys
from pathlib import Path

# 检查环境
if sys.version_info < (3, 12):
    print("请使用Python3.12及以上版本")
    print("请使用Python3.12及以上版本")
    print("请使用Python3.12及以上版本")
    sys.exit(1)
from django.core.management import execute_from_command_line
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'website.settings')
if __name__ == '__main__':
    sys.path.append(f'{Path(__file__).resolve().parent}/web')
    execute_from_command_line(['manage.py', 'runserver', '--noreload', '0.0.0.0:8009'])
    # execute_from_command_line(['manage.py', 'runserver', '0.0.0.0:8009'])
    # execute_from_command_line(['manage.py', 'migrate', "workstation", "--database=data"])
    # execute_from_command_line(['manage.py', 'makemigrations', "workstation"])
