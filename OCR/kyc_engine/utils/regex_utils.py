from datetime import datetime


def normalize_date(raw: str) -> str:
    value = raw.strip()
    for date_format in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(value, date_format).strftime("%Y-%m-%d")
        except ValueError:
            continue
    if len(value) == 4 and value.isdigit():
        return f"{value}-01-01"
    return value
