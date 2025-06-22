import time
import numpy as np
import example_utils
from hyperliquid.utils import constants

# Load API credentials
address, info, exchange = example_utils.setup(base_url=constants.TESTNET_API_URL, skip_ws=False)

# Strategy Parameters
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30
RISK_PER_TRADE = 0.05
SCALE_FACTOR = 2.5
TRADE_SYMBOL = "ETH"
LEVERAGE = 5
CHECK_INTERVAL = 1
MIN_TRADE_SIZE_ETH = 0.01  # Adjusted to ensure valid order execution

# Fetch real-time ticker price
def get_live_price(symbol):
    response = info.all_mids()
    if response and symbol in response:
        return float(response[symbol])
    print(f"❌ Error fetching price for {symbol}: {response}")
    return None

# Fetch real-time account balance
def get_account_balance():
    response = info.user_state(address)
    if response and "marginSummary" in response:
        return float(response["marginSummary"]["accountValue"])
    print("⚠️ Unable to fetch account balance, defaulting to $0")
    return 0

# Compute position size dynamically
def calculate_position_size(balance, price):
    if price <= 0 or balance < MIN_TRADE_SIZE_ETH * price:
        return 0
    position_size = (balance * RISK_PER_TRADE) / price
    return max(position_size, MIN_TRADE_SIZE_ETH)

# Compute RSI
def compute_rsi(prices, period=RSI_PERIOD):
    if len(prices) < period:
        return None
    delta = np.diff(prices)
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)
    avg_gain = np.mean(gain[-period:]) if len(gain) >= period else np.mean(gain)
    avg_loss = np.mean(loss[-period:]) if len(loss) >= period else np.mean(loss)
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# Place market order
def place_order(symbol, side, size):
    if size < MIN_TRADE_SIZE_ETH:
        print(f"⚠️ Order size {size:.4f} ETH is below the minimum required size.")
        return

    rounded_size = round(size, 4)
    is_buy = side == "long"

    order_result = exchange.market_open(symbol, is_buy, rounded_size, None, 0.01)

    if order_result["status"] == "ok":
        print(f"✅ Order executed: {side.upper()} {rounded_size:.4f} {symbol}")
        time.sleep(2)  # Allow Hyperliquid to update position
    else:
        print(f"❌ Order failed: {order_result}")

# Fetch open position
def get_position():
    response = info.user_state(address)

    if "assetPositions" in response and isinstance(response["assetPositions"], list):
        for asset in response["assetPositions"]:
            if "position" in asset and isinstance(asset["position"], dict):
                position = asset["position"]
                print(f"🔍 Position Data: {position}")

                if position.get("coin") == TRADE_SYMBOL:
                    size = float(position.get("szi", "0"))  # Convert string to float

                    if size > 0:
                        return {"size": size, "side": "long"}
                    elif size < 0:
                        return {"size": abs(size), "side": "short"}

    print("⚠️ No open position found or incorrect API response structure.")
    return None

# Compute position scaling
def compute_scaled_position_size(rsi_value, base_position_size):
    scale_factor = 1 + ((40 - rsi_value) / 20) * SCALE_FACTOR if rsi_value < 40 else 1
    return base_position_size * scale_factor

# Main trading loop
def run_real_time_trading():
    in_long = False
    in_short = False
    prices = []

    while True:
        live_price = get_live_price(TRADE_SYMBOL)
        balance = get_account_balance()

        if live_price is None:
            print("⚠️ Waiting for live data...")
            time.sleep(CHECK_INTERVAL)
            continue

        prices.append(live_price)
        if len(prices) > RSI_PERIOD:
            prices.pop(0)

        last_rsi = compute_rsi(prices)
        if last_rsi is None:
            print("⚠️ Not enough data to compute RSI...")
            time.sleep(CHECK_INTERVAL)
            continue

        position = get_position()
        base_size = calculate_position_size(balance, live_price)
        scaled_size = compute_scaled_position_size(last_rsi, base_size)

        if position:
            in_long = position["side"] == "long"
            in_short = position["side"] == "short"

        # 🚀 **Aggressive Scaling into Longs when RSI is Below 30**
        if last_rsi < 30:
            print(f"🔥 RSI {last_rsi:.2f} - Aggressively Buying ETH with scaled size {scaled_size:.4f}")
            place_order(TRADE_SYMBOL, "long", scaled_size)

        # 📈 **Regular Long Entry**
        elif last_rsi < 40 and not in_long:
            print(f"📈 RSI {last_rsi:.2f} - Buying ETH with scaled size {scaled_size:.4f}")
            place_order(TRADE_SYMBOL, "long", scaled_size)
            in_long = True
            in_short = False

        # ⚖️ **Scaling Out of Long**
        elif last_rsi > 50 and in_long:
            exit_factor = (last_rsi - 50) / 20
            close_size = position["size"] * exit_factor if position else 0
            print(f"⚖️ Scaling Out of Long: Closing {close_size:.4f} ETH")
            place_order(TRADE_SYMBOL, "short", close_size)
            if last_rsi >= 70:
                in_long = False

        # 🔻 **Short Entry when RSI is Overbought**
        if last_rsi > 70 and not in_short:
            print(f"🔻 RSI {last_rsi:.2f} - Shorting ETH with scaled size {scaled_size:.4f}")
            place_order(TRADE_SYMBOL, "short", scaled_size)
            in_short = True
            in_long = False

        # ⚖️ **Scaling Out of Short**
        elif last_rsi < 50 and in_short:
            exit_factor = (50 - last_rsi) / 20
            close_size = position["size"] * exit_factor if position else 0
            print(f"⚖️ Scaling Out of Short: Closing {close_size:.4f} ETH")
            place_order(TRADE_SYMBOL, "long", close_size)
            if last_rsi <= 30:
                in_short = False

        print(f"📊 RSI: {last_rsi:.2f} | Price: ${live_price:.2f} | Balance: ${balance:.2f}")
        print("-" * 50)
        time.sleep(CHECK_INTERVAL)

# Run the bot
if __name__ == "__main__":
    print("🚀 Starting Real-Time RSI Trading Bot on Hyperliquid with Dynamic Position Sizing")
    run_real_time_trading()
