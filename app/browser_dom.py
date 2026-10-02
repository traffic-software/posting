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

DISCOVER_PAGE = STRUCTURAL_SELECTOR_JS + """
return Array.from(document.querySelectorAll('input, button, textarea, select, a, [role="button"]'))
    .slice(0, 200).map(element => ({element, selector: structuralSelector(element)}));
"""
