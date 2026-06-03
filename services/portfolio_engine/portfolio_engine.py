"""
Portfolio Engine - Multi-Pair Portfolio Management
Fungsi: Exposure Monitoring, Correlation Analysis, Capital Allocation
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class CorrelationPair:
    """Struktur untuk pair correlation"""
    pair1: str
    pair2: str
    correlation: float
    status: str


@dataclass
class PositionInfo:
    """Informasi positioning"""
    pair: str
    direction: str
    entry_price: float
    position_size: float
    risk_amount: float
    unrealized_pnl: float = 0.0
    exposure_percent: float = 0.0


class PortfolioEngine:
    """Engine untuk portfolio management multi-pair"""

    # Standard correlation matrix untuk pair utama
    CORRELATION_MATRIX = {
        ('XAUUSD', 'XAGUSD'): 0.72,
        ('EURUSD', 'GBPUSD'): 0.85,
        ('USDJPY', 'GBPJPY'): 0.78,
        ('XAUUSD', 'EURUSD'): -0.45,
    }

    CORRELATION_THRESHOLD = 0.80

    def __init__(self, total_equity: float):
        """Initialize Portfolio Engine"""
        self.total_equity = total_equity
        self.positions: Dict[str, List[PositionInfo]] = {}
        self.price_history: Dict[str, pd.DataFrame] = {}
        self.correlation_cache: Dict = {}

    def add_position(self, pair: str, direction: str, entry_price: float,
                     position_size: float, risk_amount: float) -> PositionInfo:
        """Add new position to portfolio"""
        position = PositionInfo(
            pair=pair,
            direction=direction,
            entry_price=entry_price,
            position_size=position_size,
            risk_amount=risk_amount,
            exposure_percent=self._calculate_exposure(entry_price, position_size)
        )

        if pair not in self.positions:
            self.positions[pair] = []

        self.positions[pair].append(position)
        return position

    def update_position_pnl(self, pair: str, current_price: float) -> None:
        """Update unrealized PnL untuk semua positions di pair"""
        if pair not in self.positions:
            return

        for position in self.positions[pair]:
            if position.direction == 'BUY':
                pnl = (current_price - position.entry_price) * position.position_size
            else:
                pnl = (position.entry_price - current_price) * position.position_size

            position.unrealized_pnl = pnl
            position.exposure_percent = self._calculate_exposure(current_price, position.position_size)

    def get_portfolio_exposure(self) -> Dict:
        """Get total portfolio exposure"""
        total_exposure = 0.0
        pair_exposures = {}

        for pair, positions in self.positions.items():
            pair_exposure = sum(p.exposure_percent for p in positions)
            pair_exposures[pair] = round(pair_exposure, 2)
            total_exposure += pair_exposure

        return {
            "total_exposure_percent": round(total_exposure, 2),
            "pair_exposures": pair_exposures,
            "is_balanced": total_exposure <= 100.0
        }

    def analyze_correlation(self, pair1: str, pair2: str,
                           price_data1: pd.DataFrame,
                           price_data2: pd.DataFrame) -> CorrelationPair:
        """Analyze correlation antara 2 pair"""
        cache_key = tuple(sorted([pair1, pair2]))
        if cache_key in self.correlation_cache:
            return self.correlation_cache[cache_key]

        returns1 = price_data1['close'].pct_change()
        returns2 = price_data2['close'].pct_change()

        correlation = returns1.corr(returns2)

        if abs(correlation) >= 0.8:
            status = 'HIGH'
        elif abs(correlation) >= 0.5:
            status = 'MEDIUM'
        else:
            status = 'LOW'

        result = CorrelationPair(
            pair1=pair1,
            pair2=pair2,
            correlation=round(correlation, 3),
            status=status
        )

        self.correlation_cache[cache_key] = result
        return result

    def check_correlation_risk(self, new_pair: str, direction: str) -> Dict:
        """Check correlation risk ketika menambah posisi baru"""
        risks = []
        active_pairs = list(self.positions.keys())

        for active_pair in active_pairs:
            corr_pair = tuple(sorted([new_pair, active_pair]))

            if corr_pair in self.CORRELATION_MATRIX:
                correlation = self.CORRELATION_MATRIX[corr_pair]
            else:
                correlation = 0.3

            if abs(correlation) > self.CORRELATION_THRESHOLD:
                active_position = self.positions[active_pair][0]
                same_direction = active_position.direction == direction

                risk_level = 'HIGH' if same_direction else 'MEDIUM'
                risks.append({
                    "pair": active_pair,
                    "correlation": correlation,
                    "risk_level": risk_level,
                    "recommendation": "Adjust position size" if same_direction else "Monitor closely"
                })

        return {
            "has_correlation_risk": len(risks) > 0,
            "risks": risks,
            "action_required": len([r for r in risks if r['risk_level'] == 'HIGH']) > 0
        }

    def allocate_capital(self, available_capital: float, pairs: List[str],
                        weights: Optional[Dict[str, float]] = None) -> Dict[str, float]:
        """Allocate capital ke multiple pairs"""
        if weights is None:
            weights = {pair: 1.0 / len(pairs) for pair in pairs}
        else:
            total_weight = sum(weights.values())
            weights = {pair: w / total_weight for pair, w in weights.items()}

        allocation = {}
        for pair in pairs:
            allocation[pair] = round(available_capital * weights.get(pair, 0), 2)

        return allocation

    def get_portfolio_summary(self) -> Dict:
        """Get comprehensive portfolio summary"""
        total_pnl = 0.0
        total_risk = 0.0
        positions_count = 0

        pair_summary = {}

        for pair, positions in self.positions.items():
            pair_pnl = sum(p.unrealized_pnl for p in positions)
            pair_risk = sum(p.risk_amount for p in positions)
            pair_positions = len(positions)

            pair_summary[pair] = {
                "positions": pair_positions,
                "unrealized_pnl": round(pair_pnl, 2),
                "risk_amount": round(pair_risk, 2),
                "net_exposure": round(sum(p.exposure_percent for p in positions), 2)
            }

            total_pnl += pair_pnl
            total_risk += pair_risk
            positions_count += pair_positions

        return {
            "total_equity": round(self.total_equity, 2),
            "total_unrealized_pnl": round(total_pnl, 2),
            "total_risk_amount": round(total_risk, 2),
            "total_risk_percent": round((total_risk / self.total_equity * 100) if self.total_equity > 0 else 0, 2),
            "positions_count": positions_count,
            "pairs_count": len(self.positions),
            "pair_summary": pair_summary,
            "portfolio_exposure": self.get_portfolio_exposure()
        }

    def _calculate_exposure(self, price: float, position_size: float) -> float:
        """Calculate exposure percentage"""
        if self.total_equity <= 0:
            return 0.0

        exposure = (price * position_size) / self.total_equity * 100
        return exposure
