"""
OKX API 封装模块
"""
import hmac
import base64
import hashlib
import json
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import requests

import config
from logger import logger, log_error

class OkxAPI:
    """
    OKX API 客户端
    """

    def __init__(self):
        self.api_key = config.API_KEY
        self.secret_key = config.SECRET_KEY
        self.passphrase = config.PASSPHRASE
        self.base_url = config.BASE_URL
        self.use_simulated = config.USE_SIMULATED

    def _get_timestamp(self) -> str:
        """
        获取 ISO 格式的时间戳
        """
        return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'

    def _sign(self, timestamp: str, method: str, request_path: str, body: str = "") -> str:
        """
        生成 API 签名
        """
        message = timestamp + method + request_path + body
        mac = hmac.new(
            self.secret_key.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        )
        return base64.b64encode(mac.digest()).decode('utf-8')

    def _get_headers(self, method: str, request_path: str, body: str = "") -> Dict[str, str]:
        """
        构建请求头
        """
        timestamp = self._get_timestamp()
        sign = self._sign(timestamp, method, request_path, body)

        headers = {
            'OK-ACCESS-KEY': self.api_key,
            'OK-ACCESS-SIGN': sign,
            'OK-ACCESS-TIMESTAMP': timestamp,
            'OK-ACCESS-PASSPHRASE': self.passphrase,
            'Content-Type': 'application/json'
        }

        # 如果是模拟盘，添加模拟交易标记
        if self.use_simulated:
            headers['x-simulated-trading'] = '1'

        return headers

    def _request(self, method: str, endpoint: str, params: Optional[Dict] = None,
                 body: Optional[Dict] = None) -> Optional[Dict]:
        """
        发送 HTTP 请求
        """
        url = self.base_url + endpoint

        # 构建请求路径（用于签名）
        request_path = endpoint
        if params:
            query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
            request_path = f"{endpoint}?{query_string}"
            url = f"{url}?{query_string}"

        body_str = ""
        if body:
            body_str = json.dumps(body)

        headers = self._get_headers(method.upper(), request_path, body_str)

        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method.upper() == 'POST':
                response = requests.post(url, headers=headers, data=body_str, timeout=10)
            else:
                log_error(f"不支持的请求方法: {method}")
                return None

            data = response.json()

            if data.get('code') != '0':
                log_error(f"API 错误: {data.get('msg', '未知错误')} (code: {data.get('code')})")
                return None

            return data

        except requests.exceptions.RequestException as e:
            log_error(f"网络请求失败: {e}")
            return None
        except json.JSONDecodeError as e:
            log_error(f"JSON 解析失败: {e}")
            return None

    # ============== 公共接口 ==============

    def get_ticker(self, symbol: str = None) -> Optional[Dict]:
        """
        获取行情数据（当前价格）
        """
        symbol = symbol or config.SYMBOL
        endpoint = '/api/v5/market/ticker'
        params = {'instId': symbol}

        result = self._request('GET', endpoint, params=params)
        if result and result.get('data'):
            return result['data'][0]
        return None

    def get_current_price(self, symbol: str = None) -> Optional[float]:
        """
        获取当前价格（简化版）
        """
        ticker = self.get_ticker(symbol)
        if ticker:
            return float(ticker.get('last', 0))
        return None

    # ============== 账户接口 ==============

    def get_balance(self, currency: str = 'USDT') -> Optional[float]:
        """
        获取账户余额
        """
        endpoint = '/api/v5/account/balance'
        params = {'ccy': currency}

        result = self._request('GET', endpoint, params=params)
        if result and result.get('data'):
            details = result['data'][0].get('details', [])
            for item in details:
                if item.get('ccy') == currency:
                    return float(item.get('availBal', 0))
        return None

    def get_positions(self, symbol: str = None) -> Optional[list]:
        """
        获取持仓信息（现货账户查询余额）
        """
        symbol = symbol or config.SYMBOL
        base_currency = symbol.split('-')[0]  # ETH-USDT -> ETH

        endpoint = '/api/v5/account/balance'
        result = self._request('GET', endpoint)

        if result and result.get('data'):
            details = result['data'][0].get('details', [])
            for item in details:
                if item.get('ccy') == base_currency:
                    return {
                        'currency': base_currency,
                        'available': float(item.get('availBal', 0)),
                        'frozen': float(item.get('frozenBal', 0))
                    }
        return None

    # ============== 交易接口 ==============

    def place_order(self, side: str, size: str, price: Optional[str] = None,
                    order_type: str = 'market', symbol: str = None) -> Optional[Dict]:
        """
        下单

        Args:
            side: 'buy' 或 'sell'
            size: 交易数量
            price: 限价单价格（市价单不需要）
            order_type: 'market' 市价单 或 'limit' 限价单
            symbol: 交易对

        Returns:
            订单信息或 None
        """
        symbol = symbol or config.SYMBOL
        endpoint = '/api/v5/trade/order'

        body = {
            'instId': symbol,
            'tdMode': config.TRADE_MODE,  # cash = 现货
            'side': side,
            'ordType': order_type,
            'sz': str(size)
        }

        # 现货买入时，sz 是计价货币数量（USDT），需要设置 tgtCcy
        if side == 'buy':
            body['tgtCcy'] = 'quote_ccy'  # 按 USDT 金额买入

        if order_type == 'limit' and price:
            body['px'] = str(price)

        result = self._request('POST', endpoint, body=body)
        if result and result.get('data'):
            order_data = result['data'][0]
            if order_data.get('sCode') == '0':
                logger.info(f"下单成功: {side} {size} @ {price or 'market'}")
                return order_data
            else:
                log_error(f"下单失败: {order_data.get('sMsg')}")
        return None

    def buy_market(self, usdt_amount: float, symbol: str = None) -> Optional[Dict]:
        """
        市价买入（按 USDT 金额）
        """
        return self.place_order('buy', str(usdt_amount), order_type='market', symbol=symbol)

    def sell_market(self, coin_amount: float, symbol: str = None) -> Optional[Dict]:
        """
        市价卖出（按币数量）
        """
        symbol = symbol or config.SYMBOL
        endpoint = '/api/v5/trade/order'

        body = {
            'instId': symbol,
            'tdMode': config.TRADE_MODE,
            'side': 'sell',
            'ordType': 'market',
            'sz': str(coin_amount),
            'tgtCcy': 'base_ccy'  # 按币的数量卖出
        }

        result = self._request('POST', endpoint, body=body)
        if result and result.get('data'):
            order_data = result['data'][0]
            if order_data.get('sCode') == '0':
                logger.info(f"卖出成功: {coin_amount}")
                return order_data
            else:
                log_error(f"卖出失败: {order_data.get('sMsg')}")
        return None

    def get_order(self, order_id: str, symbol: str = None) -> Optional[Dict]:
        """
        查询订单状态
        """
        symbol = symbol or config.SYMBOL
        endpoint = '/api/v5/trade/order'
        params = {
            'instId': symbol,
            'ordId': order_id
        }

        result = self._request('GET', endpoint, params=params)
        if result and result.get('data'):
            return result['data'][0]
        return None

    def cancel_order(self, order_id: str, symbol: str = None) -> bool:
        """
        撤销订单
        """
        symbol = symbol or config.SYMBOL
        endpoint = '/api/v5/trade/cancel-order'
        body = {
            'instId': symbol,
            'ordId': order_id
        }

        result = self._request('POST', endpoint, body=body)
        if result and result.get('data'):
            return result['data'][0].get('sCode') == '0'
        return False


# 创建全局 API 实例
api = OkxAPI()


if __name__ == '__main__':
    # 测试代码
    print("测试 OKX API 连接...")

    # 测试获取价格（无需 API Key）
    price = api.get_current_price()
    if price:
        print(f"ETH-USDT 当前价格: {price}")
    else:
        print("获取价格失败")

    # 测试获取余额（需要 API Key）
    if config.API_KEY:
        balance = api.get_balance('USDT')
        if balance is not None:
            print(f"USDT 余额: {balance}")
        else:
            print("获取余额失败，请检查 API 配置")
    else:
        print("未配置 API Key，跳过余额测试")
