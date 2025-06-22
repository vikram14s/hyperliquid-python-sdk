# import time
# import numpy as np
import example_utils
from tabulate import tabulate
from hyperliquid.utils import constants
from datetime import datetime
# Load API credentials
address, info, exchange = example_utils.setup(base_url=constants.MAINNET_API_URL, skip_ws=False)

all_mids = info.all_mids()

# Target address
target_address = "0x5D2F4460Ac3514AdA79f5D9838916E508Ab39Bb7"

open_positions = info.user_state(target_address)["assetPositions"]
limit_orders = info.open_orders(target_address)

print("Fetching data for address: ", target_address)
print()
# print("Open positions: ", open_positions)
# print()
# print("Limit orders: ", limit_orders)
# print()

def format_open_positions(positions):
    if not positions:
        print("No open positions. \n")
        return
    
    table_data = []
    for pos in positions:
        p = pos["position"]
        side = "Long" if float(p["szi"]) > 0 else "Short"
        table_data.append([
            p["coin"],
            f"{abs(float(p['szi'])):,.2f}",
            side,
            f"{float(p['entryPx']):,.2f}",
            f"{float(p['positionValue']):,.2f}",
            f"{float(p['unrealizedPnl']):,.2f}",
            f"{float(p['liquidationPx']):,.2f}",
            f"{float(p['marginUsed']):,.2f}",
        ])
            
    headers = ["Coin", "Size", "Side", "Entry Price", "Position Value", "Unrealized PnL", "Liquidation Price", "Margin Used"]
    print("--- Open Positions ---")
    print(tabulate(table_data, headers=headers, tablefmt="grid"))



def format_limit_orders(orders):
    if not orders:
        print("No limit orders.\n")
        return

    table_data = []
    for order in orders:
        ts = datetime.fromtimestamp(order["timestamp"] / 1000.0).strftime("%Y-%m-%d %H:%M:%S")
        reduce_only = order.get("reduceOnly", False)
        table_data.append([
            order["coin"],
            "Buy" if order["side"] == "B" else "Sell",
            f"{float(order['limitPx']):,.2f}",
            f"{float(order['sz']):,.2f}",
            ts,
            "Yes" if reduce_only else "No"
        ])

    headers = ["Coin", "Side", "Limit Price", "Size", "Timestamp", "Reduce Only"]
    print("--- Limit Orders ---")
    print(tabulate(table_data, headers=headers, tablefmt="grid"))

user_state = info.user_state(target_address)
spot_state = info.spot_user_state(target_address)

print(f"Account Value: ${float(user_state['marginSummary']['accountValue']):,.2f}")
print()
print()
format_open_positions(open_positions)
print()
print()
format_limit_orders(limit_orders)