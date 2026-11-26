
from src.database.connection import get_supabase_client


def get_statistics():
    """
    Retrieve all available statistic definitions.
    """

    supabase = get_supabase_client()

    response = (
        supabase.table("statistics")
        .select(
            "statistic_id, statistic_code, name, "
            "unit, comparison_label, description"
        )
        .order("name")
        .execute()
    )

    return response.data


def get_entity_statistics(entity_id):
    """
    Retrieve all measurements recorded for an entity.

    The statistic definitions are joined in Python
    using statistic_id.
    """

    supabase = get_supabase_client()

    # Retrieve measurements for the entity.
    measurements_response = (
        supabase.table("entity_statistics")
        .select(
            "statistic_id, value, "
            "reference_period_start, reference_period_end, "
            "source, source_url"
        )
        .eq("entity_id", entity_id)
        .execute()
    )

    if not measurements_response.data:
        return []

    # Retrieve statistic definitions.
    statistics = get_statistics()

    statistic_lookup = {
        statistic["statistic_id"]: statistic
        for statistic in statistics
    }

    results = []

    for measurement in measurements_response.data:

        statistic = statistic_lookup.get(
            measurement["statistic_id"]
        )

        if statistic is None:
            continue

        results.append({
            "statistic_id": measurement["statistic_id"],
            "statistic_code": statistic["statistic_code"],
            "name": statistic["name"],
            "unit": statistic["unit"],
            "comparison_label": statistic["comparison_label"],
            "value": measurement["value"],
            "reference_period_start": (
                measurement["reference_period_start"]
            ),
            "reference_period_end": (
                measurement["reference_period_end"]
            ),
            "source": measurement["source"],
            "source_url": measurement["source_url"]
        })

    return results


def get_entities_with_statistic(statistic_code):
    """
    Retrieve all entities that have a measurement
    for a particular statistic.
    """

    supabase = get_supabase_client()

    # Find the statistic definition.
    statistic_response = (
        supabase.table("statistics")
        .select(
            "statistic_id, statistic_code, name, "
            "unit, comparison_label"
        )
        .eq("statistic_code", statistic_code)
        .execute()
    )

    if not statistic_response.data:
        raise ValueError(
            f"Unknown statistic code: {statistic_code}"
        )

    statistic = statistic_response.data[0]
    statistic_id = statistic["statistic_id"]

    # Find all measurements for this statistic.
    measurements_response = (
        supabase.table("entity_statistics")
        .select(
            "entity_id, value, "
            "reference_period_start, reference_period_end, "
            "source, source_url"
        )
        .eq("statistic_id", statistic_id)
        .execute()
    )

    measurements = measurements_response.data

    if not measurements:
        return []

    # Retrieve the corresponding entities.
    entity_ids = list({
        measurement["entity_id"]
        for measurement in measurements
    })

    entities_response = (
        supabase.table("entities")
        .select(
            "entity_id, external_id, name, entity_type_id"
        )
        .in_("entity_id", entity_ids)
        .execute()
    )

    entity_lookup = {
        entity["entity_id"]: entity
        for entity in entities_response.data
    }

    # Retrieve entity type names.
    entity_types_response = (
        supabase.table("entity_types")
        .select("entity_type_id, name")
        .execute()
    )

    entity_type_lookup = {
        row["entity_type_id"]: row["name"]
        for row in entity_types_response.data
    }

    results = []

    for measurement in measurements:

        entity = entity_lookup.get(
            measurement["entity_id"]
        )

        if entity is None:
            continue

        results.append({
            "entity_id": entity["entity_id"],
            "external_id": entity["external_id"],
            "name": entity["name"],
            "entity_type": entity_type_lookup.get(
                entity["entity_type_id"]
            ),
            "statistic_code": statistic["statistic_code"],
            "statistic_name": statistic["name"],
            "unit": statistic["unit"],
            "comparison_label": statistic["comparison_label"],
            "value": measurement["value"],
            "reference_period_start": (
                measurement["reference_period_start"]
            ),
            "reference_period_end": (
                measurement["reference_period_end"]
            ),
            "source": measurement["source"],
            "source_url": measurement["source_url"]
        })

    return results
