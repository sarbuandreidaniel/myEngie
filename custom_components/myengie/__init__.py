"""Custom integration for MyEngie Romania."""

import logging
from datetime import timedelta
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
    for platform in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(
                entry, platform
            )
        )

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
        self._account_data = {}
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

            # Fetch app status first
            status = await self.api.get_app_status()
            if status.get("error"):
                _LOGGER.warning("App status check failed")

            # Fetch account data - get unread notifications
            notifications = await self.api.get_unread_notifications()
            notification_count = 0
            if not notifications.get("error"):
                try:
                    notification_count = int(notifications.get("data", 0))
                except (ValueError, TypeError):
                    notification_count = 0

            # Fetch balance and invoices
            balance_details = await self.api.get_balance_details([])
            total_balance = "0.00"
            invoices = []
            pending = []
            if not balance_details.get("error"):
                data = balance_details.get("data", {})
                total_balance = data.get("total", "0.00")
                invoices = data.get("invoices", [])
                pending = data.get("pending", [])

            # Fetch index data (gas consumption)
            gas_index = None
            next_read_dates = None
            index_history = []
            
            # Try to get index data with basic parameters
            # In a real scenario, we'd need to get these from user preferences
            try:
                index_data = await self.api.get_index_data(
                    poc_number="",
                    division="gaz",
                    pa="",
                    installation_number="",
                )
                if not index_data.get("error"):
                    installations = index_data.get("data", [])
                    if installations:
                        first_inst = installations[0].get("installations", [])
                        if first_inst:
                            gas_index = first_inst[0].get("last_index", 0)
                            next_read_dates = first_inst[0].get("next_read_dates")
            except Exception as err:
                _LOGGER.debug("Could not fetch index data: %s", err)

            # Fetch balance widget
            balance_widget = await self.api.get_balance_widget([])
            balance_details_data = {}
            if not balance_widget.get("error"):
                balance_details_data = balance_widget.get("data", {})

            # Get notifications banner
            banners = []
            try:
                banner_data = await self.api.get_notifications_banner(
                    account_id="",
                    pa="",
                )
                if not banner_data.get("error"):
                    banners = [banner_data.get("data", {})]
            except Exception as err:
                _LOGGER.debug("Could not fetch banners: %s", err)

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

