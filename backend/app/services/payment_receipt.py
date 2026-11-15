"""The official payment receipt, as a PDF. It is built on the server from the stored order and receipt snapshot,
so nobody can edit it, and it is only issued for an order whose payment is verified as paid."""
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.services.receipt_service import create_receipt_for_order


class NotPaidError(Exception):
    pass


def _money(value):
    return f"PHP {float(value):,.2f}"


def build(order):
    if order.payment_status != "paid":
        raise NotPaidError("An official payment receipt is only issued after the payment is verified as paid")
    receipt = order.receipt or create_receipt_for_order(order)
    styles = getSampleStyleSheet()
    text = lambda s: Paragraph(escape(str(s)), styles["BodyText"])  # noqa: E731

    rows = [["Product", "Qty", "Unit price", "Discount", "Line total"]]
    discount_total = 0.0
    for item in receipt.items_snapshot:
        unit, qty = float(item["unitPrice"]), int(item["quantity"])
        rate = float(item.get("discountRate") or 0)
        list_unit = unit / (1 - rate) if 0 < rate < 1 else unit  # the stored unit price is after the discount
        discount = round((list_unit - unit) * qty, 2)
        discount_total += discount
        rows.append([text(item["name"]), str(qty), _money(unit), _money(discount), _money(unit * qty)])
    table = Table(rows, colWidths=[200, 40, 90, 90, 90], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeeeee")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
    ]))

    address = order.to_dict().get("formatted") or order.address_line1
    story = [
        Paragraph("<b>RAINCHEM INTERNATIONAL, INC. (RAIMOL)</b>", styles["Title"]),
        Paragraph("<b>Official Payment Receipt</b>", styles["Heading2"]),
        Spacer(1, 8),
        text(f"Receipt number: {receipt.receipt_number}"),
        text(f"Order number: {order.order_number}"),
        text(f"Issued: {receipt.issued_at.strftime('%Y-%m-%d %H:%M') if receipt.issued_at else '-'} (UTC)"),
        Spacer(1, 8),
        text(f"Customer: {order.customer_name}"),
        text(f"Phone: {order.customer_phone}"),
        text(f"Email: {order.customer_email}"),
        text(f"Delivery address: {address}"),
        Spacer(1, 12),
        table,
        Spacer(1, 12),
        text(f"Subtotal: {_money(receipt.subtotal)}"),
        text(f"Discount: {_money(discount_total)}"),
        text(f"Shipping fee: {_money(receipt.shipping_fee)}"),
        Paragraph(f"<b>Total paid: {escape(_money(receipt.total))}</b>", styles["BodyText"]),
        Spacer(1, 12),
        text(f"Payment method: {order.payment_method}"),
        text(f"Payment reference: {order.payment_reference or '-'}"),
        text(f"Payment date: {order.paid_at.strftime('%Y-%m-%d %H:%M') if order.paid_at else '-'} (UTC)"),
        text("Payment status: Paid"),
    ]
    buffer = BytesIO()
    SimpleDocTemplate(buffer, pagesize=A4, title=f"Receipt {receipt.receipt_number}",
                      leftMargin=40, rightMargin=40, topMargin=40, bottomMargin=40).build(story)
    return buffer.getvalue(), receipt
