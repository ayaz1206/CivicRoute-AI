"""Labeled evaluation dataset for the triage agent (M5).

IMPORTANT — provenance:
- ``SYNTHETIC_CASES`` are hand-written, SYNTHETIC complaint narratives with
  gold labels for classification, priority, and department. They contain NO
  real resident data and are NOT drawn from Boston 311 records. They exist to
  measure the live agent's behavior on realistic-but-fabricated text.
- Genuine Boston 311 historical labels are used ONLY in the routing evaluation
  (`app.eval.routing_eval`), which reads the separate historical table. The two
  sources are never mixed.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LabeledCase:
    title: str
    description: str
    # Gold labels:
    category: str
    priority: str
    department_slug: str
    # Whether this case is expected to be auto-confident (not flagged).
    expect_confident: bool = True


# Synthetic — fabricated narratives, not real 311 data.
SYNTHETIC_CASES: list[LabeledCase] = [
    LabeledCase(
        "Deep pothole on Dorchester Ave",
        "A deep pothole has opened on Dorchester Ave near the bus stop and cars "
        "are swerving dangerously to avoid it.",
        "Pothole", "high", "public-works",
    ),
    LabeledCase(
        "Pothole damaging tires on Beacon St",
        "There's a large pothole on Beacon St that keeps damaging car tires.",
        "Pothole", "medium", "public-works",
    ),
    LabeledCase(
        "Street light out on Blue Hill Ave",
        "The street light at the corner of Blue Hill Ave has been dark for a "
        "week, making the crosswalk unsafe at night.",
        "Street Light", "high", "public-works",
    ),
    LabeledCase(
        "Flickering street light",
        "A street light keeps flickering on and off on my block.",
        "Street Light", "low", "public-works",
    ),
    LabeledCase(
        "Overflowing trash barrels in the South End",
        "Public trash barrels have been overflowing for days with garbage "
        "spilling onto the sidewalk in the South End.",
        "Trash & Recycling", "medium", "sanitation",
    ),
    LabeledCase(
        "Missed recycling pickup",
        "Our recycling was not collected on the scheduled day this week.",
        "Trash & Recycling", "low", "sanitation",
    ),
    LabeledCase(
        "Graffiti on the playground wall",
        "Someone spray-painted graffiti across the wall at the playground.",
        "Graffiti", "low", "code-enforcement",
    ),
    LabeledCase(
        "Fallen tree branch blocking sidewalk",
        "A large tree branch fell and is completely blocking the sidewalk on Elm St.",
        "Tree Maintenance", "high", "parks-rec",
    ),
    LabeledCase(
        "Abandoned car taking up parking",
        "An abandoned vehicle has been parked on our street for weeks without moving.",
        "Parking", "medium", "transportation",
    ),
    LabeledCase(
        "Broken traffic signal",
        "The traffic signal at Main St and 1st Ave is stuck on red in all "
        "directions causing confusion.",
        "Traffic Signal", "high", "transportation",
    ),
    LabeledCase(
        "Water main leak flooding the street",
        "Water is gushing from the ground and flooding the street — looks like a "
        "water main break.",
        "Water & Sewer", "urgent", "water-sewer",
    ),
    LabeledCase(
        "Loud construction noise at night",
        "There is loud construction noise happening well past midnight every night.",
        "Noise", "medium", "code-enforcement",
    ),
    LabeledCase(
        "Cracked and uneven sidewalk",
        "The sidewalk is badly cracked and uneven, a tripping hazard for elderly "
        "residents.",
        "Sidewalk", "medium", "public-works",
    ),
    LabeledCase(
        "Pothole near school crossing",
        "A pothole has formed right at the school crossing on Washington St.",
        "Pothole", "high", "public-works",
    ),
]
