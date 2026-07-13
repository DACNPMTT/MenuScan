from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

PriceResult = tuple[str, str | None]

# Amount fragment shared by every price pattern. Two alternatives, longest first
# so grouped-thousands wins over the plain-decimal reading:
#   1) grouped thousands: 1-3 leading digits then one or more ".ddd"/",ddd"
#      groups -> "45.000", "1.250.000", "2,500,000"
#   2) plain number, optional single decimal group -> "12.50", "45000", "20"
_AMOUNT = r"\d{1,3}(?:[.,]\d{3})+|\d+(?:[.,]\d+)?"

_CURRENCY_SUFFIX_RE = re.compile(
    rf"^(?P<amount>{_AMOUNT})\s*(?P<currency>USD|EUR|VND)$",
    re.IGNORECASE,
)
_DONG_SUFFIX_RE = re.compile(rf"^(?P<amount>{_AMOUNT})\s*(?:d|đ)$", re.IGNORECASE)
_K_SUFFIX_RE = re.compile(rf"^(?P<amount>{_AMOUNT})\s*k$", re.IGNORECASE)
_DOLLAR_PREFIX_RE = re.compile(rf"^\$\s*(?P<amount>{_AMOUNT})$")
_BARE_INT_RE = re.compile(r"^\d{4,}$")

_PRICE_AT_END_RE = re.compile(
    r"(?P<price>"
    rf"\$\s*(?:{_AMOUNT})"
    r"|"
    rf"(?:{_AMOUNT})\s*(?:USD|EUR|VND|d|đ|k)"
    r"|"
    r"\d{4,}"
    r")\s*$",
    re.IGNORECASE,
)


def parse_price(text: str) -> PriceResult | None:
    """Parse a confident standalone price token.

    The parser intentionally accepts only complete price strings. Use
    ``find_price_at_end`` when extracting a trailing price from a menu line.
    """

    token = _clean_price_token(text)
    if not token:
        return None

    if match := _DOLLAR_PREFIX_RE.fullmatch(token):
        return _format_decimal_amount(match.group("amount"), "USD")

    if match := _DONG_SUFFIX_RE.fullmatch(token):
        return _format_thousands_amount(match.group("amount"), "VND")

    if match := _K_SUFFIX_RE.fullmatch(token):
        amount = _parse_decimal(match.group("amount").replace(",", "."))
        if amount is None:
            return None
        return (_format_money(amount * Decimal("1000")), "VND")

    if match := _CURRENCY_SUFFIX_RE.fullmatch(token):
        currency = match.group("currency").upper()
        amount_text = match.group("amount")
        if currency == "VND":
            return _format_thousands_amount(amount_text, "VND")
        return _format_decimal_amount(amount_text, currency)

    if _BARE_INT_RE.fullmatch(token):
        return (_format_money(Decimal(token)), None)

    return None


def find_price_at_end(text: str) -> tuple[str, int, int] | None:
    """Return the trailing price token and its span when it parses cleanly."""

    match = _PRICE_AT_END_RE.search(text.strip())
    if not match:
        return None
    price_text = match.group("price").strip()
    if parse_price(price_text) is None:
        return None
    return price_text, match.start("price"), match.end("price")


def _clean_price_token(text: str) -> str:
    return text.strip().strip(":;,. ")


def _format_thousands_amount(amount_text: str, currency: str) -> PriceResult | None:
    if re.search(r"[.,]", amount_text):
        parts = re.split(r"[.,]", amount_text)
        # Grouped thousands only: 1-3 leading digits, then every following group
        # exactly 3 digits ("45.000", "1.250.000"). Anything else (a genuine
        # decimal such as "45.50") is not a confident VND amount -> reject.
        if not (1 <= len(parts[0]) <= 3) or not all(len(p) == 3 for p in parts[1:]):
            return None
        normalized = "".join(parts)
    else:
        normalized = amount_text
    return (_format_money(Decimal(normalized)), currency)


def _format_decimal_amount(amount_text: str, currency: str) -> PriceResult | None:
    amount = _parse_decimal(amount_text.replace(",", "."))
    if amount is None:
        return None
    return (_format_money(amount), currency)


def _parse_decimal(value: str) -> Decimal | None:
    try:
        return Decimal(value)
    except InvalidOperation:
        return None


def _format_money(amount: Decimal) -> str:
    return f"{amount.quantize(Decimal('0.01'))}"
