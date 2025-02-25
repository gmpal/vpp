class Battery:
    """
    A simple battery model that tracks state-of-charge (SOC),
    enforces capacity limits, and supports charging/discharging.
    """

    def __init__(
        self,
        battery_id: str,
        capacity_kWh=10.0,
        current_soc_kWh=5.0,
        max_charge_kW=2.0,
        max_discharge_kW=2.0,
        round_trip_efficiency=1.0,
    ):
        """
        Initialize a new battery.
        :param battery_id:        Unique identifier for the battery.
        :param capacity_kWh:      Max energy the battery can store (in kWh).
        :param current_soc_kWh:   Initial State of Charge (in kWh).
        :param max_charge_kW:     Max charging power (kW).
        :param max_discharge_kW:  Max discharging power (kW).
        :param round_trip_efficiency: Fraction of energy retained from charge to discharge (0-1).
        """
        self.battery_id = battery_id
        self.capacity_kWh = capacity_kWh
        self.current_soc_kWh = current_soc_kWh
        self.max_charge_kW = max_charge_kW
        self.max_discharge_kW = max_discharge_kW
        self.round_trip_efficiency = round_trip_efficiency  # e.g., 0.9 for 90%

        # Enforce initial SOC within valid range
        if self.current_soc_kWh < 0:
            self.current_soc_kWh = 0
        elif self.current_soc_kWh > self.capacity_kWh:
            self.current_soc_kWh = self.capacity_kWh

    def charge(self, power_kW, duration_h=1.0):
        """
        Charge the battery at 'power_kW' for 'duration_h' hours.
        Respect max charge rate & capacity limit.
        Returns actual power used for charging (kW) in that interval.
        """
        # Limit power to max charge rate
        power_kW = min(power_kW, self.max_charge_kW)
        if power_kW < 0:
            power_kW = 0  # can't have negative charging

        # Energy to add
        energy_to_add_kWh = (
            power_kW * duration_h * self.round_trip_efficiency
        )  # apply round-trip efficiency on input

        # Limit by available capacity
        available_capacity_kWh = self.capacity_kWh - self.current_soc_kWh
        actual_energy_added_kWh = min(energy_to_add_kWh, available_capacity_kWh)

        # Update SOC
        self.current_soc_kWh += actual_energy_added_kWh

        # Actual power used might be lower if battery is near full
        actual_power_kW = (
            actual_energy_added_kWh / duration_h
        ) / self.round_trip_efficiency

        return actual_power_kW

    def discharge(self, power_kW, duration_h=1.0):
        """
        Discharge the battery at 'power_kW' for 'duration_h' hours.
        Respect max discharge rate & SOC limit.
        Returns actual power provided from battery (kW) in that interval.
        """
        # Limit power to max discharge rate
        power_kW = min(power_kW, self.max_discharge_kW)
        if power_kW < 0:
            power_kW = 0  # can't have negative discharge

        # Energy to remove (account for efficiency)
        # For discharging, the lost energy from the battery's perspective is more
        # than delivered if efficiency < 1.
        # We'll keep it simple by applying efficiency on the delivered energy.
        energy_requested_kWh = power_kW * duration_h
        # If the battery only has X kWh left, you can't deliver more than that
        available_energy_kWh = self.current_soc_kWh
        # With round-trip efficiency for discharge, effectively the battery must supply
        # more energy than what's delivered if eta < 1.
        # Here we keep the simpler approach: "actual delivered" is limited by battery's SOC.
        actual_energy_delivered_kWh = min(
            energy_requested_kWh, available_energy_kWh * self.round_trip_efficiency
        )

        # Update SOC (battery sees more energy drained if efficiency < 1)
        self.current_soc_kWh -= actual_energy_delivered_kWh / self.round_trip_efficiency

        # Actual power delivered from battery
        actual_power_kW = actual_energy_delivered_kWh / duration_h

        return actual_power_kW

    def __repr__(self):
        return (
            f"Battery("
            f"SOC={self.current_soc_kWh:.2f} kWh / {self.capacity_kWh} kWh, "
            f"max_charge={self.max_charge_kW} kW, "
            f"max_discharge={self.max_discharge_kW} kW, "
            f"eta={self.round_trip_efficiency})"
        )
