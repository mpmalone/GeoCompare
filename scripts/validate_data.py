
from pathlib import Path
import math
import pandas as pd


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

PROJECT_DIR = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_DIR / "data" / "processed"

ENTITIES_FILE = PROCESSED_DIR / "entities.csv"
STATISTICS_FILE = PROCESSED_DIR / "statistics.csv"
ENTITY_STATISTICS_FILE = PROCESSED_DIR / "entity_statistics.csv"
ENTITY_LOCATIONS_FILE = PROCESSED_DIR / "entity_locations.csv"

# All entity types supported by GeoCompare.
VALID_ENTITY_TYPES = {
    "country_territory",
    "city",
    "mountain",
    "river",
    "lake",
    "island"
}

# Entity types currently entered in Supabase.
ACTIVE_ENTITY_TYPES = {
    "country_territory",
    "city",
    "mountain",
    "river",
    "lake",
    "island"
}


# --------------------------------------------------
# VALIDATION RESULTS
# --------------------------------------------------

errors = []
warnings = []


def add_error(message):
    errors.append(message)


def add_warning(message):
    warnings.append(message)


def report_section(title):
    print("\n" + "=" * 55)
    print(title)
    print("=" * 55)


def print_issues(issues, limit=20):
    for issue in issues[:limit]:
        print(f"  - {issue}")

    if len(issues) > limit:
        print(f"  ... and {len(issues) - limit} more")


# --------------------------------------------------
# LOAD CSV FILES
# --------------------------------------------------

def load_csv(file_path):

    if not file_path.exists():
        add_error(f"Missing file: {file_path.name}")
        return None

    print(f"Reading: {file_path.name}")

    try:
        df = pd.read_csv(
            file_path,
            dtype=str,
            encoding="utf-8-sig",
            keep_default_na=False
        )

        df.columns = df.columns.str.strip()

        # Remove accidental whitespace from values.
        for column in df.columns:
            df[column] = df[column].str.strip()

        return df

    except Exception as error:
        add_error(
            f"Could not read {file_path.name}: {error}"
        )
        return None


# --------------------------------------------------
# CHECK REQUIRED COLUMNS
# --------------------------------------------------

def check_columns(df, required_columns, filename):

    missing = set(required_columns) - set(df.columns)

    if missing:
        add_error(
            f"{filename} is missing columns: "
            f"{sorted(missing)}"
        )
        return False

    return True


# --------------------------------------------------
# VALIDATE ENTITIES
# --------------------------------------------------

def validate_entities(entities):

    report_section("ENTITY VALIDATION")

    required_columns = [
        "external_id",
        "name",
        "entity_type",
        "description"
    ]

    if not check_columns(
        entities,
        required_columns,
        "entities.csv"
    ):
        return

    print(f"Total entities: {len(entities)}")

    # Check missing values.
    for column in ["external_id", "name", "entity_type"]:

        missing = entities[column].eq("")

        if missing.any():
            add_error(
                f"Entities have {missing.sum()} missing "
                f"values in '{column}'."
            )

    # Check duplicate IDs.
    duplicates = entities[
        entities["external_id"].ne("")
        & entities["external_id"].duplicated(keep=False)
    ]

    if not duplicates.empty:
        add_error(
            f"Duplicate entity IDs found: "
            f"{duplicates['external_id'].unique().tolist()}"
        )

    # Check supported entity types.
    invalid_types = (
        set(entities["entity_type"])
        - {""}
        - VALID_ENTITY_TYPES
    )

    if invalid_types:
        add_error(
            f"Unsupported entity types: "
            f"{sorted(invalid_types)}"
        )

    # Check entity types not yet in Supabase.
    future_types = (
        set(entities["entity_type"])
        & VALID_ENTITY_TYPES
    ) - ACTIVE_ENTITY_TYPES

    if future_types:
        add_warning(
            "These entity types are valid but have not "
            "yet been added to Supabase: "
            f"{sorted(future_types)}"
        )

    print("Entity validation complete.")


# --------------------------------------------------
# VALIDATE ENTITY LOCATIONS
# --------------------------------------------------

def validate_entity_locations(entity_locations, entities):

    report_section("GEOGRAPHICAL RELATIONSHIP VALIDATION")

    required_columns = [
        "external_id",
        "location_external_id",
        "relationship_type"
    ]

    if not check_columns(
        entity_locations,
        required_columns,
        "entity_locations.csv"
    ):
        return

    print(f"Total geographical relationships: {len(entity_locations)}")

    # Check required values.
    for column in required_columns:

        missing = entity_locations[column].eq("")

        if missing.any():
            add_error(
                f"Geographical relationships have "
                f"{missing.sum()} missing values in '{column}'."
            )

    # Check supported relationship types.
    valid_relationship_types = {
        "located_in",
        "administered_by",
        "sovereignty"
    }

    invalid_types = (
        set(entity_locations["relationship_type"])
        - {""}
        - valid_relationship_types
    )

    if invalid_types:
        add_error(
            "Unsupported geographical relationship types: "
            f"{sorted(invalid_types)}"
        )

    # Check that both referenced entities exist.
    known_entity_ids = set(entities["external_id"])

    referenced_entity_ids = (
        set(entity_locations["external_id"])
        | set(entity_locations["location_external_id"])
    )

    unknown_entities = (
        referenced_entity_ids - {""} - known_entity_ids
    )

    if unknown_entities:
        add_error(
            "Geographical relationships reference unknown "
            f"entity IDs: {sorted(unknown_entities)}"
        )

    # Check that located_in relationships point to
    # country or territory entities.
    entity_types = dict(
        zip(entities["external_id"], entities["entity_type"])
    )

    located_in = entity_locations[
        entity_locations["relationship_type"] == "located_in"
    ]

    invalid_locations = []

    for _, row in located_in.iterrows():

        location_id = row["location_external_id"]

        if location_id == "":
            continue

        if location_id in entity_types:
            if entity_types[location_id] != "country_territory":
                invalid_locations.append(
                    f"{row['external_id']} -> {location_id}"
                )

    if invalid_locations:
        add_error(
            "The following 'located_in' relationships do not "
            "point to country/territory entities: "
            f"{invalid_locations[:20]}"
        )

    # Check that entities are not located in themselves.
    self_references = entity_locations[
        entity_locations["external_id"]
        == entity_locations["location_external_id"]
    ]

    if not self_references.empty:
        add_error(
            f"{len(self_references)} geographical relationships "
            "reference the same entity as both sides."
        )

    # Check duplicate relationships.
    duplicate_columns = [
        "external_id",
        "location_external_id",
        "relationship_type"
    ]

    duplicates = entity_locations[
        entity_locations.duplicated(
            subset=duplicate_columns,
            keep=False
        )
    ]

    if not duplicates.empty:
        add_error(
            f"{len(duplicates)} rows contain duplicate "
            "geographical relationships."
        )

    print("Geographical relationship validation complete.")


# --------------------------------------------------
# VALIDATE STATISTICS
# --------------------------------------------------

def validate_statistics(statistics):

    report_section("STATISTIC VALIDATION")

    required_columns = [
        "statistic_code",
        "name",
        "unit",
        "comparison_label",
        "description"
    ]

    if not check_columns(
        statistics,
        required_columns,
        "statistics.csv"
    ):
        return

    print(f"Total statistics: {len(statistics)}")

    # Check missing required values.
    for column in [
        "statistic_code",
        "name",
        "unit",
        "comparison_label"
    ]:

        missing = statistics[column].eq("")

        if missing.any():
            add_error(
                f"Statistics have {missing.sum()} missing "
                f"values in '{column}'."
            )

    # Check duplicate statistic codes.
    duplicates = statistics[
        statistics["statistic_code"].ne("")
        & statistics["statistic_code"].duplicated(
            keep=False
        )
    ]

    if not duplicates.empty:
        add_error(
            "Duplicate statistic codes found: "
            f"{duplicates['statistic_code'].unique().tolist()}"
        )

    print("Statistic validation complete.")


# --------------------------------------------------
# VALIDATE ENTITY STATISTICS
# --------------------------------------------------

def validate_entity_statistics(
    entity_statistics,
    entities,
    statistics
):

    report_section("MEASUREMENT VALIDATION")

    required_columns = [
        "external_id",
        "statistic_code",
        "value",
        "reference_period_start",
        "reference_period_end",
        "source",
        "source_url"
    ]

    if not check_columns(
        entity_statistics,
        required_columns,
        "entity_statistics.csv"
    ):
        return

    print(f"Total measurements: {len(entity_statistics)}")

    # Check required values.
    for column in [
        "external_id",
        "statistic_code",
        "value"
    ]:

        missing = entity_statistics[column].eq("")

        if missing.any():
            add_error(
                f"Measurements have {missing.sum()} missing "
                f"values in '{column}'."
            )

    # Check numeric measurement values.
    numeric_values = pd.to_numeric(
        entity_statistics["value"],
        errors="coerce"
    )

    invalid_values = numeric_values.isna()

    invalid_values |= ~numeric_values.map(
        lambda value: (
            pd.notna(value) and math.isfinite(value)
        )
    )

    if invalid_values.any():
        add_error(
            f"{invalid_values.sum()} measurements have "
            "invalid or non-finite numeric values."
        )

    # Check entity references.
    known_entity_ids = set(entities["external_id"])

    unknown_entities = (
        set(entity_statistics["external_id"])
        - {""}
        - known_entity_ids
    )

    if unknown_entities:
        add_error(
            "Measurements reference unknown entity IDs: "
            f"{sorted(unknown_entities)}"
        )

    # Check statistic references.
    known_statistic_codes = set(
        statistics["statistic_code"]
    )

    unknown_statistics = (
        set(entity_statistics["statistic_code"])
        - {""}
        - known_statistic_codes
    )

    if unknown_statistics:
        add_error(
            "Measurements reference unknown statistic codes: "
            f"{sorted(unknown_statistics)}"
        )

    # Validate reference dates.
    date_columns = [
        "reference_period_start",
        "reference_period_end"
    ]

    parsed_dates = {}

    for column in date_columns:

        original_dates = entity_statistics[column]

        parsed = pd.to_datetime(
            original_dates.replace("", pd.NA),
            format="mixed",
            dayfirst=True,
            errors="coerce"
        )

        invalid = (
            original_dates.ne("")
            & parsed.isna()
        )

        if invalid.any():
            add_error(
                f"{invalid.sum()} invalid dates found "
                f"in '{column}'."
            )

        parsed_dates[column] = parsed

    start_dates = parsed_dates["reference_period_start"]
    end_dates = parsed_dates["reference_period_end"]

    # A reference period must have either both dates
    # or neither date.
    incomplete_periods = (
        (start_dates.isna() & end_dates.notna())
        | (start_dates.notna() & end_dates.isna())
    )

    if incomplete_periods.any():
        add_error(
            f"{incomplete_periods.sum()} measurements "
            "have incomplete reference periods."
        )

    # Check that start dates are not after end dates.
    reversed_periods = (
        start_dates.notna()
        & end_dates.notna()
        & (start_dates > end_dates)
    )

    if reversed_periods.any():
        add_error(
            f"{reversed_periods.sum()} measurements "
            "have reference periods where the start "
            "date is after the end date."
        )

    # Check duplicate measurements.
    duplicate_columns = [
        "external_id",
        "statistic_code",
        "reference_period_start",
        "reference_period_end"
    ]

    duplicates = entity_statistics[
        entity_statistics.duplicated(
            subset=duplicate_columns,
            keep=False
        )
    ]

    if not duplicates.empty:
        add_error(
            f"{len(duplicates)} rows contain duplicate "
            "measurement combinations."
        )

    # Check source URLs.
    invalid_urls = []

    for index, url in entity_statistics[
        "source_url"
    ].items():

        if url == "":
            continue

        if not url.startswith(("https://", "http://")):
            invalid_urls.append(index)

    if invalid_urls:
        add_warning(
            f"{len(invalid_urls)} source URLs do not "
            "start with http:// or https://."
        )

    print("Measurement validation complete.")


# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():

    print("\n" + "=" * 55)
    print("GEOCOMPARE DATA VALIDATION")
    print("=" * 55)

    # Load files.
    entities = load_csv(ENTITIES_FILE)
    statistics = load_csv(STATISTICS_FILE)
    entity_statistics = load_csv(ENTITY_STATISTICS_FILE)
    entity_locations = load_csv(ENTITY_LOCATIONS_FILE)

    if any(
        df is None
        for df in [
            entities,
            statistics,
            entity_statistics,
            entity_locations
        ]
    ):
        report_results()
        return

    # Validate individual files.
    validate_entities(entities)
    validate_statistics(statistics)

    validate_entity_statistics(
        entity_statistics,
        entities,
        statistics
    )

    validate_entity_locations(
        entity_locations,
        entities
    )

    report_results()


# --------------------------------------------------
# FINAL RESULTS
# --------------------------------------------------

def report_results():

    report_section("VALIDATION RESULTS")

    if warnings:
        print(f"\nWARNINGS: {len(warnings)}")
        print_issues(warnings)

    if errors:
        print(f"\nERRORS: {len(errors)}")
        print_issues(errors)

        print("\nVALIDATION FAILED")
        raise SystemExit(1)

    print("\nVALIDATION PASSED")

    print("\nAll processed CSV files passed validation.")
    print("Your data is ready for the next import stage.")


if __name__ == "__main__":
    main()
