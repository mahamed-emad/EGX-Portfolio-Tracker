# 📈 EGX Portfolio Tracker

**Portfolio tracker with real-time EGX price integration — built to solve my own investment tracking problem**

</div>

---

## 💡 Why I Built This

Tracking an Egyptian stock portfolio manually means juggling spreadsheets, refreshing broker apps, and doing mental math on every position.

I wanted **one place** that tells me:
- What I own and at what average cost
- What it's worth **right now** at the live market price
- How much I'm up or down — per stock and in total

So I built it. Clean Python backend, Arabic RTL interface, live prices pulled straight from TradingView.

---

## ✨ Features

| | Feature | Details |
|--|---------|---------|
| 📊 | **Real-time Prices** | Live EGX prices via TradingView Scanner API + 5 fallback sources |
| 🧮 | **Auto P&L** | Weighted average cost vs. live price — calculated automatically |
| 💼 | **Portfolio View** | Holdings, cost basis, current value, daily change per stock |
| 💰 | **Cash Management** | Track deposits, withdrawals, and available liquidity |
| 📋 | **Transaction Log** | Complete history — buy / sell / deposit / withdraw with timestamps |
| 👥 | **Multi-Portfolio** | Each user has a fully isolated database — zero cross-contamination |
| 🏦 | **EGX Stock Database** | Pre-loaded Egyptian stocks + bulk CSV import for 100+ custom stocks |
| 🔒 | **Smart Validation** | Prevents overselling, overdraft, and invalid tickers |
| 🌙 | **Arabic UI** | Full RTL dark interface in Egyptian Arabic |

---

## 🖥️ Interface Preview

```
┌─────────────────────────────────────────────────────────────┐
│  📈 محفظتي              أحمد ↗     14:32:07    ⟳ تحديث     │
├──────────────┬──────────────┬──────────────┬────────────────┤
│ إجمالي الإيداع│  السيولة     │ قيمة المحفظة │   الربح/الخسارة│
│  100,000 ج   │   37,000 ج   │  105,400 ج   │  +5,400 +5.4%  │
├──────────────┴──────────────┴──────────────┴────────────────┤
│  💼 المحفظة    ⚡ العمليات    📋 السجل    🏦 الأسهم          │
├───────┬──────────────────┬──────┬────────┬────────┬─────────┤
│ الكود │     الشركة       │ عدد  │ متوسط  │ الحالي │  ر/خ % │
├───────┼──────────────────┼──────┼────────┼────────┼─────────┤
│ COMI  │ CIB              │ 100  │ 85.00  │ 91.50  │ +7.6% 🟢│
│ ACTF  │ أكتيف            │ 500  │ 12.30  │ 11.80  │ -4.1% 🔴│
│ ETEL  │ المصرية للاتصالات│ 200  │ 22.50  │ 24.10  │ +7.1% 🟢│
└───────┴──────────────────┴──────┴────────┴────────┴─────────┘
```

---

## 🏗️ Architecture

```
EGX-Portfolio-Tracker/
│
├── app.py                        # Flask app factory + entry point
│
├── database/
│   ├── db.py                     # DB init · shared stocks · user registry
│   ├── shared.db                 # EGX stock reference  ← shared by all users
│   ├── registry.db               # User registry
│   └── users/
│       ├── ahmed.db              # Ahmed's isolated portfolio
│       └── mohamed.db            # Mohamed's isolated portfolio
│
├── services/
│   ├── portfolio_service.py      # Business logic — OOP, one method per operation
│   └── price_fetcher.py          # Real-time price engine — 6-level fallback chain
│
├── routes/
│   └── api.py                    # All REST API endpoints
│
├── templates/
│   └── index.html                # Arabic RTL Single Page App
│
└── static/
    ├── css/style.css             # Dark theme · CSS variables
    └── js/app.js                 # Vanilla JS · modular functions
```

### 🗄️ Database Design — Full Isolation

```
shared.db   →  Egyptian stock codes, names, sectors   (read by everyone)
registry.db →  Who the users are

users/
  ahmed.db   →  Ahmed's balance + holdings + transactions   (private)
  sara.db    →  Sara's balance + holdings + transactions    (private)
```

No shared tables between portfolios. One user cannot see another's data.

### 📡 Price Fetching — No Cache, Always Fresh

Every refresh hits the internet directly — no stale numbers:

```
Portfolio stocks
       │
       ▼
① TradingView Targeted API ──────────── all stocks in 1 request ⚡
       │ missing?
       ▼
② Yahoo Finance Bulk API ─────────────  remaining in 1 request
       │ still missing?
       ▼
③ yfinance library  ──────────────────  one by one
       │
④ Stooq (.EG)       ──────────────────  one by one
       │
⑤ Mubasher          ──────────────────  one by one
       │
⑥ EGX Official API  ──────────────────  one by one
```

TradingView resolves 95%+ of cases in a single HTTP request.
Fallbacks exist for edge cases and newly listed stocks.

---

## 🚀 Getting Started

### Prerequisites
```
Python 3.11+
```

### Installation

```bash
# 1. Clone the repo
git clone https://github.com/mahamed-emad/EGX-Portfolio-Tracker.git
cd EGX-Portfolio-Tracker

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run
python app.py
```

Open **`http://localhost:5000`** in your browser.

### First Steps

```
① Create your portfolio  →  enter a username and display name
② Deposit capital        →  sets your starting cash balance
③ Add your stocks        →  type the EGX ticker code (e.g. COMI, ETEL, ACTF)
④ Hit Refresh            →  live prices load, P&L calculates automatically
```

---

## 📋 How Operations Work

### 🟢 Buy
Records a purchase and calculates the weighted average cost.

```
First buy:   100 shares × 85.00 EGP  =  8,500 EGP
Second buy:   50 shares × 90.00 EGP  =  4,500 EGP
──────────────────────────────────────────────────
Total:        150 shares              = 13,000 EGP
New average:  13,000 ÷ 150            =  86.67 EGP/share  ✅
```

### 🔴 Sell
Reduces holdings. Proceeds are added to cash balance.
Realized P&L is calculated using the weighted average cost.

### 💵 Deposit / Withdraw
Manages your cash balance independently of stock positions.
Deposit increases net investment. Withdraw reduces it — which raises your return % if you're in profit.

---

## 🔒 Validation Rules

| Scenario | Behavior |
|----------|----------|
| Sell more shares than owned | ❌ Blocked with clear message |
| Withdraw more than cash balance | ❌ Blocked — shows available amount |
| Buy with insufficient funds | ❌ Blocked — shows shortfall |
| Invalid / unlisted EGX ticker | ❌ Blocked — must add to DB first |
| Buy same stock again | ✅ Weighted average recalculated automatically |

---

## 🏦 Adding Custom Stocks (Bulk Import)

Go to the **Stocks tab** and paste in CSV format — one stock per line:

```
COMI,بنك كومرشيال انترناشيونال,بنوك
ACTF,أكتيف للتأجير التمويلي,خدمات مالية
VLMRA,فاليور,عقارات
KRDI,كارديان,تكنولوجيا
```

Format: `TICKER, Arabic Name, Sector`

Up to 100+ stocks can be imported in one paste.

---

## 📡 API Reference

All responses follow the structure:
```json
{ "ok": true, "data": { ... }, "message": "..." }
```

### Portfolio

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/summary` | Cash balance, total portfolio value, P&L |
| `GET` | `/api/holdings` | All positions with live prices and P&L |
| `POST` | `/api/market/refresh` | Fetch live prices → recalculate everything |

### Operations

| Method | Endpoint | Required Body |
|--------|----------|---------------|
| `POST` | `/api/buy` | `{ code, quantity, amount }` |
| `POST` | `/api/sell` | `{ code, quantity, amount }` |
| `POST` | `/api/deposit` | `{ amount }` |
| `POST` | `/api/withdraw` | `{ amount }` |

### Transaction History

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/transactions` | All history (newest first) |
| `GET` | `/api/transactions?type=buy` | Filter: `buy` / `sell` / `deposit` / `withdraw` |

### Users & Sessions

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/users` | List all portfolios |
| `POST` | `/api/users` | Create new portfolio `{ username, display_name }` |
| `POST` | `/api/session` | Select active portfolio `{ username }` |

### Stock Database

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/stocks/all` | All registered EGX stocks |
| `GET` | `/api/stocks/search?q=` | Search by code or name |
| `POST` | `/api/stocks/add` | Add single stock `{ code, name, sector }` |
| `POST` | `/api/stocks/bulk` | Bulk import `{ stocks: [{code, name, sector}] }` |

---

## 🛠️ Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Backend | Python 3.11 · Flask 3.0 | Lightweight, readable |
| Database | SQLite | Zero setup, per-user file isolation |
| Frontend | Vanilla JS · HTML5 · CSS3 | No framework overhead |
| UI | RTL Arabic · Dark theme | Built for Egyptian users |
| Prices | TradingView · Yahoo · yfinance · Stooq | Redundancy + reliability |

**Dependencies — intentionally minimal:**
```
flask>=3.0.0
requests>=2.31.0
yfinance>=0.2.40
```
---

## 👨‍💻 Author

**Mahamed Emad**  
💬 If you find it useful, give it a ⭐ and share it!

Connect:
- [LinkedIn](https://linkedin.com/in/mahamed-emad)
- [Email](mahamed.emad.barakat@gmail.com)

---
---

## ⚠️ Disclaimer

This tool is for **personal portfolio tracking only**.
It does not provide financial advice or investment recommendations.
All investment decisions are the sole responsibility of the user.

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">

Built with ☕ and too much time watching stock tickers

**[⭐ Star this repo](https://github.com/mahamed-emad/EGX-Portfolio-Tracker)** if it was useful

</div>
