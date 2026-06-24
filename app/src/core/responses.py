"""Standard success-response envelope helpers.

Mirrors the success shape in ``doc/content/specification/api-response-template.md``.
The matching error envelope lives in ``src/core/errors.py``.
"""

from collections.abc import Mapping


def success_response(
    *,
    data: object = None,
    meta: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Build the standard success envelope: ``{"success": true, "data", "meta"}``."""
    return {"success": True, "data": data, "meta": meta}
