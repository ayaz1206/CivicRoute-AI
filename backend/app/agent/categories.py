"""Supported complaint categories and validated Boston department mappings.

The category -> department mapping is a curated, validated allowlist. The
routing node may use historical 311 patterns to pick a department, but the
final choice is always validated against this mapping and the city's actual
departments, so the agent can never invent a department.
"""

from __future__ import annotations

# Canonical categories the classifier may output. "Other" is the catch-all and
# always triggers human review.
SUPPORTED_CATEGORIES: tuple[str, ...] = (
    "Pothole",
    "Street Light",
    "Trash & Recycling",
    "Graffiti",
    "Tree Maintenance",
    "Parking",
    "Water & Sewer",
    "Noise",
    "Sidewalk",
    "Traffic Signal",
    "Other",
)

# Category -> department slug (slugs match app/seed.py department slugs).
CATEGORY_TO_DEPARTMENT: dict[str, str] = {
    "Pothole": "public-works",
    "Sidewalk": "public-works",
    "Street Light": "public-works",
    "Trash & Recycling": "sanitation",
    "Graffiti": "code-enforcement",
    "Tree Maintenance": "parks-rec",
    "Parking": "transportation",
    "Traffic Signal": "transportation",
    "Water & Sewer": "water-sewer",
    "Noise": "code-enforcement",
}

# Map raw Boston 311 department codes (from historical data) to our slugs, used
# to translate historical routing evidence into a validated department.
BOSTON_DEPT_CODE_TO_SLUG: dict[str, str] = {
    "PWDx": "public-works",
    "BTDT": "transportation",
    "ISD": "code-enforcement",
    "PARK": "parks-rec",
    "PROP": "public-works",
    "BWSC": "water-sewer",
}


def is_supported_category(value: str | None) -> bool:
    return value in SUPPORTED_CATEGORIES
