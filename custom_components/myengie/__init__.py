"""Custom integration for MyEngie Romania."""

import asyncio
import logging
from datetime import date, timedelta
from typing import Any
import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import MyEngieAPI
from .auth import Auth0Manager
from .const import DEFAULT_UPDATE_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "number", "button"]

_AUTH_REASONS = frozenset({"invalid_refresh_token", "token_refresh_failed", "no_token"})


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up MyEngie from a config entry."""
    _LOGGER.debug("Setting up MyEngie config entry: %s", entry.title)

    username = entry.data.get(CONF_USERNAME)
    password = entry.data.get(CONF_PASSWORD)

    # Create coordinator
    coordinator = MyEngieDataUpdateCoordinator(
        hass,
        config_entry=entry,
        username=username,
        password=password,
    )

    # Fetch initial data — raises ConfigEntryNotReady on failure
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

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

    return unload_ok


class MyEngieDataUpdateCoordinator(DataUpdateCoordinator):
    """Data update coordinator for MyEngie."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        username: str,
        password: str,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=config_entry,
            update_interval=timedelta(seconds=DEFAULT_UPDATE_INTERVAL),
        )
        self.username = username
        self.password = password
        self.session: aiohttp.ClientSession | None = None
        self.auth_manager: Auth0Manager | None = None
        self.api: MyEngieAPI | None = None
        self.places: dict[str, dict[str, Any]] = {}
        self.pending_gas_index: dict[str, int] = {}
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

        Authoritative source for: pa, poc_number, and contract_account_numbers.
        """
        if not isinstance(data, dict):
            return

        places = data.get("places_of_consumption", [])
        if not isinstance(places, list):
            return

        existing_places = self.places
        extracted_places: dict[str, dict[str, Any]] = {}

        for place in places:
            if not isinstance(place, dict):
                continue

            pa = str(place.get("pa", "")).strip()
            poc_number = str(place.get("poc_number", "")).strip()
            if not pa or not poc_number:
                continue

            place_key = f"{pa}_{poc_number}"
            existing_place = existing_places.get(place_key, {})
            contract_accounts: list[str] = []

            for contract in place.get("cont_contract", []):
                if isinstance(contract, dict) and contract.get("contract_account_number"):
                    num = str(contract["contract_account_number"])
                    if num not in contract_accounts:
                        contract_accounts.append(num)

            extracted_places[place_key] = {
                "place_key": place_key,
                "pa": pa,
                "poc_number": poc_number,
                "contract_accounts": contract_accounts,
                "installation_number": existing_place.get("installation_number", ""),
                "pod": existing_place.get("pod", ""),
                "place_name": existing_place.get(
                    "place_name", self._default_place_name(poc_number)
                ),
            }

        self.places = extracted_places

    @staticmethod
    def _default_place_name(poc_number: str) -> str:
        """Return a stable fallback name for a place."""
        if poc_number:
            return f"MyEngie {poc_number}"
        return "MyEngie"

    @staticmethod
    def _parse_amount(value: Any) -> float:
        """Normalize amount strings returned by the API."""
        try:
            return float(str(value).replace(",", "."))
        except (TypeError, ValueError):
            return 0.0

    def _apply_contract_aliases(self, contracts_data: Any) -> None:
        """Apply contract aliases to known places when a safe mapping exists."""
        if not isinstance(contracts_data, list) or not self.places:
            return

        aliases = []
        for contract in contracts_data:
            if not isinstance(contract, dict):
                continue
            alias = str(contract.get("alias", "")).strip()
            if alias:
                aliases.append(alias)

        if not aliases:
            return

        if len(self.places) == 1:
            next(iter(self.places.values()))["place_name"] = aliases[0]
            return

        if len(aliases) != len(self.places):
            _LOGGER.debug(
                "Could not map contract aliases to places: aliases=%s places=%s",
                len(aliases),
                len(self.places),
            )
            return

        for place, alias in zip(self.places.values(), aliases):
            place["place_name"] = alias

    @staticmethod
    def _is_in_read_window(next_read_dates: dict | None) -> bool:
        """Return True if today falls within the API-reported index submission window."""
        if not next_read_dates:
            return False
        try:
            # API format: "DD-MM-YYYY" (e.g. "20-04-2026")
            def _parse(val: str) -> date:
                parts = val.strip().split("-")
                return date(int(parts[2]), int(parts[1]), int(parts[0]))

            start = _parse(str(next_read_dates.get("startDate", "")))
            end = _parse(str(next_read_dates.get("endDate", "")))
            return start <= date.today() <= end
        except (ValueError, IndexError, TypeError):
            return False

    async def _async_update_data(self) -> dict:
        """Fetch data from MyEngie API."""
        try:
            async with asyncio.timeout(60):
                return await self._async_fetch_data()
        except ConfigEntryAuthFailed:
            raise
        except UpdateFailed:
            raise
        except TimeoutError as err:
            raise UpdateFailed("MyEngie API timed out") from err
        except Exception as err:
            _LOGGER.error("Error fetching MyEngie data: %s", err)
            raise UpdateFailed(f"Error fetching MyEngie data: {err}")

    async def _async_fetch_data(self) -> dict:
        """Perform data fetch — always called from within asyncio.timeout context."""
        try:
            # Authenticate if not already done
            if not self._is_initialized:
                if not await self._async_authenticate():
                    raise ConfigEntryAuthFailed("Failed to authenticate with MyEngie")

            if not self.api:
                raise ConfigEntryAuthFailed("API not initialized — re-authentication required")

            _LOGGER.debug("Fetching data from MyEngie API")

            # App status — check for maintenance or invalid token, no account data here
            status = await self.api.get_app_status()
            if status.get("reason") in _AUTH_REASONS:
                _LOGGER.warning("MyEngie auth token invalid (%s), clearing auth and re-authenticating", status.get("reason"))
                self._is_initialized = False
                self.auth_manager = None
                if not await self._async_authenticate():
                    raise ConfigEntryAuthFailed("Failed to re-authenticate after token invalidation")
                status = await self.api.get_app_status()
            if status.get("error"):
                _LOGGER.warning("App status check failed: %s", status)

            # Places of consumption — authoritative source for pa, poc_number, contract_accounts
            placesofconsumption = await self.api.get_placesofconsumption()
            if not placesofconsumption.get("error"):
                self._extract_places_of_consumption(placesofconsumption.get("data"))
            else:
                _LOGGER.warning("placesofconsumption failed: %s", placesofconsumption)
                # Silent auth expiry: token was accepted by app_status but expired by the
                # time we fetched places — force a full re-login and retry once.
                if placesofconsumption.get("reason") in _AUTH_REASONS:
                    _LOGGER.debug(
                        "MyEngie: silent auth expiry detected — re-authenticating"
                    )
                    self._is_initialized = False
                    self.auth_manager = None
                    if await self._async_authenticate():
                        placesofconsumption = await self.api.get_placesofconsumption()
                        if not placesofconsumption.get("error"):
                            self._extract_places_of_consumption(placesofconsumption.get("data"))
                        else:
                            _LOGGER.warning(
                                "MyEngie: placesofconsumption still failed after re-auth: %s",
                                placesofconsumption,
                            )

            # Contracts — source for user-defined place alias/name
            contracts = await self.api.get_contracts()
            if not contracts.get("error"):
                self._apply_contract_aliases(contracts.get("data", []))
            else:
                _LOGGER.warning("contracts fetch failed: %s", contracts)

            today = date.today()
            prev_year = today.year - 1
            places_data: dict[str, dict[str, Any]] = {}

            for place_key, place in self.places.items():
                pa = place["pa"]
                poc_number = place["poc_number"]
                contract_accounts = place.get("contract_accounts", [])

                total_balance = 0.0
                invoices: list[Any] = []
                pending: list[Any] = []
                invoice_history: list[Any] = []
                invoice_history_current: list[Any] = []
                gas_index = 0
                next_read_dates = None
                permite_index = False
                in_submission_window = False
                index_history: list[Any] = []
                balance_details_data: dict[str, Any] = {}
                banners: list[Any] = []

                if contract_accounts:
                    balance_details = await self.api.get_balance_details(contract_accounts)
                    if not balance_details.get("error"):
                        balance_data = balance_details.get("data", {})
                        total_balance = self._parse_amount(balance_data.get("total", 0.0))
                        invoices = balance_data.get("invoices", [])
                        pending = balance_data.get("pending", [])

                    balance_widget = await self.api.get_balance_widget(contract_accounts)
                    if not balance_widget.get("error"):
                        balance_details_data = balance_widget.get("data", {})
                else:
                    _LOGGER.warning(
                        "No contract accounts found for place %s, skipping balance fetch",
                        place_key,
                    )

                if poc_number and pa:
                    try:
                        inv_hist_prev = await self.api.get_invoice_history(
                            poc_number=poc_number,
                            pa=pa,
                            start_date=date(prev_year, 1, 1).isoformat(),
                            end_date=date(prev_year, 12, 31).isoformat(),
                        )
                        if not inv_hist_prev.get("error"):
                            raw = inv_hist_prev.get("data", [])
                            if isinstance(raw, list):
                                for group in raw:
                                    if isinstance(group, dict):
                                        invoice_history.extend(group.get("invoices", []))

                        inv_hist_curr = await self.api.get_invoice_history(
                            poc_number=poc_number,
                            pa=pa,
                            start_date=date(today.year, 1, 1).isoformat(),
                            end_date=today.isoformat(),
                        )
                        if not inv_hist_curr.get("error"):
                            raw = inv_hist_curr.get("data", [])
                            if isinstance(raw, list):
                                for group in raw:
                                    if isinstance(group, dict):
                                        invoice_history_current.extend(group.get("invoices", []))
                            invoice_history.extend(invoice_history_current)
                    except Exception as err:
                        _LOGGER.debug(
                            "Could not fetch invoice history for place %s: %s",
                            place_key,
                            err,
                        )

                    try:
                        index_data = await self.api.get_index_data(
                            poc_number=poc_number,
                            division="gaz",
                            pa=pa,
                            installation_number=place.get("installation_number") or None,
                        )
                        if not index_data.get("error"):
                            installations_data = index_data.get("data", [])
                            if installations_data:
                                first_inst = installations_data[0].get("installations", [])
                                if first_inst:
                                    inst = first_inst[0]
                                    if inst.get("installation_number"):
                                        place["installation_number"] = str(inst["installation_number"])
                                    if inst.get("pod"):
                                        place["pod"] = str(inst["pod"])
                                    gas_index = inst.get("last_index", 0) or 0
                                    next_read_dates = inst.get("next_read_dates")
                                    permite_index = bool(inst.get("permite_index", False))
                                    in_submission_window = permite_index and self._is_in_read_window(next_read_dates)
                                    _LOGGER.debug(
                                        "Place %s: permite_index=%s next_read_dates=%s in_window=%s",
                                        place_key,
                                        permite_index,
                                        next_read_dates,
                                        in_submission_window,
                                    )
                        else:
                            _LOGGER.warning(
                                "Index data fetch failed for place %s: %s",
                                place_key,
                                index_data,
                            )
                    except Exception as err:
                        _LOGGER.debug(
                            "Could not fetch index data for place %s: %s",
                            place_key,
                            err,
                        )

                    try:
                        consumption = await self.api.get_index_consumption(
                            poc_number=poc_number,
                            pa=pa,
                            start_date=date(today.year - 1, 1, 1).isoformat(),
                            end_date=today.isoformat(),
                        )
                        if not consumption.get("error"):
                            index_history = consumption.get("data", [])
                    except Exception as err:
                        _LOGGER.debug(
                            "Could not fetch consumption history for place %s: %s",
                            place_key,
                            err,
                        )

                    try:
                        banner_data = await self.api.get_notifications_banner(
                            poc_number=poc_number,
                            pa=pa,
                        )
                        if not banner_data.get("error"):
                            banner = banner_data.get("data", {})
                            if banner:
                                banners = [banner]
                    except Exception as err:
                        _LOGGER.debug(
                            "Could not fetch banners for place %s: %s",
                            place_key,
                            err,
                        )
                else:
                    _LOGGER.warning(
                        "Place fetch skipped - missing poc=%s or pa=%s",
                        poc_number,
                        pa,
                    )

                invoice_history_current.sort(
                    key=lambda inv: inv.get("invoiced_at", ""),
                    reverse=True,
                )

                places_data[place_key] = {
                    "place_key": place_key,
                    "pa": pa,
                    "poc_number": poc_number,
                    "contract_accounts": contract_accounts,
                    "installation_number": place.get("installation_number", ""),
                    "pod": place.get("pod", ""),
                    "place_name": place.get(
                        "place_name", self._default_place_name(poc_number)
                    ),
                    "balance": total_balance,
                    "gas_index": gas_index,
                    "permite_index": permite_index,
                    "in_submission_window": in_submission_window,
                    "invoices": invoices,
                    "invoice_history": invoice_history,
                    "invoice_history_current": invoice_history_current,
                    "pending": pending,
                    "next_read_dates": next_read_dates,
                    "balance_details": balance_details_data,
                    "banners": banners,
                    "index_history": index_history,
                    "is_up_to_date": len(pending) == 0,
                    "invoice_count": len(invoices),
                }

            data = {
                "places": places_data,
            }

            _LOGGER.debug("Successfully fetched MyEngie data")
            return data

        except (ConfigEntryAuthFailed, UpdateFailed):
            raise
        except Exception as err:
            _LOGGER.error("Error fetching MyEngie data: %s", err)
            raise UpdateFailed(f"Error fetching MyEngie data: {err}")

    async def async_shutdown(self) -> None:
        """Cleanup on shutdown."""
        if self.session:
            await self.session.close()
            self.session = None

