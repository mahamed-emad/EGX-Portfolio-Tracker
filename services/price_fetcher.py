"""
services/price_fetcher.py
==================================================
  جلب أسعار الأسهم من البورصة المصرية
  بدون أي cache — كل تحديث يجيب السعر من الإنترنت مباشرة
==================================================
الترتيب (الأسرع أولاً):
  1. TradingView Scanner (bulk — كل الأسهم في طلب واحد)
  2. Yahoo Finance Bulk API (لو TradingView فشل)
  3. yfinance library
  4. Stooq (.EG)
  5. Mubasher
  6. EGX Official API
==================================================
"""

import logging
import requests
import re
import csv
import io
from typing import Optional, List

log = logging.getLogger(__name__)

TV_URL = "https://scanner.tradingview.com/global/scan"

# Session موحدة لتسريع الطلبات
_SESSION = requests.Session()
_SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept":       "application/json",
    "Content-Type": "application/json",
    "Origin":       "https://www.tradingview.com",
    "Referer":      "https://www.tradingview.com/",
})


# ══════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════

def _parse_tv_items(stocks_data: list) -> dict:
    """تحويل بيانات TradingView لـ dict {TICKER: {...}}"""
    result = {}
    for item in stocks_data:
        full_ticker = item.get("s", "")
        ticker = (full_ticker.split(":")[-1] if ":" in full_ticker else full_ticker).upper()
        d = item.get("d", [])
        if len(d) < 3:
            continue
        price   = d[2]
        chg_pct = d[3] if len(d) > 3 else None
        chg_abs = d[4] if len(d) > 4 else None
        result[ticker] = {
            "ticker":         ticker,
            "name":           d[0] if d[0] else ticker,
            "description":    d[1] if d[1] else "",
            "price":          round(float(price),   2) if price   is not None else None,
            "change_percent": round(float(chg_pct), 2) if chg_pct is not None else 0.0,
            "change_abs":     round(float(chg_abs), 2) if chg_abs is not None else 0.0,
            "source":         "TradingView",
        }
    return result


# ══════════════════════════════════════════════════════════
# LEVEL 1: TradingView — Targeted (الأسرع لأسهم المحفظة)
# ══════════════════════════════════════════════════════════

def _fetch_tv_targeted(tickers: List[str]) -> dict:
    """جلب أسهم محددة من TradingView في طلب واحد."""
    tv_tickers = [f"EGX:{t}" for t in tickers]
    payload = {
        "symbols": {"tickers": tv_tickers, "query": {"types": []}},
        "columns": ["name", "description", "close", "change", "change_abs", "volume"],
    }
    try:
        r = _SESSION.post(TV_URL, json=payload, timeout=10)
        r.raise_for_status()
        return _parse_tv_items(r.json().get("data", []))
    except Exception as e:
        log.warning(f"[TradingView Targeted] {e}")
        return {}


# ══════════════════════════════════════════════════════════
# LEVEL 2: Yahoo Finance Bulk API
# ══════════════════════════════════════════════════════════

def _fetch_yahoo_bulk(tickers: List[str]) -> dict:
    """جلب مجموعة أسهم دفعة واحدة من Yahoo Finance."""
    yahoo_tickers = [f"{t}.CA" for t in tickers]
    symbols_str = ",".join(yahoo_tickers)
    url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={symbols_str}"
    result = {}
    try:
        r = _SESSION.get(url, timeout=7)
        r.raise_for_status()
        for data in r.json().get("quoteResponse", {}).get("result", []):
            raw_sym = data.get("symbol", "")
            ticker  = raw_sym.split(".")[0].upper()
            price   = data.get("regularMarketPrice")
            chg_pct = data.get("regularMarketChangePercent")
            chg_abs = data.get("regularMarketChange")
            result[ticker] = {
                "ticker":         ticker,
                "name":           data.get("shortName") or ticker,
                "description":    data.get("longName") or "",
                "price":          round(float(price),   2) if price   is not None else None,
                "change_percent": round(float(chg_pct), 2) if chg_pct is not None else 0.0,
                "change_abs":     round(float(chg_abs), 2) if chg_abs is not None else 0.0,
                "source":         "YahooFinance",
            }
    except Exception as e:
        log.warning(f"[Yahoo Bulk] {e}")
    return result


# ══════════════════════════════════════════════════════════
# LEVEL 3-6: Individual Fallbacks (سهم واحد في كل مرة)
# ══════════════════════════════════════════════════════════

def _fetch_yfinance_single(code: str) -> Optional[float]:
    try:
        import yfinance as yf
        stock = yf.Ticker(f"{code}.CA")
        fast  = stock.fast_info
        price = fast.get("last_price") or fast.get("regularMarketPrice")
        if price and float(price) > 0:
            return round(float(price), 2)
        hist = stock.history(period="2d", interval="1d", auto_adjust=True)
        if not hist.empty:
            last = hist["Close"].dropna().iloc[-1]
            if last > 0:
                return round(float(last), 2)
    except ImportError:
        pass
    except Exception as e:
        log.debug(f"[yfinance] {code}: {e}")
    return None


def _fetch_stooq_single(code: str) -> Optional[float]:
    try:
        url = f"https://stooq.com/q/d/l/?s={code}.EG&i=d"
        r   = _SESSION.get(url, timeout=8)
        if r.status_code == 200 and r.text.strip():
            rows = list(csv.DictReader(io.StringIO(r.text)))
            if rows:
                price = float(rows[-1].get("Close", 0))
                if price > 0:
                    return round(price, 2)
    except Exception as e:
        log.debug(f"[Stooq] {code}: {e}")
    return None


def _fetch_mubasher_single(code: str) -> Optional[float]:
    try:
        url = f"https://www.mubasher.info/countries/eg/stocks/{code}/overview"
        r   = _SESSION.get(url, timeout=8)
        if r.status_code == 200:
            for pattern in [r'"currentPrice"[:\s]+([\d.]+)', r'"lastPrice"[:\s]+([\d.]+)']:
                m = re.search(pattern, r.text)
                if m:
                    price = float(m.group(1).replace(",", ""))
                    if price > 0:
                        return price
    except Exception as e:
        log.debug(f"[Mubasher] {code}: {e}")
    return None


def _fetch_egx_single(code: str) -> Optional[float]:
    try:
        r = _SESSION.get(f"https://www.egx.com.eg/api/stocks/{code}", timeout=8)
        if r.status_code == 200:
            data  = r.json()
            price = data.get("lastPrice") or data.get("price")
            if price:
                return float(price)
    except Exception as e:
        log.debug(f"[EGX] {code}: {e}")
    return None


def _deep_fallback_single(code: str) -> Optional[dict]:
    """جرب المصادر الفردية واحدة واحدة وارجع أول سعر تلاقيه."""
    fallbacks = [
        ("yfinance",  _fetch_yfinance_single),
        ("Stooq",     _fetch_stooq_single),
        ("Mubasher",  _fetch_mubasher_single),
        ("EGX",       _fetch_egx_single),
    ]
    for source_name, fn in fallbacks:
        try:
            price = fn(code)
            if price:
                log.info(f"[DeepFallback] ✅ {code} = {price} من {source_name}")
                return {
                    "ticker":         code,
                    "name":           code,
                    "description":    "",
                    "price":          round(float(price), 2),
                    "change_percent": 0.0,
                    "change_abs":     0.0,
                    "source":         source_name,
                }
        except Exception:
            continue
    log.error(f"[DeepFallback] ❌ تعذر جلب {code} من جميع المصادر")
    return None


# ══════════════════════════════════════════════════════════
# MAIN: جلب أسهم المحفظة — بدون cache — كل مرة جديدة
# ══════════════════════════════════════════════════════════

def fetch_portfolio_prices(tickers: List[str]) -> dict:
    """
    جلب أسعار أسهم المحفظة الآن مباشرة — بدون cache.
    الترتيب: TradingView → Yahoo Bulk → Fallbacks فردية
    """
    if not tickers:
        return {}

    tickers = [t.strip().upper() for t in tickers]
    result  = {}

    # ── المستوى 1: TradingView Targeted ───────────────────
    tv_data = _fetch_tv_targeted(tickers)
    for t in tickers:
        if t in tv_data and tv_data[t].get("price") is not None:
            result[t] = tv_data[t]

    missing = [t for t in tickers if t not in result]
    if not missing:
        log.info(f"[PriceFetcher] ✅ جلب {len(result)} سهم من TradingView")
        return result

    # ── المستوى 2: Yahoo Finance Bulk ─────────────────────
    yahoo_data = _fetch_yahoo_bulk(missing)
    for t in list(missing):
        if t in yahoo_data and yahoo_data[t].get("price") is not None:
            result[t] = yahoo_data[t]
            missing.remove(t)

    if not missing:
        log.info(f"[PriceFetcher] ✅ اكتملت الأسهم بعد Yahoo Bulk")
        return result

    # ── المستويات 3-6: Fallbacks فردية ────────────────────
    log.info(f"[PriceFetcher] 🔄 Fallbacks لـ {missing}")
    for t in missing:
        info = _deep_fallback_single(t)
        if info:
            result[t] = info
        else:
            import requests
            from bs4 import BeautifulSoup
            url = f"https://english.mubasher.info/markets/EGX/stocks/{t}/"
            response = requests.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            price = soup.find(
                class_="market-summary__last-price down-icon-only"
            ).get_text()
            result[t] = {"price": price}

    return result


# ══════════════════════════════════════════════════════════
# PUBLIC API — واجهة المشروع
# ══════════════════════════════════════════════════════════

def get_stock_price(ticker: str) -> Optional[float]:
    """سعر سهم واحد — بدون cache."""
    result = fetch_portfolio_prices([ticker])
    return result.get(ticker.upper(), {}).get("price")


def get_stock_price_full(ticker: str) -> dict:
    """سعر + تغيير + مصدر لسهم واحد — بدون cache."""
    result = fetch_portfolio_prices([ticker])
    info   = result.get(ticker.upper())
    if info:
        return {
            "ticker":         ticker.upper(),
            "price":          info.get("price"),
            "change_percent": info.get("change_percent"),
            "change_abs":     info.get("change_abs"),
            "name":           info.get("description") or info.get("name"),
            "source":         info.get("source"),
        }
    return {"ticker": ticker.upper(), "price": None, "change_percent": None,
            "change_abs": None, "name": None, "source": None}


def get_bulk_prices(tickers: list) -> dict:
    """
    أسعار قائمة أسهم — بدون cache — يجيب الأسعار الآن.
    يُعيد {TICKER: price_or_None}
    """
    result = fetch_portfolio_prices(tickers)
    return {t: result.get(t, {}).get("price") for t in [x.upper() for x in tickers]}


def refresh_market_cache() -> int:
    """
    لم يعد هناك cache.
    الدالة دي بتجيب أسعار السوق كلها من TradingView
    وبترجع عدد الأسهم اللي اتجابت.
    """
    from database.db import get_all_stocks
    all_codes = [s["code"] for s in get_all_stocks()]
    if not all_codes:
        return 0
    result = fetch_portfolio_prices(all_codes)
    return len([v for v in result.values() if v.get("price") is not None])
