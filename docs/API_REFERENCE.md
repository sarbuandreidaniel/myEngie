"""MyEngie API Data Structure and Endpoints Reference

This document describes the MyEngie Romania API structure discovered through
browser inspection and network analysis.
"""

# Authentication
# ==============
# Provider: Auth0 (https://auth.engie.ro)
# Base URL: https://gwss.engie.ro/myservices/
#
# The application uses Auth0 for authentication with the following scopes:
# - openid
# - profile
# - email
# - offline_access
#
# After successful login, a Bearer JWT token is provided and must be included
# in all API requests in the Authorization header.
#
# Request Headers Required:
# - Authorization: Bearer {token}
# - Accept: application/json
# - Source: desktop
# - Origin: https://my.engie.ro
# - Referer: https://my.engie.ro/

# API Endpoints
# =============

# 1. Application Status
# GET /v2/app_status
# Purpose: Check application status and availability
# Response: Status information
# Example Response:
# {
#     "error": false,
#     "type": "GET",
#     "description": "App Status",
#     "data": {...},
#     "errors": [],
#     "domain": "https://myservices.engie.ro"
# }

# 2. Invoices and Balance Details
# POST /v1/invoices/ballance-details
# Purpose: Get invoice and balance details for account(s)
# Request Body:
# contract_account[]: {contract_account_ids}
# Example Response:
# {
#     "error": false,
#     "type": "GET",
#     "description": "Detalii sold",
#     "data": {
#         "total": "0.00",
#         "invoices": [...],
#         "pending": [...]
#     },
#     "errors": [],
#     "domain": "https://myservices.engie.ro"
# }

# 3. Gas/Electricity Index Data
# GET /v1/index/{poc_number}
# Purpose: Get consumption index and history
# Query Parameters:
# - poc_number: Point of Connection number (e.g., "5002533828")
# - division: "gaz" or "electric"
# - pa: Provider account ID (e.g., "191090997880")
# - installation_number: Installation number (e.g., "4002733447")
# Example Response:
# {
#     "error": false,
#     "type": "GET",
#     "description": "Detalii index",
#     "data": [
#         {
#             "poc_number": "5002533828",
#             "division": "gaz",
#             "installations": [
#                 {
#                     "installation_number": 4002733447,
#                     "pod": "PEYIFBERC305003",
#                     "autocit": "0000000",
#                     "last_index": "4417",
#                     "next_read_dates": {
#                         "startDate": "20-04-2026",
#                         "endDate": "25-04-2026"
#                     },
#                     "permite_index": true,
#                     "retransmission_key": false,
#                     "hide_index": false
#                 }
#             ]
#         }
#     ],
#     "errors": [],
#     "domain": "https://myservices.engie.ro"
# }

# 4. Balance Widget
# POST /v1/widgets/ballance
# Purpose: Get balance widget information
# Request Body:
# contract_account[]: {contract_account_ids}
# Example Response:
# {
#     "error": false,
#     "type": "GET",
#     "description": "Sold",
#     "data": {
#         "total": "0.00",
#         "details": [...]
#     },
#     "errors": [],
#     "domain": "https://myservices.engie.ro"
# }

# 5. Unread Notifications Count
# GET /v1/notifications/unread-number
# Purpose: Get count of unread notifications
# Response: Count of unread notifications

# 6. Notification Banner
# GET /v1/notifications/banner/{account_id}
# Purpose: Get notification banners for account
# Query Parameters:
# - pa: Provider account ID
# - account_class: "CS" (Customer)

# 7. User Invitations
# GET /v1/invitations
# Purpose: Get pending invitations for user
# Response: List of invitations

# 8. Banners (Marketing/Info)
# POST /v1/banners
# Purpose: Get marketing and informational banners
# Response: List of banners with content and metadata

# Account Data Structure
# ======================
#
# Key Identifiers:
# - POC Number: Point of Connection number (identifies the connection point)
# - Installation Number: Physical installation ID for gas/electric meter
# - POD: Point of Delivery (standardized facility identifier)
# - PA: Provider Account ID
# - Contract Account: Internal contract account number
#
# Example Account Info:
# {
#     "poc_number": "5002533828",         # Connection point identifier
#     "installation_number": 4002733447,   # Meter ID
#     "pod": "PEYIFBERC305003",            # Standardized facility code
#     "provider_account_id": "191090997880", # Provider internal ID
#     "contract_account": "2103540725",    # Contract account
#     "division": "gaz"                    # Service type (gas/electric)
# }

# Consumption Data Structure
# ==========================
#
# Index Information:
# {
#     "last_index": "4417",                # Current meter reading
#     "next_read_dates": {
#         "startDate": "20-04-2026",      # Next reading period start
#         "endDate": "25-04-2026"         # Next reading period end
#     },
#     "permite_index": true,               # Can submit new reading
#     "retransmission_key": false,        # Can retransmit reading
#     "hide_index": false                 # Display index on interface
# }

# Balance Data Structure
# ======================
#
# Balance Information:
# {
#     "total": "0.00",              # Total balance in RON
#     "invoices": [                    # List of invoices
#         {
#             # Invoice details...
#         }
#     ],
#     "pending": [                     # Pending payments
#         {
#             # Pending payment details...
#         }
#     ]
# }

# Response Structure
# ==================
#
# All API responses follow this structure:
# {
#     "error": false,                           # Error status
#     "type": "GET",                            # Request type
#     "description": "Description of data",    # Operation description
#     "data": {...},                           # Actual data payload
#     "errors": [],                            # Error details if any
#     "domain": "https://myservices.engie.ro" # Service domain
# }

# Consumption Timeline
# ====================
# 
# Historical Data Available:
# - Last 12 months of consumption data
# - Individual readings with dates and values
# - Transmission method for each reading (auto-reading, manual, estimate)
# - Consumption estimates based on historical patterns
#
# Available Periods for Analysis:
# - Last 12 months (default)
# - Last 24 months
# - Last 36 months
# - Custom date range
# - Comparison views

# Rate Limiting & Performance
# ===========================
#
# - Token validity: ~1 hour (3600 seconds)
# - Recommended update interval: 1 hour
# - Minimum update interval: 5 minutes (to avoid excessive API calls)
# - CORS enabled: Requests must come from approved origins
# - Caching: Responses can be cached based on update interval

# Error Handling
# ==============
#
# Error Response Structure:
# {
#     "error": true,
#     "type": "GET",
#     "description": "Error description",
#     "data": {},
#     "errors": ["error detail 1", "error detail 2"],
#     "domain": "https://myservices.engie.ro"
# }
#
# Common Errors:
# - 401: Unauthorized (invalid token)
# - 403: Forbidden (insufficient permissions)
# - 404: Not found (invalid account/resource)
# - 429: Rate limited
# - 500: Server error
