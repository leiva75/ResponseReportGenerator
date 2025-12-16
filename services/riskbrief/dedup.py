"""Deduplication utilities for Risk Brief events."""
from .classifier import similarity


def deduplicate(events: list, title_threshold: float = 0.86) -> list:
    """
    Same day (YYYY-MM-DD) + same category + similar title -> keep highest confidence.
    """
    kept = []
    for e in events:
        dt = (e.get("datetime") or "")
        day = dt[:10] if len(dt) >= 10 else ""
        cat = e.get("category", "UNKNOWN")
        title = e.get("title", "")

        merged = False
        for k in kept:
            kdt = (k.get("datetime") or "")
            kday = kdt[:10] if len(kdt) >= 10 else ""
            if kday == day and k.get("category") == cat and similarity(title, k.get("title", "")) >= title_threshold:
                if float(e.get("confidence", 0.0)) > float(k.get("confidence", 0.0)):
                    k.update(e)
                merged = True
                break

        if not merged:
            kept.append(e)

    return kept
