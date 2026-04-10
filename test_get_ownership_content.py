import argparse
import importlib.util
from pathlib import Path


SOURCE_PATH = Path(__file__).with_name("Source Code.pyw")


def load_source_module():
    spec = importlib.util.spec_from_file_location("v3mt_source", SOURCE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load source module from {SOURCE_PATH}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_logic(module, economic_law):
    class OwnershipTestLogic(module.Vic3Logic):
        def load_country_history_details(self, tag):
            return {
                "gov_type": "monarchy",
                "laws": [economic_law] if economic_law else [],
                "ruler": {"first": "", "last": "", "ig": "", "ideology": ""},
            }

    return OwnershipTestLogic(lambda *args, **kwargs: None)


def main():
    parser = argparse.ArgumentParser(description="Test get_ownership_content() output.")
    parser.add_argument("--building-type", default="building_tooling_workshops")
    parser.add_argument("--owner-tag", default="USA")
    parser.add_argument("--level", type=int, default=5)
    parser.add_argument("--state-name", default="STATE_TEST")
    parser.add_argument(
        "--law",
        default="law_interventionism",
        help="Economic law to simulate. Use empty string to test fallback behavior.",
    )
    parser.add_argument(
        "--all-laws",
        action="store_true",
        help="Print outputs for all supported economic laws plus the fallback case.",
    )
    args = parser.parse_args()

    module = load_source_module()

    if args.all_laws:
        laws_to_test = [
            "law_command_economy",
            "law_traditionalism",
            "law_agrarianism",
            "law_interventionism",
            "law_laissez_faire",
            "",
        ]
    else:
        laws_to_test = [args.law]

    for index, law in enumerate(laws_to_test):
        logic = build_logic(module, law)
        output = logic.get_ownership_content(
            args.building_type,
            args.owner_tag,
            args.level,
            args.state_name,
        )

        label = law if law else "fallback/no economic law"
        if index:
            print("\n" + ("-" * 60))
        print(f"Law: {label}")
        print(output)


if __name__ == "__main__":
    main()
