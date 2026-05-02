"""Config flow for MyEngie integration."""

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
import aiohttp
import logging

from .const import DOMAIN
from .auth import Auth0Manager

_LOGGER = logging.getLogger(__name__)


class MyEngieConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for MyEngie."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # Validate input
            try:
                username = user_input.get(CONF_USERNAME, "").strip()
                password = user_input.get(CONF_PASSWORD, "")

                if not username:
                    errors["base"] = "missing_username"
                elif not password:
                    errors["base"] = "missing_password"
                else:
                    # Check if already configured
                    await self.async_set_unique_id(username)
                    self._abort_if_unique_id_configured()

                    # Validate credentials with Auth0
                    valid, error_key = await self._validate_credentials(username, password)
                    if not valid:
                        errors["base"] = error_key
                    else:
                        return self.async_create_entry(
                            title=username,
                            data={
                                CONF_USERNAME: username,
                                CONF_PASSWORD: password,
                            },
                        )
            except Exception as err:
                _LOGGER.error("Error validating config: %s", err)
                errors["base"] = "invalid_auth"

        schema = vol.Schema(
            {
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
            description_placeholders={},
        )

    async def _validate_credentials(self, username: str, password: str) -> tuple[bool, str]:
        """Validate credentials with Auth0."""
        try:
            async with aiohttp.ClientSession() as session:
                auth_manager = Auth0Manager()
                success, error_key = await auth_manager.authenticate(session, username, password)
                if not success:
                    _LOGGER.warning("Auth0 authentication failed for user: %s", username)
                    return False, error_key or "invalid_auth"
                return True, ""
        except Exception as err:
            _LOGGER.error("Error validating credentials: %s", err)
            return False, "cannot_connect"

    async def async_step_reauth(
        self, entry_data: dict
    ) -> FlowResult:
        """Handle re-authentication triggered by ConfigEntryAuthFailed."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Show reauth form and process updated credentials."""
        errors = {}
        reauth_entry = self._get_reauth_entry()

        if user_input is not None:
            try:
                username = user_input.get(CONF_USERNAME, "").strip()
                password = user_input.get(CONF_PASSWORD, "")
                valid, error_key = await self._validate_credentials(username, password)
                if not valid:
                    errors["base"] = error_key
                else:
                    return self.async_update_reload_and_abort(
                        reauth_entry,
                        data={**reauth_entry.data, CONF_USERNAME: username, CONF_PASSWORD: password},
                    )
            except Exception as err:  # noqa: BLE001
                _LOGGER.error("Error during reauth: %s", err)
                errors["base"] = "cannot_connect"

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_USERNAME,
                    default=reauth_entry.data.get(CONF_USERNAME, ""),
                ): str,
                vol.Required(CONF_PASSWORD): str,
            }
        )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=schema,
            errors=errors,
        )
