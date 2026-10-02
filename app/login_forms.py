"""Value-free classification of editable login controls."""

from app.totp_forms import input_kind


def login_input(element, field: str) -> bool:
    return (
        element.tag_name.lower() == "input"
        and input_kind(element) in (("password",) if field == "password" else ("text", "email", "tel"))
        and element.get_attribute("autocomplete") != "one-time-code"
        and not element.get_attribute("readonly") and not element.get_attribute("disabled")
        and element.is_enabled() and element.is_displayed()
    )


def continuation_control(element) -> bool:
    tag = element.tag_name.lower()
    kind = (element.get_attribute("type") or ("submit" if tag == "button" else "text")).lower()
    return (
        tag in ("button", "input") and kind in ("button", "submit")
        and not element.get_attribute("disabled") and element.is_enabled() and element.is_displayed()
    )
