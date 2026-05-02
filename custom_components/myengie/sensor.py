"""Sensor platform for MyEngie integration."""

from __future__ import annotations

import calendar
from datetime import datetime, date, timedelta
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfVolume
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from .const import DOMAIN

CURRENCY_RON = "RON"


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _parse_date(value: Any) -> date | None:
    """Parse ISO (YYYY-MM-DD) or Romanian (DD.MM.YYYY) date strings."""
    if not value:
        return None
    try:
        s = str(value).strip()
        if len(s) >= 10 and s[4] == "-":
            return date.fromisoformat(s[:10])
        if "." in s:
            parts = s.split(".")
            if len(parts) == 3:
                return date(int(parts[2]), int(parts[1]), int(parts[0]))
    except (ValueError, TypeError):
        pass
    return None


def _to_dd_mm_yyyy(value: Any) -> str | None:
    """Format any parseable date as DD/MM/YYYY."""
    d = _parse_date(value)
    return d.strftime("%d/%m/%Y") if d is not None else None


def _days_until(value: Any) -> int | None:
    """Return days until the given date string."""
    d = _parse_date(value)
    return (d - date.today()).days if d is not None else None


def _parse_ron(value: Any) -> float | None:
    """Parse a RON amount string like '67,34' or '67.34' to float."""
    if value is None:
        return None
    try:
        return float(str(value).replace(",", "."))
    except (ValueError, TypeError):
        return None


def _extract_m3(entry: dict) -> float | None:
    """Try common field names to extract m³ from a consumption history entry."""
    for key in ("value", "consumption", "consum", "quantity", "index"):
        v = entry.get(key)
        if v is not None:
            try:
                return float(str(v).replace(",", "."))
            except (ValueError, TypeError):
                pass
    return None


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors for MyEngie."""
    coordinator = config_entry.runtime_data

    def build_place_entities(place_keys: list[str]) -> list[SensorEntity]:
        """Build all place-scoped entities for the provided place keys."""
        current_year = datetime.now().year
        entities: list[SensorEntity] = []

        for place_key in place_keys:
            entities.extend(
                [
                    # Billing
                    MyEngieBalanceSensor(coordinator, config_entry, place_key),
                    # Latest unpaid invoice (single sensor with attributes)
                    MyEngieUnpaidInvoiceSensor(coordinator, config_entry, place_key),
                    # Meter identifiers
                    MyEngieGasIndexSensor(coordinator, config_entry, place_key),
                    MyEngiePocNumberSensor(coordinator, config_entry, place_key),
                    MyEngiePodSensor(coordinator, config_entry, place_key),
                    MyEngieInstallationNumberSensor(coordinator, config_entry, place_key),
                    # Consumption history
                    MyEngieLastMonthConsumptionSensor(coordinator, config_entry, place_key),
                    MyEngieConsumptionHistoryYearSensor(
                        coordinator, config_entry, place_key, current_year
                    ),
                    MyEngieConsumptionHistoryYearSensor(
                        coordinator, config_entry, place_key, current_year - 1
                    ),
                    # Invoice history
                    MyEngieInvoiceHistoryYearSensor(
                        coordinator, config_entry, place_key, current_year
                    ),
                    MyEngieInvoiceHistoryYearSensor(
                        coordinator, config_entry, place_key, current_year - 1
                    ),
                ]
            )

        return entities

    place_keys = list((coordinator.data or {}).get("places", {}))
    known_place_keys = set(place_keys)

    entities = build_place_entities(place_keys)

    async_add_entities(entities)

    @callback
    def async_add_new_place_entities() -> None:
        """Add entities for places that appear after initial setup."""
        current_places = (coordinator.data or {}).get("places", {})
        new_place_keys = [
            place_key for place_key in current_places if place_key not in known_place_keys
        ]
        if not new_place_keys:
            return

        async_add_entities(build_place_entities(new_place_keys))
        known_place_keys.update(new_place_keys)

    config_entry.async_on_unload(
        coordinator.async_add_listener(async_add_new_place_entities)
    )


class MyEngieBaseSensor(CoordinatorEntity, SensorEntity):
    """Base sensor for shared behavior."""

    def __init__(self, coordinator, config_entry):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.config_entry = config_entry


class MyEngiePlaceSensor(MyEngieBaseSensor):
    """Base sensor for place-scoped entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, config_entry, place_key: str):
        """Initialize the place sensor."""
        super().__init__(coordinator, config_entry)
        self._place_key = place_key

    @property
    def place_data(self):
        """Return the current payload for this place."""
        if not self.coordinator.data:
            return {}
        return self.coordinator.data.get("places", {}).get(self._place_key, {})

    @property
    def device_info(self):
        """Return place-level device info."""
        place_data = self.place_data
        poc_number = place_data.get("poc_number", "")
        fallback_name = f"MyEngie {poc_number}" if poc_number else "MyEngie"

        return {
            "identifiers": {(DOMAIN, self.config_entry.entry_id, self._place_key)},
            "name": place_data.get("place_name", fallback_name),
            "manufacturer": "ENGIE Romania",
        }

    def _base_device_slug(self, place_data: dict, place_key: str) -> str:
        """Return the base slug used for IDs for a place."""
        place_name = str(place_data.get("place_name", "")).strip()
        poc_number = str(place_data.get("poc_number", "")).strip()

        if place_name and place_name.lower() not in {
            "myengie",
            f"myengie {poc_number}".lower(),
        }:
            base_name = place_name
        elif poc_number:
            base_name = poc_number
        else:
            base_name = place_key

        return slugify(base_name) or slugify(place_key) or place_key

    @property
    def device_name_slug(self) -> str:
        """Return the slug used as the device segment in IDs."""
        place_data = self.place_data
        base_slug = self._base_device_slug(place_data, self._place_key)
        current_places = (self.coordinator.data or {}).get("places", {})
        duplicates = [
            key
            for key, data in current_places.items()
            if key != self._place_key
            and self._base_device_slug(data, key) == base_slug
        ]
        if not duplicates:
            return base_slug

        poc_number = slugify(str(place_data.get("poc_number", "")))
        if poc_number:
            return f"{base_slug}_{poc_number}"
        return slugify(self._place_key) or base_slug

    def _set_sensor_ids(self, sensor_name: str) -> None:
        """Set unique and suggested IDs using integration_device_sensor format."""
        object_id = f"{DOMAIN}_{self.device_name_slug}_{sensor_name}"
        self._attr_unique_id = object_id
        self._attr_suggested_object_id = object_id


class MyEngieBalanceSensor(MyEngiePlaceSensor):
    """Sensor for MyEngie balance."""

    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_translation_key = "balance"
    _attr_native_unit_of_measurement = "RON"
    _attr_icon = "mdi:currency-eur"

    def __init__(self, coordinator, config_entry, place_key: str):
        """Initialize the sensor."""
        super().__init__(coordinator, config_entry, place_key)
        self._set_sensor_ids("balance")

    @property
    def native_value(self):
        """Return the state."""
        place_data = self.place_data
        if place_data:
            return place_data.get("balance", 0.0)
        return None


class MyEngieGasIndexSensor(MyEngiePlaceSensor):
    """Sensor for MyEngie gas index."""

    _attr_translation_key = "gas_index"
    _attr_icon = "mdi:gauge"
    _attr_native_unit_of_measurement = UnitOfVolume.CUBIC_METERS

    def __init__(self, coordinator, config_entry, place_key: str):
        """Initialize the sensor."""
        super().__init__(coordinator, config_entry, place_key)
        self._set_sensor_ids("gas_index")

    @property
    def native_value(self):
        """Return the state."""
        place_data = self.place_data
        if place_data:
            index = place_data.get("gas_index", 0)
            return int(index)
        return None

    @property
    def extra_state_attributes(self):
        """Return extra state attributes."""
        place_data = self.place_data
        if place_data:
            next_read = place_data.get("next_read_dates")
            if next_read:
                return {
                    "next_read_start": _to_dd_mm_yyyy(next_read.get("startDate")),
                    "next_read_end": _to_dd_mm_yyyy(next_read.get("endDate")),
                }
        return None


class MyEngieInvoiceHistoryYearSensor(MyEngiePlaceSensor):
    """Sensor for invoice history for a specific year."""

    _attr_icon = "mdi:receipt-text"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = "RON"

    def __init__(self, coordinator, config_entry, place_key: str, year: int):
        """Initialize the sensor."""
        super().__init__(coordinator, config_entry, place_key)
        self._year = year
        self._attr_translation_key = "invoice_history_year"
        self._attr_translation_placeholders = {"year": str(year)}
        self._set_sensor_ids(f"invoice_history_{year}")

    def _get_year_invoices(self):
        """Return invoices for this sensor's year (Jan 1 – Dec 31), sorted by date ascending."""
        history = self.place_data.get("invoice_history", [])
        year_str = str(self._year)
        filtered = [
            inv for inv in history
            if str(inv.get("invoiced_at", ""))[:4] == year_str
        ]
        return sorted(filtered, key=lambda inv: str(inv.get("invoiced_at", "")))

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
            date_str = _to_dd_mm_yyyy(inv.get("invoiced_at")) or inv.get("invoiced_at", "unknown")
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


# ------------------------------------------------------------------
# New sensors matching Hidroelectrica parity
# ------------------------------------------------------------------


class MyEngieUnpaidInvoiceSensor(MyEngiePlaceSensor):
    """Single sensor for the latest unpaid invoice; detail fields exposed as attributes."""

    _attr_translation_key = "unpaid_invoice"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = CURRENCY_RON
    _attr_state_class = SensorStateClass.TOTAL
    _attr_suggested_display_precision = 2
    _attr_icon = "mdi:file-document-alert"

    def __init__(self, coordinator, config_entry, place_key: str) -> None:
        super().__init__(coordinator, config_entry, place_key)
        self._set_sensor_ids("unpaid_invoice")

    def _unpaid_invoice(self) -> dict | None:
        """Return the first unpaid invoice entry, or None."""
        history = self.place_data.get("invoice_history_current", [])
        for inv in history:
            if inv.get("unpaid", 0) != 0:
                return inv
        return None

    @property
    def native_value(self) -> float | None:
        inv = self._unpaid_invoice()
        return _parse_ron(inv.get("total")) if inv else None

    @property
    def extra_state_attributes(self) -> dict:
        inv = self._unpaid_invoice()
        if not inv:
            return {"overdue": False}
        due_date_str = _to_dd_mm_yyyy(inv.get("due_date"))
        days = _days_until(inv.get("due_date"))
        overdue = days is not None and days < 0
        attrs: dict = {
            "due_date": due_date_str,
            "days_until_due": days,
            "overdue": overdue,
        }
        if inv.get("invoice_number") is not None:
            attrs["invoice_number"] = str(inv["invoice_number"])
        if inv.get("division"):
            attrs["division"] = inv["division"]
        return attrs


class MyEngiePocNumberSensor(MyEngiePlaceSensor):
    """Sensor for the Place of Consumption (POC) number."""

    _attr_translation_key = "poc_number"
    _attr_icon = "mdi:map-marker"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator, config_entry, place_key: str) -> None:
        super().__init__(coordinator, config_entry, place_key)
        self._set_sensor_ids("poc_number")

    @property
    def native_value(self) -> str | None:
        return self.place_data.get("poc_number") or None


class MyEngiePodSensor(MyEngiePlaceSensor):
    """Sensor for the Point of Delivery (POD) code."""

    _attr_translation_key = "pod"
    _attr_icon = "mdi:map-marker-check"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator, config_entry, place_key: str) -> None:
        super().__init__(coordinator, config_entry, place_key)
        self._set_sensor_ids("pod")

    @property
    def native_value(self) -> str | None:
        return self.place_data.get("pod") or None


class MyEngieInstallationNumberSensor(MyEngiePlaceSensor):
    """Sensor for the installation / meter number."""

    _attr_translation_key = "installation_number"
    _attr_icon = "mdi:counter"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator, config_entry, place_key: str) -> None:
        super().__init__(coordinator, config_entry, place_key)
        self._set_sensor_ids("installation_number")

    @property
    def native_value(self) -> str | None:
        return self.place_data.get("installation_number") or None


class MyEngieLastMonthConsumptionSensor(MyEngiePlaceSensor):
    """Sensor for the previous month's gas consumption in m³."""

    _attr_translation_key = "last_month_m3"
    _attr_device_class = SensorDeviceClass.GAS
    _attr_native_unit_of_measurement = UnitOfVolume.CUBIC_METERS
    _attr_state_class = SensorStateClass.TOTAL
    _attr_suggested_display_precision = 1
    _attr_icon = "mdi:fire"

    _PCS = 10.861  # Puterea calorifică superioară (kWh/m³)

    def __init__(self, coordinator, config_entry, place_key: str) -> None:
        super().__init__(coordinator, config_entry, place_key)
        self._set_sensor_ids("last_month_m3")

    def _last_month_entry(self) -> dict | None:
        """Return the index/consumption entry for last calendar month, or None."""
        today = date.today()
        last_month = today.replace(day=1) - timedelta(days=1)
        year_str = str(last_month.year)
        month_str = f"{last_month.month:02d}"

        history = self.place_data.get("index_history", [])
        for entry in history:
            val = str(entry.get("invoiced_at", ""))
            if val[:4] == year_str and val[5:7] == month_str:
                return entry

        # Fallback: last entry in history
        return history[-1] if history else None

    @property
    def native_value(self) -> float | None:
        entry = self._last_month_entry()
        if entry is None:
            return None
        raw = entry.get("consum_gaz")
        if raw is None:
            return None
        try:
            kwh = float(str(raw).replace(",", "."))
            return round(kwh / self._PCS, 1)
        except (ValueError, TypeError):
            return None

    @property
    def extra_state_attributes(self) -> dict:
        entry = self._last_month_entry()
        if not entry:
            return {}
        raw = entry.get("consum_gaz")
        return {
            "consum_gaz_kwh": raw,
            "pcs": self._PCS,
            **{k: v for k, v in entry.items() if k != "consum_gaz"},
        }


class MyEngieConsumptionHistoryYearSensor(MyEngiePlaceSensor):
    """Sensor for yearly gas consumption history in m³, with per-month attributes."""

    _attr_device_class = SensorDeviceClass.GAS
    _attr_native_unit_of_measurement = UnitOfVolume.CUBIC_METERS
    _attr_state_class = SensorStateClass.TOTAL
    _attr_suggested_display_precision = 1
    _attr_icon = "mdi:fire"

    _PCS = 10.861  # Puterea calorifică superioară (kWh/m³)

    def __init__(self, coordinator, config_entry, place_key: str, year: int) -> None:
        super().__init__(coordinator, config_entry, place_key)
        self._year = year
        self._attr_translation_key = "consumption_history_year"
        self._attr_translation_placeholders = {"year": str(year)}
        self._set_sensor_ids(f"consumption_history_{year}")

    def _get_year_entries(self) -> list[dict]:
        """Return index_history entries for this year, sorted by month."""
        history = self.place_data.get("index_history", [])
        year_str = str(self._year)
        return sorted(
            [e for e in history if str(e.get("invoiced_at", ""))[:4] == year_str],
            key=lambda e: str(e.get("invoiced_at", "")),
        )

    def _to_m3(self, entry: dict) -> float | None:
        raw = entry.get("consum_gaz")
        if raw is None:
            return None
        try:
            return round(float(str(raw).replace(",", ".")) / self._PCS, 1)
        except (ValueError, TypeError):
            return None

    @property
    def native_value(self) -> float | None:
        entries = self._get_year_entries()
        if not entries:
            return None
        total = sum(self._to_m3(e) or 0.0 for e in entries)
        return round(total, 1)

    @property
    def extra_state_attributes(self) -> dict:
        entries = self._get_year_entries()
        attrs: dict = {}
        total = 0.0
        for entry in entries:
            val = str(entry.get("invoiced_at", ""))
            try:
                month_num = int(val[5:7])
                month_name = calendar.month_name[month_num]
            except (ValueError, IndexError):
                month_name = val
            m3 = self._to_m3(entry)
            if m3 is not None:
                attrs[month_name] = m3
                total += m3
        count = len(entries)
        days_in_year = 366 if calendar.isleap(self._year) else 365
        attrs["total_m3"] = round(total, 1)
        attrs["average_monthly_m3"] = round(total / count, 1) if count else 0.0
        attrs["average_daily_m3"] = round(total / days_in_year, 2)
        return attrs


