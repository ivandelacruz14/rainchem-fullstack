import io
from datetime import datetime

import openpyxl
from sqlalchemy import text

from app.extensions import db
from app.models import Order, Product, SalesRecord
from conftest import PASSWORD

URL = "/api/admin/sales-records"
HEADER = ["Order No.", "Order Date", "Paid Date", "Shipped Date", "Delivered Date", "Product", "Variant", "Category",
          "Qty", "Unit Price", "Gross Amount", "Platform Discount", "Seller Discount", "Net Amount", "Shipping Fee",
          "Order Total", "Refund Amount", "Return Qty", "Payment Method", "Sales Channel", "Courier", "Tracking No.",
          "Region", "Province"]


def line(order="1001", product="Demo Oil", qty=2, unit=100, net=180, shipping=0, paid=True, refund=None, return_qty=0, **extra):
    row = {h: None for h in HEADER}
    row.update({"Order No.": order, "Order Date": datetime(2026, 10, 30, 9, 0), "Product": product, "Variant": "A",
                "Category": "Oils", "Qty": qty, "Unit Price": unit, "Gross Amount": unit * qty, "Platform Discount": 0,
                "Seller Discount": unit * qty - net, "Net Amount": net, "Shipping Fee": shipping,
                "Payment Method": "Cash on delivery", "Sales Channel": "Product Page", "Courier": "J&T",
                "Tracking No.": "JT1", "Region": "Metro Manila", "Province": "Manila",
                "Delivered Date": datetime(2026, 11, 1, 9, 0), "Shipped Date": datetime(2026, 10, 31, 9, 0)})
    if paid:
        row["Paid Date"] = datetime(2026, 10, 30, 10, 0)
    if refund is not None:
        row["Refund Amount"] = refund
        row["Return Qty"] = return_qty
    row.update(extra)
    return [row[h] for h in HEADER]


def workbook(rows, sheet="Orders", header=HEADER, summary=None):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = sheet
    ws.append(header)
    for r in rows:
        ws.append(r)
    if summary is not None:
        s = wb.create_sheet("Summary")
        for k, v in summary:
            s.append([k, v])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def send(client, h, data, path="/import/preview", **form):
    fields = {"file": (io.BytesIO(data), "demo.xlsx")}
    fields.update(form)
    return client.post(URL + path, headers=h, data=fields, content_type="multipart/form-data")


def head(make_admin, admin_login):
    make_admin()
    return admin_login("head@example.com")


def test_preview_counts_valid_rows_and_explains_the_rest(client, make_admin, admin_login):
    h = head(make_admin, admin_login)
    rows = [
        line("1001", "Oil A", qty=2, net=180),
        line("1002", "Oil B", qty=0),                                     # bad qty
        line("1003", "Oil C", qty=1, unit=100, net=50, **{"Seller Discount": 0}),   # discounts do not add up
        [None] * len(HEADER),                                            # blank row is ignored
        line("1001", "Oil A", qty=2, net=180),                           # repeated line in the file
    ]
    data = workbook(rows, summary=[("Net sales", 180), ("Gross sales", 200)])
    r = send(client, h, data)
    assert r.status_code == 200
    body = r.get_json()
    assert body["rows"] == 4 and body["valid"] == 1 and body["errorCount"] == 3
    assert [e["row"] for e in body["errors"]] == [3, 4, 6]
    assert "Qty must be at least 1" in body["errors"][0]["message"]
    assert body["totals"]["net"] == 180.0 and body["declared"]["Net sales"] == 180
    assert SalesRecord.query.count() == 0                                       # a preview saves nothing


def test_import_saves_rows_as_imported_and_leaves_orders_and_stock_alone(client, make_user, make_product, make_order, make_admin, admin_login):
    h = head(make_admin, admin_login)
    user = make_user()
    p = make_product("Real Oil", stock=50)
    make_order(user, [(p, 100, 1)], status="delivered", payment_status="paid")
    orders_before, stock_before = Order.query.count(), db.session.get(Product, p.id).stock
    rows = [line("2001", "Oil A", qty=2, net=180, shipping=12),
            line("2001", "Oil B", qty=1, net=90, shipping=12),        # same order: shipping counted once
            line("2002", "Oil C", qty=1, net=40, paid=False, refund=40, return_qty=1)]
    r = send(client, h, workbook(rows), path="/import", confirm="yes")
    assert r.status_code == 201, r.get_json()
    batch = r.get_json()["batch"]
    imported = SalesRecord.query.filter_by(source="import").order_by(SalesRecord.id).all()
    assert len(imported) == 3 and all(s.import_batch == batch and s.order_id is None and s.order_item_id is None for s in imported)
    assert [float(s.shipping_share) for s in imported] == [12.0, 0.0, 0.0]
    assert imported[0].sold_at == datetime(2026, 10, 30, 1, 0)                 # shop time UTC+8 stored as UTC
    assert imported[0].customer_name == "Marketplace buyer" and imported[0].notes.startswith("Imported demo data.")
    assert imported[2].state == "refunded" and imported[2].refund_status == "refunded" and imported[2].return_status == "returned"
    assert float(imported[2].refund_amount) == 40.0 and imported[0].refund_amount is None
    assert imported[0].unit_price == 90 and float(imported[0].subtotal) == 200.0
    assert Order.query.count() == orders_before and db.session.get(Product, p.id).stock == stock_before


def test_importing_the_same_file_twice_adds_nothing(client, make_admin, admin_login):
    h = head(make_admin, admin_login)
    data = workbook([line("3001", "Oil A"), line("3002", "Oil B")])
    assert send(client, h, data, path="/import", confirm="yes").status_code == 201
    again = send(client, h, data, path="/import", confirm="yes")
    assert again.status_code == 400 and "no new rows" in again.get_json()["error"]
    assert SalesRecord.query.filter_by(source="import").count() == 2


def test_the_import_needs_a_confirmation_and_a_real_xlsx(client, make_admin, admin_login):
    h = head(make_admin, admin_login)
    data = workbook([line()])
    assert send(client, h, data, path="/import").status_code == 400                              # no confirm
    assert send(client, h, b"not a spreadsheet", path="/import/preview").status_code == 400
    csv = io.BytesIO(b"a,b\n1,2\n")
    assert client.post(URL + "/import/preview", headers=h, data={"file": (csv, "data.csv")}, content_type="multipart/form-data").status_code == 400
    assert client.post(URL + "/import/preview", headers=h, content_type="multipart/form-data").status_code == 400
    wrong = send(client, h, workbook([line()], header=["Only", "Other"]), path="/import/preview").get_json()
    assert "required columns" in wrong["error"]


def test_imported_rows_show_in_the_list_and_can_be_filtered_and_exported(client, make_admin, admin_login, make_user, make_product, make_order):
    h = head(make_admin, admin_login)
    user = make_user()
    make_order(user, [(make_product("Real"), 100, 1)], status="delivered", payment_status="paid")
    send(client, h, workbook([line("4001", "Imported Oil")]), path="/import", confirm="yes")
    everything = client.get(URL, headers=h).get_json()
    assert everything["total"] == 2
    only = client.get(URL, headers=h, query_string={"source": "import"}).get_json()
    assert only["total"] == 1 and only["records"][0]["source"] == "import" and only["records"][0]["productName"] == "Imported Oil"
    orders = client.get(URL, headers=h, query_string={"source": "order"}).get_json()
    assert orders["total"] == 1 and orders["records"][0]["source"] == "order"
    csv = client.get(URL + "/export.csv", headers=h, query_string={"source": "import"}).data.decode("utf-8")
    assert "Imported Oil" in csv and ",import," in csv
    assert client.get(URL + "/summary", headers=h).get_json()["summary"]["completedRows"] == 2


def test_an_import_can_be_removed_as_one_batch_without_touching_orders(client, make_admin, admin_login, make_user, make_product, make_order):
    h = head(make_admin, admin_login)
    user = make_user()
    make_order(user, [(make_product("Real"), 100, 1)], status="delivered", payment_status="paid")
    batch = send(client, h, workbook([line("5001"), line("5002")]), path="/import", confirm="yes").get_json()["batch"]
    assert client.get(URL + "/imports", headers=h).get_json()["batches"][0]["rows"] == 2
    assert client.delete(f"{URL}/imports/{batch}", headers=h).get_json() == {"removed": 2}
    assert SalesRecord.query.filter_by(source="import").count() == 0
    assert SalesRecord.query.filter(SalesRecord.order_id.isnot(None)).count() == 1
    assert client.delete(f"{URL}/imports/{batch}", headers=h).status_code == 404


def test_only_a_head_admin_imports_or_removes(client, make_admin, admin_login):
    make_admin()
    make_admin("staff@example.com", "Support Staff", ["analytics"])
    staff = admin_login("staff@example.com")
    data = workbook([line()])
    assert send(client, staff, data).status_code == 403
    assert send(client, staff, data, path="/import", confirm="yes").status_code == 403
    assert client.delete(f"{URL}/imports/abc", headers=staff).status_code == 403
    assert client.get(URL + "/imports", headers=staff).status_code == 200                       # viewing is allowed
