## OG 1048 with edits

import backtrader as bt
# import backtrader.feeds as btfeeds
import datetime

class RSIStrategy(bt.Strategy):
    params = (
        ('rsi_period', 14),   # Standard RSI period, use 7 for 1min, 9 for 5min, 14 fine for 15 mins
        ('rsi_overbought', 70),
        ('rsi_oversold', 30),
        ('rsi_buffer', 7),     # Buffer to avoid flipping positions frequently, 3 for smaller time-frame
        ('atr_period', 14),     # ATR period for stop-loss calculation
        ('risk_per_trade', 0.05),  # Risking 5% of account balance per trade
        ('scale_factor', 2.5),  # How much to scale position sizes
    )

    def log(self, txt, dt=None):
        """ Logging function """
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()}: {txt}')

    def __init__(self):
        """ Initialize indicators and variables """
        self.rsi = bt.indicators.RSI(self.data, period=self.params.rsi_period)
        self.atr = bt.indicators.ATR(self.data, period=self.params.atr_period)

        self.in_long = False
        self.in_short = False
        self.entry_price = None
        self.stop_loss = None

    def calculate_position_size(self):
      balance = self.broker.get_cash()
      price = self.data.close[0]

      if price <= 0 or balance < 50:
          return 0

      risk_per_trade = self.params.risk_per_trade
      position_size = (balance * risk_per_trade) / price
      return max(position_size, 50 / price) if balance >= 50 else self.position.size



    def next(self):
        cash = self.broker.get_cash()
        position_size = self.calculate_position_size()
        atr_value = self.atr[0]


        # --- LONG ENTRY STRATEGY ---
        if self.rsi[0] < 40 and not self.in_long:
            scale_factor = self.params.scale_factor * (40 - self.rsi[0]) / 20
            long_size = position_size * scale_factor / self.params.scale_factor
            self.buy(size=long_size)
            self.in_long = True
            self.entry_price = self.data.close[0]

            self.stop_loss = self.entry_price + (atr_value * 5)  # 3x ATR Stop-Loss, 1.5x for 1,5min
            self.stop_loss = min(self.stop_loss, self.data.close[0] - (atr_value * 2))  # ✅ Dynamic trailing stop
            
            # self.log(f"Portfolio value at time of trade: ${self.broker.get_value()}, Cash at time of trade: ${self.broker.get_cash()}")
            self.log(f"Portfolio Value: ${self.broker.get_value()}, Cash: ${self.broker.get_cash()}, Holdings: ${self.broker.get_value() - self.broker.get_cash()}")
            self.log(f"BUY {long_size} ETH at {self.entry_price}, Stop: {self.stop_loss}")
            self.log(f"RSI: {self.rsi[0]}, Dollar amount longed: ${long_size * self.entry_price}")
            self.log("-")
  

        elif self.rsi[0] > 50 and self.in_long:
            # Scale out of long positions
            exit_factor = (self.rsi[0] - 50) / 20
            # close_size = position_size * exit_factor
            close_size = self.position.size * exit_factor
            self.sell(size=close_size)

            # self.log(f"Portfolio value at time of trade: ${self.broker.get_value()}, Cash at time of trade: ${self.broker.get_cash()}")
            self.log(f"Portfolio Value: ${self.broker.get_value()}, Cash: ${self.broker.get_cash()}, Holdings: ${self.broker.get_value() - self.broker.get_cash()}")

            self.log(f"SELL {close_size} ETH at {self.data.close[0]} (Closing Long)")
            self.log(f"RSI: {self.rsi[0]}, Long amount closed: ${close_size * self.data.close[0]}")
            self.log("-")
            if self.rsi[0] >= 70:
                self.in_long = False  # Fully exited long position

        # --- SHORT ENTRY STRATEGY ---
        if self.rsi[0] > 50 and not self.in_short:
            scale_factor = self.params.scale_factor * (self.rsi[0] - 50) / 20
            short_size = position_size * scale_factor / self.params.scale_factor
            self.sell(size=short_size)
            self.in_short = True
            self.entry_price = self.data.close[0]

            self.stop_loss = self.entry_price + (atr_value * 5)  # 3x ATR Stop-Loss, 1.5x for 1,5min
            self.stop_loss = max(self.stop_loss, self.data.close[0] - (atr_value * 2))  # ✅ Dynamic trailing stop

            # self.log(f"Portfolio value at time of trade: ${self.broker.get_value()}, Cash at time of trade: ${self.broker.get_cash()}")
            self.log(f"Portfolio Value: ${self.broker.get_value()}, Cash: ${self.broker.get_cash()}, Holdings: ${self.broker.get_value() - self.broker.get_cash()}")

            self.log(f"SHORT {short_size} ETH at {self.entry_price}, Stop: {self.stop_loss}")
            self.log(f"RSI: {self.rsi[0]}, Dollar amount shorted: ${short_size * self.entry_price}")
            self.log("-")

        elif self.rsi[0] < 50 and self.in_short:
            # Scale out of short positions
            exit_factor = (50 - self.rsi[0]) / 20
            # close_size = position_size * exit_factor
            close_size = self.position.size * exit_factor
            self.buy(size=close_size)
            # self.log(f"Portfolio value at time of trade: ${self.broker.get_value()}, Cash at time of trade: ${self.broker.get_cash()}")
            self.log(f"Portfolio Value: ${self.broker.get_value()}, Cash: ${self.broker.get_cash()}, Holdings: ${self.broker.get_value() - self.broker.get_cash()}")
            self.log(f"COVER SHORT {close_size} ETH at {self.data.close[0]}")
            self.log(f"RSI: {self.rsi[0]}, Short amount closed: ${close_size * self.data.close[0]}")
            self.log("-")
            if self.rsi[0] <= 30:
                self.in_short = False  # Fully exited short position


        # --- STOP-LOSS LOGIC ---
        if self.in_long and self.data.close[0] < self.stop_loss:
            self.sell(size=position_size)  # Exit long
            self.log(f"STOP LOSS HIT for LONG at {self.data.close[0]}, Dollar Value SL: ${position_size * self.data.close[0]}")
            self.in_long = False

        if self.in_short and self.data.close[0] > self.stop_loss:
            self.buy(size=position_size)  # Exit short
            self.log(f"STOP LOSS HIT for SHORT at {self.data.close[0]}, Dollar Value SL: ${position_size * self.data.close[0]}")
            self.in_short = False


# --- BACKTESTING SETUP ---
if __name__ == '__main__':
    cerebro = bt.Cerebro()
    cerebro.addstrategy(RSIStrategy)

    # data = bt.feeds.GenericCSVData(
    #     dataname="ETH_clean_data.csv",
    #     openinterest=-1
    # )
    data = bt.feeds.YahooFinanceCSVData(dataname='examples/Data_ETH.csv')

    cerebro.adddata(data)
    cerebro.broker.set_cash(10000)  
    cerebro.broker.setcommission(commission=0.0001)  
    cerebro.broker.set_slippage_perc(0.001)

    start_value = cerebro.getbroker().getvalue()
    print('🚀 Starting Portfolio Value:', cerebro.broker.getvalue())
    cerebro.run()
    end_value = cerebro.getbroker().getvalue()
    pnl = end_value - start_value
    print('🏁 Final Portfolio Value:', cerebro.broker.getvalue())
    print('PNL:', pnl)