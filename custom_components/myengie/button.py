"""Button platform for MyEngie integration — gas index submission."""

import logging

from homeassistant.components.button import ButtonEntity
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
    """Set up button entities for MyEngie."""
    coordinator = config_entry.runtime_data

    def build_place_entities(place_keys: list[str]) -> list[ButtonEntity]:
        return [
            MyEngieSubmitGasIndexButton(coordinator, config_entry, place_key)
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


class MyEngieSubmitGasIndexButton(CoordinatorEntity, ButtonEntity):
    """Button that submits the staged gas index to ENGIE."""

    _attr_has_entity_name = True
    _attr_translation_key = "gas_index_submit"
    _attr_icon = "mdi:send"

    def __init__(self, coordinator, config_entry, place_key: str):
        """Initialize the button entity."""
        super().__init__(coordinator)
        self.config_entry = config_entry
        self._place_key = place_key

        place_data = (coordinator.data or {}).get("places", {}).get(place_key, {})
        poc_number = place_data.get("poc_number", "")
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

        object_id = f"{DOMAIN}_{base_slug}_gas_index_submit"
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
    def available(self) -> bool:
        """Only available during the index submission window."""
        return super().available and bool(self.place_data.get("in_submission_window", False))

    async def async_press(self) -> None:
        """Submit the staged gas index (or current index as fallback)."""
        place_data = self.place_data
        poc_number = place_data.get("poc_number")
        installation_number = place_data.get("installation_number")

        if not poc_number or not installation_number:
            raise HomeAssistantError(
                "Cannot submit index: missing POC number or installation number"
            )

        # Read the value staged by the number entity, fall back to current index
        pending = self.coordinator.pending_gas_index
        index_value = pending.get(self._place_key)
        if index_value is None:
            index_value = int(place_data.get("gas_index", 0))

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

        # Clear the staged value and refresh so the number entity reverts
        # to showing the freshly confirmed index from the API.
        pending.pop(self._place_key, None)
        await coordinator.async_request_refresh()
