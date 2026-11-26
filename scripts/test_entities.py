
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.entities import (
    get_entities,
    get_random_entities
)


def main():

    print("Testing entity database queries...")

    # Test retrieving all entities.
    entities = get_entities()
    print(f"\nTotal entities: {len(entities)}")

    # Test retrieving individual entity types.
    for entity_type in [
        "country_territory",
        "city",
        "mountain"
    ]:

        results = get_entities(entity_type)

        print(
            f"\n{entity_type}: {len(results)} entities"
        )

        # Display three examples.
        for entity in results[:3]:
            print(f"  {entity['name']}")

    # Test random entity selection.
    print("\nRandom mountains:")

    random_mountains = get_random_entities(
        "mountain",
        count=2
    )

    for mountain in random_mountains:
        print(f"  {mountain['name']}")

    print("\nAll tests completed!")


if __name__ == "__main__":
    main()
