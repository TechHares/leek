#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/01/20 17:38
# @Author  : shenglin.li
# @File    : data_binance_download.py
# @Software: PyCharm

import json
import threading
from abc import abstractmethod

import websocket

from leek.common import EventBus, logger
from leek.common.utils import decimal_to_str


class DataSource(threading.Thread):
    """
    数据源定义
    """

    def __init__(self, bus: EventBus):
        threading.Thread.__init__(self, daemon=True)
        self.bus = bus

    def _send_tick_data(self, data):
        self.bus.publish(EventBus.TOPIC_TICK_DATA, data)

    @abstractmethod
    def _run(self):
        raise NotImplemented

    def run(self):
        logger.info(f"数据源开始启动")
        self._run()

    def shutdown(self):
        """
        关闭钩子
        """
        pass


class WSDataSource(DataSource):
    """
    WebSocket 数据源
    """

    def __init__(self, url):
        self.ws = None
        self.url = url

    def on_open(self, ws):
        """
        当打开websocket时调用的回调对象。
        1个参数：
        @ ws：WebSocketApp对象
        """
        pass

    def on_data(self, ws, string, data_type, continue_flag):
        """
        接收到数据时调用的方法。

        参数:
            ws (WebSocket): WebSocket对象
            string (str): 从服务器接收到的UTF-8编码的字符串
            type (int): 数据类型，可能是ABNF.OPCODE_TEXT或ABNF.OPCODE_BINARY
            continue_flag (int): 是否继续接收数据的标志，如果为0，则表示数据接收完毕

        返回:
            无
        """
        pass

    @abstractmethod
    def on_message(self, ws, message):
        """
        当接收到数据时调用的回调函数。
        有两个参数：
        @ ws: WebSocketApp 对象
        @ message: 从服务器接收到的 utf-8 格式的数据
        """
        raise NotImplemented

    def on_error(self, ws, error):
        """
        当发生错误时调用的回调对象。
        有两个参数：
        @ ws: WebSocketApp 对象
        @ error: 异常对象
        """
        logger.error(f"WSDataSource连接异常: {self.url}/{ws}, error={error}")

    def on_close(self, ws, close_status_code, close_msg):
        """
        当连接关闭时调用的回调对象。
        有两个参数：
        @ ws: WebSocketApp 对象
        @ close_status_code: 关闭状态码
        @ close_msg: 关闭信息
        """
        if close_status_code is None and close_msg is None:
            logger.info(f"WSDataSource连接关闭: {self.url}")
        else:
            logger.error(f"WSDataSource连接关闭: {self.url}, close_status_code={close_status_code}, {close_msg}")
        if self.ws and self.ws.keep_running:
            self.start()  # 重连

    def send_to_ws(self, data):
        """
        发送数据
        """
        self.ws.send(json.dumps(data, default=decimal_to_str))

    def _run(self):
        self.ws = websocket.WebSocketApp(
            self.url,
            on_open=self.__wrap(self.on_open),
            on_message=self.__wrap(self.on_message),
            on_data=self.__wrap(self.on_data),
            on_error=self.__wrap(self.on_error),
            on_close=self.__wrap(self.on_close),
        )
        self.ws.run_forever()

    def __wrap(self, func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"WSDataSource异常: func={func}, error={e}", e)
                self.shutdown()

        return wrapper

    def shutdown(self):
        self.ws.keep_running = False
        self.ws.close()
