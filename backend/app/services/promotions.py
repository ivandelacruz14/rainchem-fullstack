from datetime import datetime, timedelta

from app.models import ProductSale
from app.services.sales_analytics import local_today, utc_offset


class SaleError(ValueError):
    pass


MAX_PERCENT = 90
MAX_LABEL = 60
MAX_DAYS = 366


def local_midnight_utc(day):
    """Start of a shop-local day, as the UTC time stored in the database."""
    return datetime.combine(day, datetime.min.time()) - utc_offset()


def window_for(start_day, end_day):
    """A sale runs from the start of its first day to the end of its last day (shop time)."""
    return local_midnight_utc(start_day), local_midnight_utc(end_day + timedelta(days=1))


def local_days(sale):
    """The first and last shop-local day of a sale, for showing in the admin form."""
    start = (sale.starts_at + utc_offset()).date()
    end = (sale.ends_at + utc_offset() - timedelta(seconds=1)).date()
    return start, end


def active_sales(product_ids=None, now=None):
    """{product_id: sale} for sales running right now."""
    now = now or datetime.utcnow()
    query = ProductSale.query.filter(
        ProductSale.is_active.is_(True), ProductSale.starts_at <= now, ProductSale.ends_at > now,
    )
    if product_ids is not None:
        query = query.filter(ProductSale.product_id.in_(list(product_ids) or [-1]))
    # If two ever overlap, the bigger discount wins for the customer.
    result = {}
    for sale in query.order_by(ProductSale.discount_percent).all():
        result[sale.product_id] = sale
    return result


def read_percent(value):
    try:
        percent = int(value)
    except (TypeError, ValueError):
        raise SaleError("Enter a whole number for the discount, from 1 to 90")
    if str(value).strip() != str(percent) and not isinstance(value, int):
        raise SaleError("Enter a whole number for the discount, from 1 to 90")
    if percent < 1 or percent > MAX_PERCENT:
        raise SaleError(f"The discount must be between 1% and {MAX_PERCENT}%")
    return percent


def read_label(value):
    label = str(value or "").strip()
    if len(label) > MAX_LABEL:
        raise SaleError(f"The label can be at most {MAX_LABEL} characters")
    return label or None


def read_window(start_raw, end_raw, now=None):
    from datetime import date
    try:
        start_day, end_day = date.fromisoformat(str(start_raw)), date.fromisoformat(str(end_raw))
    except ValueError:
        raise SaleError("Choose a start date and an end date")
    if end_day < start_day:
        raise SaleError("The end date cannot be before the start date")
    if start_day < local_today():
        raise SaleError("The start date cannot be in the past")
    if (end_day - start_day).days + 1 > MAX_DAYS:
        raise SaleError(f"A sale can run for at most {MAX_DAYS} days")
    return window_for(start_day, end_day)


def overlapping(product_id, starts_at, ends_at, ignore_id=None, now=None):
    now = now or datetime.utcnow()
    query = ProductSale.query.filter(
        ProductSale.product_id == product_id, ProductSale.is_active.is_(True),
        ProductSale.ends_at > now, ProductSale.starts_at < ends_at, ProductSale.ends_at > starts_at,
    )
    if ignore_id:
        query = query.filter(ProductSale.id != ignore_id)
    return query.first()
