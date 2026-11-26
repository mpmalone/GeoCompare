
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.entities import get_random_entities
from src.database.statistics import (
    get_statistics,
    get_entity_statistics,
    get_entities_with_statistic
)


def main():

    print("Testing statistics database queries...")

    # --------------------------------------------------
    # Test 1: Retrieve statistic definitions
    # --------------------------------------------------

    print("\nAvailable statistics:")

    statistics = get_statistics()

    for statistic in statistics:
        print(
            f"  {statistic['statistic_code']}: "
            f"{statistic['name']} "
            f"({statistic['unit']})"
        )

    print(f"\nTotal statistics: {len(statistics)}")

    # --------------------------------------------------
    # Test 2: Retrieve measurements for one entity
    # --------------------------------------------------

    print("\nTesting measurements for a random mountain:")

    mountain = get_random_entities(
        "mountain",
        count=1
    )[0]

    print(f"\nMountain: {mountain['name']}")

    measurements = get_entity_statistics(
        mountain["entity_id"]
    )

    if measurements:
        for measurement in measurements:
            print(
                f"  {measurement['name']}: "
                f"{measurement['value']} "
                f"{measurement['unit']}"
            )
    else:
        print("  No measurements found.")

    # --------------------------------------------------
    # Test 3: Retrieve entities with a particular statistic
    # --------------------------------------------------

    print("\nTesting entities with recorded statistics:")

    populated_statistic = None
    entities = []

    for statistic in statistics:

        results = get_entities_with_statistic(
            statistic["statistic_code"]
        )

        if results:
            populated_statistic = statistic
            entities = results
            break

    if populated_statistic:

        print(
            f"\nStatistic: {populated_statistic['name']}"
        )

        print(f"Entities found: {len(entities)}")

        for entity in entities[:5]:
            print(
                f"  {entity['name']} "
                f"({entity['entity_type']}): "
                f"{entity['value']} {entity['unit']}"
            )

    else:
        print("No populated statistics found.")

    print("\nAll tests completed!")


if __name__ == "__main__":
    main()
