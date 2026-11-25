import re
from decimal import Decimal

# Right-to-left mark: keeps a symbol on the correct side of the number in RTL text.
RLM = "\u200f"

ISO_CODE = re.compile(r"^(?:AED|ARS|AUD|BRL|CAD|CHF|CLP|CNY|COP|CZK|DKK|EGP|EUR|GBP|HKD|HUF|IDR|ILS|INR|ISK|JPY|KES|KRW|KWD|MAD|MXN|MYR|NGN|NOK|NZD|PEN|PHP|PKR|PLN|QAR|RON|SAR|SEK|SGD|THB|TRY|TWD|UAH|USD|VND|ZAR)$")

# code: (symbol, local name, decimals, right_to_left)
CURRENCIES = {
    "USD": ("$", "US dollar", 2, False),
    "EUR": ("€", "euro", 2, False),
    "GBP": ("£", "pound sterling", 2, False),
    "JPY": ("¥", "円", 0, False),
    "ILS": ("₪", "שקל חדש", 2, True),
    "AED": ("د.إ", "درهم إماراتي", 2, True),
    "SAR": ("﷼", "ريال سعودي", 2, True),
    "KWD": ("د.ك", "دينار كويتي", 3, True),
}

CATEGORY_ICONS = {
    "travel": "🧑‍✈️",
    "meals": "🍽️",
    "lodging": "🏨",
    "software": "👩‍💻",
    "hardware": "🖥️",
    "office": "🗂️",
    "other": "🧾",
}


def normalize_code(code):
    code = (code or "USD").strip().upper()
    return code if ISO_CODE.match(code) else "USD"


def format_amount(amount, currency="USD"):
    code = normalize_code(currency)
    symbol, _name, decimals, rtl = CURRENCIES.get(code, (code, code, 2, False))                                                                                                                                                                                    
    value = Decimal(amount).quantize(Decimal(1).scaleb(-decimals))
    text = f"{value:,.{decimals}f}"
    if rtl:
        return f"{RLM}{text} {symbol}{RLM}"
    return f"{symbol}{text}" if len(symbol) == 1 else f"{text} {symbol}"


def currency_name(currency):
    return CURRENCIES.get(normalize_code(currency), (None, currency))[1]


def category_icon(category):
    return CATEGORY_ICONS.get(category, CATEGORY_ICONS["other"])
