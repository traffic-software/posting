"""Bounded, value-free selectors for live browser controls."""

STRUCTURAL_SELECTOR_JS = """
const structuralSelector = (target) => {
    const parts = [];
    let element = target;
    while (element && parts.length < 12) {
        let index = 1;
        for (let sibling = element.previousElementSibling; sibling; sibling = sibling.previousElementSibling) index++;
        const tag = element.localName;
        if (!/^[a-z][a-z0-9-]{0,31}$/.test(tag)) return '';
        parts.unshift(`${tag}:nth-child(${index})`);
        const selector = parts.join(' > ');
        if (selector.length > 300) return '';
        const matches = document.querySelectorAll(selector);
        if (matches.length === 1 && matches[0] === target) return selector;
        element = element.parentElement;
    }
    return '';
};
"""

EDITING_HOST_JS = """
const editingHost = el => !!el && el.isContentEditable &&
    !(el.parentElement && el.parentElement.isContentEditable);
"""
IS_EDITING_HOST = EDITING_HOST_JS + "return editingHost(arguments[0]);"
SAFE_TEXT_TARGET = """
const el = arguments[0];
const privateTarget = '[data-private],[data-sensitive],[autocomplete="current-password"],[autocomplete="new-password"],[autocomplete="one-time-code"],input[type="password"],input[type="file"],input[type="hidden"]';
return !!el && !el.closest(privateTarget) && !el.querySelector(privateTarget);
"""

DISCOVER_PAGE = STRUCTURAL_SELECTOR_JS + EDITING_HOST_JS + """
return Array.from(document.querySelectorAll('input, button, textarea, select, a, [role="button"], [contenteditable]'))
    .filter(element => !element.hasAttribute('contenteditable') || editingHost(element))
    .slice(0, 200).map(element => ({element, selector: structuralSelector(element), editable_host: editingHost(element)}));
"""
