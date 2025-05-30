# app/utils.py

from datetime import datetime

def parse_datetime(date_str: str, fmt="%Y-%m-%d %H:%M:%S") -> datetime:
    return datetime.strptime(date_str, fmt)