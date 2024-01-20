#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2024/01/20 22:40
# @Author  : shenglin.li
# @File    : trade_okx.py
# @Software: PyCharm
import json
import threading
import time
from decimal import Decimal
from typing import Dict

import okx.Account as Account
import okx.MarketData as MarketData
import okx.PublicData as PublicData
import okx.Trade as Trade
import websocket
from cachetools import cached, TTLCache
from okx.utils import sign

from leek.common import logger
from leek.common.utils import decimal_to_str, decimal_quantize
from leek.trade.trade import Trader, Order, PositionSide as PS, OrderType as OT


class OkxWsTradeClient(threading.Thread):
    """
    OKX WS客户端
    """

    def __init__(self, callback, api_key="api_key", api_secret_key="api_secret_key",
                 passphrase="passphrase", inst_type="",
                 domain="domain", flag="1"):
        threading.Thread.__init__(self)
        self.inst_type = inst_type
        self.api_key = api_key
        self.api_secret_key = api_secret_key
        self.passphrase = passphrase
        self.domain = domain
        self.flag = flag
        self.ws = None
        self.callback = callback
        self.login = False
        self.timer = None

    def on_open(self, ws):
        timestamp = str(int(time.time()))
        s = sign(timestamp + "GET" + "/users/self/verify", self.api_secret_key).decode()
        data = {
            "op": "login",
            "args":
                [
                    {
                        "apiKey": self.api_key,
                        "passphrase": self.passphrase,
                        "timestamp": timestamp,
                        "sign": s,
                    }
                ]
        }
        self.ws.send(json.dumps(data, default=decimal_to_str))

    def on_message(self, ws, message):
        try:
            if message == "pong":
                return

            logger.info(f"OKX推送: {message}")
            msg = json.loads(message)
            if "event" in msg:
                if msg["event"] == "login" and msg["code"] == "0":  # 登陆成功
                    self.send({
                        "op": "subscribe",
                        "args": [{
                            "channel": "orders",
                            "instType": self.inst_type,
                        }]
                    }, False)
                    self.ping()
                if msg["event"] == "subscribe":  # 订阅成功
                    self.login = True
                return
            if "op" in msg and msg["op"] == "order" and msg["code"] != "0":  # 订单失败
                raise RuntimeError(f"订单失败: {msg['id']}-{msg['code']}-{msg['msg']}")

            if "arg" in msg and "data" in msg:  # 订阅推送
                ch = msg["arg"]["channel"]
                if ch == "orders" and len(msg["data"]) > 0:  # 订单
                    logger.info(f"OKX订单推送: {msg['data']}")
                    for d in msg["data"]:
                        self.callback({
                            "order_id": d["clOrdId"],  # 用户设置的订单ID
                            "acc_fill_sz": d["accFillSz"],  # 累计成交数量
                            "avg_price": d["avgPx"],  # 成交均价，如果成交数量为0，该字段也为0
                            # 订单状态 canceled：撤单成功 live：等待成交 partially_filled： 部分成交 filled：完全成交 mmp_canceled：做市商保护机制导致的自动撤单
                            "state": d["state"],
                            "fee": d["fee"],  # 订单交易累计的手续费与返佣
                            "pnl": d["pnl"],  # 收益，适用于有成交的平仓订单，其他情况均为0
                            "cancel_source": d["cancelSource"],  # 取消原因
                        })
        except Exception as e:
            logger.error(f"OkxWsTradeClient 消息处理异常: {e}", e)

    def on_error(self, ws, error):
        ws.close()
        logger.error(f"OkxWsTradeClient连接异常: {self.domain}/{ws}, error={error}", error)

    def run(self):
        self.ws = websocket.WebSocketApp(
            self.domain,
            on_open=self.on_open,
            on_message=self.on_message,
            on_close=self.on_close,
            on_error=self.on_error,
        )
        self.ws.run_forever()

    def on_close(self, ws, close_status_code, close_msg):
        print(f"OkxWsTradeClient连接关闭: {self.domain}/{ws}, close_status_code={close_status_code}, close_msg={close_msg}")

    def send(self, data, login=True):
        while login and not self.login:
            time.sleep(1)
        self.ws.send(json.dumps(data, default=decimal_to_str))

    def ping(self):
        if self.ws.keep_running:
            self.ws.send("ping")
            self.timer = threading.Timer(25, self.ping)
            self.timer.start()


class OkxTrader(Trader):
    """
    OKX 永续合约币本位交易
    """
    __Side_Map = {
        PS.LONG: "buy",
        PS.SHORT: "sell",
    }

    __Inst_Type_SPOT = "SPOT"
    __Inst_Type_MARGIN = "MARGIN"
    __Inst_Type_SWAP = "SWAP"
    __Inst_Type_FUTURES = "FUTURES"
    __Inst_Type_OPTION = "OPTION"

    def __init__(self, api_key="", api_secret_key="", passphrase="", leverage=3, ws_domain="", pub_domain="",
                 acct_domain="", domain="", flag="", debug=False, inst_type="SWAP",
                 td_mode="isolated"):
        self.inst_type = inst_type
        self.td_mode = td_mode
        self.lever = int(leverage)
        self.order_map: Dict[str, Order] = {}

        self.client = Trade.TradeAPI(api_key=api_key, api_secret_key=api_secret_key, passphrase=passphrase,
                                     domain=domain, flag=flag, debug=debug)
        self.accountAPI = Account.AccountAPI(api_key=api_key, api_secret_key=api_secret_key, passphrase=passphrase,
                                             domain=acct_domain, flag=flag, debug=debug)

        self.market = MarketData.MarketAPI(domain=pub_domain, flag=flag, debug=debug)
        self.publicApi = PublicData.PublicAPI(domain=pub_domain, flag=flag, debug=debug)
        self.ws_client = OkxWsTradeClient(self.__trade_callback, api_key=api_key,
                                          api_secret_key=api_secret_key, passphrase=passphrase, domain=ws_domain,
                                          flag=flag, inst_type=inst_type)

    def order(self, order: Order):
        if order.order_id in self.order_map:
            raise RuntimeError(f"订单ID重复: {order.order_id}")

        if not self.ws_client.is_alive():
            self.ws_client.start()

        args = {
            "tdMode": self.td_mode,
            "instId": order.symbol,
            "clOrdId": "%s" % order.order_id,
            "side": OkxTrader.__Side_Map[order.side],
            "ordType": "limit",
            "sz": self.__calculate_sz(order),
        }
        if order.price is not None:
            args["px"] = "%s" % order.price
        if order.type == OT.MarketOrder:
            args["ordType"] = "optimal_limit_ioc"

        logger.info(f"[{order.strategy_id} - 下单], args: {args}, {order}")
        # res = self.client.place_order(**args)
        self.ws_client.send({
            "id": str(order.order_id),
            "op": "order",
            "args": [
                args
            ]
        })
        self.order_map[order.order_id] = order
        # self.logger.info(f"[{order.strategy} - 下单], response: {res}")
        # return order

    def __trade_callback(self, data):
        logger.info(f"OKX交易回调：{data}")
        if data["order_id"] not in self.order_map:
            return

        if data["state"] == "canceled":
            logger.error(f"订单已撤单: {data['order_id']}, 取消原因: {data['cancel_source']}")
            return

        if data["state"] != "filled":
            return

        order = self.order_map[data["order_id"]]
        order.transaction_price = Decimal(data["avg_price"])
        order.fee = Decimal(data["fee"])
        instrument = self.__get_instrument(order.symbol)
        if not instrument:
            raise RuntimeError("交易信息获取失败")

        ct_val = instrument["ctVal"]  # 合约面值
        order.transaction_volume = Decimal(data["acc_fill_sz"])
        if self.inst_type == OkxTrader.__Inst_Type_SWAP:
            order.transaction_volume *= Decimal(ct_val)
        order.transaction_amount = decimal_quantize(order.transaction_volume * order.transaction_price / self.lever)
        order.sz = Decimal(data["acc_fill_sz"])
        if order.side == PS.SHORT:
            order.sz *= -1
        self._trade_callback(order)

    def cancel_order(self, strategy, order_id, symbol: str):
        logger.info(f"[{strategy} - 撤单], order_id: {order_id}, symbol={symbol}")
        res = self.client.cancel_order(instId=symbol, clOrdId="%s" % order_id)
        logger.info(f"[{strategy} - 撤单], response: {res}")

    # def close_order(self, order: Order):
    #     od = copy.copy(order)
    #     od.side = PS.switch_side(od.side)
    #     od.type = OT.MarketOrder  # 平仓采用市价立刻平
    #     od.order_id = "P%s" % od.order_id
    #     logger.info(f"[{od.strategy} - 平单], args: {od}")
    #     self.place_order(od)

    # def close_position(self, strategy, symbol: str):
    #     logger.info(f"[{strategy} - 出清], symbol: {symbol}")
    #     response = self.client.close_positions(instId=self.__build_inst_id(symbol), mgnMode=self.td_mode)
    #     logger.info(f"[{strategy} - 出清], response: {response}")

    def __calculate_sz(self, order: Order) -> str:
        """
        计算下单数量 sz
        :param order: 订单
        :return: sz -> str
        """
        if order.sz:
            return order.sz
        instrument = self.__get_instrument(order.symbol)
        if not instrument:
            raise RuntimeError("交易信息获取失败")

        ct_val = instrument["ctVal"]  # 合约面值
        num = order.amount * self.lever / (order.price * Decimal(ct_val))

        lot_sz = instrument["lotSz"]  # 下单数量精度
        sz = num - (num % Decimal(lot_sz))

        min_sz = instrument["minSz"]  # 最小下单数量
        if sz < Decimal(min_sz):
            raise RuntimeError(f"下单数量 sz {sz}小于最低限制{min_sz}")

        if self.inst_type == OkxTrader.__Inst_Type_SPOT or self.inst_type == OkxTrader.__Inst_Type_SWAP:
            if order.type == OT.MarketOrder:
                max_mkt_sz = instrument["maxMktSz"]  # 合约或现货市价单的单笔最大委托数量
                sz = min(sz, Decimal(max_mkt_sz))
            else:
                max_lmt_sz = instrument["maxLmtSz"]  # 合约或现货限价单的单笔最大委托数量
                sz = min(sz, Decimal(max_lmt_sz))
        return sz

    @cached(cache=TTLCache(maxsize=20, ttl=300))
    def __get_instrument(self, symbol):
        """
        获取交易产品基础信息
        :param symbol:
        :return:
        """
        self.accountAPI.set_leverage(lever="%s" % self.lever, mgnMode=self.td_mode, instId=symbol)
        instruments = self.publicApi.get_instruments(instType=self.inst_type, instId=symbol)
        if not instruments:
            return None

        if instruments['code'] != '0':
            return None

        if len(instruments['data']) == 0:
            return None

        instrument = instruments['data'][0]
        return instrument

    def shutdown(self):
        if self.ws_client:
            if self.ws_client.ws:
                self.ws_client.ws.keep_running = False
                self.ws_client.ws.close()
            if self.ws_client.timer:
                self.ws_client.timer.cancel()


if __name__ == '__main__':
    pass
