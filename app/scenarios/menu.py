from app.scenarios.registry import ScenarioContext, get_registered_scenarios


def show_main_menu(context: ScenarioContext) -> None:
    while True:
        scenarios = get_registered_scenarios()

        print("\n=== Scenario Menu ===")
        for key, scenario in scenarios.items():
            print(f"{key}. {scenario.label}")
        print("0. Exit")

        choice = input("Choose an option: ").strip()

        if choice == "0":
            print("Bye.")
            return

        selected = scenarios.get(choice)
        if not selected:
            print("Invalid choice. Please try again.")
            continue

        selected.handler(context)