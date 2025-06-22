import time
import numpy as np
import example_utils
from hyperliquid.utils import constants

# === CONFIG ===
RSI_PERIOD = 14
RSI_ENTRY_THRESHOLD = 20
RSI_EXIT_THRESHOLD = 30
TRADE_SYMBOL = "HYPE"
LEVERAGE = 5
CHECK_INTERVAL = 5  # seconds
MIN_TRADE_SIZE_HYPE = 0.01
PRICE_HISTORY_LIMIT = RSI_PERIOD * 10  # Keep enough price data

# === INIT ===
address, info, exchange = example_utils.setup(base_url=constants.MAINNET_API_URL, skip_ws=False)

# Set leverage once
try:
    exchange.update_leverage(LEVERAGE, TRADE_SYMBOL)
except Exception as e:
    print(f"⚠️ Could not set leverage: {e}")

# === STATE ===
prices_1m = []

# === UTILS ===
def get_live_price(symbol):
    response = info.all_mids()
    if response and symbol in response:
        return float(response[symbol])
    print(f"❌ Error fetching price for {symbol}")
    return None

def get_account_balance():
    response = info.user_state(address)
    if response and "marginSummary" in response:
        return float(response["marginSummary"]["accountValue"])
    print("⚠️ Unable to fetch account balance.")
    return 0

def calculate_position_size(balance, price):
    if price <= 0 or balance < MIN_TRADE_SIZE_HYPE * price:
        return 0
    position_size = (balance * 0.05) / price  # 5% per trade
    return max(position_size, MIN_TRADE_SIZE_HYPE)

def get_position():
    response = info.user_state(address)
    if "assetPositions" in response:
        for asset in response["assetPositions"]:
            if "position" in asset and isinstance(asset["position"], dict):
                p = asset["position"]
                if p.get("coin") == TRADE_SYMBOL:
                    size = float(p.get("szi", "0"))
                    if size > 0:
                        return {"size": size, "side": "long"}
                    elif size < 0:
                        return {"size": abs(size), "side": "short"}
    return None

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

def place_order(symbol, side, size):
    try:
        resp = exchange.market_open(symbol, side, size, LEVERAGE)
        print(f"✅ {side.upper()} order placed: {size:.4f} {symbol}")
        return resp
    except Exception as e:
        print(f"❌ Order failed: {e}")
        return None

# === MAIN BOT LOOP ===
def run_trading_bot():
    print(f"\n🚀 RSI Trading Bot started for {TRADE_SYMBOL}")
    print(f"🎯 Strategy: Long when RSI < {RSI_ENTRY_THRESHOLD} on both 1m & 5m")
    print(f"🔚 Exit when RSI > {RSI_EXIT_THRESHOLD} on either timeframe")
    print("-" * 60)

    while True:
        try:
            # Step 1: Price feed
            live_price = get_live_price(TRADE_SYMBOL)
            if not live_price:
                time.sleep(CHECK_INTERVAL)
                continue

            prices_1m.append(live_price)
            if len(prices_1m) > PRICE_HISTORY_LIMIT:
                prices_1m.pop(0)

            # Step 2: RSI calculation
            rsi_1m = compute_rsi(prices_1m)
            rsi_5m = compute_rsi(prices_1m[::5])  # Downsample for 5m

            if rsi_1m is None or rsi_5m is None:
                print("⏳ Waiting for enough price data...")
                time.sleep(CHECK_INTERVAL)
                continue

            # Step 3: Fetch account info
            balance = get_account_balance()
            position = get_position()

            print(
                f"📊 RSI 1m: {rsi_1m:.2f} | RSI 5m: {rsi_5m:.2f} | Price: ${live_price:.2f}"
            )
            print(
                f"💰 Balance: ${balance:.2f} | Position: {position}\n"
            )

            # Step 4: Entry Condition
            if rsi_1m < RSI_ENTRY_THRESHOLD and rsi_5m < RSI_ENTRY_THRESHOLD and not position:
                size = calculate_position_size(balance, live_price)
                if size >= MIN_TRADE_SIZE_HYPE:
                    place_order(TRADE_SYMBOL, "long", size)

            # Step 5: Exit Condition
            elif position and position["side"] == "long":
                if rsi_1m > RSI_EXIT_THRESHOLD or rsi_5m > RSI_EXIT_THRESHOLD:
                    close_size = position["size"] * 0.1  # 10% per run
                    if close_size >= MIN_TRADE_SIZE_HYPE:
                        place_order(TRADE_SYMBOL, "short", close_size)

            print("-" * 60)
            time.sleep(CHECK_INTERVAL)

        except Exception as e:
            print(f"❌ Runtime error: {e}")
            time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    run_trading_bot()
