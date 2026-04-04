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
import os

# Auth0 configuration
AUTH0_DOMAIN = "auth.engie.ro"
AUTH0_ENDPOINT = f"https://{AUTH0_DOMAIN}"
CLIENT_ID = "iTSW5r2awGCwSdkGDx66h76wiTnbNZgy"
CLIENT_REALM = "MyEngieUsers"

API_BASE_URL = "https://gwss.engie.ro/myservices"


class MyEngieAPI:
    """MyEngie API client."""

    def __init__(self, session, auth_manager):
        """Initialize API client."""
        self.session = session
        self.auth_manager = auth_manager

    async def get_app_status(self):
        """Get application status."""
        return await self._request("GET", f"{API_BASE_URL}/v2/app_status")

    async def get_userinfo(self):
        """Get user info from Auth0."""
        headers = {
            "Authorization": f"Bearer {self.auth_manager.id_token}",
            "Accept": "application/json",
        }
        try:
            async with self.session.get(
                f"{AUTH0_ENDPOINT}/userinfo",
                headers=headers,
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    return {"error": True, "status": response.status, "reason": error_text[:200]}
        except Exception as err:
            return {"error": True, "reason": str(err)}

    async def get_placesofconsumption(self):
        """Get places of consumption data."""
        return await self._request("GET", f"{API_BASE_URL}/v1/placesofconsumption")

    async def _request(self, method, url, params=None, data=None):
        """Make API request with automatic token refresh."""
        access_token = self.auth_manager.access_token
        if not access_token:
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
                else:
                    error_text = await response.text()
                    return {"error": True, "data": {}, "status": response.status, "reason": error_text[:200]}
        except Exception as err:
            return {"error": True, "data": {}, "reason": str(err)}

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

    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(verify_ssl=False)) as session:
        auth_manager = Auth0Manager()
        success, token_data = await auth_manager.authenticate(session, username, password)

        if success:
            print("✅ Authentication successful!")
            print(f"🔑 Access token received: {token_data.get('access_token')[:20]}...")
            print(f"🔄 Refresh token: {'Yes' if token_data.get('refresh_token') else 'No'}")
            print(f"⏰ Expires in: {token_data.get('expires_in', 'Unknown')} seconds")

            # Test API endpoints
            print("\n🔍 Testing API endpoints for account data...")
            auth_manager = Auth0Manager()
            auth_manager.access_token = token_data.get('access_token')
            auth_manager.refresh_token = token_data.get('refresh_token')
            auth_manager.id_token = token_data.get('id_token')

            api = MyEngieAPI(session, auth_manager)

            # Test get_app_status first
            print("\n📡 Testing get_app_status()...")
            try:
                status_data = await api.get_app_status()
                if status_data.get('error'):
                    print(f"❌ get_app_status failed: {status_data}")
                else:
                    print("✅ get_app_status successful!")
                    print(f"📊 Status data keys: {list(status_data.keys())}")
                    print(f"📄 Status data: {json.dumps(status_data, indent=2)}")
            except Exception as e:
                print(f"❌ get_app_status error: {e}")

            # Test Auth0 userinfo
            print("\n📡 Testing Auth0 userinfo...")
            try:
                userinfo_data = await api.get_userinfo()
                if userinfo_data.get('error'):
                    print(f"❌ userinfo failed: {userinfo_data}")
                else:
                    print("✅ userinfo successful!")
                    print(f"📊 Userinfo data keys: {list(userinfo_data.keys())}")
                    print(f"📄 Userinfo data: {json.dumps(userinfo_data, indent=2)}")
            except Exception as e:
                print(f"❌ userinfo error: {e}")

            # Test get_placesofconsumption
            print("\n📡 Testing get_placesofconsumption()...")
            try:
                placesofconsumption_data = await api.get_placesofconsumption()
                if placesofconsumption_data.get('error'):
                    print(f"❌ get_placesofconsumption failed: {placesofconsumption_data}")
                else:
                    print("✅ get_placesofconsumption successful!")
                    print(f"📊 PlacesOfConsumption data keys: {list(placesofconsumption_data.keys())}")
                    print(f"📄 PlacesOfConsumption data: {json.dumps(placesofconsumption_data, indent=2)}")
            except Exception as e:
                print(f"❌ get_placesofconsumption error: {e}")

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