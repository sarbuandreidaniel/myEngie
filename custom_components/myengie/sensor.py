"""Sensor platform for MyEngie integration."""

import calendar
import logging
from datetime import datetime
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
        
        # Invoice history and details
        MyEngieLatestInvoiceSensor(coordinator, config_entry),
        MyEngieInvoiceHistoryYearSensor(coordinator, config_entry, datetime.now().year),
        MyEngieInvoiceHistoryYearSensor(coordinator, config_entry, datetime.now().year - 1),
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
            "name": self.coordinator.data.get("place_name", "MyEngie") if self.coordinator.data else "MyEngie",
            "manufacturer": "ENGIE Romania",
        }


class MyEngieGasIndexSensor(CoordinatorEntity, SensorEntity):
    """Sensor for MyEngie gas index."""

    _attr_name = "MyEngie Gas Index"
    _attr_icon = "mdi:gauge"
    _attr_native_unit_of_measurement = "m³"

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
            return int(index)
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
            "name": self.coordinator.data.get("place_name", "MyEngie") if self.coordinator.data else "MyEngie",
            "manufacturer": "ENGIE Romania",
        }


class MyEngieNotificationsSensor(CoordinatorEntity, SensorEntity):
    """Sensor for MyEngie unread notifications."""

    _attr_name = "MyEngie Unread Notifications"
    _attr_icon = "mdi:bell"

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
            "name": self.coordinator.data.get("place_name", "MyEngie") if self.coordinator.data else "MyEngie",
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

        # Add consumption history if available
        index_history = data.get("index_history", [])
        if index_history:
            attributes["consumption_history"] = index_history

        return attributes

    @property
    def device_info(self):
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, self.config_entry.entry_id)},
            "name": self.coordinator.data.get("place_name", "MyEngie") if self.coordinator.data else "MyEngie",
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
            "name": self.coordinator.data.get("place_name", "MyEngie") if self.coordinator.data else "MyEngie",
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
            "name": self.coordinator.data.get("place_name", "MyEngie") if self.coordinator.data else "MyEngie",
            "manufacturer": "ENGIE Romania",
        }


class MyEngiePendingPaymentsSensor(CoordinatorEntity, SensorEntity):
    """Sensor for pending payments."""

    _attr_name = "MyEngie Pending Payments"
    _attr_icon = "mdi:alert-circle"
    _attr_native_unit_of_measurement = "RON"

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
            "name": self.coordinator.data.get("place_name", "MyEngie") if self.coordinator.data else "MyEngie",
            "manufacturer": "ENGIE Romania",
        }


class MyEngieLatestInvoiceSensor(CoordinatorEntity, SensorEntity):
    """Sensor for latest invoice details."""

    _attr_name = "MyEngie Latest Invoice"
    _attr_icon = "mdi:file-invoice"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = "RON"

    def __init__(self, coordinator, config_entry):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.config_entry = config_entry
        self._attr_unique_id = (
            f"{DOMAIN}_{config_entry.entry_id}_latest_invoice"
        )

    @property
    def native_value(self):
        """Return the latest invoice amount."""
        if self.coordinator.data:
            history = self.coordinator.data.get("invoice_history", [])
            if history:
                amount = history[0].get("total")
                if amount:
                    try:
                        return float(str(amount).replace(",", "."))
                    except (ValueError, TypeError):
                        return None
        return None

    @property
    def extra_state_attributes(self):
        """Return latest invoice details."""
        if not self.coordinator.data:
            return {}

        history = self.coordinator.data.get("invoice_history", [])
        if history:
            latest = history[0]
            return {
                "invoice_number": latest.get("invoice_number"),
                "date": latest.get("invoiced_at"),
                "due_date": latest.get("due_date"),
                "amount": latest.get("total"),
                "paid": latest.get("unpaid", 0) == 0,
                "division": latest.get("division"),
                "download_url": latest.get("download_url"),
            }
        return {}

    @property
    def device_info(self):
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, self.config_entry.entry_id)},
            "name": self.coordinator.data.get("place_name", "MyEngie") if self.coordinator.data else "MyEngie",
            "manufacturer": "ENGIE Romania",
        }


class MyEngieInvoiceHistoryYearSensor(CoordinatorEntity, SensorEntity):
    """Sensor for invoice history for a specific year."""

    _attr_icon = "mdi:file-document-multiple"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = "RON"

    def __init__(self, coordinator, config_entry, year: int):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.config_entry = config_entry
        self._year = year
        self._attr_name = f"MyEngie Invoice History {year}"
        self._attr_unique_id = (
            f"{DOMAIN}_{config_entry.entry_id}_invoice_history_{year}"
        )

    def _get_year_invoices(self):
        """Return invoices filtered for this sensor's year."""
        if not self.coordinator.data:
            return []
        history = self.coordinator.data.get("invoice_history", [])
        return [
            inv for inv in history
            if str(inv.get("invoiced_at", ""))[:4] == str(self._year)
        ]

    @property
    def native_value(self):
        """Return total amount paid for the year."""
        invoices = self._get_year_invoices()
        if not invoices:
            return None
        try:
            total = sum(
                float(str(inv.get("total", 0)).replace(",", "."))
                for inv in invoices
                if inv.get("total")
            )
            return round(total, 2)
        except (ValueError, TypeError):
            return None

    @property
    def extra_state_attributes(self):
        """Return per-invoice attributes and yearly summary."""
        invoices = self._get_year_invoices()
        if not invoices:
            return {
                "total_invoices": 0,
                "total_amount_paid": 0.0,
                "average_monthly_amount": 0.0,
                "average_daily_amount": 0.0,
            }

        attributes = {}
        total_amount = 0.0

        for idx, inv in enumerate(invoices, 1):
            date_str = inv.get("invoiced_at", "unknown")
            try:
                amount = round(float(str(inv.get("total", 0)).replace(",", ".")), 2)
            except (ValueError, TypeError):
                amount = 0.0
            total_amount += amount
            attributes[f"Invoice {idx} {date_str}"] = amount

        invoice_count = len(invoices)
        days_in_year = 366 if calendar.isleap(self._year) else 365

        attributes["total_invoices"] = invoice_count
        attributes["total_amount_paid"] = round(total_amount, 2)
        attributes["average_monthly_amount"] = (
            round(total_amount / invoice_count, 2) if invoice_count else 0.0
        )
        attributes["average_daily_amount"] = round(total_amount / days_in_year, 2)

        return attributes

    @property
    def device_info(self):
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, self.config_entry.entry_id)},
            "name": self.coordinator.data.get("place_name", "MyEngie") if self.coordinator.data else "MyEngie",
            "manufacturer": "ENGIE Romania",
        }
