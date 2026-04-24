"""
Returns tools exposed via the A2A service.

Two Python functions are turned into ADK ``FunctionTool``s so the remote
agent can advertise them in its A2A agent-card:

* ``check_return_eligibility(order_id)``
* ``initiate_return(order_id, reason)``

Return policy mirrors the store-wide FAQ:
    * Order status must be **delivered**.
    * The order must have been placed within the last **30 days**.
    * Orders already marked ``returned`` are never eligible again.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .db import execute_sql, quote_literal

RETURN_WINDOW_DAYS = 30


def _parse_ts(value: str) -> datetime:
    """Parse a Supabase timestamptz string into a tz-aware datetime."""
    # Supabase returns 'YYYY-MM-DDTHH:MM:SS+00:00' or with 'Z'.
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _fetch_order(order_id: int) -> dict[str, Any] | None:
    rows = execute_sql(
        f"""
        SELECT id, customer_id, product_name, quantity, unit_price,
               total_amount, status, order_date
        FROM orders
        WHERE id = {int(order_id)}
        LIMIT 1
        """
    )
    return rows[0] if rows else None


def check_return_eligibility(order_id: int) -> dict[str, Any]:
    """Check whether an order can still be returned.

    Args:
        order_id: Numeric id of the order from the ``orders`` table.

    Returns:
        A dict with ``eligible`` (bool), ``reason`` (str), and ``order``
        (the order row) when found. On eligibility, ``days_remaining``
        indicates how many days of the return window remain.
    """
    try:
        order_id = int(order_id)
    except (TypeError, ValueError):
        return {"eligible": False, "reason": "order_id must be an integer."}

    order = _fetch_order(order_id)
    if order is None:
        return {
            "eligible": False,
            "reason": f"Order #{order_id} was not found.",
        }

    if order["status"] == "returned":
        return {
            "eligible": False,
            "reason": "This order has already been returned.",
            "order": order,
        }
    if order["status"] != "delivered":
        return {
            "eligible": False,
            "reason": (
                f"Only delivered orders are returnable. Current status: "
                f"{order['status']}."
            ),
            "order": order,
        }

    order_date = _parse_ts(order["order_date"])
    age_days = (datetime.now(timezone.utc) - order_date).days
    if age_days > RETURN_WINDOW_DAYS:
        return {
            "eligible": False,
            "reason": (
                f"Return window expired ({age_days} days since order; "
                f"limit is {RETURN_WINDOW_DAYS} days)."
            ),
            "order": order,
        }

    return {
        "eligible": True,
        "reason": "Within return window and delivered.",
        "days_remaining": RETURN_WINDOW_DAYS - age_days,
        "order": order,
    }


def initiate_return(order_id: int, reason: str) -> dict[str, Any]:
    """Initiate a return: create a refund ticket and mark the order returned.

    Args:
        order_id: Numeric id of the order from the ``orders`` table.
        reason: Short free-text reason provided by the customer (stored as
            the ticket description).

    Returns:
        On success: ``{"success": True, "ticket_id": <int>, "order_id": <int>}``
        On failure: ``{"success": False, "reason": <str>}``
    """
    eligibility = check_return_eligibility(order_id)
    if not eligibility.get("eligible"):
        return {
            "success": False,
            "reason": eligibility.get("reason", "Not eligible for return."),
            "order_id": int(order_id) if str(order_id).isdigit() else order_id,
        }

    order = eligibility["order"]
    product = order["product_name"]
    subject = f"Return initiated: {product}"

    sql = f"""
    WITH new_ticket AS (
        INSERT INTO support_tickets
            (customer_id, order_id, subject, description,
             category, priority, status, assigned_agent)
        VALUES (
            {int(order['customer_id'])},
            {int(order_id)},
            {quote_literal(subject)},
            {quote_literal(reason)},
            'refund',
            'medium',
            'open',
            'returns_agent'
        )
        RETURNING id
    ),
    updated_order AS (
        UPDATE orders
           SET status = 'returned'
         WHERE id = {int(order_id)}
        RETURNING id
    )
    SELECT (SELECT id FROM new_ticket) AS ticket_id,
           (SELECT id FROM updated_order) AS order_id;
    """
    rows = execute_sql(sql)
    if not rows or rows[0].get("ticket_id") is None:
        return {
            "success": False,
            "reason": "Database did not return a ticket id after insert.",
        }

    return {
        "success": True,
        "ticket_id": rows[0]["ticket_id"],
        "order_id": rows[0]["order_id"],
        "message": (
            f"Return initiated. Ticket #{rows[0]['ticket_id']} has been "
            "created and the order is now marked 'returned'. A prepaid "
            "shipping label will be emailed within 24 hours."
        ),
    }
