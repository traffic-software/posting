"""Narrow OTP control validation and value-free DOM discovery."""

import re


def structural_selector(value) -> bool:
    return isinstance(value, str) and len(value) <= 300 and re.fullmatch(
        r"\*:nth-child\([1-9][0-9]{0,5}\)(?: > \*:nth-child\([1-9][0-9]{0,5}\)){0,11}", value,
    ) is not None


DISCOVER_CONTROLS = """
const structuralSelector = (element) => {
    const parts = [];
    while (element && parts.length < 12) {
        let index = 1;
        for (let sibling = element.previousElementSibling; sibling; sibling = sibling.previousElementSibling) index++;
        parts.unshift(`*:nth-child(${index})`);
        element = element.parentElement;
    }
    return element ? '' : parts.join(' > ');
};
return Array.from(document.querySelectorAll('input, button')).slice(0, 200).map(element => ({
    element, selector: structuralSelector(element), form: Array.from(document.forms).indexOf(element.form)
}));
"""


SUBMISSION_FORM = """
return {
    sameForm: arguments[0].form !== null && arguments[0].form === arguments[1].form,
    action: arguments[1].getAttribute('formaction') ? arguments[1].formAction
        : (arguments[0].form && arguments[0].form.action)
};
"""


def input_kind(element) -> str:
    return (element.get_attribute("type") or "text").lower()


def editable_input(element) -> bool:
    return (
        element.tag_name.lower() == "input" and input_kind(element) in ("text", "tel", "number")
        and not element.get_attribute("readonly") and not element.get_attribute("disabled")
        and element.is_enabled() and element.is_displayed()
    )


def numeric_input(element) -> bool:
    return input_kind(element) in ("tel", "number") or element.get_attribute("inputmode") == "numeric"


def single_input(element) -> bool:
    if not editable_input(element):
        return False
    maxlength = element.get_attribute("maxlength")
    if element.get_attribute("autocomplete") == "one-time-code":
        return maxlength in (None, "", "6")
    pattern = element.get_attribute("pattern")
    return maxlength == "6" and (
        numeric_input(element) or pattern in (r"\d{6}", "[0-9]{6}", r"^\d{6}$", "^[0-9]{6}$")
    )


def split_input(element) -> bool:
    return editable_input(element) and element.get_attribute("maxlength") == "1" and (
        numeric_input(element) or element.get_attribute("autocomplete") == "one-time-code"
    )


def validate_inputs(elements) -> None:
    if len(elements) == 1 and single_input(elements[0]):
        return
    if len(elements) == 6 and all(split_input(element) for element in elements):
        return
    raise ValueError("Authenticator inputs are not authorized")


def submit_control(element) -> bool:
    return (
        element.tag_name.lower() in ("button", "input")
        and (element.get_attribute("type") or "submit").lower() == "submit"
        and element.is_enabled() and element.is_displayed()
    )
