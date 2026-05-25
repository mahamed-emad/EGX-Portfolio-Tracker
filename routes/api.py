"""
routes/api.py
All API endpoints — user-scoped + shared stock management
"""

from flask import Blueprint, jsonify, request, session
from services.portfolio_service import PortfolioService, PortfolioError
from services.price_fetcher import get_stock_price, get_stock_price_full, fetch_portfolio_prices
from database.db import (
    search_stocks, add_stock_to_shared, bulk_add_stocks,
    get_all_stocks, list_users, add_user, user_exists
)

api = Blueprint("api", __name__, url_prefix="/api")


# ─── Helpers ──────────────────────────────────────────────────────────────────

def ok(data=None, message=""):
    return jsonify({"ok": True,  "data": data, "message": message})

def err(msg, code=400):
    return jsonify({"ok": False, "error": msg}), code

def get_service() -> PortfolioService:
    username = session.get("username")
    if not username:
        raise PermissionError("لم يتم اختيار محفظة.")
    return PortfolioService(username)


# ═══ USER / SESSION ═══════════════════════════════════════════════════════════

@api.route("/users", methods=["GET"])
def get_users():
    return ok(list_users())

@api.route("/users", methods=["POST"])
def create_user():
    body = request.get_json() or {}
    name = body.get("display_name", "").strip()
    user = body.get("username", "").strip()
    if not name or not user:
        return err("اسم المستخدم والاسم المعروض مطلوبان.")
    try:
        result = add_user(user, name)
        session["username"] = result["username"]
        return ok(result, f"تم إنشاء محفظة {name} بنجاح")
    except ValueError as e:
        return err(str(e))

@api.route("/session", methods=["POST"])
def set_session():
    body = request.get_json() or {}
    username = body.get("username", "").strip()
    if not username or not user_exists(username):
        return err("المستخدم غير موجود.")
    session["username"] = username
    return ok({"username": username}, "تم تحديد المحفظة.")

@api.route("/session", methods=["GET"])
def get_session():
    return ok({"username": session.get("username")})

@api.route("/session", methods=["DELETE"])
def clear_session():
    session.pop("username", None)
    return ok(message="تم تسجيل الخروج.")


# ═══ PORTFOLIO ════════════════════════════════════════════════════════════════

@api.route("/summary")
def summary():
    try:
        return ok(get_service().get_portfolio_summary())
    except PermissionError as e:
        return err(str(e), 401)
    except Exception as e:
        return err(str(e), 500)

@api.route("/holdings")
def holdings():
    try:
        return ok(get_service().get_holdings())
    except PermissionError as e:
        return err(str(e), 401)
    except Exception as e:
        return err(str(e), 500)

@api.route("/holdings/prices", methods=["POST"])
def holdings_prices():
    """
    جلب أسعار أسهم محددة مباشرة من TradingView.
    Body: {"tickers": ["COMI", "ACTF", "VLMRA"]}
    يُستخدم لتحديث الأسعار فور دخول المحفظة.
    """
    try:
        from services.price_fetcher import get_bulk_prices
        b       = request.get_json() or {}
        tickers = b.get("tickers", [])
        if not tickers:
            return ok({})
        prices = get_bulk_prices(tickers)
        return ok(prices)
    except Exception as e:
        return err(str(e), 500)

@api.route("/transactions")
def transactions():
    try:
        tx_type = request.args.get("type")
        limit   = int(request.args.get("limit", 200))
        return ok(get_service().get_transactions(tx_type, limit))
    except PermissionError as e:
        return err(str(e), 401)
    except Exception as e:
        return err(str(e), 500)


# ═══ OPERATIONS ═══════════════════════════════════════════════════════════════

@api.route("/deposit", methods=["POST"])
def deposit():
    try:
        b = request.get_json() or {}
        r = get_service().deposit(float(b.get("amount", 0)), b.get("notes", ""))
        return ok(message=r["message"])
    except (PortfolioError, ValueError) as e:
        return err(str(e))
    except PermissionError as e:
        return err(str(e), 401)

@api.route("/withdraw", methods=["POST"])
def withdraw():
    try:
        b = request.get_json() or {}
        r = get_service().withdraw(float(b.get("amount", 0)), b.get("notes", ""))
        return ok(message=r["message"])
    except (PortfolioError, ValueError) as e:
        return err(str(e))
    except PermissionError as e:
        return err(str(e), 401)

@api.route("/buy", methods=["POST"])
def buy():
    try:
        b = request.get_json() or {}
        r = get_service().buy(
            b.get("code", ""), int(b.get("quantity", 0)),
            float(b.get("amount", 0)), b.get("notes", "")
        )
        return ok(message=r["message"])
    except (PortfolioError, ValueError) as e:
        return err(str(e))
    except PermissionError as e:
        return err(str(e), 401)

@api.route("/sell", methods=["POST"])
def sell():
    try:
        b = request.get_json() or {}
        r = get_service().sell(
            b.get("code", ""), int(b.get("quantity", 0)),
            float(b.get("amount", 0)), b.get("notes", "")
        )
        return ok(message=r["message"])
    except (PortfolioError, ValueError) as e:
        return err(str(e))
    except PermissionError as e:
        return err(str(e), 401)


# ═══ SHARED STOCKS ════════════════════════════════════════════════════════════

@api.route("/stocks/search")
def stocks_search():
    q = request.args.get("q", "").strip()
    return ok(search_stocks(q) if q else [])

@api.route("/stocks/all")
def stocks_all():
    return ok(get_all_stocks())

@api.route("/stocks/add", methods=["POST"])
def stocks_add():
    b = request.get_json() or {}
    code = b.get("code", "").strip()
    name = b.get("name", "").strip()
    if not code or not name:
        return err("الكود والاسم مطلوبان.")
    result = add_stock_to_shared(code, name, b.get("sector", "أخرى"))
    return ok(message=result["message"])

@api.route("/stocks/bulk", methods=["POST"])
def stocks_bulk():
    """Bulk add stocks: [{code, name, sector}, ...]"""
    b = request.get_json() or {}
    stocks = b.get("stocks", [])
    if not stocks or not isinstance(stocks, list):
        return err("أرسل قائمة أسهم في حقل 'stocks'.")
    result = bulk_add_stocks(stocks)
    return ok(message=result["message"])

@api.route("/price/<code>")
def price(code):
    """جلب السعر الحالي + بيانات التغيير لسهم معين."""
    info = get_stock_price_full(code.upper())
    return ok(info)

@api.route("/market/refresh", methods=["POST"])
def market_refresh():
    """
    جلب أسعار أسهم المحفظة الآن من الإنترنت مباشرة — بدون cache.
    يُعيد ملخص المحفظة المحدث بعد جلب الأسعار.
    """
    try:
        svc = get_service()
        # جلب الأسهم الموجودة في المحفظة
        holdings = svc.get_holdings()   # هنا بيجيب الأسعار تلقائياً
        summary  = svc.get_portfolio_summary()
        count    = len([h for h in holdings if h.get("current_price") is not None])
        return ok({
            "summary":        summary,
            "prices_fetched": count,
            "total_holdings": len(holdings),
        }, f"تم تحديث أسعار {count} سهم من {len(holdings)} في المحفظة")
    except PermissionError as e:
        return err(str(e), 401)
    except Exception as e:
        return err(str(e), 500)
