# from app.services.guardrails.pii_masking import (
#     mask_sensitive_information,
# )


# def test_email_masking():
#     result = mask_sensitive_information(
#         "Contact me at user@gmail.com"
#     )
#     assert "[EMAIL_REDACTED]" in result


# def test_phone_masking():
#     result = mask_sensitive_information(
#         "Call me at 9876543210"
#     )
#     assert "[PHONE_REDACTED]" in result


# def test_api_key_masking():
#     result = mask_sensitive_information(
#         "API key: sk-" + "a" * 30
#     )
#     assert "[SECRET_REDACTED]" in result


# def test_normal_text_unchanged():
#     text = "Machine learning uses data to learn patterns."
#     assert mask_sensitive_information(text) == text


