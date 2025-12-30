#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test API status"""
import sys
import io

# Fix Windows encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from okx_grid_bot.api.okx_client import api
from okx_grid_bot.utils import config
import json
import time
import random

# Get account balance
print('=== Account Balance ===')
balance = api.get_balance('USDT')
print(f'USDT: {balance}')

eth_position = api.get_position(config.SYMBOL)
print(f'ETH Position: {json.dumps(eth_position, indent=2)}')

# Get current price
print('\n=== Current Price ===')
price = api.get_current_price()
print(f'ETH-USDT: {price}')

# Test clOrdId generation
print('\n=== Test clOrdId Generation ===')
for i in range(5):
    test_clOrdId = f'TEST-{i}-{int(time.time() * 1000000)}-{random.randint(1000, 9999)}'
    print(f'{i+1}. {test_clOrdId}')
    time.sleep(0.1)

print('\n=== Checking ANALYZE_ONLY status ===')
print(f'ANALYZE_ONLY: {config.ANALYZE_ONLY}')
print(f'USE_SIMULATED: {config.USE_SIMULATED}')
