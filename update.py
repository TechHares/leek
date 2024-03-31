#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/01/21 21:12
# @Author  : shenglin.li
# @File    : app.py
# @Software: PyCharm
import os
import sys
from pathlib import Path

from django.core.management import execute_from_command_line
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'website.settings')
if __name__ == '__main__':
    os.environ.setdefault("DISABLE_WORKER", "true")
    sys.path.append(f'{Path(__file__).resolve().parent}/web')
    sys.argv=['manage.py', 'migrate', "workstation", "--database=data"]
    execute_from_command_line(['manage.py', 'migrate', "workstation", "--database=data"])
    sys.argv=['manage.py', 'migrate', "workstation"]
    execute_from_command_line(['manage.py', 'migrate', "workstation"])
