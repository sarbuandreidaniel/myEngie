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
        self._account_data = {}
        self.contract_accounts: list[str] = []
        self.account_id: str = ""
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

    def _extract_account_info(self, raw_data: dict | list | None) -> None:
        """Extract account identifiers from API responses."""
        if raw_data is None:
            return

        def search(value: object) -> None:
            if isinstance(value, dict):
                for key, item in value.items():
                    lower_key = key.lower()

                    if lower_key in ("contract_account", "contract_account_id", "contractaccount", "contractAccount", "contract_accountid", "contractAccountId", "contract_account_number", "contractaccountnumber", "contractAccountNumber"):
                        if isinstance(item, (list, tuple)):
                            for x in item:
                                if x and str(x) not in self.contract_accounts:
                                    self.contract_accounts.append(str(x))
                        elif item:
                            item_str = str(item)
                            if item_str not in self.contract_accounts:
                                self.contract_accounts.append(item_str)
                    elif lower_key in ("provider_account_id", "pa", "provider_id", "pa_number", "provider_number"):
                        if item and not self.provider_account_id:
                            self.provider_account_id = str(item)
                            _LOGGER.debug("Extracted provider_account_id (pa): %s from key: %s", self.provider_account_id, key)
                    elif lower_key in ("poc_number", "poc", "connection_point", "point_of_connection"):
                        if item and not self.poc_number:
                            self.poc_number = str(item)
                            _LOGGER.debug("Extracted poc_number: %s from key: %s", self.poc_number, key)
                    elif lower_key in ("installation_number", "installation_id", "installation"):
                        if item and not self.installation_number:
                            self.installation_number = str(item)
                            _LOGGER.debug("Extracted installation_number: %s from key: %s", self.installation_number, key)
                    elif lower_key in ("pod", "point_of_delivery", "point_of_dispatch"):
                        if item and not self.pod:
                            self.pod = str(item)
                            _LOGGER.debug("Extracted pod: %s from key: %s", self.pod, key)
                    elif lower_key in ("account_id", "id", "accountid", "accountId", "poc_number", "pocnumber", "pocNumber"):
                        if item and str(item).isdigit():
                            self.account_id = str(item)
                            _LOGGER.debug("Extracted account_id: %s from key: %s", self.account_id, key)

                    search(item)
            elif isinstance(value, (list, tuple)):
                for item in value:
                    search(item)

        search(raw_data)

        # Use contract account as account_id if not already set
        if not self.account_id and self.contract_accounts:
            self.account_id = self.contract_accounts[0]
            _LOGGER.debug("Set account_id from contract_accounts: %s", self.account_id)

        # Fallback: if no contract accounts but have account_id, use account_id as contract account
        if not self.contract_accounts and self.account_id:
            self.contract_accounts = [self.account_id]
            _LOGGER.debug("Set contract_accounts from account_id: %s", self.contract_accounts)

        # Normalize unique accounts
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

            # Fetch app status first and extract account identifiers
            status = await self.api.get_app_status()
            
            # Check if refresh token is invalid
            if status.get("reason") == "invalid_refresh_token":
                _LOGGER.warning("Refresh token invalid, clearing auth and re-authenticating")
                self._is_initialized = False
                self.auth_manager = None
                if not await self._async_authenticate():
                    raise UpdateFailed("Failed to re-authenticate after token invalidation")
                # Retry the app status call
                status = await self.api.get_app_status()
            
            if status.get("error"):
                _LOGGER.warning("App status check failed: %s", status)
            self._extract_account_info(status.get("data"))

            # If no contract accounts found in app status, try invitations
            if not self.contract_accounts:
                invitations = await self.api.get_invitations()
                if not invitations.get("error"):
                    self._extract_account_info(invitations.get("data"))
                    _LOGGER.debug("Extracted account info from invitations")

            # If still no contract accounts, try places
            if not self.contract_accounts:
                places = await self.api.get_places()
                if not places.get("error"):
                    self._extract_account_info(places.get("data"))
                    _LOGGER.debug("Extracted account info from places")
            notifications = await self.api.get_unread_notifications()
            notification_count = 0
            if not notifications.get("error"):
                try:
                    notification_count = int(notifications.get("data", 0))
                except (ValueError, TypeError):
                    notification_count = 0

            # Fetch balance and invoices when contract accounts are available
            balance_details = {"error": True}
            total_balance = "0.00"
            invoices = []
            pending = []
            if self.contract_accounts:
                balance_details = await self.api.get_balance_details(self.contract_accounts)
                if not balance_details.get("error"):
                    data = balance_details.get("data", {})
                    # Extract account info from balance details response
                    self._extract_account_info(balance_details.get("data"))
                    total_balance = data.get("total", "0.00")
                    invoices = data.get("invoices", [])
                    pending = data.get("pending", [])
            else:
                _LOGGER.warning("No contract accounts available, skipping balance and invoice fetch")

            # Fetch index data (gas consumption) if parameters are available
            gas_index = None
            next_read_dates = None
            index_history = []
            if self.poc_number and self.provider_account_id and self.installation_number:
                try:
                    index_data = await self.api.get_index_data(
                        poc_number=self.poc_number,
                        division="gaz",
                        pa=self.provider_account_id,
                        installation_number=self.installation_number,
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
            else:
                _LOGGER.warning(
                    "Index fetch skipped because POC/PA/installation data are missing: poc=%s pa=%s installation=%s",
                    self.poc_number,
                    self.provider_account_id,
                    self.installation_number,
                )

            # Fetch balance widget only with contract accounts
            balance_widget = {"error": True}
            balance_details_data = {}
            if self.contract_accounts:
                balance_widget = await self.api.get_balance_widget(self.contract_accounts)
                if not balance_widget.get("error"):
                    balance_details_data = balance_widget.get("data", {})
                    # Extract account info from balance widget response
                    self._extract_account_info(balance_widget.get("data"))
            else:
                _LOGGER.warning("No contract accounts available, skipping balance widget fetch")

            # Get notifications banner if account ID and PA available
            banners = []
            if self.account_id and self.provider_account_id:
                try:
                    banner_data = await self.api.get_notifications_banner(
                        account_id=self.account_id,
                        pa=self.provider_account_id,
                    )
                    if not banner_data.get("error"):
                        banners = [banner_data.get("data", {})]
                except Exception as err:
                    _LOGGER.debug("Could not fetch banners: %s", err)
            else:
                _LOGGER.warning(
                    "Banner fetch skipped - missing required fields. account_id=%s, pa=%s. "
                    "Extracted data: contract_accounts=%s, poc=%s, installation=%s, pod=%s",
                    self.account_id,
                    self.provider_account_id,
                    self.contract_accounts,
                    self.poc_number,
                    self.installation_number,
                    self.pod,
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

