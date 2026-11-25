
import csv
import math
import sys
from pathlib import Path

# Add the project root to Python's import path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.connection import get_supabase_client


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

BATCH_SIZE = 500


# ---------------------------------------------------------
# Helper functions
# ---------------------------------------------------------

def read_csv(filename):
    """Read a processed CSV file and return its rows."""

    file_path = PROCESSED_DIR / filename

    with file_path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def clean(value):
    """Convert empty CSV values into None."""

    if value is None or value.strip() == "":
        return None

    return value.strip()


def upsert_in_batches(supabase, table, records, conflict_column):
    """Insert or update records in manageable batches."""

    if not records:
        print(f"No records to import into {table}.")
        return

    for start in range(0, len(records), BATCH_SIZE):
        batch = records[start:start + BATCH_SIZE]

        (
            supabase
            .table(table)
            .upsert(batch, on_conflict=conflict_column)
            .execute()
        )

        print(
            f"{table}: imported "
            f"{min(start + BATCH_SIZE, len(records))} "
            f"of {len(records)} records"
        )


# ---------------------------------------------------------
# 1. Import statistics
# ---------------------------------------------------------

def import_statistics(supabase):

    print("\nImporting statistics...")

    rows = read_csv("statistics.csv")

    records = []

    for row in rows:
        records.append({
            "statistic_code": clean(row["statistic_code"]),
            "name": clean(row["name"]),
            "unit": clean(row["unit"]),
            "comparison_label": clean(row["comparison_label"]),
            "description": clean(row["description"]),
        })

    upsert_in_batches(
        supabase,
        "statistics",
        records,
        "statistic_code"
    )

    # Retrieve database-generated statistic IDs.
    response = (
        supabase
        .table("statistics")
        .select("statistic_id,statistic_code")
        .execute()
    )

    return {
        row["statistic_code"]: row["statistic_id"]
        for row in response.data
    }


# ---------------------------------------------------------
# 2. Import entities
# ---------------------------------------------------------

def import_entities(supabase):

    print("\nImporting entities...")

    # Retrieve the entity types already defined in Supabase.
    response = (
        supabase
        .table("entity_types")
        .select("entity_type_id,name")
        .execute()
    )

    entity_type_ids = {
        row["name"]: row["entity_type_id"]
        for row in response.data
    }

    rows = read_csv("entities.csv")

    records = []

    for row in rows:

        entity_type = clean(row["entity_type"])

        if entity_type not in entity_type_ids:
            raise ValueError(
                f"Unknown entity type '{entity_type}' "
                f"for entity {row['external_id']}"
            )

        records.append({
            "external_id": clean(row["external_id"]),
            "name": clean(row["name"]),
            "entity_type_id": entity_type_ids[entity_type],
            "description": clean(row["description"]),
        })

    upsert_in_batches(
        supabase,
        "entities",
        records,
        "external_id"
    )

    # Retrieve database-generated entity IDs.
    response = (
        supabase
        .table("entities")
        .select("entity_id,external_id")
        .execute()
    )

    return {
        row["external_id"]: row["entity_id"]
        for row in response.data
    }


# ---------------------------------------------------------
# 3. Import entity statistics
# ---------------------------------------------------------

def import_entity_statistics(
    supabase,
    entity_ids,
    statistic_ids
):

    print("\nImporting entity statistics...")

    rows = read_csv("entity_statistics.csv")

    records = []

    for row in rows:

        external_id = clean(row["external_id"])
        statistic_code = clean(row["statistic_code"])

        if external_id not in entity_ids:
            raise ValueError(
                f"Unknown entity external ID: {external_id}"
            )

        if statistic_code not in statistic_ids:
            raise ValueError(
                f"Unknown statistic code: {statistic_code}"
            )

        value = float(row["value"])

        if not math.isfinite(value):
            raise ValueError(
                f"Invalid numeric value for {external_id}, "
                f"{statistic_code}"
            )

        records.append({
            "entity_id": entity_ids[external_id],
            "statistic_id": statistic_ids[statistic_code],
            "value": value,
            "reference_period_start": clean(
                row["reference_period_start"]
            ),
            "reference_period_end": clean(
                row["reference_period_end"]
            ),
            "source": clean(row["source"]),
            "source_url": clean(row["source_url"]),
        })

    upsert_in_batches(
        supabase,
        "entity_statistics",
        records,
        (
            "entity_id,statistic_id,"
            "reference_period_start,reference_period_end"
        )
    )


def import_entity_locations(supabase, entity_ids):
    print("\nImporting geographical relationships...")

    rows = read_csv("entity_locations.csv")
    records = []

    valid_relationship_types = {
        "located_in",
        "administered_by",
        "sovereignty"
    }

    for row in rows:
        external_id = clean(row["external_id"])
        location_external_id = clean(row["location_external_id"])
        relationship_type = clean(row["relationship_type"])

        # Check that both entities exist.
        if external_id not in entity_ids:
            raise ValueError(
                f"Unknown entity external ID: {external_id}"
            )

        if location_external_id not in entity_ids:
            raise ValueError(
                f"Unknown location external ID: "
                f"{location_external_id}"
            )

        # Check the relationship type.
        if relationship_type not in valid_relationship_types:
            raise ValueError(
                f"Invalid relationship type: {relationship_type}"
            )

        # Convert external IDs into Supabase entity IDs.
        records.append({
            "entity_id": entity_ids[external_id],
            "location_entity_id": entity_ids[location_external_id],
            "relationship_type": relationship_type,
            "source": clean(row["source"]),
            "source_url": clean(row["source_url"]),
        })

    upsert_in_batches(
        supabase,
        "entity_locations",
        records,
        "entity_id,location_entity_id,relationship_type"
    )



# ---------------------------------------------------------
# Main import process
# ---------------------------------------------------------

def main():

    print("Connecting to Supabase...")

    supabase = get_supabase_client()

    print("Successfully connected!")

    statistic_ids = import_statistics(supabase)
    entity_ids = import_entities(supabase)

    import_entity_statistics(
        supabase,
        entity_ids,
        statistic_ids
    )

    import_entity_locations(
        supabase,
        entity_ids
    )

    print("\nImport completed successfully!")

    print(f"Statistics available: {len(statistic_ids)}")
    print(f"Entities available: {len(entity_ids)}")


if __name__ == "__main__":
    main()
