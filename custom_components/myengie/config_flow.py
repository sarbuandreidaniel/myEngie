"""Config flow for MyEngie integration."""

import voluptuous as vol
from homeassistant import config_entries
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
                username = user_input.get("username", "").strip()
                password = user_input.get("password", "")

                if not username:
                    errors["base"] = "missing_username"
                elif not password:
                    errors["base"] = "missing_password"
                else:
                    # Check if already configured
                    await self.async_set_unique_id(username)
                    self._abort_if_unique_id_configured()

                    # Validate credentials with Auth0
                    valid = await self._validate_credentials(username, password)
                    if not valid:
                        errors["base"] = "invalid_auth"
                    else:
                        return self.async_create_entry(
                            title=username,
                            data={
                                "username": username,
                                "password": password,
                            },
                        )
            except Exception as err:
                _LOGGER.error("Error validating config: %s", err)
                errors["base"] = "invalid_auth"

        schema = vol.Schema(
            {
                vol.Required("username"): str,
                vol.Required("password"): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
            description_placeholders={},
        )

    async def _validate_credentials(self, username: str, password: str) -> bool:
        """Validate credentials with Auth0."""
        try:
            async with aiohttp.ClientSession() as session:
                auth_manager = Auth0Manager()
                success = await auth_manager.authenticate(session, username, password)
                return success
        except Exception as err:
            _LOGGER.error("Error validating credentials: %s", err)
            return False

    async def async_step_import(self, import_data: dict) -> FlowResult:
        """Handle import from configuration.yaml."""
        return await self.async_step_user(import_data)
