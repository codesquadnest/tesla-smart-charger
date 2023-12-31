"""Utility functions for tesla_smart_charger."""


def show_vehicles(vehicles: dict) -> None:
    """
    Show the vehicles.

    Args:
    ----
        vehicles (dict): The vehicles.

    """
    # Print the vehicles
    for vehicle in vehicles:
        print(
            f"{vehicle['id']:<10} - {vehicle['display_name']} "
            f"- VIN - {vehicle['vin']:<30}",
        )
        print("-" * 60)
