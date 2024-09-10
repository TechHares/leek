#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/01/20 17:43
# @Author  : shenglin.li
# @File    : notify.py
# @Software: PyCharm
import json

import requests

from leek.common import config
from leek.common.utils import decimal_to_str
from multiprocessing import current_process


def send_to_dingding(content):
    pre = f"leek => {config.LOGGER_NAME}({current_process().pid}):"
    requests.post("https://oapi.dingtalk.com/robot/send?access_token=" + config.ALERT_TOKEN,
                  headers={"Content-Type": "application/json"},
                  data=json.dumps({"msgtype": "text", "text": {"content": "%s %s" % (pre, content)}},
                                  default=decimal_to_str))


def send_to_console(content):
    print("leek:", content)


def alert(msg):
    if config.ALERT_TYPE == "dingding":
        send_to_dingding(msg)
    if config.ALERT_TYPE == "console":
        send_to_console(msg)


if __name__ == '__main__':
    send_to_dingding("asdaas")
