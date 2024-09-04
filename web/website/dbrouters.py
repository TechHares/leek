#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/1/28 00:26
# @Author  : shenglin.li
# @File    : dbrouters.py
# @Software: PyCharm
# dbrouters.py
from .settings import DATABASES
class LeekRouter:
    def __init__(self):
        self.route_model_names = set()

    def db_for_read(self, model, **hints):
        try:
            if model._meta.db_tablespace in DATABASES:
                return model._meta.db_tablespace
        except Exception:
            pass

        return "default"

    def db_for_write(self, model, **hints):
        try:
            if model._meta.db_tablespace in DATABASES:
                return model._meta.db_tablespace
        except Exception:
            pass

        return "default"

    def allow_relation(self, obj1, obj2, **hints):
        return obj1._meta.db_tablespace == obj2._meta.db_tablespace

    def allow_syncdb(self, db, model):
        try:
            if model._meta.db_tablespace in DATABASES:
                return model._meta.db_tablespace == db
        except Exception:
            pass

        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        try:
            if hints["model"]._meta.db_tablespace in DATABASES:
                return hints["model"]._meta.db_tablespace == db
        except Exception:
            pass

        return True


if __name__ == '__main__':
    pass
