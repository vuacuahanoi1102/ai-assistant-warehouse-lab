from sqlmodel import Session, select
from models import Sample
from sqlalchemy.orm import selectinload
import re

def extract_code_and_lot(question: str) -> tuple[str | None, str | None]:
    code = None
    lot = None

    # 1) Explicit 'code' keyword
    m = re.search(r"\bcode[:\s]*([A-Za-z0-9\-]+)\b", question, re.IGNORECASE)
    if m:
        code = m.group(1)

    # 2) Explicit 'lot' keyword
    m2 = re.search(r"\blot[:\s]*([A-Za-z0-9\-]+)\b", question, re.IGNORECASE)
    if m2:
        lot = m2.group(1)

    # Fallbacks if either missing
    tokens = re.findall(r"\b[A-Za-z0-9\-]+\b", question)
    if not code and tokens:
        code = tokens[0]
    if not lot and tokens:
        # find first token that is all-digit or contains digits
        for tok in tokens[1:]:
            if re.search(r"\d", tok):
                lot = tok
                break

    return code, lot

