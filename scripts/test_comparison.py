
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.game.comparison import generate_comparison


def test_comparison(direction):

    comparison = generate_comparison(
        entity_type="mountain",
        statistic_code="ELEV",
        direction=direction
    )

    entity_a = comparison["entity_a"]
    entity_b = comparison["entity_b"]
    statistic = comparison["statistic"]

    print(f"\n{'=' * 45}")
    print(f"Testing direction: {direction.upper()}")
    print(f"{'=' * 45}")

    print(f"\nStatistic: {statistic['name']}")
    print(f"Unit: {statistic['unit']}")

    print(f"\nEntity A: {entity_a['name']}")
    print(f"Value: {entity_a['value']} {statistic['unit']}")

    print(f"\nEntity B: {entity_b['name']}")
    print(f"Value: {entity_b['value']} {statistic['unit']}")

    print(f"\nCorrect answer: {comparison['correct_entity_name']}")

    print(f"Direction: {comparison['direction']}")


def main():

    print("Testing comparison generation...")

    test_comparison("higher")
    test_comparison("lower")

    print("\nAll tests completed!")


if __name__ == "__main__":
    main()
