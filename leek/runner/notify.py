#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/01/20 17:43
# @Author  : shenglin.li
# @File    : notify.py
# @Software: PyCharm
import json

import requests

from leek.common.utils import decimal_to_str


def send_to_dingding(token, content):
    requests.post("https://oapi.dingtalk.com/robot/send?access_token=" + token,
                  headers={"Content-Type": "application/json"},
                  data=json.dumps({"msgtype": "text", "text": {"content": "策略" + content}}, default=decimal_to_str))


def send_to_console(content):
    print(content)


if __name__ == '__main__':
    send_to_dingding("xxx", "asdaas")
