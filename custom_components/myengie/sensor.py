"""Sensor platform for MyEngie integration."""

import logging
from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors for MyEngie."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]

    entities = [
        # Primary sensors
        MyEngieBalanceSensor(coordinator, config_entry),
        MyEngieGasIndexSensor(coordinator, config_entry),
        MyEngieNotificationsSensor(coordinator, config_entry),
        
        # Consumption and invoice details
        MyEngieConsumptionDetailsSensor(coordinator, config_entry),
        MyEngieUpToDateStatusSensor(coordinator, config_entry),
        MyEngieInvoiceCountSensor(coordinator, config_entry),
        MyEngiePendingPaymentsSensor(coordinator, config_entry),
    ]

    async_add_entities(entities)


class MyEngieBalanceSensor(CoordinatorEntity, SensorEntity):
    """Sensor for MyEngie balance."""

    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_name = "MyEngie Balance"
    _attr_native_unit_of_measurement = "RON"
    _attr_icon = "mdi:currency-eur"

    def __init__(self, coordinator, config_entry):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.config_entry = config_entry
        self._attr_unique_id = (
            f"{DOMAIN}_{config_entry.entry_id}_balance"
        )

    @property
    def native_value(self):
        """Return the state."""
        if self.coordinator.data:
            return self.coordinator.data.get("balance", 0.0)
        return None

    @property
    def device_info(self):
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, self.config_entry.entry_id)},
            "name": "MyEngie",
            "manufacturer": "ENGIE Romania",
        }


class MyEngieGasIndexSensor(CoordinatorEntity, SensorEntity):
    """Sensor for MyEngie gas index."""

    _attr_name = "MyEngie Gas Index"
    _attr_icon = "mdi:gauge"
    _attr_unit_of_measurement = "kWh"

    def __init__(self, coordinator, config_entry):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.config_entry = config_entry
        self._attr_unique_id = (
            f"{DOMAIN}_{config_entry.entry_id}_gas_index"
        )

    @property
    def native_value(self):
        """Return the state."""
        if self.coordinator.data:
            index = self.coordinator.data.get("gas_index", 0)
            return int(index) if index else None
        return None

    @property
    def extra_state_attributes(self):
        """Return extra state attributes."""
        if self.coordinator.data:
            next_read = self.coordinator.data.get("next_read_dates")
            if next_read:
                return {
                    "next_read_start": next_read.get("startDate"),
                    "next_read_end": next_read.get("endDate"),
                }
        return None

    @property
    def device_info(self):
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, self.config_entry.entry_id)},
            "name": "MyEngie",
            "manufacturer": "ENGIE Romania",
        }


class MyEngieNotificationsSensor(CoordinatorEntity, SensorEntity):
    """Sensor for MyEngie unread notifications."""

    _attr_name = "MyEngie Unread Notifications"
    _attr_icon = "mdi:bell"
    _attr_device_class = SensorDeviceClass.ENUM

    def __init__(self, coordinator, config_entry):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.config_entry = config_entry
        self._attr_unique_id = (
            f"{DOMAIN}_{config_entry.entry_id}_notifications"
        )

    @property
    def native_value(self):
        """Return the state."""
        if self.coordinator.data:
            return self.coordinator.data.get("notifications", 0)
        return None

    @property
    def device_info(self):
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, self.config_entry.entry_id)},
            "name": "MyEngie",
            "manufacturer": "ENGIE Romania",
        }


class MyEngieConsumptionDetailsSensor(CoordinatorEntity, SensorEntity):
    """Sensor for consumption details and additional information."""

    _attr_name = "MyEngie Consumption Details"
    _attr_icon = "mdi:chart-line"

    def __init__(self, coordinator, config_entry):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.config_entry = config_entry
        self._attr_unique_id = (
            f"{DOMAIN}_{config_entry.entry_id}_consumption_details"
        )

    @property
    def native_value(self):
        """Return summary information."""
        if self.coordinator.data:
            gas_index = self.coordinator.data.get("gas_index", 0)
            balance = self.coordinator.data.get("balance", 0.0)
            return f"Index: {gas_index} | Balance: {balance:.2f} RON"
        return None

    @property
    def extra_state_attributes(self):
        """Return extra state attributes with detailed consumption info."""
        if not self.coordinator.data:
            return {}

        data = self.coordinator.data
        attributes = {
            "gas_index": data.get("gas_index", 0),
            "balance": data.get("balance", 0.0),
            "notifications": data.get("notifications", 0),
            "invoice_count": data.get("invoice_count", 0),
            "pending_payments": len(data.get("pending", [])),
            "is_up_to_date": data.get("is_up_to_date", True),
        }

        # Add next read dates if available
        next_read = data.get("next_read_dates")
        if next_read:
            attributes["next_read_start"] = next_read.get("startDate")
            attributes["next_read_end"] = next_read.get("endDate")

        return attributes

    @property
    def device_info(self):
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, self.config_entry.entry_id)},
            "name": "MyEngie",
            "manufacturer": "ENGIE Romania",
        }


class MyEngieUpToDateStatusSensor(CoordinatorEntity, SensorEntity):
    """Sensor for account status (up to date or not)."""

    _attr_name = "MyEngie Account Status"
    _attr_icon = "mdi:check-circle"

    def __init__(self, coordinator, config_entry):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.config_entry = config_entry
        self._attr_unique_id = (
            f"{DOMAIN}_{config_entry.entry_id}_account_status"
        )

    @property
    def native_value(self):
        """Return the state."""
        if self.coordinator.data:
            is_up_to_date = self.coordinator.data.get("is_up_to_date", True)
            return "Up to Date" if is_up_to_date else "Pending Payments"
        return None

    @property
    def device_info(self):
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, self.config_entry.entry_id)},
            "name": "MyEngie",
            "manufacturer": "ENGIE Romania",
        }


class MyEngieInvoiceCountSensor(CoordinatorEntity, SensorEntity):
    """Sensor for invoice count."""

    _attr_name = "MyEngie Invoice Count"
    _attr_icon = "mdi:file-document"

    def __init__(self, coordinator, config_entry):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.config_entry = config_entry
        self._attr_unique_id = (
            f"{DOMAIN}_{config_entry.entry_id}_invoice_count"
        )

    @property
    def native_value(self):
        """Return the state."""
        if self.coordinator.data:
            return self.coordinator.data.get("invoice_count", 0)
        return None

    @property
    def extra_state_attributes(self):
        """Return invoice details."""
        if not self.coordinator.data:
            return {}

        invoices = self.coordinator.data.get("invoices", [])
        if invoices:
            return {
                "invoices": [
                    {
                        "date": inv.get("date"),
                        "amount": inv.get("amount"),
                        "status": inv.get("status"),
                    }
                    for inv in invoices[:5]  # Last 5 invoices
                ]
            }
        return {}

    @property
    def device_info(self):
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, self.config_entry.entry_id)},
            "name": "MyEngie",
            "manufacturer": "ENGIE Romania",
        }


class MyEngiePendingPaymentsSensor(CoordinatorEntity, SensorEntity):
    """Sensor for pending payments."""

    _attr_name = "MyEngie Pending Payments"
    _attr_icon = "mdi:alert-circle"
    _attr_unit_of_measurement = "RON"

    def __init__(self, coordinator, config_entry):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.config_entry = config_entry
        self._attr_unique_id = (
            f"{DOMAIN}_{config_entry.entry_id}_pending_payments"
        )

    @property
    def native_value(self):
        """Return the state."""
        if self.coordinator.data:
            pending = self.coordinator.data.get("pending", [])
            if pending:
                # Sum all pending amounts
                total = sum(
                    float(p.get("amount", 0)) 
                    for p in pending
                )
                return total
            return 0.0
        return None

    @property
    def extra_state_attributes(self):
        """Return pending payment details."""
        if not self.coordinator.data:
            return {}

        pending = self.coordinator.data.get("pending", [])
        if pending:
            return {
                "pending_count": len(pending),
                "payments": [
                    {
                        "amount": p.get("amount"),
                        "due_date": p.get("due_date"),
                        "description": p.get("description"),
                    }
                    for p in pending[:5]  # First 5 pending
                ]
            }
        return {"pending_count": 0}

    @property
    def device_info(self):
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, self.config_entry.entry_id)},
            "name": "MyEngie",
            "manufacturer": "ENGIE Romania",
        }
