#!/usr/bin/env python3
"""
Debug script for MyEngie authentication.
Run this to test authentication outside of Home Assistant.
"""

import asyncio
import aiohttp
import json
import logging
import os
import sys

from dotenv import load_dotenv

load_dotenv()

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

    async def get_placesofconsumption(self):
        """Get places of consumption data."""
        return await self._request("GET", f"{API_BASE_URL}/v1/placesofconsumption")

    async def get_balance_details(self, contract_accounts):
        """Get balance and invoice details."""
        from aiohttp import FormData
        data = FormData()
        for account in contract_accounts:
            data.add_field("contract_account[]", account)

        return await self._request(
            "POST",
            f"{API_BASE_URL}/v1/invoices/ballance-details",
            data=data,
        )

    async def get_balance_widget(self, contract_accounts):
        """Get balance widget data."""
        from aiohttp import FormData
        data = FormData()
        for account in contract_accounts:
            data.add_field("contract_account[]", account)

        return await self._request(
            "POST",
            f"{API_BASE_URL}/v1/widgets/ballance",
            data=data,
        )

    async def get_invitations(self):
        """Get user invitations."""
        return await self._request("GET", f"{API_BASE_URL}/v1/invitations")

    async def get_unread_notifications(self):
        """Get unread notifications count."""
        return await self._request("GET", f"{API_BASE_URL}/v1/notifications/unread-number")

    async def get_notifications_banner(self, poc_number, pa):
        """Get notification banner."""
        params = {"pa": pa, "account_class": "CS"}
        return await self._request(
            "GET",
            f"{API_BASE_URL}/v1/notifications/banner/{poc_number}",
            params=params,
        )

    async def get_index_data(self, poc_number, division, pa, installation_number=None):
        """Get gas/electricity index data. installation_number is optional."""
        params = {
            "poc_number": poc_number,
            "division": division,
            "pa": pa,
        }
        if installation_number:
            params["installation_number"] = installation_number
        return await self._request(
            "GET",
            f"{API_BASE_URL}/v1/index/{poc_number}",
            params=params,
        )

    async def get_index_consumption(self, poc_number, pa, start_date, end_date):
        """Get gas consumption history by month."""
        params = {"startDate": start_date, "endDate": end_date, "pa": pa}
        return await self._request(
            "GET",
            f"{API_BASE_URL}/v1/index/consumption/{poc_number}",
            params=params,
        )

    async def get_index_prognosis(self, poc_number, pa, installation_number):
        """Get gas consumption prognosis by month."""
        params = {"installation_number": installation_number, "pa": pa}
        return await self._request(
            "GET",
            f"{API_BASE_URL}/v1/index/prognosis/{poc_number}",
            params=params,
        )

    async def get_invoice_history(self, poc_number, pa, start_date, end_date):
        """Get invoice history for a given date range."""
        params = {"startDate": start_date, "endDate": end_date, "pa": pa}
        return await self._request(
            "GET",
            f"{API_BASE_URL}/v1/invoices/history-only/{poc_number}",
            params=params,
        )

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

    success = False
    token_data = {}
    session_ctx = aiohttp.ClientSession(connector=aiohttp.TCPConnector(verify_ssl=False))

    async with session_ctx as session:
        while not success:
            env_user = os.getenv("ENGIE_USERNAME", "").strip()
            env_pass = os.getenv("ENGIE_PASSWORD", "")
            username = env_user or input("Enter your ENGIE email/username: ").strip()
            password = env_pass or input("Enter your ENGIE password: ")

            if not username or not password:
                print("❌ Username and password are required")
                continue

            print(f"\n🔐 Attempting authentication for: {username}")
            print("⏳ Please wait...")

            auth_manager = Auth0Manager()
            success, token_data = await auth_manager.authenticate(session, username, password)

            if not success:
                print("\n❌ Authentication failed. Please try again.\n")

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

            # Extracted account fields (populated as we go)
            contract_accounts = []
            poc_number = None
            pa = None
            installation_number = None
            account_id = None

            # ----------------------------------------------------------------
            # 1. get_app_status
            # ----------------------------------------------------------------
            print("\n📡 Testing get_app_status()...")
            try:
                status_data = await api.get_app_status()
                if status_data.get('error'):
                    print(f"❌ get_app_status failed: {status_data}")
                else:
                    print("✅ get_app_status successful!")
                    print(f"📊 Keys: {list(status_data.keys())}")
                    print(f"📄 Data: {json.dumps(status_data, indent=2)}")
            except Exception as e:
                print(f"❌ get_app_status error: {e}")

            # ----------------------------------------------------------------
            # 2. get_placesofconsumption  ← KEY endpoint for pa/poc/installation
            # ----------------------------------------------------------------
            print("\n📡 Testing get_placesofconsumption()...")
            try:
                poc_data = await api.get_placesofconsumption()
                if poc_data.get('error'):
                    print(f"❌ get_placesofconsumption failed: {poc_data}")
                else:
                    print("✅ get_placesofconsumption successful!")
                    print(f"📊 Keys: {list(poc_data.keys())}")
                    print(f"📄 Full response: {json.dumps(poc_data, indent=2)}")

                    # Extract account fields from the response
                    inner = poc_data.get("data") or poc_data
                    places = None
                    if isinstance(inner, dict):
                        places = inner.get("places_of_consumption") or inner.get("placesOfConsumption")
                    elif isinstance(inner, list):
                        places = inner

                    if places:
                        for place in places:
                            if isinstance(place, dict):
                                if place.get("pa") and not pa:
                                    pa = str(place["pa"])
                                    print(f"   ✅ Extracted pa: {pa}")
                                if place.get("poc_number") and not poc_number:
                                    poc_number = str(place["poc_number"])
                                    print(f"   ✅ Extracted poc_number: {poc_number}")
                                if place.get("installation_number") and not installation_number:
                                    installation_number = str(place["installation_number"])
                                    print(f"   ✅ Extracted installation_number: {installation_number}")
                                for contract in place.get("cont_contract", []):
                                    if isinstance(contract, dict):
                                        num = contract.get("contract_account_number")
                                        if num and str(num) not in contract_accounts:
                                            contract_accounts.append(str(num))
                                            print(f"   ✅ Extracted contract_account_number: {num}")
                    else:
                        print("   ⚠️  No places_of_consumption list found in response")
            except Exception as e:
                print(f"❌ get_placesofconsumption error: {e}")

            if not contract_accounts:
                print("\n⚠️  No contract accounts extracted from placesofconsumption")

            print(f"\n📋 Extracted so far: contract_accounts={contract_accounts}, pa={pa}, poc_number={poc_number}, installation_number={installation_number}")

            # ----------------------------------------------------------------
            # 4. get_invitations
            # ----------------------------------------------------------------
            print("\n📡 Testing get_invitations()...")
            try:
                invitations_data = await api.get_invitations()
                if invitations_data.get('error'):
                    print(f"❌ get_invitations failed: {invitations_data}")
                else:
                    print("✅ get_invitations successful!")
                    print(f"📊 Keys: {list(invitations_data.keys())}")
                    print(f"📄 Data: {json.dumps(invitations_data, indent=2)}")
            except Exception as e:
                print(f"❌ get_invitations error: {e}")

            # ----------------------------------------------------------------
            # 5. get_unread_notifications
            # ----------------------------------------------------------------
            print("\n📡 Testing get_unread_notifications()...")
            try:
                notif_data = await api.get_unread_notifications()
                if notif_data.get('error'):
                    print(f"❌ get_unread_notifications failed: {notif_data}")
                else:
                    print("✅ get_unread_notifications successful!")
                    print(f"📄 Data: {json.dumps(notif_data, indent=2)}")
            except Exception as e:
                print(f"❌ get_unread_notifications error: {e}")

            # ----------------------------------------------------------------
            # 6. get_balance_details  (needs contract_accounts)
            # ----------------------------------------------------------------
            print("\n📡 Testing get_balance_details()...")
            if contract_accounts:
                try:
                    balance_details_data = await api.get_balance_details(contract_accounts)
                    if balance_details_data.get('error'):
                        print(f"❌ get_balance_details failed: {balance_details_data}")
                    else:
                        print("✅ get_balance_details successful!")
                        print(f"📊 Keys: {list(balance_details_data.keys())}")
                        print(f"📄 Data: {json.dumps(balance_details_data, indent=2)}")
                        # Try to grab account_id from the response
                        inner = (balance_details_data.get("data") or {})
                        if isinstance(inner, dict) and inner.get("account_id") and not account_id:
                            account_id = str(inner["account_id"])
                            print(f"   ✅ Extracted account_id: {account_id}")
                except Exception as e:
                    print(f"❌ get_balance_details error: {e}")
            else:
                print("⚠️  Skipped - no contract_accounts available")

            # ----------------------------------------------------------------
            # 7. get_balance_widget  (needs contract_accounts)
            # ----------------------------------------------------------------
            print("\n📡 Testing get_balance_widget()...")
            if contract_accounts:
                try:
                    balance_widget_data = await api.get_balance_widget(contract_accounts)
                    if balance_widget_data.get('error'):
                        print(f"❌ get_balance_widget failed: {balance_widget_data}")
                    else:
                        print("✅ get_balance_widget successful!")
                        print(f"📊 Keys: {list(balance_widget_data.keys())}")
                        print(f"📄 Data: {json.dumps(balance_widget_data, indent=2)}")
                except Exception as e:
                    print(f"❌ get_balance_widget error: {e}")
            else:
                print("⚠️  Skipped - no contract_accounts available")

            # ----------------------------------------------------------------
            # 8. get_notifications_banner  (needs poc_number and pa)
            # ----------------------------------------------------------------
            print("\n📡 Testing get_notifications_banner()...")
            _poc_for_banner = poc_number
            if _poc_for_banner and pa:
                try:
                    banner_data = await api.get_notifications_banner(
                        poc_number=_poc_for_banner,
                        pa=pa,
                    )
                    if banner_data.get('error'):
                        print(f"❌ get_notifications_banner failed: {banner_data}")
                    else:
                        print("✅ get_notifications_banner successful!")
                        print(f"📄 Data: {json.dumps(banner_data, indent=2)}")
                except Exception as e:
                    print(f"❌ get_notifications_banner error: {e}")
            else:
                    print(f"⚠️  Skipped - missing poc_number ({_poc_for_banner}) or pa ({pa})")

            # ----------------------------------------------------------------
            # 9. get_index_data  (installation_number is optional - discovered from response)
            # ----------------------------------------------------------------
            print("\n📡 Testing get_index_data()...")
            _poc = poc_number
            _pa = pa
            if _poc and _pa:
                try:
                    index_data = await api.get_index_data(
                        poc_number=_poc,
                        division="gaz",
                        pa=_pa,
                        # No installation_number - let the API return it
                    )
                    if index_data.get('error'):
                        print(f"❌ get_index_data failed: {index_data}")
                    else:
                        print("✅ get_index_data successful!")
                        print(f"📄 Data: {json.dumps(index_data, indent=2)}")
                        # Extract installation_number from response
                        inst_data = index_data.get("data", [])
                        if inst_data:
                            insts = inst_data[0].get("installations", [])
                            if insts:
                                discovered_inst = str(insts[0].get("installation_number", ""))
                                if discovered_inst and not installation_number:
                                    installation_number = discovered_inst
                                    print(f"   ✅ Discovered installation_number: {installation_number}")
                except Exception as e:
                    print(f"❌ get_index_data error: {e}")
            else:
                print(f"⚠️  Skipped - missing poc_number ({_poc}) or pa ({_pa})")

            # ----------------------------------------------------------------
            # 10. get_index_consumption  (needs poc_number, pa)
            # ----------------------------------------------------------------
            print("\n📡 Testing get_index_consumption()...")
            if _poc and _pa:
                from datetime import date, timedelta
                today = date.today().isoformat()
                one_year_ago = (date.today() - timedelta(days=365)).isoformat()
                try:
                    cons_data = await api.get_index_consumption(
                        poc_number=_poc, pa=_pa,
                        start_date=one_year_ago, end_date=today,
                    )
                    if cons_data.get('error'):
                        print(f"❌ get_index_consumption failed: {cons_data}")
                    else:
                        print("✅ get_index_consumption successful!")
                        print(f"📄 Data: {json.dumps(cons_data, indent=2)}")
                except Exception as e:
                    print(f"❌ get_index_consumption error: {e}")
            else:
                print(f"⚠️  Skipped - missing poc_number or pa")

            # ----------------------------------------------------------------
            # 11. get_index_prognosis  (needs poc_number, pa, installation_number)
            # ----------------------------------------------------------------
            print("\n📡 Testing get_index_prognosis()...")
            if _poc and _pa and installation_number:
                try:
                    prog_data = await api.get_index_prognosis(
                        poc_number=_poc, pa=_pa,
                        installation_number=installation_number,
                    )
                    if prog_data.get('error'):
                        print(f"❌ get_index_prognosis failed: {prog_data}")
                    else:
                        print("✅ get_index_prognosis successful!")
                        print(f"📄 Data: {json.dumps(prog_data, indent=2)}")
                except Exception as e:
                    print(f"❌ get_index_prognosis error: {e}")
            else:
                print(f"⚠️  Skipped - missing poc_number ({_poc}), pa ({_pa}), or installation_number ({installation_number})")

            # ----------------------------------------------------------------
            # 12. get_invoice_history  (needs poc_number, pa)
            # ----------------------------------------------------------------
            print("\n📡 Testing get_invoice_history()...")
            if _poc and _pa:
                try:
                    from datetime import date as _date
                    _today = _date.today()
                    _prev_year = _today.year - 1

                    # Previous year
                    print(f"   Fetching previous year ({_prev_year})...")
                    inv_hist_prev = await api.get_invoice_history(
                        poc_number=_poc, pa=_pa,
                        start_date=_date(_prev_year, 1, 1).isoformat(),
                        end_date=_date(_prev_year, 12, 31).isoformat(),
                    )
                    if inv_hist_prev.get('error'):
                        print(f"❌ get_invoice_history (prev year) failed: {inv_hist_prev}")
                    else:
                        print(f"✅ Previous year successful!")
                        print(f"   📄 Full response: {json.dumps(inv_hist_prev, indent=2)}")

                    # Current year
                    print(f"   Fetching current year ({_today.year})...")
                    inv_hist_curr = await api.get_invoice_history(
                        poc_number=_poc, pa=_pa,
                        start_date=_date(_today.year, 1, 1).isoformat(),
                        end_date=_today.isoformat(),
                    )
                    if inv_hist_curr.get('error'):
                        print(f"❌ get_invoice_history (curr year) failed: {inv_hist_curr}")
                    else:
                        print(f"✅ Current year successful!")
                        print(f"   📄 Full response: {json.dumps(inv_hist_curr, indent=2)}")
                except Exception as e:
                    print(f"❌ get_invoice_history error: {e}")
            else:
                print(f"⚠️  Skipped - missing poc_number or pa")

            # ----------------------------------------------------------------
            # Summary
            # ----------------------------------------------------------------
            print("\n" + "=" * 40)
            print("📋 SUMMARY OF EXTRACTED ACCOUNT FIELDS")
            print("=" * 40)
            print(f"  contract_accounts   : {contract_accounts}")
            print(f"  account_id          : {account_id}")
            print(f"  pa                  : {pa}")
            print(f"  poc_number          : {poc_number}")
            print(f"  installation_number : {installation_number}")

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