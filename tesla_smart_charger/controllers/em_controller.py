"""Energy Monitor Controller.

This controller is responsible for monitoring the energy usage of the house
to determine if the power limit can be increased or decreased.

The controller is implemented as an abstract class that defines the interface
for the controller. This allows for different implementations of the controller
to be used.
"""

from abc import ABC, abstractmethod


class EnergyMonitorController(ABC):
    """Abstract class that defines the interface for the controller."""

    @abstractmethod
    def get_state(self: object) -> str:
        """Return the current state of the controller."""

    @abstractmethod
    def set_state(self: object, state: str) -> None:
        """Set the current state of the controller."""

    @abstractmethod
    def get_consumption(self: object) -> float:
        """Return the current consumption of the house."""


"""Energy Monitor Controller Factory."""


def create_energy_monitor_controller(
    implementation_type: str,
    host: str,
) -> EnergyMonitorController:
    """Create instances of EnergyMonitorController based on the implementation_type."""
    from tesla_smart_charger.controllers import shelly_em_controller

    if implementation_type == "shelly_em":
        return shelly_em_controller.ShellyEMController(host)

    msg = f"Invalid implementation type: {implementation_type}"
    raise ValueError(msg)
