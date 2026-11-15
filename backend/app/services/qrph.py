"""QR Ph (EMV) payment codes with the amount filled in.

A GCash / bank QR code is an EMV "merchant presented" QR: a flat list of
tag-length-value items ending with a CRC. The shop's own code has no amount,
so the payer has to type it. This module takes the text of that code and
rebuilds it for one order: the "point of initiation" becomes dynamic (12), the
amount item (54) is added, and the CRC is recalculated. Scanning the result
in the GCash app then shows the exact amount already filled in.
"""

from decimal import Decimal, InvalidOperation
from importlib.util import find_spec

MAX_PAYLOAD_CHARS = 1000
MAX_AMOUNT = Decimal("9999999.99")


class QrError(ValueError):
    pass


def crc16(text):
    """CRC-16/CCITT-FALSE (polynomial 0x1021, start 0xFFFF), as EMV requires."""
    crc = 0xFFFF
    for byte in text.encode("utf-8"):
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if crc & 0x8000 else (crc << 1)
            crc &= 0xFFFF
    return crc


def parse(payload):
    """Splits the code into [(tag, value), ...]. Raises QrError if it is not a
    well formed EMV QR code with a correct CRC."""
    payload = (payload or "").strip()
    if not payload or len(payload) > MAX_PAYLOAD_CHARS:
        raise QrError("That does not look like a QR Ph code.")

    items, i = [], 0
    while i < len(payload):
        header = payload[i:i + 4]
        if len(header) < 4 or not header.isdigit():
            raise QrError("That does not look like a QR Ph code.")
        tag, length = header[:2], int(header[2:])
        value = payload[i + 4:i + 4 + length]
        if len(value) != length:
            raise QrError("That QR code text is incomplete or damaged.")
        items.append((tag, value))
        i += 4 + length

    if not items or items[0] != ("00", "01"):
        raise QrError("That does not look like a QR Ph code.")
    if items[-1][0] != "63" or len(items[-1][1]) != 4:
        raise QrError("That QR code text has no checksum. Copy the whole text.")
    expected = format(crc16(payload[:-4]), "04X")
    if items[-1][1].upper() != expected:
        raise QrError("That QR code text is damaged (the checksum does not match).")
    return items


def format_amount(amount):
    try:
        value = Decimal(str(amount)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        raise QrError("The amount is not valid.")
    if value <= 0 or value > MAX_AMOUNT:
        raise QrError("The amount is not valid.")
    return f"{value:.2f}"


def with_amount(payload, amount):
    """The same code, but for a fixed amount."""
    items = [(t, v) for t, v in parse(payload) if t != "63"]
    amount_text = format_amount(amount)

    rebuilt, placed = [], False
    for tag, value in items:
        if tag == "01":
            value = "12"
        if tag == "54":
            value, placed = amount_text, True
        elif not placed and tag.isdigit() and int(tag) > 54:
            rebuilt.append(("54", amount_text))
            placed = True
        rebuilt.append((tag, value))
    if not placed:
        rebuilt.append(("54", amount_text))

    body = "".join(f"{tag}{len(value):02d}{value}" for tag, value in rebuilt) + "6304"
    return body + format(crc16(body), "04X")


def image_support():
    """True when the QR picture library (segno) is installed on the server."""
    return find_spec("segno") is not None


def to_svg_data_uri(payload, scale=6):
    # Imported here, not at the top, so a server that does not have segno yet
    # still starts. The payment page then just shows the normal QR.
    try:
        import segno
    except ImportError:
        raise QrError("The QR picture library (segno) is not installed on the server.")
    code = segno.make(payload, error="m")
    return code.svg_data_uri(scale=scale, border=2, dark="#000000", light="#ffffff")
