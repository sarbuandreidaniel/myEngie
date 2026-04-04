#!/usr/bin/env python3
"""
Debug script for MyEngie authentication.
Run this to test authentication outside of Home Assistant.
"""

import asyncio
import aiohttp
import json
import logging
import sys

# Set up logging
logging.basicConfig(level=logging.DEBUG)
_LOGGER = logging.getLogger(__name__)

# Auth0 configuration
AUTH0_DOMAIN = "auth.engie.ro"
AUTH0_ENDPOINT = f"https://{AUTH0_DOMAIN}"
CLIENT_ID = "iTSW5r2awGCwSdkGDx66h76wiTnbNZgy"
CLIENT_REALM = "MyEngieUsers"

class Auth0Manager:
    """Manages Auth0 authentication for MyEngie."""

    def __init__(self):
        """Initialize Auth0 manager."""
        self.access_token = None
        self.refresh_token = None
        self.token_expiry = None
        self.id_token = None

    async def authenticate(self, session, username, password):
        """Authenticate with Auth0 using username and password."""
        try:
            _LOGGER.info("Attempting Auth0 authentication for user: %s", username)

            # Method 1: Resource Owner Password Grant (current implementation)
            auth_data = {
                "client_id": CLIENT_ID,
                "grant_type": "http://auth0.com/oauth/grant-type/password-realm",
                "username": username,
                "password": password,
                "realm": CLIENT_REALM,
                "scope": "openid profile email offline_access",
                "audience": "https://myservices.engie.ro",
            }

            _LOGGER.debug("Trying Resource Owner Password Grant...")
            async with session.post(
                f"{AUTH0_ENDPOINT}/oauth/token",
                json=auth_data,
                headers={"Content-Type": "application/json"},
            ) as resp:
                _LOGGER.info("Auth0 response status: %s", resp.status)

                if resp.status == 200:
                    token_data = await resp.json()
                    _LOGGER.info("Authentication successful!")
                    _LOGGER.debug("Token data keys: %s", list(token_data.keys()))
                    return True, token_data
                else:
                    error_text = await resp.text()
                    _LOGGER.error("Method 1 failed: %s", error_text)

                    # Try to parse error
                    try:
                        error_json = json.loads(error_text)
                        _LOGGER.error("Error type: %s", error_json.get("error"))
                        _LOGGER.error("Error description: %s", error_json.get("error_description"))
                    except:
                        pass

            # Method 2: Passwordless OTP (alternative from development docs)
            _LOGGER.debug("Trying Passwordless OTP method...")
            otp_data = {
                "client_id": CLIENT_ID,
                "username": username,
                "password": password,
                "grant_type": "http://auth0.com/oauth/grant-type/passwordless/otp",
                "realm": "SMS",
                "scope": "openid profile email offline_access",
                "audience": "https://myservices.engie.ro",
            }

            async with session.post(
                f"{AUTH0_ENDPOINT}/oauth/token",
                json=otp_data,
                headers={"Content-Type": "application/json"},
            ) as resp:
                _LOGGER.info("Passwordless OTP response status: %s", resp.status)

                if resp.status == 200:
                    token_data = await resp.json()
                    _LOGGER.info("Passwordless OTP authentication successful!")
                    return True, token_data
                else:
                    error_text = await resp.text()
                    _LOGGER.error("Method 2 also failed: %s", error_text)

            return False, None

        except Exception as err:
            _LOGGER.error("Authentication error: %s", err)
            return False, None

async def test_auth():
    """Test authentication with user input."""
    print("MyEngie Authentication Debug Tool")
    print("=" * 40)

    username = input("Enter your ENGIE email/username: ").strip()
    password = input("Enter your ENGIE password: ")

    if not username or not password:
        print("❌ Username and password are required")
        return

    print(f"\n🔐 Attempting authentication for: {username}")
    print("⏳ Please wait...")

    async with aiohttp.ClientSession() as session:
        auth_manager = Auth0Manager()
        success, token_data = await auth_manager.authenticate(session, username, password)

        if success:
            print("✅ Authentication successful!")
            print(f"🔑 Access token received: {token_data.get('access_token')[:20]}...")
            print(f"🔄 Refresh token: {'Yes' if token_data.get('refresh_token') else 'No'}")
            print(f"⏰ Expires in: {token_data.get('expires_in', 'Unknown')} seconds")
        else:
            print("❌ Authentication failed!")
            print("\n🔍 Possible issues:")
            print("1. Incorrect username/password")
            print("2. Account locked due to too many failed attempts")
            print("3. ENGIE authentication system changes")
            print("4. Network connectivity issues")
            print("\n💡 Try:")
            print("- Check your credentials on https://my.engie.ro")
            print("- Wait a few minutes if account is locked")
            print("- Contact ENGIE support if issues persist")

if __name__ == "__main__":
    asyncio.run(test_auth())