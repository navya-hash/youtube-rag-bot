
import re


# Common PII patterns.
EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)

# Matches 10-digit phone numbers, optionally with separators
# or an international country-code prefix.
PHONE_PATTERN = re.compile(
    r"(?<!\w)(?:\+\d{1,3}[\s.-]?)?"
    r"(?:\d[\s.-]?){10}(?!\w)"
)

# Common API keys and access tokens.
SECRET_PATTERNS = [
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bgsk_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bAKIA[A-Z0-9]{16}\b"),
    re.compile(
        r"\bBearer\s+[A-Za-z0-9._~+/=-]{20,}",
        re.IGNORECASE,
    ),
]


def mask_sensitive_information(text: str) -> str:
    """
    Detect and mask common PII and secrets in generated text.
    """

    if not isinstance(text, str):
        raise TypeError("Output must be a string.")

    if not text:
        return text

    # Mask secrets first.
    for pattern in SECRET_PATTERNS:
        text = pattern.sub("[SECRET_REDACTED]", text)

    # Mask email addresses.
    text = EMAIL_PATTERN.sub("[EMAIL_REDACTED]", text)

    # Mask phone numbers.
    text = PHONE_PATTERN.sub("[PHONE_REDACTED]", text)

    return text
