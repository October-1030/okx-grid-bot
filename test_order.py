#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test actual order placement to see detailed error"""
import sys
import io

# Fix Windows encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from okx_grid_bot.api.okx_client import api
from okx_grid_bot.utils import config
import time
import random

print('=== Testing Order Placement ===')
print(f'SYMBOL: {config.SYMBOL}')
print(f'AMOUNT_PER_GRID: {config.AMOUNT_PER_GRID}')
print(f'ANALYZE_ONLY: {config.ANALYZE_ONLY}')

# Get current balance
balance = api.get_balance('USDT')
print(f'USDT Balance: {balance}')

# Get current price
price = api.get_current_price()
print(f'Current Price: {price}')

# Try to place a test order
print('\nAttempting to place order...')
test_clOrdId = f'B-TEST-{int(time.time() * 1000000)}-{random.randint(1000, 9999)}'
print(f'clOrdId: {test_clOrdId}')

try:
    result = api.buy_market(config.AMOUNT_PER_GRID, client_order_id=test_clOrdId)
    print(f'Order result: {result}')
except Exception as e:
    print(f'Error type: {type(e).__name__}')
    print(f'Error message: {e}')
    if hasattr(e, 'raw_response'):
        print(f'Raw response: {e.raw_response}')
