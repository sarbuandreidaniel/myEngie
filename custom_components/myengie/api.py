"""API client for MyEngie Romania."""

import aiohttp
import json
import logging
from typing import Any, Dict, Optional
from .auth import Auth0Manager

_LOGGER = logging.getLogger(__name__)

API_BASE_URL = "https://gwss.engie.ro/myservices"
AUTH_BASE_URL = "https://auth.engie.ro"


class MyEngieAPI:
    """MyEngie API client."""

    def __init__(self, session: aiohttp.ClientSession, auth_manager: Auth0Manager):
        """Initialize API client."""
        self.session = session
        self.auth_manager = auth_manager

    async def get_app_status(self) -> Dict[str, Any]:
        """Get application status."""
        return await self._request("GET", f"{API_BASE_URL}/v2/app_status")

    async def get_unread_notifications(self) -> Dict[str, Any]:
        """Get unread notifications count."""
        return await self._request(
            "GET", f"{API_BASE_URL}/v1/notifications/unread-number"
        )

    async def get_balance_details(
        self, contract_accounts: list
    ) -> Dict[str, Any]:
        """Get balance and invoice details."""
        data = aiohttp.FormData()
        for account in contract_accounts:
            data.add_field("contract_account[]", account)

        return await self._request(
            "POST",
            f"{API_BASE_URL}/v1/invoices/ballance-details",
            data=data,
        )

    async def get_index_data(
        self,
        poc_number: str,
        division: str,
        pa: str,
        installation_number: str,
    ) -> Dict[str, Any]:
        """Get gas/electricity index data."""
        params = {
            "poc_number": poc_number,
            "division": division,
            "pa": pa,
            "installation_number": installation_number,
        }
        return await self._request(
            "GET",
            f"{API_BASE_URL}/v1/index/{poc_number}",
            params=params,
        )

    async def get_balance_widget(
        self, contract_accounts: list
    ) -> Dict[str, Any]:
        """Get balance widget data."""
        data = aiohttp.FormData()
        for account in contract_accounts:
            data.add_field("contract_account[]", account)

        return await self._request(
            "POST",
            f"{API_BASE_URL}/v1/widgets/ballance",
            data=data,
        )

    async def get_notifications_banner(
        self, account_id: str, pa: str
    ) -> Dict[str, Any]:
        """Get notification banner."""
        params = {"pa": pa, "account_class": "CS"}
        return await self._request(
            "GET",
            f"{API_BASE_URL}/v1/notifications/banner/{account_id}",
            params=params,
        )

    async def get_invitations(self) -> Dict[str, Any]:
        """Get user invitations."""
        return await self._request("GET", f"{API_BASE_URL}/v1/invitations")

    async def get_banners(self) -> Dict[str, Any]:
        """Get banners."""
        return await self._request("POST", f"{API_BASE_URL}/v1/banners")

    async def get_account(self) -> Dict[str, Any]:
        """Get account data."""
        return await self._request("GET", f"{API_BASE_URL}/v1/account")

    async def get_user(self) -> Dict[str, Any]:
        """Get user data."""
        return await self._request("GET", f"{API_BASE_URL}/v1/user")

    async def get_places(self) -> Dict[str, Any]:
        """Get places of consumption."""
        return await self._request("GET", f"{API_BASE_URL}/v1/places")

    async def get_places(self) -> Dict[str, Any]:
        """Get places of consumption."""
        return await self._request("GET", f"{API_BASE_URL}/v1/places")

    async def _request(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, str]] = None,
        data: Optional[aiohttp.FormData] = None,
    ) -> Dict[str, Any]:
        """Make API request with automatic token refresh."""
        # Check if token needs refresh
        if self.auth_manager.is_token_expired():
            _LOGGER.debug("Token expired, attempting refresh")
            if not await self.auth_manager.refresh_access_token(self.session):
                _LOGGER.error("Failed to refresh token")
                return {"error": True, "data": {}, "reason": "token_refresh_failed"}

        access_token = self.auth_manager.get_token()
        if not access_token:
            _LOGGER.error("No access token available")
            return {"error": True, "data": {}, "reason": "no_token"}

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "Source": "desktop",
            "Origin": "https://my.engie.ro",
            "Referer": "https://my.engie.ro/",
        }

        try:
            async with self.session.request(
                method,
                url,
                params=params,
                data=data,
                headers=headers,
            ) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status in (400, 401):
                    # Token may be expired or invalid, try refresh once
                    error_text = await response.text()
                    _LOGGER.debug("Auth error response: %s", error_text)
                    
                    # Check if refresh token is invalid
                    if "Token de refresh invalid" in error_text or "refresh_token" in error_text.lower():
                        _LOGGER.error("Refresh token is invalid - re-authentication required")
                        return {"error": True, "data": {}, "reason": "invalid_refresh_token"}
                    
                    _LOGGER.debug("Attempting token refresh due to auth response")
                    if await self.auth_manager.refresh_access_token(self.session):
                        # Retry request with new token
                        return await self._request(method, url, params, data)
                    _LOGGER.error("Token refresh failed after auth failure")
                    return {"error": True, "data": {}, "reason": "token_refresh_failed"}
                else:
                    error_text = await response.text()
                    _LOGGER.error(
                        "API request failed: %s %s - Status: %s - Response: %s",
                        method,
                        url,
                        response.status,
                        error_text[:200] if error_text else "",
                    )
                    return {"error": True, "data": {}, "status": response.status}
        except Exception as err:
            _LOGGER.error("API request error: %s", err)
            return {"error": True, "data": {}, "reason": str(err)}
