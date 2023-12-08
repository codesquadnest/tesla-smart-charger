"""
Energy Monitor Controller

This controller is responsible for monitoring the energy usage of the house
to determine if the power limit can be increased or decreased.

The controller is implemented as an abstract class that defines the interface
for the controller. This allows for different implementations of the controller
to be used.
"""

from abc import ABC, abstractmethod


class EnergyMonitorController(ABC):
    """
    Abstract class that defines the interface for the controller
    """

    @abstractmethod
    def get_state(self: object) -> str:
        """
        Returns the current state of the controller
        """
        pass

    @abstractmethod
    def set_state(self: object, state: str) -> None:
        """
        Sets the current state of the controller
        """
        pass

    @abstractmethod
    def get_consumption(self: object) -> float:
        """
        Returns the current consumption of the house
        """
        pass


"""
Energy Monitor Controller Factory
"""
def create_energy_monitor_controller(
    implementation_type: str, host: str
) -> EnergyMonitorController:
    """
    Factory function to create instances of EnergyMonitorController based on the
    implementation_type
    """
    import tesla_smart_charger.controllers.shelly_em_controller as shelly_em_controller

    if implementation_type == "shelly_em":
        return shelly_em_controller.ShellyEMController(host)
    else:
        raise ValueError("Invalid implementation type")
