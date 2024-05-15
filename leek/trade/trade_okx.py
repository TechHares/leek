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

from leek.common import logger, G, config
from leek.common.utils import decimal_to_str, decimal_quantize
from leek.trade.trade import Trader, Order, PositionSide as PS, OrderType as OT

LOCK = threading.RLock()


class OkxWsTradeClient(threading.Thread):
    """
    OKX WS客户端
    """

    def __init__(self, callback, api_key="api_key", api_secret_key="api_secret_key",
                 passphrase="passphrase", domain="domain"):
        threading.Thread.__init__(self, daemon=True)
        self.api_key = api_key
        self.api_secret_key = api_secret_key
        self.passphrase = passphrase
        self.domain = domain
        self.ws = None
        self.callback = callback
        self.login = False
        self.timer = None
        self.keep_running = True

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
                            "instType": "SWAP",
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
                        order_result = G(
                            order_id=d["clOrdId"],  # 用户设置的订单ID
                            price=d["avgPx"],  # 成交均价，如果成交数量为0，该字段也为0
                            sz=d["accFillSz"],  # 累计成交数量
                            side=d["side"],  # 订单方向
                            state=d["state"],
                            lever=d["lever"],  # 杠杆倍数
                            # 订单状态 canceled：撤单成功 live：等待成交 partially_filled： 部分成交 filled：完全成交 mmp_canceled：做市商保护机制导致的自动撤单
                            fee=d["fee"],  # 订单交易累计的手续费
                            pnl=d["pnl"],  # 收益，适用于有成交的平仓订单，其他情况均为0
                            cancel_source=d["cancelSource"],  # 取消原因
                            symbol=d["instId"],
                            pos_side=d["posSide"],
                        ).__json__()
                        self.callback(order_result)

        except Exception as e:
            logger.error(f"OkxWsTradeClient 消息处理异常: {e}", e)

    def on_error(self, ws, error):
        logger.error(f"OkxWsTradeClient连接异常: {self.domain}, error={error}")
        ws.close()
        self.on_close(ws, None, None)

    def run(self):
        if self.ws is None:
            self.ws = websocket.WebSocketApp(
                self.domain,
                on_open=self.on_open,
                on_message=self.on_message,
                on_close=self.on_close,
                on_error=self.on_error,
            )
        with LOCK:
            if self.ws.keep_running:
                return
            self.login = False
            self.ws.run_forever(http_proxy_host=config.PROXY_HOST, http_proxy_port=config.PROXY_PORT, proxy_type="http")

    def on_close(self, ws, close_status_code, close_msg):
        logger.error(f"OkxWsTradeClient连接关闭: {self.domain}, close_status_code={close_status_code}, close_msg={close_msg}")
        if self.keep_running:
            time.sleep(5)
            logger.info("OkxWsTradeClient 重连 ... ...")
            self.run()

    def send(self, data, login=True):
        while login and not self.login:
            time.sleep(1)
        self.ws.send(json.dumps(data, default=decimal_to_str))

    def ping(self):
        if self.ws.keep_running:
            self.ws.send("ping")
            self.timer = threading.Timer(25, self.ping)
            self.timer.start()


class SwapOkxTrader(Trader):
    verbose_name = "OKX永续合约U本位交易"
    """
    OKX 永续合约U本位交易

    实盘API交易地址如下：
        REST：https://www.okx.com/
        WebSocket公共频道：wss://ws.okx.com:8443/ws/v5/public
        WebSocket私有频道：wss://ws.okx.com:8443/ws/v5/private
        WebSocket业务频道：wss://ws.okx.com:8443/ws/v5/business
    AWS 地址如下：
        REST：https://aws.okx.com
        WebSocket公共频道：wss://wsaws.okx.com:8443/ws/v5/public
        WebSocket私有频道：wss://wsaws.okx.com:8443/ws/v5/private
        WebSocket业务频道：wss://wsaws.okx.com:8443/ws/v5/business

    模拟盘API交易地址如下：
        REST：https://www.okx.com
        WebSocket公共频道：wss://wspap.okx.com:8443/ws/v5/public?brokerId=9999
        WebSocket私有频道：wss://wspap.okx.com:8443/ws/v5/private?brokerId=9999
        WebSocket业务频道：wss://wspap.okx.com:8443/ws/v5/business?brokerId=9999
    """
    __Side_Map = {
        PS.LONG: "buy",
        PS.SHORT: "sell",
    }

    __Pos_Side_Map = {
        PS.LONG: "long",
        PS.SHORT: "short",
    }

    __Inst_Type_SPOT = "SPOT"
    __Inst_Type_MARGIN = "MARGIN"
    __Inst_Type_SWAP = "SWAP"
    __Inst_Type_FUTURES = "FUTURES"
    __Inst_Type_OPTION = "OPTION"

    def __init__(self, api_key="", api_secret_key="", passphrase="", leverage=3, work_flag="0", td_mode="isolated"):
        self.api_key = api_key
        self.api_secret_key = api_secret_key
        self.passphrase = passphrase
        self.td_mode = td_mode
        self.flag = "0"
        self.domain = "https://www.okx.com"
        ws_domain = "wss://ws.okx.com:8443/ws/v5/private"
        if work_flag == "1":
            self.flag = "1"
            ws_domain = "wss://wspap.okx.com:8443/ws/v5/private?brokerId=9999"
        if work_flag == "2":
            self.domain = "https://aws.okx.com"
            ws_domain = "wss://wsaws.okx.com:8443/ws/v5/private"

        self.lever = int(leverage)

        self.client = Trade.TradeAPI(domain=self.domain, api_key=api_key, api_secret_key=api_secret_key, passphrase=passphrase, flag=self.flag, debug=False, proxy=config.PROXY)
        self.account = Account.AccountAPI(api_key=api_key, api_secret_key=api_secret_key, passphrase=passphrase,
                                          domain=self.domain, flag=self.flag, debug=False, proxy=config.PROXY)

        self.public_client = PublicData.PublicAPI(domain=self.domain, flag=self.flag, debug=False, proxy=config.PROXY)
        self.ws_client = OkxWsTradeClient(self.__trade_callback, api_key=api_key,
                                          api_secret_key=api_secret_key, passphrase=passphrase, domain=ws_domain)
        self.ws_client.start()

    def order(self, order: Order):
        args = {
            "tdMode": self.td_mode,
            "instId": order.symbol,
            "clOrdId": "%s" % order.order_id,
            "side": SwapOkxTrader.__Side_Map[order.side],
            "posSide": SwapOkxTrader.__Pos_Side_Map[order.side],
            "ordType": "limit",
            "sz": "%s" % self.__calculate_sz(order),
        }
        if order.price is not None:
            args["px"] = "%s" % order.price
        if order.type == OT.MarketOrder:
            args["ordType"] = "optimal_limit_ioc"

        logger.info(f"[{order.strategy_id} - 下单], args: {args}, {order}")
        res = self.client.place_order(**args)
        # self.ws_client.send({
        #     "id": str(order.order_id),
        #     "op": "order",
        #     "args": [
        #         args
        #     ]
        # })
        logger.info(f"[{order.strategy_id} - 下单], response: {res}")
        # return order

    def __trade_callback(self, data):
        if data["state"] == "canceled":
            logger.error(f"订单已撤单: {data['order_id']}, 取消原因: {data['cancel_source']}")
            return

        if data["state"] != "filled":
            return
        pos_trade = G()
        pos_trade.order_id = data["order_id"]
        pos_trade.transaction_price = Decimal(data["price"])
        pos_trade.lever = Decimal(data["lever"])
        pos_trade.fee = abs(Decimal(data["fee"]))
        pos_trade.pnl = Decimal(data["pnl"])
        pos_trade.sz = Decimal(data["sz"])
        pos_trade.cancel_source = data["cancel_source"]
        pos_trade.symbol = data["symbol"]

        instrument = self.__get_instrument(data["symbol"], data["pos_side"])
        if not instrument:
            raise RuntimeError("交易信息获取失败")

        pos_trade.ct_val = Decimal(instrument["ctVal"])

        pos_trade.transaction_volume = pos_trade.sz * pos_trade.ct_val
        amt = decimal_quantize(pos_trade.transaction_volume * pos_trade.transaction_price / self.lever, 8)
        pos_trade.transaction_amount = abs(Decimal(amt))
        pos_trade.side = PS.LONG
        if data["side"] == "sell":
            pos_trade.side = PS.SHORT
        logger.info(f"OKX交易回调：{pos_trade}")
        self._trade_callback(pos_trade)

    def cancel_order(self, strategy, order_id, symbol: str):
        logger.info(f"[{strategy} - 撤单], order_id: {order_id}, symbol={symbol}")
        res = self.client.cancel_order(instId=symbol, clOrdId="%s" % order_id)
        logger.info(f"[{strategy} - 撤单], response: {res}")

    def __calculate_sz(self, order: Order):
        """
        计算下单数量 sz
        :param order: 订单
        :return: sz -> str
        """
        if order.sz:
            return Decimal(order.sz)
        instrument = self.__get_instrument(order.symbol, SwapOkxTrader.__Pos_Side_Map[order.side])
        if not instrument:
            raise RuntimeError("交易信息获取失败")

        ct_val = instrument["ctVal"]  # 合约面值
        if not order.price:
            res = trader.public_client.get_mark_price("SWAP", instId=order.symbol)
            order.price = Decimal(res["data"][0]["markPx"])
        num = order.amount * self.lever / (order.price * Decimal(ct_val))

        lot_sz = instrument["lotSz"]  # 下单数量精度
        sz = num - (num % Decimal(lot_sz))

        min_sz = instrument["minSz"]  # 最小下单数量
        if sz < Decimal(min_sz):
            raise RuntimeError(f"下单数量 sz {sz}小于最低限制{min_sz}")

        if order.type == OT.MarketOrder:
            max_mkt_sz = instrument["maxMktSz"]  # 合约或现货市价单的单笔最大委托数量
            sz = min(sz, Decimal(max_mkt_sz))
        else:
            max_lmt_sz = instrument["maxLmtSz"]  # 合约或现货限价单的单笔最大委托数量
            sz = min(sz, Decimal(max_lmt_sz))
        return Decimal(sz)

    @cached(cache=TTLCache(maxsize=20, ttl=600))
    def __get_instrument(self, symbol, posSide):
        """
        获取交易产品基础信息
        :param symbol:
        :return:
        """
        res = self.account.set_leverage(lever="%s" % self.lever, mgnMode=self.td_mode, instId=symbol, posSide=posSide)
        if res and res["code"] != "0":
            logger.error(f"设置杠杆失败:{res['msg'] if res else res}")
        instruments = self.public_client.get_instruments(instType="SWAP", instId=symbol)
        if not instruments:
            return None

        if instruments['code'] != '0':
            return None

        if len(instruments['data']) == 0:
            return None

        instrument = instruments['data'][0]
        return instrument

    def shutdown(self):
        self.ws_client.keep_running = False
        if self.ws_client:
            if self.ws_client.ws:
                self.ws_client.ws.keep_running = False
                self.ws_client.ws.close()
            if self.ws_client.timer:
                self.ws_client.timer.cancel()


# async def subscribe_private():
#     ws = WsPrivateAsync(
#         "key",
#         "passphrase",
#         "secret",
#         "wss://wspap.okx.com:8443/ws/v5/private?brokerId=9999",
#         useServerTime=False
#     )
#     await ws.start()
#     args = [{"channel": "balance_and_position"}]
#     await ws.subscribe(args, callback=callback)
#     await asyncio.sleep(10)
#     await ws.unsubscribe(args, callback=callback)
#  asyncio.run(main())

if __name__ == '__main__':
    trader = SwapOkxTrader("", "",
                 "", work_flag="2")
    leverage = trader.account.set_leverage(lever="3", mgnMode="isolated", instId="FIL-USDT-SWAP", posSide="short")
    print(leverage)
    # trader.order(Order("T0", "TOLONG1", OT.MarketOrder, "DOGE-USDT-SWAP", Decimal(100), side=PS.SHORT))
    #
    # time.sleep(100)
    # trader.shutdown()