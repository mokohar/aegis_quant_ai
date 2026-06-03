"""
Risk Engine - Portfolio dan Per-Trade Risk Management
Kebijakan: 2% portfolio risk, 0.75%-1% per trade, no martingale/grid
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum
import math


class AccountType(Enum):
    """Tipe akun berdasarkan balance"""
    NANO = "nano"  # $100-250
    MICRO = "micro"  # $250-1k
    STANDARD = "standard"  # $1k-10k
    PROFESSIONAL = "professional"  # >10k


@dataclass
class AccountConfig:
    """Konfigurasi akun berdasarkan type"""
    account_type: AccountType
    max_pairs: int
    max_layers: int
    risk_percent: float
    min_balance: float
    max_balance: float


class RiskEngine:
    """Engine untuk manajemen risiko portfolio dan trade"""

    # Account Configuration
    ACCOUNT_CONFIGS = {
        AccountType.NANO: AccountConfig(
            account_type=AccountType.NANO,
            max_pairs=2,
            max_layers=2,
            risk_percent=0.75,
            min_balance=100,
            max_balance=250
        ),
        AccountType.MICRO: AccountConfig(
            account_type=AccountType.MICRO,
            max_pairs=3,
            max_layers=2,
            risk_percent=1.0,
            min_balance=250,
            max_balance=1000
        ),
        AccountType.STANDARD: AccountConfig(
            account_type=AccountType.STANDARD,
            max_pairs=5,
            max_layers=3,
            risk_percent=1.0,
            min_balance=1000,
            max_balance=10000
        ),
        AccountType.PROFESSIONAL: AccountConfig(
            account_type=AccountType.PROFESSIONAL,
            max_pairs=10,
            max_layers=5,
            risk_percent=1.0,
            min_balance=10000,
            max_balance=float('inf')
        )
    }

    # Global Risk Limits
    PORTFOLIO_RISK_LIMIT = 2.0  # %
    MAX_DRAWDOWN_LIMIT = 10.0  # %

    def __init__(self, balance: float, equity: float, account_leverage: int = 100):
        """
        Initialize Risk Engine
        
        Args:
            balance: Account balance
            equity: Current equity
            account_leverage: Account leverage
        """
        self.balance = balance
        self.equity = equity
        self.account_leverage = account_leverage
        self.account_type = self._determine_account_type(balance)
        self.account_config = self.ACCOUNT_CONFIGS[self.account_type]
        self.active_trades: Dict = {}
        self.drawdown_history: List[float] = []

    def _determine_account_type(self, balance: float) -> AccountType:
        """Tentukan tipe akun berdasarkan balance"""
        for acc_type, config in self.ACCOUNT_CONFIGS.items():
            if config.min_balance <= balance < config.max_balance:
                return acc_type
        return AccountType.PROFESSIONAL

    def calculate_position_size(self, entry_price: float, stop_loss: float,
                                 risk_amount: Optional[float] = None) -> float:
        """
        Calculate optimal position size berdasarkan risk
        """
        if risk_amount is None:
            risk_amount = self.equity * (self.account_config.risk_percent / 100)

        # Prevent exceeding portfolio risk limit
        portfolio_risk = self.equity * (self.PORTFOLIO_RISK_LIMIT / 100)
        if risk_amount > portfolio_risk:
            risk_amount = portfolio_risk

        # Calculate pip distance
        pip_distance = abs(entry_price - stop_loss)
        if pip_distance == 0:
            return 0

        # Position size = Risk Amount / Pip Distance
        position_size = risk_amount / pip_distance

        return round(position_size, 2)

    def validate_trade_entry(self, pair: str, direction: str, entry_price: float,
                            stop_loss: float, take_profit: float) -> Dict:
        """
        Validasi sebelum entry trade
        """
        errors = []
        warnings = []

        # Check: Pair limit
        active_pairs = len(set(t['pair'] for t in self.active_trades.values()))
        if active_pairs >= self.account_config.max_pairs:
            errors.append(f"Max pairs ({self.account_config.max_pairs}) exceeded")

        # Check: Stop Loss exist
        if stop_loss is None or stop_loss == entry_price:
            errors.append("Stop Loss must be set and different from entry")

        # Check: Take Profit exist
        if take_profit is None or take_profit == entry_price:
            errors.append("Take Profit must be set and different from entry")

        # Check: Risk/Reward Ratio
        risk = abs(entry_price - stop_loss)
        reward = abs(take_profit - entry_price)
        rr_ratio = 0
        if risk > 0:
            rr_ratio = reward / risk
            if rr_ratio < 1.0:
                warnings.append(f"Low RR ratio: {rr_ratio:.2f}:1")

        # Check: Position size
        pos_size = self.calculate_position_size(entry_price, stop_loss)
        if pos_size <= 0:
            errors.append("Invalid position size calculated")

        # Check: Margin available
        margin_required = self.calculate_margin_required(entry_price, pos_size)
        available_margin = self.equity * self.account_leverage
        if margin_required > available_margin:
            errors.append("Insufficient margin")

        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "position_size": pos_size,
            "margin_required": margin_required,
            "rr_ratio": rr_ratio if risk > 0 else 0
        }

    def calculate_margin_required(self, price: float, position_size: float) -> float:
        """Calculate margin required untuk position"""
        # Standard: 1% margin requirement (leverage 100)
        margin_percent = 1.0 / self.account_leverage
        margin = (price * position_size) * margin_percent
        return round(margin, 2)

    def update_drawdown(self, new_equity: float) -> float:
        """Update dan calculate drawdown"""
        peak_equity = max([self.equity] + self.drawdown_history)
        drawdown = ((peak_equity - new_equity) / peak_equity) * 100 if peak_equity > 0 else 0
        self.drawdown_history.append(new_equity)
        self.equity = new_equity

        return round(drawdown, 2)

    def check_drawdown_limit(self) -> bool:
        """Check apakah drawdown sudah exceed limit"""
        if not self.drawdown_history:
            return True

        peak = max(self.drawdown_history + [self.equity])
        current_dd = ((peak - self.equity) / peak) * 100 if peak > 0 else 0

        return current_dd <= self.MAX_DRAWDOWN_LIMIT

    def get_portfolio_risk_status(self) -> Dict:
        """Get status risiko portfolio"""
        total_risk = sum(t.get('risk_amount', 0) for t in self.active_trades.values())
        portfolio_risk_percent = (total_risk / self.equity * 100) if self.equity > 0 else 0

        return {
            "total_risk_amount": round(total_risk, 2),
            "portfolio_risk_percent": round(portfolio_risk_percent, 2),
            "risk_limit_percent": self.PORTFOLIO_RISK_LIMIT,
            "remaining_risk_capacity": round(self.PORTFOLIO_RISK_LIMIT - portfolio_risk_percent, 2),
            "can_trade": portfolio_risk_percent < self.PORTFOLIO_RISK_LIMIT,
            "trades_count": len(self.active_trades),
            "pairs_count": len(set(t['pair'] for t in self.active_trades.values()))
        }

    def get_account_status(self) -> Dict:
        """Get comprehensive account status"""
        return {
            "account_type": self.account_type.value,
            "balance": round(self.balance, 2),
            "equity": round(self.equity, 2),
            "leverage": f"1:{self.account_leverage}",
            "max_pairs": self.account_config.max_pairs,
            "max_layers": self.account_config.max_layers,
            "risk_percent": self.account_config.risk_percent,
            "portfolio_risk_limit": self.PORTFOLIO_RISK_LIMIT,
            "max_drawdown_limit": self.MAX_DRAWDOWN_LIMIT
        }
