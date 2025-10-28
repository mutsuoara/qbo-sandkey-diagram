# QBO Sankey Dashboard - Log Analysis

## Last Logs Pulled (2025-10-28T03:52:48 - 2025-10-28T04:03:12)

### Application Startup
```
2025-10-28T03:53:03.196620+00:00 app[web.1]: 2025-10-28 03:53:03,196 - INFO - ==================================================
2025-10-28T03:53:03.196682+00:00 app[web.1]: 2025-10-28 03:53:03,196 - INFO - QBO Sankey Dashboard - Starting Application
2025-10-28T03:53:03.196760+00:00 app[web.1]: 2025-10-28 03:53:03,196 - INFO - Startup time: 2025-10-28 03:53:03
2025-10-28T03:53:03.196817+00:00 app[web.1]: 2025-10-28 03:53:03,196 - INFO - ==================================================
```

### OAuth Flow Success
```
2025-10-28T04:03:00.631492+00:00 app[web.1]: 2025-10-28 04:03:00,631 - INFO - OAuth callback received
2025-10-28T04:03:00.631583+00:00 app[web.1]: 2025-10-28 04:03:00,631 - INFO - OAuth callback - Code: XAB1176162..., Realm: 9130351249176506, State: aDP2Cf-5eB8BP4YhiPQQnZKfmqe0048nVpDcabhQyzY
2025-10-28T04:03:01.078536+00:00 app[web.1]: 2025-10-28 04:03:01,078 - INFO - Token exchange response status: 200
2025-10-28T04:03:01.108714+00:00 app[web.1]: 2025-10-28 04:03:01,086 - INFO - OAuth tokens stored successfully
2025-10-28T04:03:02.204883+00:00 app[web.1]: 2025-10-28 04:03:02,204 - INFO - Company info stored successfully
2025-10-28T04:03:02.204954+00:00 app[web.1]: 2025-10-28 04:03:02,204 - INFO - OAuth flow completed successfully
```

### Dashboard Access Attempt
```
2025-10-28T04:03:06.444508+00:00 app[web.1]: 2025-10-28 04:03:06,444 - INFO - View Dashboard button clicked
2025-10-28T04:03:06.444548+00:00 app[web.1]: 2025-10-28 04:03:06,444 - INFO - Creating dashboard page with Sankey diagrams
2025-10-28T04:03:06.445384+00:00 app[web.1]: 2025-10-28 04:03:06,445 - INFO - Getting P&L report with customer grouping for Sankey diagram...
2025-10-28T04:03:06.445432+00:00 app[web.1]: 2025-10-28 04:03:06,445 - INFO - Attempting P&L report with customer grouping...
```

### API Call Success but Data Structure Issue
```
2025-10-28T04:03:07.334889+00:00 app[web.1]: 2025-10-28 04:03:07,334 - INFO - Successfully retrieved P&L report with customer grouping
2025-10-28T04:03:07.334941+00:00 app[web.1]: 2025-10-28 04:03:07,334 - INFO - Parsing P&L report structure: ['Fault', 'time']
2025-10-28T04:03:07.334997+00:00 app[web.1]: 2025-10-28 04:03:07,334 - WARNING - No 'Rows' found in response
2025-10-28T04:03:07.335044+00:00 app[web.1]: 2025-10-28 04:03:07,335 - ERROR - Failed to parse P&L data - check API response structure
2025-10-28T04:03:07.335093+00:00 app[web.1]: 2025-10-28 04:03:07,335 - ERROR - Error getting financial data for Sankey: Failed to parse Profit & Loss data. The data structure may have changed.
2025-10-28T04:03:07.335145+00:00 app[web.1]: 2025-10-28 04:03:07,335 - ERROR - Error fetching real data: Failed to parse Profit & Loss data. The data structure may have changed.
```

## Key Issues Identified

### 1. **API Response Structure Problem**
- **Status**: API call returns HTTP 200 (success)
- **Issue**: Response contains `['Fault', 'time']` instead of expected `['Rows', 'ColData', ...]`
- **Root Cause**: The `columns=customer` parameter is causing QuickBooks to return a Fault object

### 2. **Fault Handling**
- The `_make_request` method returns the Fault object instead of `None`
- The parsing logic expects a `Rows` structure but gets a `Fault` structure
- No fallback mechanism is triggered because the API call appears "successful"

### 3. **Customer Grouping Not Supported**
- QuickBooks API is rejecting the `columns=customer` parameter
- This suggests that either:
  - The parameter is not supported for this company/account type
  - The parameter syntax is incorrect
  - The account doesn't have customer data configured properly

## Recommended Solutions

### Option 1: Fix Fault Handling
Modify `_make_request` to detect and handle Fault objects:
```python
if response.status_code == 200:
    data = response.json()
    if 'Fault' in data:
        logger.error(f"QuickBooks API Fault: {data}")
        return None
    return data
```

### Option 2: Remove Customer Grouping
Remove the `columns=customer` parameter and use standard P&L report:
```python
params = {
    'start_date': start_date,
    'end_date': end_date
    # Remove 'columns': 'customer'
}
```

### Option 3: Implement Proper Fallback
Add explicit fault detection in the P&L method:
```python
data = self._make_request('reports/ProfitAndLoss', params)
if data and 'Fault' in data:
    logger.warning("Customer grouping failed, falling back to standard P&L")
    # Retry without customer grouping
```

## Current Status
- ✅ OAuth authentication working perfectly
- ✅ API connectivity established
- ❌ Customer grouping parameter causing API faults
- ❌ Sankey diagram falling back to sample data
- ❌ No real QuickBooks data being displayed

## Next Steps
1. Implement fault detection in `_make_request`
2. Add proper fallback mechanism for customer grouping
3. Test with standard P&L report (no customer grouping)
4. Verify real data is displayed in Sankey diagram
