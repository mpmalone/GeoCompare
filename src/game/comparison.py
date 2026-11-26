
import random

from src.database.statistics import get_entities_with_statistic


def generate_comparison(
    entity_type,
    statistic_code,
    direction="higher"
):
    """
    Generate a comparison between two randomly selected entities.

    direction:
        "higher" - the entity with the greater value wins.
        "lower"  - the entity with the smaller value wins.
    """

    if direction not in {"higher", "lower"}:
        raise ValueError(
            "Direction must be either 'higher' or 'lower'."
        )

    # Retrieve entities with the requested statistic.
    results = get_entities_with_statistic(statistic_code)

    # Keep only entities of the requested type.
    candidates = [
        row for row in results
        if row["entity_type"] == entity_type
    ]

    if len(candidates) < 2:
        raise ValueError(
            f"Not enough {entity_type} entities have "
            f"the statistic '{statistic_code}'."
        )

    # Group measurements by reference period.
    period_groups = {}

    for entity in candidates:

        period = (
            entity["reference_period_start"],
            entity["reference_period_end"]
        )

        period_groups.setdefault(period, []).append(entity)

    # Find periods containing at least two different values.
    valid_groups = []

    for period, entities in period_groups.items():

        value_groups = {}

        for entity in entities:
            value = float(entity["value"])
            value_groups.setdefault(value, []).append(entity)

        if len(value_groups) >= 2:
            valid_groups.append({
                "period": period,
                "value_groups": value_groups
            })

    if not valid_groups:
        raise ValueError(
            f"Could not find two {entity_type} entities "
            f"with different '{statistic_code}' values "
            "for the same reference period."
        )

    # Select the most recent available reference period.
    selected_group = max(
        valid_groups,
        key=lambda group: (
            group["period"][1] or group["period"][0] or "",
            group["period"][0] or ""
        )
    )

    value_groups = selected_group["value_groups"]

    # Select two different measurement values.
    selected_values = random.sample(
        list(value_groups.keys()),
        2
    )

    entity_a = random.choice(value_groups[selected_values[0]])
    entity_b = random.choice(value_groups[selected_values[1]])

    value_a = float(entity_a["value"])
    value_b = float(entity_b["value"])

    # Determine the correct answer based on direction.
    if direction == "higher":
        correct_entity = (
            entity_a if value_a > value_b else entity_b
        )
    else:
        correct_entity = (
            entity_a if value_a < value_b else entity_b
        )

    return {
        "entity_a": entity_a,
        "entity_b": entity_b,
        "statistic": {
            "code": entity_a["statistic_code"],
            "name": entity_a["statistic_name"],
            "unit": entity_a["unit"],
            "comparison_label": entity_a["comparison_label"]
        },
        "direction": direction,
        "reference_period_start": selected_group["period"][0],
        "reference_period_end": selected_group["period"][1],
        "correct_entity_id": correct_entity["entity_id"],
        "correct_entity_name": correct_entity["name"]
    }
