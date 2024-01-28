#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2023/01/20 20:21
# @Author  : shenglin.li
# @File    : event.py
# @Software: PyCharm
from leek.common.log import logger


class EventBus:
    """
    事件总线
    """
    TOPIC_TICK_DATA = "TICK_DATA"
    TOPIC_ORDER_DATA = "ORDER_DATA"
    TOPIC_POSITION_DATA = "POSITION_DATA"
    TOPIC_NOTIFY = "NOTIFY"

    def __init__(self):
        self.handlers = {}

    def subscribe(self, topic: str, func):
        if topic not in self.handlers:
            self.handlers[topic] = []
        self.handlers[topic].append(func)
        logger.info(f"topic[{topic}] 订阅成功: {func}")

    def unsubscribe(self, topic: str, func):
        if topic in self.handlers:
            length = len(self.handlers[topic])
            for i in range(length):
                if self.handlers[topic][i] == func:
                    self.handlers[topic][i] = self.handlers[topic][length - 1]
                    self.handlers[topic] = self.handlers[topic][:length - 1]
                    logger.info(f"topic[{topic}] 取消订阅: {func}")

    def publish(self, topic: str, *args, **kwargs):
        logger.debug(f"topic[{topic}] 发布事件: {args} {kwargs}")
        if topic in self.handlers:
            for handler in self.handlers[topic]:
                try:
                    handler(*args, **kwargs)
                except Exception as e:
                    logger.error(f"topic[{topic}] 发布事件: {args} {kwargs} 处理失败:", e)
                    if topic != "ERROR":
                        self.publish("ERROR", e)


if __name__ == '__main__':
    from leek.common.log import logger

    bus = EventBus()


    def consumer(a, b):
        print("sss", a, b)


    def consumer1(a="", b=None):
        print("111", a, b)


    bus.subscribe("tests", consumer)
    bus.subscribe("tests", consumer1)
    bus.publish("tests", a="aaaa", b="bbbbb")
    bus.unsubscribe("tests", consumer1)
    bus.publish("tests", a="aaaa", b="bbbbb")
