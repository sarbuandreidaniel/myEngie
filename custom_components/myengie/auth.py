"""Auth0 authentication for MyEngie integration."""

import aiohttp
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

_LOGGER = logging.getLogger(__name__)

AUTH0_DOMAIN = "auth.engie.ro"
AUTH0_ENDPOINT = f"https://{AUTH0_DOMAIN}"
CLIENT_ID = "iTSW5r2awGCwSdkGDx66h76wiTnbNZgy"
CLIENT_REALM = "MyEngieUsers"


class Auth0Manager:
    """Manages Auth0 authentication for MyEngie."""

    def __init__(self):
        """Initialize Auth0 manager."""
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.token_expiry: Optional[datetime] = None
        self.id_token: Optional[str] = None

    async def authenticate(
        self, 
        session: aiohttp.ClientSession,
        username: str, 
        password: str
    ) -> tuple[bool, str]:
        """
        Authenticate with Auth0 using username and password.
        
        Returns (success: bool, error_key: str)
        """
        try:
            _LOGGER.debug("Attempting Auth0 authentication for user: %s", username)
            
            # Step 1: Get authorization code using Resource Owner Password Grant
            auth_data = {
                "client_id": CLIENT_ID,
                "grant_type": "http://auth0.com/oauth/grant-type/password-realm",
                "username": username,
                "password": password,
                "realm": CLIENT_REALM,
                "scope": "openid profile email offline_access",
                "audience": "https://myservices.engie.ro",
            }

            async with session.post(
                f"{AUTH0_ENDPOINT}/oauth/token",
                json=auth_data,
                headers={"Content-Type": "application/json"},
            ) as resp:
                if resp.status == 200:
                    token_data = await resp.json()
                    self.access_token = token_data.get("access_token")
                    self.refresh_token = token_data.get("refresh_token")
                    self.id_token = token_data.get("id_token")
                    
                    # Calculate token expiry
                    expires_in = token_data.get("expires_in", 3600)
                    self.token_expiry = datetime.now() + timedelta(seconds=expires_in)
                    
                    _LOGGER.debug("Auth0 authentication successful")
                    return True, ""
                else:
                    error_text = await resp.text()
                    _LOGGER.error(
                        "Auth0 authentication failed with status %s: %s",
                        resp.status,
                        error_text,
                    )
                    
                    # Try to parse error response for better error messages
                    try:
                        error_json = json.loads(error_text)
                        error_type = error_json.get("error", "")
                        error_description = error_json.get("error_description", "")
                        
                        if error_type == "invalid_grant":
                            _LOGGER.warning("Invalid username/password combination for user: %s", username)
                        elif error_type == "invalid_client":
                            _LOGGER.error("Auth0 client configuration error - client_id may be invalid")
                        elif "temporarily_locked" in error_description.lower():
                            _LOGGER.warning("Account temporarily locked due to too many failed attempts")
                        elif "invalid_realm" in error_description.lower():
                            _LOGGER.error("Auth0 realm configuration error")
                        else:
                            _LOGGER.warning("Auth0 authentication failed: %s - %s", error_type, error_description)
                    except json.JSONDecodeError:
                        _LOGGER.warning("Auth0 returned non-JSON error response: %s", error_text)
                    
                    return False, "invalid_auth"

        except Exception as err:
            _LOGGER.error("Auth0 authentication error: %s", err)
            return False, "cannot_connect"

    async def refresh_access_token(
        self,
        session: aiohttp.ClientSession
    ) -> bool:
        """
        Refresh access token using refresh token.
        
        Returns True if refresh successful, False otherwise.
        """
        if not self.refresh_token:
            _LOGGER.error("No refresh token available")
            return False

        try:
            _LOGGER.debug("Attempting to refresh Auth0 access token")
            
            refresh_data = {
                "client_id": CLIENT_ID,
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
                "scope": "openid profile email offline_access",
                "audience": "https://myservices.engie.ro",
            }

            async with session.post(
                f"{AUTH0_ENDPOINT}/oauth/token",
                data=refresh_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            ) as resp:
                if resp.status == 200:
                    token_data = await resp.json()
                    self.access_token = token_data.get("access_token")
                    
                    # Update refresh token if provided
                    if "refresh_token" in token_data:
                        self.refresh_token = token_data.get("refresh_token")
                    
                    # Calculate token expiry
                    expires_in = token_data.get("expires_in", 3600)
                    self.token_expiry = datetime.now() + timedelta(seconds=expires_in)
                    
                    _LOGGER.debug("Auth0 token refresh successful")
                    return True
                else:
                    error_text = await resp.text()
                    _LOGGER.error(
                        "Auth0 token refresh failed with status %s: %s",
                        resp.status,
                        error_text,
                    )
                    # Try to parse error for better diagnostics
                    try:
                        error_json = json.loads(error_text)
                        if error_json.get("error") == "invalid_grant":
                            _LOGGER.error("Auth0: Invalid grant - refresh token may be expired or invalid")
                        else:
                            _LOGGER.error("Auth0 error: %s - %s", error_json.get("error"), error_json.get("error_description"))
                    except json.JSONDecodeError:
                        pass
                    return False

        except Exception as err:
            _LOGGER.error("Auth0 token refresh error: %s", err)
            return False

    def is_token_expired(self) -> bool:
        """Check if access token is expired or expiring soon."""
        if not self.token_expiry:
            return True
        
        # Consider token expired if less than 5 minutes remaining
        expiry_buffer = datetime.now() + timedelta(minutes=5)
        return self.token_expiry <= expiry_buffer

    def get_token(self) -> Optional[str]:
        """Get current access token."""
        return self.access_token

    def clear_tokens(self) -> None:
        """Clear all stored tokens."""
        self.access_token = None
        self.refresh_token = None
        self.id_token = None
        self.token_expiry = None
