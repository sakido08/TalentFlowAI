"""Conservative cleanup that keeps dates, names, and contact details intact."""

import re
import unicodedata


def preprocess_text(text: str) -> str:
    # Keep punctuation because it carries meaning in emails, dates, and technology names.
    text = unicodedata.normalize("NFC", text)
    text = text.replace("\u00a0", " ").replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[\u200b\ufeff\u2060\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    text = re.sub(r"[\t ]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
