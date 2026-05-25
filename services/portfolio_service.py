"""
services/portfolio_service.py
Per-user portfolio logic. Each PortfolioService instance is scoped to one user.
"""

from database.db import get_user_conn, get_stock_by_code
from services.price_fetcher import fetch_portfolio_prices, get_stock_price
from typing import Optional


class PortfolioError(Exception):
    pass


class PortfolioService:
    """One instance per user — pass username on construction."""

    def __init__(self, username: str):
        self.username = username

    def _conn(self):
        return get_user_conn(self.username)

    # ─── Stock Validation ─────────────────────────────────────────────────────

    def validate_stock_code(self, code: str) -> dict:
        info = get_stock_by_code(code)
        if not info:
            raise PortfolioError(
                f"كود السهم '{code.upper()}' غير موجود في قاعدة بيانات الأسهم المصرية. "
                f"أضفه أولاً من صفحة إدارة الأسهم."
            )
        return info

    # ─── Account ──────────────────────────────────────────────────────────────

    def get_account(self) -> dict:
        conn = self._conn()
        row = conn.execute("SELECT * FROM account WHERE id=1").fetchone()
        conn.close()
        return dict(row) if row else {}

    def deposit(self, amount: float, notes: str = "") -> dict:
        if amount <= 0:
            raise PortfolioError("مبلغ الإيداع يجب أن يكون أكبر من صفر.")
        conn = self._conn()
        try:
            conn.execute("""
                UPDATE account SET
                  total_deposited = total_deposited + ?,
                  cash_balance    = cash_balance    + ?,
                  updated_at      = datetime('now','localtime')
                WHERE id=1
            """, (amount, amount))
            conn.execute(
                "INSERT INTO transactions (type,amount,notes) VALUES ('deposit',?,?)",
                (amount, notes)
            )
            conn.commit()
            return {"success": True, "message": f"تم إيداع {amount:,.2f} جنيه بنجاح."}
        finally:
            conn.close()

    def withdraw(self, amount: float, notes: str = "") -> dict:
        if amount <= 0:
            raise PortfolioError("مبلغ السحب يجب أن يكون أكبر من صفر.")
        account = self.get_account()
        if amount > account["cash_balance"]:
            raise PortfolioError(
                f"رصيد غير كافٍ. السيولة الحالية: {account['cash_balance']:,.2f} جنيه."
            )
        conn = self._conn()
        try:
            conn.execute("""
                UPDATE account SET
                  total_withdrawn = total_withdrawn + ?,
                  cash_balance    = cash_balance    - ?,
                  updated_at      = datetime('now','localtime')
                WHERE id=1
            """, (amount, amount))
            conn.execute(
                "INSERT INTO transactions (type,amount,notes) VALUES ('withdraw',?,?)",
                (amount, notes)
            )
            conn.commit()
            return {"success": True, "message": f"تم سحب {amount:,.2f} جنيه بنجاح."}
        finally:
            conn.close()

    # ─── Trading ──────────────────────────────────────────────────────────────

    def buy(self, code: str, quantity: int, total_amount: float, notes: str = "") -> dict:
        if quantity <= 0:
            raise PortfolioError("عدد الأسهم يجب أن يكون أكبر من صفر.")
        if total_amount <= 0:
            raise PortfolioError("المبلغ المدفوع يجب أن يكون أكبر من صفر.")

        stock = self.validate_stock_code(code)
        code  = stock["code"]

        account = self.get_account()
        if total_amount > account["cash_balance"]:
            raise PortfolioError(
                f"رصيد غير كافٍ. السيولة: {account['cash_balance']:,.2f} جنيه، "
                f"مطلوب: {total_amount:,.2f} جنيه."
            )

        pps  = total_amount / quantity
        conn = self._conn()
        try:
            existing = conn.execute(
                "SELECT * FROM holdings WHERE stock_code=?", (code,)
            ).fetchone()

            if existing:
                new_qty  = existing["quantity"]   + quantity
                new_cost = existing["total_cost"] + total_amount
                new_avg  = new_cost / new_qty
                conn.execute("""
                    UPDATE holdings SET quantity=?, total_cost=?, avg_price=?,
                      updated_at=datetime('now','localtime')
                    WHERE stock_code=?
                """, (new_qty, new_cost, new_avg, code))
            else:
                conn.execute("""
                    INSERT INTO holdings (stock_code,stock_name,quantity,total_cost,avg_price)
                    VALUES (?,?,?,?,?)
                """, (code, stock["name"], quantity, total_amount, pps))

            conn.execute("""
                UPDATE account SET cash_balance=cash_balance-?,
                  updated_at=datetime('now','localtime') WHERE id=1
            """, (total_amount,))
            conn.execute("""
                INSERT INTO transactions
                  (type,stock_code,stock_name,quantity,amount,price_per_share,notes)
                VALUES ('buy',?,?,?,?,?,?)
            """, (code, stock["name"], quantity, total_amount, pps, notes))
            conn.commit()
            return {"success": True,
                    "message": f"تم شراء {quantity} سهم من {stock['name']} بمتوسط {pps:,.2f} ج/سهم."}
        finally:
            conn.close()

    def sell(self, code: str, quantity: int, total_amount: float, notes: str = "") -> dict:
        if quantity <= 0:
            raise PortfolioError("عدد الأسهم يجب أن يكون أكبر من صفر.")
        if total_amount <= 0:
            raise PortfolioError("مبلغ البيع يجب أن يكون أكبر من صفر.")

        stock = self.validate_stock_code(code)
        code  = stock["code"]

        conn = self._conn()
        try:
            holding = conn.execute(
                "SELECT * FROM holdings WHERE stock_code=?", (code,)
            ).fetchone()
            if not holding:
                raise PortfolioError(f"لا توجد أسهم من {stock['name']} في محفظتك.")
            if quantity > holding["quantity"]:
                raise PortfolioError(
                    f"لا يمكن بيع {quantity} سهم. لديك {holding['quantity']} سهم فقط."
                )

            pps          = total_amount / quantity
            cost_of_sold = quantity * holding["avg_price"]
            new_qty      = holding["quantity"]   - quantity
            new_cost     = holding["total_cost"] - cost_of_sold

            if new_qty == 0:
                conn.execute("DELETE FROM holdings WHERE stock_code=?", (code,))
            else:
                conn.execute("""
                    UPDATE holdings SET quantity=?, total_cost=?,
                      updated_at=datetime('now','localtime')
                    WHERE stock_code=?
                """, (new_qty, max(new_cost, 0), code))

            conn.execute("""
                UPDATE account SET cash_balance=cash_balance+?,
                  updated_at=datetime('now','localtime') WHERE id=1
            """, (total_amount,))
            conn.execute("""
                INSERT INTO transactions
                  (type,stock_code,stock_name,quantity,amount,price_per_share,notes)
                VALUES ('sell',?,?,?,?,?,?)
            """, (code, stock["name"], quantity, total_amount, pps, notes))
            conn.commit()

            profit     = total_amount - cost_of_sold
            profit_pct = (profit / cost_of_sold * 100) if cost_of_sold > 0 else 0
            label      = "ربح" if profit >= 0 else "خسارة"
            return {"success": True,
                    "message": f"تم بيع {quantity} سهم من {stock['name']}. "
                               f"{label}: {abs(profit):,.2f} ج ({abs(profit_pct):.2f}%)"}
        finally:
            conn.close()

    # ─── Summary ──────────────────────────────────────────────────────────────

    def get_holdings(self) -> list:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM holdings WHERE quantity>0 ORDER BY stock_code"
        ).fetchall()
        conn.close()

        holdings = [dict(r) for r in rows]
        if not holdings:
            return []

        # جلب أسعار أسهم المحفظة الآن مباشرة — بدون cache
        codes      = [h["stock_code"] for h in holdings]
        price_data = fetch_portfolio_prices(codes)

        result = []
        for h in holdings:
            code  = h["stock_code"].upper()
            info  = price_data.get(code, {})
            price = info.get("price")

            h["current_price"]    = price
            h["change_percent"]   = info.get("change_percent")
            h["change_abs"]       = info.get("change_abs")
            h["price_source"]     = info.get("source")

            if price and h["avg_price"] > 0:
                h["profit_loss_pct"]    = (price - h["avg_price"]) / h["avg_price"] * 100
                h["profit_loss_amount"] = (price - h["avg_price"]) * h["quantity"]
                h["current_value"]      = price * h["quantity"]
            else:
                h["profit_loss_pct"]    = None
                h["profit_loss_amount"] = None
                h["current_value"]      = h["total_cost"]
            result.append(h)
        return result

    def get_portfolio_summary(self) -> dict:
        account  = self.get_account()
        holdings = self.get_holdings()

        stocks_val  = sum(h["current_value"] for h in holdings if h["current_value"] is not None)
        total_val   = account["cash_balance"] + stocks_val
        net_invest  = account["total_deposited"] - account["total_withdrawn"]
        profit_amt  = (total_val - net_invest) if net_invest > 0 else 0
        profit_pct  = (profit_amt / net_invest * 100) if net_invest > 0 else 0

        return {
            "cash_balance":          account["cash_balance"],
            "total_deposited":       account["total_deposited"],
            "total_withdrawn":       account["total_withdrawn"],
            "net_invested":          net_invest,
            "stocks_market_value":   stocks_val,
            "total_portfolio_value": total_val,
            "total_profit_amount":   profit_amt,
            "total_profit_pct":      profit_pct,
            "holdings_count":        len(holdings),
        }

    def get_transactions(self, tx_type: Optional[str] = None, limit: int = 200) -> list:
        conn = self._conn()
        if tx_type in ("buy", "sell", "deposit", "withdraw"):
            rows = conn.execute(
                "SELECT * FROM transactions WHERE type=? ORDER BY created_at DESC LIMIT ?",
                (tx_type, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM transactions ORDER BY created_at DESC LIMIT ?",
                (limit,)
            ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
