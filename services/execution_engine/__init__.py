"""
Execution Engine - Trade Execution & Position Management
Fungsi: Open, Modify, Close, Break Even, Partial Close, ATR Trailing, Layering
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from enum import Enum
from datetime import datetime


class OrderType(Enum):
    """Tipe order"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderStatus(Enum):
    """Status order"""
    PENDING = "pending"
    OPEN = "open"
    PARTIALLY_CLOSED = "partially_closed"
    CLOSED = "closed"
    CANCELLED = "cancelled"


@dataclass
class Order:
    """Struktur Order"""
    order_id: str
    pair: str
    order_type: OrderType
    direction: str
    entry_price: float
    position_size: float
    stop_loss: float
    take_profit: float
    status: OrderStatus = OrderStatus.PENDING
    opened_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    closing_price: float = 0.0
    pnl: float = 0.0
    layer_number: int = 1
    spread: float = 0.0
    slippage: float = 0.0


class ExecutionEngine:
    """Engine untuk execution dan position management"""

    LAYER_CONFIGS = {
        1: {"risk_percent": 0.75, "min_profit": 0.0, "min_score": 0.0},
        2: {"risk_percent": 0.50, "min_profit": 1.0, "min_score": 90.0},
        3: {"risk_percent": 0.25, "min_profit": 1.5, "min_score": 90.0},
    }

    MAX_SPREAD = 0.5
    MAX_SLIPPAGE = 0.3

    def __init__(self):
        """Initialize Execution Engine"""
        self.orders: Dict[str, Order] = {}
        self.order_counter = 0
        self.execution_log: List[Dict] = []

    def open_position(self, pair: str, direction: str, entry_price: float,
                     position_size: float, stop_loss: float, take_profit: float,
                     spread: float = 0.0, slippage: float = 0.0,
                     layer_number: int = 1) -> Tuple[bool, Optional[Order], str]:
        """Buka position baru"""
        if spread > self.MAX_SPREAD:
            return False, None, f"Spread exceeds maximum"

        if slippage > self.MAX_SLIPPAGE:
            return False, None, f"Slippage exceeds maximum"

        order_id = self._generate_order_id()
        order = Order(
            order_id=order_id,
            pair=pair,
            order_type=OrderType.MARKET,
            direction=direction,
            entry_price=entry_price,
            position_size=position_size,
            stop_loss=stop_loss,
            take_profit=take_profit,
            status=OrderStatus.OPEN,
            opened_at=datetime.now(),
            layer_number=layer_number,
            spread=spread,
            slippage=slippage
        )

        self.orders[order_id] = order
        self._log_execution("OPEN", order)
        return True, order, f"Position opened: {order_id}"

    def close_position(self, order_id: str, closing_price: float,
                      close_type: str = "manual") -> Tuple[bool, Optional[Order], str]:
        """Close existing position"""
        if order_id not in self.orders:
            return False, None, f"Order not found"

        order = self.orders[order_id]
        if order.status == OrderStatus.CLOSED:
            return False, None, f"Order already closed"

        if order.direction == "BUY":
            pnl = (closing_price - order.entry_price) * order.position_size
        else:
            pnl = (order.entry_price - closing_price) * order.position_size

        order.closing_price = closing_price
        order.pnl = pnl
        order.closed_at = datetime.now()
        order.status = OrderStatus.CLOSED

        self._log_execution("CLOSE", order, close_type=close_type)
        return True, order, f"Position closed: {order_id}"

    def modify_position(self, order_id: str, new_stop_loss: Optional[float] = None,
                       new_take_profit: Optional[float] = None) -> Tuple[bool, Optional[Order], str]:
        """Modify existing position"""
        if order_id not in self.orders:
            return False, None, f"Order not found"

        order = self.orders[order_id]
        if new_stop_loss:
            order.stop_loss = new_stop_loss
        if new_take_profit:
            order.take_profit = new_take_profit

        self._log_execution("MODIFY", order)
        return True, order, f"Position modified"

    def set_break_even(self, order_id: str, buffer_pips: float = 0.5) -> Tuple[bool, Optional[Order], str]:
        """Set break even"""
        if order_id not in self.orders:
            return False, None, f"Order not found"

        order = self.orders[order_id]
        if order.direction == "BUY":
            new_sl = order.entry_price + buffer_pips
        else:
            new_sl = order.entry_price - buffer_pips

        order.stop_loss = new_sl
        return True, order, f"Break even set"

    def set_atr_trailing(self, order_id: str, atr_value: float,
                        multiplier: float = 2.0) -> Tuple[bool, Optional[Order], str]:
        """Set ATR trailing stop"""
        if order_id not in self.orders:
            return False, None, f"Order not found"

        order = self.orders[order_id]
        trailing_distance = atr_value * multiplier

        if order.direction == "BUY":
            new_sl = order.entry_price - trailing_distance
        else:
            new_sl = order.entry_price + trailing_distance

        order.stop_loss = new_sl
        return True, order, f"ATR trailing set"

    def add_layer(self, base_order_id: str, current_price: float,
                 position_size: float, stop_loss: float, take_profit: float,
                 opportunity_score: float) -> Tuple[bool, Optional[Order], str]:
        """Add layer to position"""
        if base_order_id not in self.orders:
            return False, None, f"Base order not found"

        base_order = self.orders[base_order_id]
        current_layers = [o for o in self.orders.values()
                         if o.pair == base_order.pair and not o.closed_at]
        next_layer = len(current_layers) + 1

        if next_layer > 3:
            return False, None, "Maximum 3 layers reached"

        order_id = self._generate_order_id()
        layer_order = Order(
            order_id=order_id,
            pair=base_order.pair,
            order_type=OrderType.MARKET,
            direction=base_order.direction,
            entry_price=current_price,
            position_size=position_size,
            stop_loss=stop_loss,
            take_profit=take_profit,
            status=OrderStatus.OPEN,
            opened_at=datetime.now(),
            layer_number=next_layer
        )

        self.orders[order_id] = layer_order
        return True, layer_order, f"Layer {next_layer} added"

    def get_active_positions(self, pair: Optional[str] = None) -> List[Order]:
        """Get active positions"""
        active_orders = [o for o in self.orders.values()
                        if o.status in [OrderStatus.OPEN, OrderStatus.PARTIALLY_CLOSED]]
        if pair:
            active_orders = [o for o in active_orders if o.pair == pair]
        return active_orders

    def get_execution_summary(self) -> Dict:
        """Get execution summary"""
        closed_orders = [o for o in self.orders.values() if o.status == OrderStatus.CLOSED]
        total_pnl = sum(o.pnl for o in closed_orders)
        winning_trades = len([o for o in closed_orders if o.pnl > 0])
        losing_trades = len([o for o in closed_orders if o.pnl < 0])

        return {
            "total_orders": len(self.orders),
            "active_orders": len(self.get_active_positions()),
            "closed_orders": len(closed_orders),
            "total_pnl": round(total_pnl, 2),
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
        }

    def _generate_order_id(self) -> str:
        """Generate unique order ID"""
        self.order_counter += 1
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"ORD-{timestamp}-{self.order_counter:05d}"

    def _log_execution(self, action: str, order: Order, **kwargs) -> None:
        """Log execution"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "order_id": order.order_id,
            "pair": order.pair,
            "direction": order.direction,
            **kwargs
        }
        self.execution_log.append(log_entry)
