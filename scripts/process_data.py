
from pathlib import Path
import pandas as pd
import sys

# --------------------------------------------------
# 1. File locations
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------
# 2. Helper functions
# --------------------------------------------------

def read_csv_files(file_paths):
    """Read and combine multiple CSV files."""

    frames = []

    for file_path in file_paths:
        print(f"Reading: {file_path.name}")
        frames.append(
            pd.read_csv(
                file_path,
                dtype=str,
                encoding="utf-8-sig"
            )
        )

    if not frames:
        return pd.DataFrame()

    return pd.concat(frames, ignore_index=True)


def check_columns(df, required_columns, filename):
    """Check that a CSV contains all required columns."""

    missing = set(required_columns) - set(df.columns)

    if missing:
        raise ValueError(
            f"{filename} is missing columns: {sorted(missing)}"
        )


def check_not_empty(df, columns, filename):
    """Check that required fields are not blank."""

    for column in columns:
        if df[column].isna().any() or (
            df[column].astype(str).str.strip() == ""
        ).any():
            raise ValueError(
                f"{filename} contains missing values in '{column}'."
            )


# --------------------------------------------------
# 3. Read raw entity files
# --------------------------------------------------


entity_files = [
    path for path in RAW_DIR.glob("*.csv")
    if not path.stem.endswith("_statistics")
]

if not entity_files:
    raise ValueError("No entity CSV files found.")

entity_frames = []

for file_path in entity_files:

    print(f"Reading: {file_path.name}")

    df = pd.read_csv(file_path, dtype=str)

    # Remove accidental whitespace from column headings.
    df.columns = df.columns.str.strip()

    # Check required columns.
    required_columns = ["external_id", "name"]

    check_columns(df, required_columns, file_path.name)

    check_not_empty(
        df,
        required_columns,
        file_path.name
    )

    # Determine entity type.
    if "entity_type" in df.columns:
        entity_type = df["entity_type"]
    else:
        entity_type = (
            "country_territory"
            if file_path.stem == "countries_and_territories"
            else file_path.stem.rstrip("s")
        )

    # Standardise entity data.
    standardised = pd.DataFrame({
        "external_id": df["external_id"],
        "name": df["name"],
        "entity_type": entity_type,
        "description": df["description"]
            if "description" in df.columns
            else ""
    })

    # Remove accidental whitespace.
    for column in standardised.columns:
        standardised[column] = standardised[column].str.strip()

    entity_frames.append(standardised)

# Combine all standardised entity files.
entities = pd.concat(entity_frames, ignore_index=True)

# Check for duplicate entity identifiers.
if entities["external_id"].duplicated().any():

    duplicates = entities[
        entities["external_id"].duplicated(keep=False)
    ]

    raise ValueError(
        "Duplicate entity IDs found:\n"
        + duplicates.to_string(index=False)
    )



# --------------------------------------------------
# 3A. Generate geographical relationships
# --------------------------------------------------

location_frames = []

# Identify all valid country/territory external IDs.
country_entities = entities[
    entities["entity_type"] == "country_territory"
]

country_ids = set(country_entities["external_id"])

# Process every raw entity file containing country_code.
for file_path in entity_files:

    df = pd.read_csv(
        file_path,
        dtype=str,
        encoding="utf-8-sig"
    )

    df.columns = df.columns.str.strip()

    # Skip files without geographical country associations.
    if "country_code" not in df.columns:
        continue

    print(f"Processing geographical relationships: {file_path.name}")

    check_columns(
        df,
        ["external_id", "country_code"],
        file_path.name
    )

    # Split comma-separated country codes into individual rows.
    relationships = df[
        ["external_id", "country_code"]
    ].copy()

    relationships["country_code"] = (
        relationships["country_code"]
        .fillna("")
        .str.strip()
    )

    relationships["location_external_id"] = (
        relationships["country_code"].str.split(",")
    )

    relationships = relationships.explode(
        "location_external_id"
    )

    relationships["location_external_id"] = (
        relationships["location_external_id"].str.strip()
    )

    # Remove blank country codes.
    relationships = relationships[
        relationships["location_external_id"] != ""
    ].copy()

    # Validate that every country code exists.
    unknown_codes = (
        set(relationships["location_external_id"])
        - country_ids
    )

    if unknown_codes:
        raise ValueError(
            f"{file_path.name} contains country codes "
            f"that do not match a country/territory entity: "
            f"{sorted(unknown_codes)}"
        )

    # Standardise relationship records.
    standardised = pd.DataFrame({
        "external_id": relationships["external_id"].str.strip(),
        "location_external_id": relationships["location_external_id"],
        "relationship_type": "located_in",
        "source": "",
        "source_url": ""
    })

    location_frames.append(standardised)


# Combine relationships from all applicable entity files.
if location_frames:

    processed_entity_locations = pd.concat(
        location_frames,
        ignore_index=True
    )

else:

    processed_entity_locations = pd.DataFrame(
        columns=[
            "external_id",
            "location_external_id",
            "relationship_type",
            "source",
            "source_url"
        ]
    )


# Check for duplicate relationships.
duplicate_relationships = [
    "external_id",
    "location_external_id",
    "relationship_type"
]

if processed_entity_locations.duplicated(
    subset=duplicate_relationships
).any():

    duplicates = processed_entity_locations[
        processed_entity_locations.duplicated(
            subset=duplicate_relationships,
            keep=False
        )
    ]

    raise ValueError(
        "Duplicate geographical relationships found:\n"
        + duplicates.to_string(index=False)
    )


# Check that all associated entities exist.
known_entity_ids = set(entities["external_id"])

referenced_entities = (
    set(processed_entity_locations["external_id"])
    | set(processed_entity_locations["location_external_id"])
)

unknown_entities = referenced_entities - known_entity_ids

if unknown_entities:
    raise ValueError(
        f"Geographical relationships reference unknown entities: "
        f"{sorted(unknown_entities)}"
    )


# --------------------------------------------------
# 3B. Save processed entity_locations.csv
# --------------------------------------------------

processed_entity_locations.to_csv(
    PROCESSED_DIR / "entity_locations.csv",
    index=False,
    encoding="utf-8-sig"
)




# --------------------------------------------------
# 4. Read raw statistic files
# --------------------------------------------------

statistic_files = list(RAW_DIR.glob("*_statistics.csv"))

if not statistic_files:
    raise ValueError("No statistic CSV files found.")

raw_statistics = read_csv_files(statistic_files)

required_stat_columns = [
    "external_id",
    "statistic_code",
    "statistic_name",
    "value",
    "unit",
    "comparison_label"
]

check_columns(
    raw_statistics,
    required_stat_columns,
    "Statistic files"
)

check_not_empty(
    raw_statistics,
    required_stat_columns,
    "Statistic files"
)

# Optional columns.
optional_columns = [
    "description",
    "reference_period_start",
    "reference_period_end",
    "source",
    "source_url"
]

for column in optional_columns:
    if column not in raw_statistics.columns:
        raw_statistics[column] = ""

# Remove accidental whitespace.
for column in raw_statistics.columns:
    if raw_statistics[column].dtype == "object":
        raw_statistics[column] = (
            raw_statistics[column].str.strip()
        )


# --------------------------------------------------
# 5. Validate statistic values and references
# --------------------------------------------------

raw_statistics["value"] = pd.to_numeric(
    raw_statistics["value"],
    errors="coerce"
)

if raw_statistics["value"].isna().any():
    raise ValueError(
        "Some statistic values are missing or non-numeric."
    )

# Check that every statistic belongs to an existing entity.
unknown_entities = set(
    raw_statistics["external_id"]
) - set(entities["external_id"])

if unknown_entities:
    raise ValueError(
        f"Statistics reference unknown entities: "
        f"{sorted(unknown_entities)}"
    )

# Validate reference periods.

for column in ["reference_period_start", "reference_period_end"]:

    if column in raw_statistics.columns:

        original_dates = raw_statistics[column]

        parsed_dates = pd.to_datetime(
            original_dates,
            format="mixed",
            dayfirst=True,
            errors="coerce"
        )

        invalid = (
            original_dates.notna()
            & original_dates.str.strip().ne("")
            & parsed_dates.isna()
        )

        if invalid.any():

            print("\nInvalid date values found:")

            print(
                raw_statistics.loc[
                    invalid,
                    ["external_id", "statistic_code", column]
                ].to_string(index=False)
            )

            raise ValueError(
                f"Invalid dates found in '{column}'."
            )

        raw_statistics[column] = parsed_dates.dt.strftime(
            "%Y-%m-%d"
        )


# Check that start dates are not after end dates.
start = pd.to_datetime(
    raw_statistics["reference_period_start"],
    errors="coerce"
)

end = pd.to_datetime(
    raw_statistics["reference_period_end"],
    errors="coerce"
)

invalid_periods = start.notna() & end.notna() & (start > end)

if invalid_periods.any():
    raise ValueError(
        "Some reference period start dates are after their end dates."
    )


# --------------------------------------------------
# 6. Generate processed entities.csv
# --------------------------------------------------

processed_entities = entities.copy()

processed_entities.to_csv(
    PROCESSED_DIR / "entities.csv",
    index=False,
    encoding="utf-8-sig"
)


# --------------------------------------------------
# 7. Generate processed statistics.csv
# --------------------------------------------------

statistic_metadata = [
    "statistic_code",
    "statistic_name",
    "unit",
    "comparison_label",
    "description"
]

statistics = raw_statistics[statistic_metadata].copy()

statistics = statistics.rename(
    columns={"statistic_name": "name"}
)

# Each statistic code must have one consistent definition.
if statistics.groupby("statistic_code")[
    ["name", "unit", "comparison_label", "description"]
].nunique(dropna=False).gt(1).any().any():

    raise ValueError(
        "Conflicting definitions found for one or more statistic codes."
    )

statistics = statistics.drop_duplicates(
    subset=["statistic_code"]
)

statistics = statistics.sort_values(
    "statistic_code"
)

statistics.to_csv(
    PROCESSED_DIR / "statistics.csv",
    index=False,
    encoding="utf-8-sig"
)


# --------------------------------------------------
# 8. Generate processed entity_statistics.csv
# --------------------------------------------------

processed_entity_statistics = raw_statistics[
    [
        "external_id",
        "statistic_code",
        "value",
        "reference_period_start",
        "reference_period_end",
        "source",
        "source_url"
    ]
].copy()

# Check for duplicate measurements.
duplicate_columns = [
    "external_id",
    "statistic_code",
    "reference_period_start",
    "reference_period_end"
]

if processed_entity_statistics.duplicated(
    subset=duplicate_columns
).any():

    raise ValueError(
        "Duplicate entity/statistic/reference-period records found."
    )

processed_entity_statistics.to_csv(
    PROCESSED_DIR / "entity_statistics.csv",
    index=False,
    encoding="utf-8-sig"
)


# --------------------------------------------------
# 9. Completion message
# --------------------------------------------------

print("\nData processing completed successfully!")

print(f"Entities: {len(processed_entities)}")
print(f"Statistics: {len(statistics)}")
print(f"Measurements: {len(processed_entity_statistics)}")
print(f"Geographical relationships: {len(processed_entity_locations)}")

print(f"\nProcessed files saved to: {PROCESSED_DIR}")
