"""
MQL5 Indicator Bridge - Integration dengan MQL5 Indicators
Bridge antara Python dan MT5 Terminal untuk latest algo trading indicators
"""

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class IndicatorResult:
    """Struktur hasil indicator"""
    indicator_name: str
    pair: str
    timeframe: str
    timestamp: datetime
    value: float
    signal: Optional[float] = None
    histogram: Optional[float] = None
    interpretation: str = "NEUTRAL"


class MQL5Bridge:
    """Bridge untuk menggunakan MQL5 indicators dalam Python"""

    SUPPORTED_INDICATORS = [
        "RSI", "MACD", "ATR", "BB", "STOCHASTIC", "EMA", "SMA", 
        "ADX", "ICHIMOKU", "ALLIGATOR", "FRACTAL", "ZZ"
    ]

    TIMEFRAME_MAP = {
        "M1": mt5.TIMEFRAME_M1,
        "M5": mt5.TIMEFRAME_M5,
        "M15": mt5.TIMEFRAME_M15,
        "M30": mt5.TIMEFRAME_M30,
        "H1": mt5.TIMEFRAME_H1,
        "H4": mt5.TIMEFRAME_H4,
        "D1": mt5.TIMEFRAME_D1,
        "W1": mt5.TIMEFRAME_W1,
    }

    def __init__(self, login: int, password: str, server: str, path: Optional[str] = None):
        """Initialize MQL5 Bridge"""
        self.login = login
        self.password = password
        self.server = server
        self.path = path
        self.connected = False
        self.indicators_cache: Dict = {}

    def connect(self) -> bool:
        """Connect ke MT5 Terminal"""
        try:
            if self.path:
                self.connected = mt5.initialize(path=self.path)
            else:
                self.connected = mt5.initialize()

            if not self.connected:
                print(f"MT5 initialization failed")
                return False

            authorized = mt5.login(self.login, password=self.password, server=self.server)
            if not authorized:
                print(f"Failed to login to MT5")
                return False

            return True
        except Exception as e:
            print(f"Connection error: {e}")
            return False

    def disconnect(self) -> None:
        """Disconnect dari MT5 Terminal"""
        mt5.shutdown()
        self.connected = False

    def get_candles(self, pair: str, timeframe: str, count: int = 100) -> Optional[pd.DataFrame]:
        """Get candle data dari MT5"""
        if not self.connected:
            print("Not connected to MT5")
            return None

        try:
            tf = self.TIMEFRAME_MAP.get(timeframe)
            if not tf:
                print(f"Unsupported timeframe: {timeframe}")
                return None

            rates = mt5.copy_rates_from_pos(pair, tf, 0, count)
            if rates is None or len(rates) == 0:
                print(f"No data for {pair} {timeframe}")
                return None

            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df.rename(columns={
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'tick_volume': 'volume'
            }, inplace=True)

            return df[['time', 'open', 'high', 'low', 'close', 'volume']]
        except Exception as e:
            print(f"Error getting candles: {e}")
            return None

    def calculate_rsi(self, pair: str, timeframe: str, period: int = 14) -> Optional[IndicatorResult]:
        """Calculate RSI (Relative Strength Index)"""
        df = self.get_candles(pair, timeframe, period + 10)
        if df is None:
            return None

        closes = df['close'].values
        deltas = np.diff(closes)
        seed = deltas[:period+1]
        up = seed[seed >= 0].sum() / period
        down = -seed[seed < 0].sum() / period if seed[seed < 0].sum() != 0 else 0.0001
        rs = up / down if down != 0 else 0
        rsi = 100.0 - 100.0 / (1.0 + rs)

        if rsi > 70:
            interpretation = "OVERBOUGHT"
        elif rsi < 30:
            interpretation = "OVERSOLD"
        else:
            interpretation = "NEUTRAL"

        return IndicatorResult(
            indicator_name="RSI",
            pair=pair,
            timeframe=timeframe,
            timestamp=df.iloc[-1]['time'],
            value=round(rsi, 2),
            interpretation=interpretation
        )

    def calculate_macd(self, pair: str, timeframe: str,
                      fast: int = 12, slow: int = 26, signal: int = 9) -> Optional[IndicatorResult]:
        """Calculate MACD (Moving Average Convergence Divergence)"""
        df = self.get_candles(pair, timeframe, slow + 10)
        if df is None:
            return None

        closes = df['close'].values
        ema_fast = pd.Series(closes).ewm(span=fast, adjust=False).mean().values
        ema_slow = pd.Series(closes).ewm(span=slow, adjust=False).mean().values
        macd_line = ema_fast - ema_slow
        signal_line = pd.Series(macd_line).ewm(span=signal, adjust=False).mean().values
        histogram = macd_line - signal_line

        macd_val = macd_line[-1]
        signal_val = signal_line[-1]
        hist_val = histogram[-1]

        if macd_val > signal_val:
            interpretation = "BULLISH"
        elif macd_val < signal_val:
            interpretation = "BEARISH"
        else:
            interpretation = "NEUTRAL"

        return IndicatorResult(
            indicator_name="MACD",
            pair=pair,
            timeframe=timeframe,
            timestamp=df.iloc[-1]['time'],
            value=round(macd_val, 5),
            signal=round(signal_val, 5),
            histogram=round(hist_val, 5),
            interpretation=interpretation
        )

    def calculate_atr(self, pair: str, timeframe: str, period: int = 14) -> Optional[IndicatorResult]:
        """Calculate ATR (Average True Range)"""
        df = self.get_candles(pair, timeframe, period + 10)
        if df is None:
            return None

        high = df['high'].values
        low = df['low'].values
        close = df['close'].values

        tr = np.maximum(
            high[1:] - low[1:],
            np.maximum(
                np.abs(high[1:] - close[:-1]),
                np.abs(low[1:] - close[:-1])
            )
        )

        atr = np.mean(tr[-period:])

        return IndicatorResult(
            indicator_name="ATR",
            pair=pair,
            timeframe=timeframe,
            timestamp=df.iloc[-1]['time'],
            value=round(atr, 5),
            interpretation="VOLATILITY_MEASURE"
        )

    def calculate_bollinger_bands(self, pair: str, timeframe: str,
                                 period: int = 20, std_dev: float = 2.0) -> Optional[Dict]:
        """Calculate Bollinger Bands"""
        df = self.get_candles(pair, timeframe, period + 10)
        if df is None:
            return None

        closes = df['close'].values
        sma = pd.Series(closes).rolling(window=period).mean().values
        std = pd.Series(closes).rolling(window=period).std().values

        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)

        last_close = closes[-1]
        interpretation = "NORMAL"
        if last_close > upper_band[-1]:
            interpretation = "OVERBOUGHT"
        elif last_close < lower_band[-1]:
            interpretation = "OVERSOLD"

        return {
            "indicator_name": "BB",
            "pair": pair,
            "timeframe": timeframe,
            "upper_band": round(upper_band[-1], 5),
            "middle_band": round(sma[-1], 5),
            "lower_band": round(lower_band[-1], 5),
            "close": round(last_close, 5),
            "interpretation": interpretation
        }

    def calculate_stochastic(self, pair: str, timeframe: str,
                           k_period: int = 14, d_period: int = 3) -> Optional[IndicatorResult]:
        """Calculate Stochastic Oscillator"""
        df = self.get_candles(pair, timeframe, k_period + 10)
        if df is None:
            return None

        high = df['high'].values
        low = df['low'].values
        close = df['close'].values

        highest_high = pd.Series(high).rolling(window=k_period).max().values
        lowest_low = pd.Series(low).rolling(window=k_period).min().values

        k_values = 100 * (close - lowest_low) / (highest_high - lowest_low + 0.0001)
        k_smooth = pd.Series(k_values).rolling(window=3).mean().values
        d_smooth = pd.Series(k_smooth).rolling(window=d_period).mean().values

        k_val = k_smooth[-1]
        d_val = d_smooth[-1]

        if k_val > 80:
            interpretation = "OVERBOUGHT"
        elif k_val < 20:
            interpretation = "OVERSOLD"
        else:
            interpretation = "NEUTRAL"

        return IndicatorResult(
            indicator_name="STOCHASTIC",
            pair=pair,
            timeframe=timeframe,
            timestamp=df.iloc[-1]['time'],
            value=round(k_val, 2),
            signal=round(d_val, 2),
            interpretation=interpretation
        )

    def get_all_indicators(self, pair: str, timeframe: str) -> Dict:
        """Get all supported indicators"""
        results = {
            "rsi": self.calculate_rsi(pair, timeframe),
            "macd": self.calculate_macd(pair, timeframe),
            "atr": self.calculate_atr(pair, timeframe),
            "bb": self.calculate_bollinger_bands(pair, timeframe),
            "stochastic": self.calculate_stochastic(pair, timeframe)
        }
        return results
