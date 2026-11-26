
import random

from src.database.connection import get_supabase_client


def get_entities(entity_type=None):
    """
    Retrieve entities from Supabase.

    Optionally filter by entity type, such as:
    country_territory, city or mountain.
    """

    supabase = get_supabase_client()

    # Retrieve available entity types.
    types_response = (
        supabase.table("entity_types")
        .select("entity_type_id, name")
        .execute()
    )

    entity_types = {
        row["entity_type_id"]: row["name"]
        for row in types_response.data
    }

    # Apply optional entity type filter.
    query = (
        supabase.table("entities")
        .select(
            "entity_id, external_id, name, "
            "description, entity_type_id"
        )
    )

    if entity_type is not None:

        matching_type_ids = [
            type_id
            for type_id, name in entity_types.items()
            if name == entity_type
        ]

        if not matching_type_ids:
            raise ValueError(
                f"Unknown entity type: {entity_type}"
            )

        query = query.eq(
            "entity_type_id",
            matching_type_ids[0]
        )

    response = query.order("name").execute()

    # Add the entity type name to each result.
    entities = []

    for row in response.data:
        row["entity_type"] = entity_types.get(
            row["entity_type_id"]
        )
        entities.append(row)

    return entities


def get_random_entities(entity_type, count=2):
    """
    Retrieve a random selection of entities
    from a particular entity type.
    """

    if count < 1:
        raise ValueError("Count must be at least 1.")

    entities = get_entities(entity_type)

    if len(entities) < count:
        raise ValueError(
            f"Not enough {entity_type} entities available. "
            f"Requested {count}, found {len(entities)}."
        )

    return random.sample(entities, count)
