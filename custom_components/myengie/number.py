"""Number platform for MyEngie integration — gas index submission."""

import logging

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up number entities for MyEngie."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]

    def build_place_entities(place_keys: list[str]) -> list[NumberEntity]:
        return [
            MyEngieGasIndexNumber(coordinator, config_entry, place_key)
            for place_key in place_keys
        ]

    place_keys = list((coordinator.data or {}).get("places", {}))
    known_place_keys = set(place_keys)

    async_add_entities(build_place_entities(place_keys))

    @callback
    def async_add_new_place_entities() -> None:
        current_places = (coordinator.data or {}).get("places", {})
        new_keys = [k for k in current_places if k not in known_place_keys]
        if not new_keys:
            return
        async_add_entities(build_place_entities(new_keys))
        known_place_keys.update(new_keys)

    config_entry.async_on_unload(
        coordinator.async_add_listener(async_add_new_place_entities)
    )


class MyEngieGasIndexNumber(CoordinatorEntity, NumberEntity):
    """Writable number entity for submitting the gas meter index."""

    _attr_has_entity_name = True
    _attr_name = "Submit Gas Index"
    _attr_icon = "mdi:counter"
    _attr_native_min_value = 0
    _attr_native_max_value = 999999
    _attr_native_step = 1
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator, config_entry, place_key: str):
        """Initialize the number entity."""
        super().__init__(coordinator)
        self.config_entry = config_entry
        self._place_key = place_key
        self._pending_value: float | None = None

        place_data = (coordinator.data or {}).get("places", {}).get(place_key, {})
        poc_number = place_data.get("poc_number", "")
        # Reuse the same slug logic as sensors for consistent entity IDs
        place_name = str(place_data.get("place_name", "")).strip()
        if place_name and place_name.lower() not in {
            "myengie",
            f"myengie {poc_number}".lower(),
        }:
            base_slug = slugify(place_name)
        elif poc_number:
            base_slug = slugify(poc_number)
        else:
            base_slug = slugify(place_key) or place_key

        object_id = f"{DOMAIN}_{base_slug}_submit_gas_index"
        self._attr_unique_id = object_id
        self._attr_suggested_object_id = object_id

    @property
    def place_data(self) -> dict:
        """Return coordinator data for this place."""
        if not self.coordinator.data:
            return {}
        return self.coordinator.data.get("places", {}).get(self._place_key, {})

    @property
    def device_info(self):
        """Return device info — same device as the sensors."""
        place_data = self.place_data
        poc_number = place_data.get("poc_number", "")
        fallback_name = f"MyEngie {poc_number}" if poc_number else "MyEngie"
        return {
            "identifiers": {(DOMAIN, self.config_entry.entry_id, self._place_key)},
            "name": place_data.get("place_name", fallback_name),
            "manufacturer": "ENGIE Romania",
        }

    @property
    def native_value(self) -> float | None:
        """Return pending input value, or last known index as default."""
        if self._pending_value is not None:
            return self._pending_value
        index = self.place_data.get("gas_index", 0)
        try:
            return float(index)
        except (TypeError, ValueError):
            return None

    @property
    def available(self) -> bool:
        """Only available when the API reports index submission is open."""
        return bool(self.place_data.get("permite_index", False))

    @property
    def extra_state_attributes(self) -> dict:
        """Expose next read window and installation number."""
        place_data = self.place_data
        attrs: dict = {}
        next_read = place_data.get("next_read_dates")
        if next_read:
            attrs["next_read_start"] = next_read.get("startDate")
            attrs["next_read_end"] = next_read.get("endDate")
        installation = place_data.get("installation_number")
        if installation:
            attrs["installation_number"] = installation
        return attrs

    async def async_set_native_value(self, value: float) -> None:
        """Submit the gas index to the ENGIE API."""
        place_data = self.place_data
        poc_number = place_data.get("poc_number")
        installation_number = place_data.get("installation_number")

        if not poc_number or not installation_number:
            raise HomeAssistantError(
                "Cannot submit index: missing POC number or installation number"
            )

        index_value = int(value)
        coordinator = self.coordinator
        api = coordinator.api

        if not api:
            raise HomeAssistantError("Cannot submit index: API not initialized")

        _LOGGER.debug(
            "Submitting gas index %s for POC %s / installation %s",
            index_value,
            poc_number,
            installation_number,
        )

        result = await api.submit_index(
            poc_number=poc_number,
            installation_number=installation_number,
            index_value=index_value,
        )

        if result.get("error") or not result.get("data", {}).get("status"):
            _LOGGER.error("Gas index submission failed: %s", result)
            raise HomeAssistantError(
                f"Gas index submission failed: {result.get('description', result)}"
            )

        _LOGGER.info(
            "Gas index %s submitted successfully for POC %s",
            index_value,
            poc_number,
        )

        # Store the submitted value so the entity reflects it immediately,
        # then schedule a coordinator refresh to sync fresh API state.
        self._pending_value = float(value)
        self.async_write_ha_state()
        await coordinator.async_request_refresh()
        self._pending_value = None
