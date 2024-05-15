#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/01/20 17:43
# @Author  : shenglin.li
# @File    : notify.py
# @Software: PyCharm
import json

import requests

from leek.common.config import ALERT_TOKEN, ALERT_TYPE
from leek.common.utils import decimal_to_str


def send_to_dingding(content):
    requests.post("https://oapi.dingtalk.com/robot/send?access_token=" + ALERT_TOKEN,
                  headers={"Content-Type": "application/json"},
                  data=json.dumps({"msgtype": "text", "text": {"content": "leek:" + content}}, default=decimal_to_str))


def send_to_console(content):
    print("leek:", content)


def alert(msg):
    if ALERT_TYPE == "dingding":
        send_to_dingding(msg)
    if ALERT_TYPE == "console":
        send_to_console(msg)


if __name__ == '__main__':
    send_to_dingding("asdaas")
