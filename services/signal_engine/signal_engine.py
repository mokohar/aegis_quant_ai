"""
Signal Engine - Advanced Market Signal Generation
Komponen: Liquidity Sweep, BOS, Order Block, FVG, Momentum
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class SignalType(Enum):
    """Tipe Signal"""
    LIQUIDITY_SWEEP = "liquidity_sweep"
    BREAK_OF_STRUCTURE = "bos"
    ORDER_BLOCK = "order_block"
    FAIR_VALUE_GAP = "fvg"
    MOMENTUM_EXPANSION = "momentum"


@dataclass
class Signal:
    """Struktur Signal"""
    signal_type: SignalType
    direction: str  # 'BUY' or 'SELL'
    score: float  # 0-100
    price: float
    timestamp: str
    confidence: float
    strength: str  # 'WEAK', 'MEDIUM', 'STRONG'


class SignalEngine:
    """Engine untuk generate trading signals"""

    # Scoring Configuration
    SCORE_CONFIG = {
        SignalType.LIQUIDITY_SWEEP: 30,
        SignalType.BREAK_OF_STRUCTURE: 20,
        SignalType.ORDER_BLOCK: 20,
        SignalType.FAIR_VALUE_GAP: 15,
        SignalType.MOMENTUM_EXPANSION: 15,
    }

    def __init__(self):
        """Initialize Signal Engine"""
        self.max_score = sum(self.SCORE_CONFIG.values())
        self.signals: List[Signal] = []

    def analyze_liquidity_sweep(self, candles: pd.DataFrame) -> Tuple[float, str]:
        """
        Deteksi Liquidity Sweep - Price action yang mencapai extreme level lalu reversal
        """
        if len(candles) < 5:
            return 0.0, 'BUY'

        recent = candles.iloc[-5:]
        high = recent['high'].max()
        low = recent['low'].min()
        close = candles.iloc[-1]['close']

        if close > high * 0.999:
            score = self.SCORE_CONFIG[SignalType.LIQUIDITY_SWEEP]
            direction = 'SELL'
            return score, direction
        elif close < low * 1.001:
            score = self.SCORE_CONFIG[SignalType.LIQUIDITY_SWEEP]
            direction = 'BUY'
            return score, direction

        return 0.0, 'HOLD'

    def analyze_break_of_structure(self, candles: pd.DataFrame) -> Tuple[float, str]:
        """Break of Structure (BOS) - Price breaks previous structure"""
        if len(candles) < 10:
            return 0.0, 'BUY'

        recent = candles.iloc[-10:]
        prev_high = recent.iloc[:-1]['high'].max()
        prev_low = recent.iloc[:-1]['low'].min()
        current_close = candles.iloc[-1]['close']

        score = self.SCORE_CONFIG[SignalType.BREAK_OF_STRUCTURE]

        if current_close > prev_high * 1.001:
            return score, 'BUY'
        elif current_close < prev_low * 0.999:
            return score, 'SELL'

        return 0.0, 'HOLD'

    def analyze_order_block(self, candles: pd.DataFrame) -> Tuple[float, str]:
        """Order Block Detection - Area dengan banyak transaksi"""
        if len(candles) < 15:
            return 0.0, 'BUY'

        recent = candles.iloc[-15:]
        volumes = recent['volume'].values
        closes = recent['close'].values

        avg_volume = np.mean(volumes)
        high_volume_idx = np.where(volumes > avg_volume * 1.5)[0]

        if len(high_volume_idx) > 0:
            ob_price = closes[high_volume_idx[-1]]
            current_price = candles.iloc[-1]['close']

            score = self.SCORE_CONFIG[SignalType.ORDER_BLOCK]

            if current_price < ob_price:
                return score, 'BUY'
            elif current_price > ob_price:
                return score, 'SELL'

        return 0.0, 'HOLD'

    def analyze_fair_value_gap(self, candles: pd.DataFrame) -> Tuple[float, str]:
        """Fair Value Gap (FVG) - Gap antara candle yang belum terisi"""
        if len(candles) < 3:
            return 0.0, 'BUY'

        recent = candles.iloc[-3:]
        prev_low = recent.iloc[0]['low']
        prev_high = recent.iloc[0]['high']
        curr_high = recent.iloc[1]['high']
        curr_low = recent.iloc[1]['low']

        score = self.SCORE_CONFIG[SignalType.FAIR_VALUE_GAP]

        if curr_low > prev_high:
            return score, 'BUY'
        elif curr_high < prev_low:
            return score, 'SELL'

        return 0.0, 'HOLD'

    def analyze_momentum_expansion(self, candles: pd.DataFrame) -> Tuple[float, str]:
        """Momentum Expansion - Analisis kecepatan dan arah momentum"""
        if len(candles) < 20:
            return 0.0, 'BUY'

        closes = candles['close'].values[-20:]
        changes = np.diff(closes)
        up_moves = np.sum(changes[changes > 0])
        down_moves = np.abs(np.sum(changes[changes < 0]))

        score = self.SCORE_CONFIG[SignalType.MOMENTUM_EXPANSION]

        if up_moves > down_moves * 1.5:
            return score, 'BUY'
        elif down_moves > up_moves * 1.5:
            return score, 'SELL'

        return 0.0, 'HOLD'

    def generate_signals(self, candles: pd.DataFrame, pair: str) -> List[Signal]:
        """Generate comprehensive signals dari semua komponen"""
        signals = []
        timestamp = candles.iloc[-1].name if hasattr(candles.iloc[-1], 'name') else str(pd.Timestamp.now())

        components = [
            (self.analyze_liquidity_sweep, SignalType.LIQUIDITY_SWEEP),
            (self.analyze_break_of_structure, SignalType.BREAK_OF_STRUCTURE),
            (self.analyze_order_block, SignalType.ORDER_BLOCK),
            (self.analyze_fair_value_gap, SignalType.FAIR_VALUE_GAP),
            (self.analyze_momentum_expansion, SignalType.MOMENTUM_EXPANSION),
        ]

        total_score = 0.0
        active_signals = []

        for analyzer, signal_type in components:
            score, direction = analyzer(candles)
            if score > 0:
                active_signals.append((signal_type, direction, score))
                total_score += score

        for signal_type, direction, score in active_signals:
            current_price = candles.iloc[-1]['close']
            confidence = score / self.SCORE_CONFIG[signal_type]
            strength = self._get_strength(confidence)

            signal = Signal(
                signal_type=signal_type,
                direction=direction,
                score=score,
                price=current_price,
                timestamp=str(timestamp),
                confidence=confidence,
                strength=strength
            )
            signals.append(signal)

        self.signals = signals
        return signals

    def get_composite_score(self) -> float:
        """Hitung composite score dari semua active signals (0-100)"""
        if not self.signals:
            return 0.0

        total = sum(signal.score for signal in self.signals)
        return min(total, self.max_score) / self.max_score * 100

    def get_signal_summary(self) -> Dict:
        """Get summary dari semua signals"""
        if not self.signals:
            return {"total_signals": 0, "composite_score": 0.0, "direction": "HOLD"}

        buy_signals = len([s for s in self.signals if s.direction == 'BUY'])
        sell_signals = len([s for s in self.signals if s.direction == 'SELL'])

        direction = 'BUY' if buy_signals > sell_signals else 'SELL' if sell_signals > buy_signals else 'HOLD'

        return {
            "total_signals": len(self.signals),
            "buy_signals": buy_signals,
            "sell_signals": sell_signals,
            "composite_score": self.get_composite_score(),
            "direction": direction,
            "signals": [self._signal_to_dict(s) for s in self.signals]
        }

    @staticmethod
    def _get_strength(confidence: float) -> str:
        """Determine signal strength based on confidence"""
        if confidence >= 0.75:
            return 'STRONG'
        elif confidence >= 0.50:
            return 'MEDIUM'
        else:
            return 'WEAK'

    @staticmethod
    def _signal_to_dict(signal: Signal) -> Dict:
        """Convert Signal to dictionary"""
        return {
            "type": signal.signal_type.value,
            "direction": signal.direction,
            "score": signal.score,
            "price": signal.price,
            "timestamp": signal.timestamp,
            "confidence": round(signal.confidence, 3),
            "strength": signal.strength
        }
