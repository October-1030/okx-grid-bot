#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test simple clOrdId format without hyphens"""
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

print('=== Testing Simple clOrdId Format (no hyphens) ===')

# Try different formats
formats_to_test = [
    f"B{int(time.time() * 1000)}",  # Just timestamp
    f"TEST{random.randint(100000, 999999)}",  # Just random
    f"B{int(time.time() * 1000) % 100000000}{random.randint(1000, 9999)}",  # Short timestamp + random
]

for fmt in formats_to_test:
    print(f'Testing: {fmt} (length: {len(fmt)})')

print('\n=== Attempting Order with Simple Format ===')
test_clOrdId = f"B{int(time.time() * 1000) % 100000000}{random.randint(10000, 99999)}"
print(f'clOrdId: {test_clOrdId} (length: {len(test_clOrdId)})')

try:
    result = api.buy_market(config.AMOUNT_PER_GRID, client_order_id=test_clOrdId)
    print(f'✓ SUCCESS! Order placed: {result}')
    print(f'Order ID: {result.get("ordId")}')
except Exception as e:
    print(f'✗ Error: {e}')
    if hasattr(e, 'raw_response'):
        data = e.raw_response.get('data', [])
        if data:
            print(f'Error code: {data[0].get("sCode")}')
            print(f'Error message: {data[0].get("sMsg")}')
