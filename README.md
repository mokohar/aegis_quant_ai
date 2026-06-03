# AEGIS QUANT AI - Enterprise Algorithmic Trading Platform

Platform trading otomatis berbasis AI dengan multi-broker MT5, full auto trading, adaptive account management, dan institutional risk management.

## 🎯 Fitur Utama

- ✅ Multi-Broker MT5 Support (Exness, HFM, IC Markets, Pepperstone)
- ✅ Full Automated Trading dengan AI Learning
- ✅ 8 Trading Pairs Prioritas (XAUUSD, XAGUSD, USTEC, BTCUSD, EURUSD, GBPUSD, USDJPY, GBPJPY)
- ✅ Advanced Signal Engine (Liquidity Sweep, BOS, Order Block, FVG, Momentum)
- ✅ Adaptive Account Management (Nano, Micro, Standard, Professional)
- ✅ Portfolio Risk Management (2% portfolio risk, no martingale/grid)
- ✅ Layering Engine dengan Multi-Layer Support
- ✅ AI Scoring (LightGBM, XGBoost, PyTorch)
- ✅ Enterprise Dashboard + Telegram Control Center
- ✅ Backtest Engine dengan Monte Carlo Simulation
- ✅ Self-Learning Engine untuk Strategy Improvement
- ✅ MQL5 Indicator Integration (Latest Algo Trading)

## 📊 Teknologi Stack

### Backend
- Python 3.12 + FastAPI
- LightGBM, XGBoost, PyTorch

### Database
- PostgreSQL + TimescaleDB
- Redis

### Frontend
- Next.js + React + TypeScript

### Deployment
- Docker & Kubernetes
- Grafana, Prometheus, Loki

## 📁 Project Structure

```
aegis_quant_ai/
├── services/
│   ├── signal_engine/
│   ├── opportunity_engine/
│   ├── risk_engine/
│   ├── portfolio_engine/
│   ├── execution_engine/
│   ├── learning_engine/
│   ├── backtest_engine/
│   ├── mt5_bridge/
│   ├── broker_adapter/
│   └── mql5_indicator_bridge/
├── apps/
│   ├── api/
│   ├── dashboard/
│   └── telegram/
├── database/
├── deployment/
└── docs/
```

## 🚀 Quick Start

```bash
git clone https://github.com/mokohar/aegis_quant_ai.git
cd aegis_quant_ai
pip install -r requirements.txt
docker-compose up -d
```

**Version**: 1.0  
**Last Updated**: 2026-06-03
