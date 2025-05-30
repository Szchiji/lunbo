from datetime import datetime

def parse_datetime(text: str):
    try:
        return datetime.strptime(text.strip(), "%Y-%m-%d %H:%M")
    except ValueError:
        return None