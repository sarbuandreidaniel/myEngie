"""Custom integration for MyEngie Romania."""

import logging
from datetime import date, timedelta
import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import MyEngieAPI
from .auth import Auth0Manager
from .const import DEFAULT_UPDATE_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the MyEngie component."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up MyEngie from a config entry."""
    _LOGGER.debug("Setting up MyEngie config entry: %s", entry.title)

    username = entry.data.get(CONF_USERNAME)
    password = entry.data.get(CONF_PASSWORD)

    # Create coordinator
    coordinator = MyEngieDataUpdateCoordinator(
        hass,
        username=username,
        password=password,
    )

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
    }

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a MyEngie config entry."""
    _LOGGER.debug("Unloading MyEngie config entry: %s", entry.title)

    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(
        entry, PLATFORMS
    )

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class MyEngieDataUpdateCoordinator(DataUpdateCoordinator):
    """Data update coordinator for MyEngie."""

    def __init__(
        self,
        hass: HomeAssistant,
        username: str,
        password: str,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_UPDATE_INTERVAL),
        )
        self.username = username
        self.password = password
        self.session: aiohttp.ClientSession | None = None
        self.auth_manager: Auth0Manager | None = None
        self.api: MyEngieAPI | None = None
        self.contract_accounts: list[str] = []
        self.provider_account_id: str = ""
        self.poc_number: str = ""
        self.installation_number: str = ""
        self.pod: str = ""
        self._is_initialized = False

    async def _async_authenticate(self) -> bool:
        """Authenticate with MyEngie API."""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()

            if not self.auth_manager:
                self.auth_manager = Auth0Manager()

            success = await self.auth_manager.authenticate(
                self.session, self.username, self.password
            )

            if success:
                self.api = MyEngieAPI(self.session, self.auth_manager)
                self._is_initialized = True
                _LOGGER.debug("MyEngie authentication successful")
                return True
            else:
                _LOGGER.error("Failed to authenticate with MyEngie")
                return False

        except Exception as err:
            _LOGGER.error("Authentication error: %s", err)
            return False

    def _extract_places_of_consumption(self, data: dict | None) -> None:
        """Extract account identifiers from placesofconsumption response data.

        Authoritative source for: pa (provider_account_id), poc_number,
        and contract_account_numbers. All come exclusively from this endpoint.
        """
        if not isinstance(data, dict):
            return
        places = data.get("places_of_consumption", [])
        if not isinstance(places, list):
            return
        for place in places:
            if not isinstance(place, dict):
                continue
            if place.get("pa") and not self.provider_account_id:
                self.provider_account_id = str(place["pa"])
                _LOGGER.debug("Extracted pa: %s", self.provider_account_id)
            if place.get("poc_number") and not self.poc_number:
                self.poc_number = str(place["poc_number"])
                _LOGGER.debug("Extracted poc_number: %s", self.poc_number)
            for contract in place.get("cont_contract", []):
                if isinstance(contract, dict) and contract.get("contract_account_number"):
                    num = str(contract["contract_account_number"])
                    if num not in self.contract_accounts:
                        self.contract_accounts.append(num)
                        _LOGGER.debug("Extracted contract_account: %s", num)
        self.contract_accounts = list(dict.fromkeys(self.contract_accounts))

    async def _async_update_data(self) -> dict:
        """Fetch data from MyEngie API."""
        try:
            # Authenticate if not already done
            if not self._is_initialized:
                if not await self._async_authenticate():
                    raise UpdateFailed("Failed to authenticate with MyEngie")

            if not self.api:
                raise UpdateFailed("API not initialized")

            _LOGGER.debug("Fetching data from MyEngie API")

            # App status — check for maintenance or invalid token, no account data here
            status = await self.api.get_app_status()
            if status.get("reason") == "invalid_refresh_token":
                _LOGGER.warning("Refresh token invalid, clearing auth and re-authenticating")
                self._is_initialized = False
                self.auth_manager = None
                if not await self._async_authenticate():
                    raise UpdateFailed("Failed to re-authenticate after token invalidation")
                status = await self.api.get_app_status()
            if status.get("error"):
                _LOGGER.warning("App status check failed: %s", status)

            # Places of consumption — authoritative source for pa, poc_number, contract_accounts
            placesofconsumption = await self.api.get_placesofconsumption()
            if not placesofconsumption.get("error"):
                self._extract_places_of_consumption(placesofconsumption.get("data"))
            else:
                _LOGGER.warning("placesofconsumption failed: %s", placesofconsumption)

            # Notifications count
            notification_count = 0
            notifications = await self.api.get_unread_notifications()
            if not notifications.get("error"):
                try:
                    notif_data = notifications.get("data", {})
                    if isinstance(notif_data, dict):
                        notification_count = int(notif_data.get("unreadMessages", 0))
                    else:
                        notification_count = int(notif_data)
                except (ValueError, TypeError):
                    notification_count = 0

            # Balance and invoices
            total_balance = "0.00"
            invoices = []
            pending = []
            if self.contract_accounts:
                balance_details = await self.api.get_balance_details(self.contract_accounts)
                if not balance_details.get("error"):
                    bd = balance_details.get("data", {})
                    total_balance = bd.get("total", "0.00")
                    invoices = bd.get("invoices", [])
                    pending = bd.get("pending", [])
            else:
                _LOGGER.warning("No contract accounts found, skipping balance fetch")

            # Index data — installation_number and pod are discovered from the response
            gas_index = None
            next_read_dates = None
            index_history = []
            if self.poc_number and self.provider_account_id:
                try:
                    index_data = await self.api.get_index_data(
                        poc_number=self.poc_number,
                        division="gaz",
                        pa=self.provider_account_id,
                        installation_number=self.installation_number or None,
                    )
                    if not index_data.get("error"):
                        installations_data = index_data.get("data", [])
                        if installations_data:
                            first_inst = installations_data[0].get("installations", [])
                            if first_inst:
                                inst = first_inst[0]
                                if inst.get("installation_number") and not self.installation_number:
                                    self.installation_number = str(inst["installation_number"])
                                    _LOGGER.debug("Discovered installation_number: %s", self.installation_number)
                                if inst.get("pod") and not self.pod:
                                    self.pod = str(inst["pod"])
                                    _LOGGER.debug("Discovered pod: %s", self.pod)
                                gas_index = inst.get("last_index", 0)
                                next_read_dates = inst.get("next_read_dates")
                    else:
                        _LOGGER.warning("Index data fetch failed: %s", index_data)
                except Exception as err:
                    _LOGGER.debug("Could not fetch index data: %s", err)

                # Consumption history (12 months)
                try:
                    end_date = date.today().isoformat()
                    start_date = (date.today() - timedelta(days=365)).isoformat()
                    consumption = await self.api.get_index_consumption(
                        poc_number=self.poc_number,
                        pa=self.provider_account_id,
                        start_date=start_date,
                        end_date=end_date,
                    )
                    if not consumption.get("error"):
                        index_history = consumption.get("data", [])
                except Exception as err:
                    _LOGGER.debug("Could not fetch consumption history: %s", err)
            else:
                _LOGGER.warning(
                    "Index fetch skipped - missing poc=%s or pa=%s",
                    self.poc_number,
                    self.provider_account_id,
                )

            # Balance widget
            balance_details_data = {}
            if self.contract_accounts:
                balance_widget = await self.api.get_balance_widget(self.contract_accounts)
                if not balance_widget.get("error"):
                    balance_details_data = balance_widget.get("data", {})

            # Notifications banner
            banners = []
            if self.poc_number and self.provider_account_id:
                try:
                    banner_data = await self.api.get_notifications_banner(
                        poc_number=self.poc_number,
                        pa=self.provider_account_id,
                    )
                    if not banner_data.get("error"):
                        banners = [banner_data.get("data", {})]
                except Exception as err:
                    _LOGGER.debug("Could not fetch banners: %s", err)
            else:
                _LOGGER.warning(
                    "Banner fetch skipped - missing poc=%s or pa=%s",
                    self.poc_number,
                    self.provider_account_id,
                )

            # Compile data
            data = {
                "balance": float(total_balance.replace(",", ".")),
                "gas_index": gas_index or 0,
                "notifications": notification_count,
                "invoices": invoices,
                "pending": pending,
                "next_read_dates": next_read_dates,
                "balance_details": balance_details_data,
                "banners": banners,
                "index_history": index_history,
                "is_up_to_date": len(pending) == 0,
                "invoice_count": len(invoices),
            }

            _LOGGER.debug("Successfully fetched MyEngie data")
            return data

        except UpdateFailed:
            raise
        except Exception as err:
            _LOGGER.error("Error fetching MyEngie data: %s", err)
            raise UpdateFailed(f"Error fetching MyEngie data: {err}")

    async def async_shutdown(self) -> None:
        """Cleanup on shutdown."""
        if self.session:
            await self.session.close()
            self.session = None

