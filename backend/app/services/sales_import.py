"""Imports sales from a marketplace Excel export (.xlsx), for demo or history.

Imported rows are stored with source="import". They are not orders, so they never change orders, payments, or
stock. Each import has a batch id, so the whole batch can be removed later. Money is read exactly (Decimal)."""
import io
import uuid
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

import openpyxl
from sqlalchemy import func

from app.extensions import db
from app.models import SalesRecord
from app.services import audit
from app.services import sales_analytics as dates

MAX_BYTES = 5 * 1024 * 1024
MAX_ROWS = 5000
CENT = Decimal("0.01")
REQUIRED = ["Order No.", "Order Date", "Product", "Qty", "Unit Price", "Net Amount"]
CUSTOMER = "Marketplace buyer"


class ImportFileError(Exception):
    pass


def _cell(row, idx, name):
    i = idx.get(name)
    return None if i is None or i >= len(row) else row[i]


def _money(value, field, allow_blank=False):
    if value is None or (isinstance(value, str) and not value.strip()):
        if allow_blank:
            return Decimal("0.00")
        raise ValueError(f"{field} is missing")
    try:
        number = Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)
    except Exception:
        raise ValueError(f"{field} must be a number")
    if number < 0:
        raise ValueError(f"{field} cannot be negative")
    return number


def _order_no(value):
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return "" if value is None else str(value).strip()[:40]


def read_file(data):
    """Returns (sheet name, column index, [(excel row number, row)], declared summary figures)."""
    if not data:
        raise ImportFileError("The file is empty.")
    if len(data) > MAX_BYTES:
        raise ImportFileError("The file is larger than 5 MB.")
    try:
        wb = openpyxl.load_workbook(io.BytesIO(data), data_only=True, read_only=True)
    except Exception:
        raise ImportFileError("The file could not be read. Save it as an .xlsx file and try again.")
    declared = {}
    for ws in wb.worksheets:
        if ws.title.lower() == "summary":
            for row in ws.iter_rows(values_only=True):
                if row and row[0] in ("Net sales", "Gross sales", "Order lines") and isinstance(row[1], (int, float)):
                    declared[row[0]] = row[1]
    for ws in wb.worksheets:
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            continue
        header = [str(h).strip() if h is not None else "" for h in rows[0]]
        if all(name in header for name in REQUIRED):
            idx = {name: header.index(name) for name in header if name}
            body = []
            for number, row in enumerate(rows[1:], start=2):
                if any(v is not None and str(v).strip() for v in row):
                    body.append((number, row))
            if len(body) > MAX_ROWS:
                raise ImportFileError(f"The sheet has more than {MAX_ROWS} rows.")
            return ws.title, idx, body, declared
    raise ImportFileError("No sheet has the required columns: " + ", ".join(REQUIRED))


def _parse_line(row, idx):
    order_no = _order_no(_cell(row, idx, "Order No."))
    if not order_no:
        raise ValueError("Order No. is missing")
    sold = _cell(row, idx, "Order Date")
    if not isinstance(sold, datetime):
        raise ValueError("Order Date must be a date and time")
    product = str(_cell(row, idx, "Product") or "").strip()[:200]
    if not product:
        raise ValueError("Product is missing")
    try:
        qty = int(_cell(row, idx, "Qty"))
    except (TypeError, ValueError):
        raise ValueError("Qty must be a whole number")
    if qty <= 0:
        raise ValueError("Qty must be at least 1")
    unit = _money(_cell(row, idx, "Unit Price"), "Unit Price")
    net = _money(_cell(row, idx, "Net Amount"), "Net Amount")
    gross_raw = _cell(row, idx, "Gross Amount")
    gross = _money(gross_raw, "Gross Amount") if gross_raw is not None else (unit * qty).quantize(CENT)
    platform = _money(_cell(row, idx, "Platform Discount"), "Platform Discount", allow_blank=True)
    seller = _money(_cell(row, idx, "Seller Discount"), "Seller Discount", allow_blank=True)
    if gross - platform - seller != net:
        raise ValueError("Gross Amount minus the discounts does not equal Net Amount")
    refund = _money(_cell(row, idx, "Refund Amount"), "Refund Amount", allow_blank=True)
    try:
        return_qty = int(_cell(row, idx, "Return Qty") or 0)
    except (TypeError, ValueError):
        raise ValueError("Return Qty must be a whole number")
    delivered = _cell(row, idx, "Delivered Date")
    shipped = _cell(row, idx, "Shipped Date")
    paid = _cell(row, idx, "Paid Date")
    if refund > 0 or return_qty > 0:
        state = "refunded" if refund > 0 else "returned"
    else:
        state = "completed" if paid else "pending"
    text = lambda name: str(_cell(row, idx, name) or "").strip()
    return {
        "orderNumber": order_no, "soldAt": sold, "product": product, "variant": text("Variant")[:80],
        "category": text("Category")[:80] or None, "qty": qty, "unit": unit, "gross": gross,
        "discount": platform + seller, "net": net,
        "shipping": _money(_cell(row, idx, "Shipping Fee"), "Shipping Fee", allow_blank=True),
        "refund": refund, "returnQty": return_qty, "state": state,
        "paid": paid is not None, "delivered": isinstance(delivered, datetime),
        "shipped": isinstance(shipped, datetime) or isinstance(delivered, datetime),
        "method": text("Payment Method") or "Unknown",
        "notes": (f"Imported demo data. Channel: {text('Sales Channel') or '-'}. Courier: {text('Courier') or '-'}. "
                  f"Tracking: {text('Tracking No.') or '-'}. Region: {text('Region') or '-'}, {text('Province') or '-'}.")[:500],
    }


def _parse_all(body, idx):
    lines, errors, seen = [], [], set()
    for number, row in body:
        try:
            line = _parse_line(row, idx)
        except ValueError as error:
            errors.append({"row": number, "message": str(error)})
            continue
        key = (line["orderNumber"], line["product"], line["variant"])
        if key in seen:
            errors.append({"row": number, "message": "Repeated line: same order, product and variant already appear above"})
            continue
        seen.add(key)
        lines.append(line)
    return lines, errors


def _existing_keys(order_numbers):
    keys, numbers = set(), list(set(order_numbers))
    for i in range(0, len(numbers), 500):
        found = SalesRecord.query.filter(SalesRecord.source == "import", SalesRecord.order_number.in_(numbers[i:i + 500])).all()
        keys.update((r.order_number, r.product_name, r.variant or "") for r in found)
    return keys


def _totals(lines):
    units = sum(l["qty"] for l in lines)
    return {
        "lines": len(lines), "orders": len({l["orderNumber"] for l in lines}), "units": units,
        "gross": float(sum((l["gross"] for l in lines), Decimal(0))),
        "discounts": float(sum((l["discount"] for l in lines), Decimal(0))),
        "net": float(sum((l["net"] for l in lines), Decimal(0))),
        "refunds": float(sum((l["refund"] for l in lines), Decimal(0))),
    }


def analyse(data):
    """Checks the file without saving anything. Returns (summary, lines ready to import)."""
    sheet, idx, body, declared = read_file(data)
    lines, errors = _parse_all(body, idx)
    existing = _existing_keys(l["orderNumber"] for l in lines)
    fresh = [l for l in lines if (l["orderNumber"], l["product"], l["variant"]) not in existing]
    summary = {
        "sheet": sheet, "rows": len(body), "valid": len(fresh), "alreadyImported": len(lines) - len(fresh),
        "errorCount": len(errors), "errors": errors[:50], "totals": _totals(fresh),
        "declared": {k: float(v) for k, v in declared.items()},
    }
    return summary, fresh


def commit(data, admin, filename):
    summary, fresh = analyse(data)
    if not fresh:
        raise ImportFileError("There are no new rows to import. Every valid row is already in the sales records.")
    batch = uuid.uuid4().hex[:12]
    shipped_orders = set()
    for line in fresh:
        # A marketplace order can have several lines, and its shipping fee is repeated on them. Count it once.
        shipping = line["shipping"] if line["orderNumber"] not in shipped_orders else Decimal("0.00")
        shipped_orders.add(line["orderNumber"])
        qty = line["qty"]
        if line["state"] in ("refunded", "returned"):
            payment_status = "refunded" if line["refund"] > 0 else "paid"
        else:
            payment_status = "paid" if line["paid"] else "unpaid"
        fulfillment = "Delivered" if line["delivered"] else ("Shipped" if line["shipped"] else "Preparing")
        db.session.add(SalesRecord(
            source="import", import_batch=batch, order_id=None, order_item_id=None,
            order_number=line["orderNumber"], transaction_ref=line["orderNumber"],
            sold_at=line["soldAt"] - dates.utc_offset(),
            customer_id=None, customer_name=CUSTOMER,
            product_id=None, product_name=line["product"], variant=line["variant"] or None, sku=None,
            category=line["category"], quantity=qty,
            list_unit_price=line["unit"], unit_price=(line["net"] / qty).quantize(CENT, rounding=ROUND_HALF_UP),
            subtotal=line["gross"], discount_amount=line["discount"], line_total=line["net"],
            shipping_share=shipping, tax_amount=Decimal("0.00"), order_total=line["net"] + shipping,
            payment_method=line["method"], payment_status=payment_status,
            order_status="delivered" if line["delivered"] else "processing",
            fulfillment_status=fulfillment,
            refund_status="refunded" if line["refund"] > 0 else "none",
            return_status="returned" if line["returnQty"] > 0 else "none",
            state=line["state"], notes=line["notes"],
            refund_amount=line["refund"] if line["refund"] > 0 else None,
        ))
    audit.record("sales_import", "sales_records", batch, None,
                 {"file": (filename or "")[:120], "rows": len(fresh), "orders": summary["totals"]["orders"],
                  "errors": summary["errorCount"], "alreadyImported": summary["alreadyImported"]}, None, admin)
    db.session.commit()
    return batch, summary


def list_batches():
    rows = (
        db.session.query(SalesRecord.import_batch, func.count(SalesRecord.id), func.sum(SalesRecord.line_total),
                         func.min(SalesRecord.created_at), func.count(func.distinct(SalesRecord.order_number)))
        .filter(SalesRecord.source == "import")
        .group_by(SalesRecord.import_batch)
        .order_by(func.min(SalesRecord.created_at).desc())
        .all()
    )
    return [{"batch": b, "rows": int(n), "orders": int(o), "net": float(total or 0),
             "createdAt": created.isoformat() if created else None} for b, n, total, created, o in rows]


def delete_batch(batch, admin):
    removed = SalesRecord.query.filter_by(source="import", import_batch=batch).delete(synchronize_session=False)
    if removed:
        audit.record("sales_import_removed", "sales_records", batch, {"rows": removed}, None, None, admin)
    db.session.commit()
    return removed
