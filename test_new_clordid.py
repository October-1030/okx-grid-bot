#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test new clOrdId format"""
import sys
import io
import time
import random

# Fix Windows encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from okx_grid_bot.api.okx_client import api
from okx_grid_bot.utils import config

print('=== Testing New clOrdId Format ===')

# Generate test IDs
for i in range(5):
    grid_index = i
    ts = int(time.time() * 1000)
    rnd = random.randint(10000, 99999)
    client_order_id = f"B{grid_index}-{ts}-{rnd}"
    print(f'{i+1}. {client_order_id} (length: {len(client_order_id)})')
    time.sleep(0.1)

print('\n=== Attempting Real Order ===')
# Try actual order
ts = int(time.time() * 1000)
rnd = random.randint(10000, 99999)
test_clOrdId = f"BTEST-{ts}-{rnd}"
print(f'clOrdId: {test_clOrdId} (length: {len(test_clOrdId)})')

try:
    result = api.buy_market(config.AMOUNT_PER_GRID, client_order_id=test_clOrdId)
    print(f'SUCCESS! Order result: {result}')
except Exception as e:
    print(f'Error: {e}')
    if hasattr(e, 'raw_response'):
        print(f'Raw response: {e.raw_response}')
