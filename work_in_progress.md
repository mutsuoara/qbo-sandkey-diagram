# QBO Sankey Dashboard - Work In Progress

## Current Status: 🔄 **ACTIVE DEVELOPMENT**

**Last Updated**: October 28, 2025  
**Current Branch**: `test/manual-customer-pull`  
**Deployment**: Heroku v38 (Live)

---

## 🎯 **Primary Objective**
Create a Sankey diagram that displays real QuickBooks Online financial data with:
- **Income sources** grouped by customer
- **Expense categories** properly categorized
- **Real-time data** from live QBO instance (not sample data)

---

## 🚨 **Current Critical Issues**

### 1. **API Fault Handling Problem** ⚠️ **HIGH PRIORITY**
**Problem**: QuickBooks API returns `Fault` objects when using `columns=customer` parameter
- **Status**: API call returns HTTP 200 (appears successful)
- **Issue**: Response structure is `['Fault', 'time']` instead of `['Rows', 'ColData', ...]`
- **Impact**: Parser fails, falls back to sample data
- **Root Cause**: Customer grouping parameter not supported or incorrectly formatted

**Evidence from Logs**:
```
INFO - Successfully retrieved P&L report with customer grouping
INFO - Parsing P&L report structure: ['Fault', 'time']
WARNING - No 'Rows' found in response
ERROR - Failed to parse P&L data - check API response structure
```

### 2. **Sankey Diagram Shows Sample Data** ⚠️ **HIGH PRIORITY**
**Problem**: Dashboard displays template/sample data instead of real QuickBooks data
- **Status**: Real data is being fetched but not parsed correctly
- **Issue**: Fault objects prevent proper data parsing
- **Impact**: Users see generic sample data instead of their actual financial flows

### 3. **NoneType Error Resolved** ✅ **FIXED**
**Problem**: `'NoneType' object has no attribute 'lower'` errors
- **Status**: ✅ **RESOLVED** in v37
- **Solution**: Added null checks in account categorization methods
- **Impact**: Eliminated parsing crashes

---

## 🔧 **Solutions Implemented**

### ✅ **Completed Fixes**

#### 1. **Reverted from ProfitAndLossDetail to Standard P&L** (v38)
**What we did**:
- Removed complex ProfitAndLossDetail approach that was causing date parsing issues
- Updated `get_profit_and_loss()` to use `columns=customer` parameter
- Simplified `get_financial_data_for_sankey()` to use standard P&L parsing
- Fixed `_parse_row_data()` to use standard column structure

**Code Changes**:
```python
# Before: Complex ProfitAndLossDetail with transaction-level data
detail_data = self.get_profit_and_loss_detail(start_date, end_date)

# After: Simple P&L with customer grouping
params = {
    'start_date': start_date,
    'end_date': end_date,
    'columns': 'customer'  # Group income by customer
}
```

#### 2. **Fixed NoneType Errors** (v37)
**What we did**:
- Added null checks in `_categorize_account_dynamically()`
- Added null checks in `_is_income_account()` and `_is_expense_account()`
- Improved account name extraction with proper null handling

**Code Changes**:
```python
# Before: Direct .lower() call
account_lower = account_name.lower()

# After: Safe null checking
if not account_name or account_name is None:
    logger.warning(f"Account name is None or empty, defaulting to 'other'")
    return 'other'
account_lower = account_name.lower()
```

#### 3. **Fixed Column Structure Parsing** (v36)
**What we did**:
- Updated amount extraction to handle ProfitAndLossDetail's 8+ column structure
- Added fallback logic for different column positions
- Improved error handling for missing data

---

## 🔄 **Work In Progress**

### 1. **Fault Detection Implementation** 🚧 **IN PROGRESS**
**Current Issue**: `_make_request` method doesn't detect Fault objects
**Proposed Solution**:
```python
def _make_request(self, endpoint: str, params: Dict = None, retry_on_auth_error: bool = True) -> Optional[Dict]:
    # ... existing code ...
    if response.status_code == 200:
        data = response.json()
        if 'Fault' in data:
            logger.error(f"QuickBooks API Fault: {data}")
            return None
        return data
```

### 2. **Fallback Mechanism** 🚧 **PLANNED**
**Current Issue**: No fallback when customer grouping fails
**Proposed Solution**:
```python
def get_profit_and_loss(self, start_date: str = None, end_date: str = None) -> Optional[Dict]:
    # Try customer grouping first
    data = self._make_request('reports/ProfitAndLoss', params_with_customer)
    if data and 'Fault' not in data:
        return data
    
    # Fallback to standard P&L
    logger.warning("Customer grouping failed, using standard P&L")
    return self._make_request('reports/ProfitAndLoss', params_standard)
```

---

## 📊 **Technical Architecture**

### **Current Data Flow**:
```
User clicks "View Dashboard" 
→ get_financial_data_for_sankey()
→ get_profit_and_loss() with columns=customer
→ _make_request() returns Fault object
→ _parse_profit_loss_report() fails
→ Falls back to sample data
```

### **Target Data Flow**:
```
User clicks "View Dashboard"
→ get_financial_data_for_sankey()
→ get_profit_and_loss() with columns=customer
→ Fault detected → Fallback to standard P&L
→ _parse_profit_loss_report() succeeds
→ Real QuickBooks data displayed
```

---

## 🧪 **Testing Status**

### ✅ **Working Components**:
- OAuth authentication flow
- Token storage and refresh
- API connectivity to QuickBooks
- Dashboard UI rendering
- Sankey diagram creation (with sample data)

### ❌ **Failing Components**:
- Customer grouping API parameter
- Real data parsing and display
- Fault object handling

### 🧪 **Test Cases Needed**:
1. **Fault Detection Test**: Verify Fault objects are properly detected
2. **Fallback Test**: Ensure standard P&L works when customer grouping fails
3. **Real Data Test**: Confirm actual QuickBooks data displays in Sankey
4. **Customer Income Test**: Verify income sources show customer names

---

## 📋 **Next Steps**

### **Immediate (Next 1-2 hours)**:
1. **Implement fault detection** in `_make_request` method
2. **Add fallback mechanism** for customer grouping failures
3. **Test with standard P&L report** (no customer grouping)
4. **Deploy and verify** real data displays

### **Short Term (Next 1-2 days)**:
1. **Investigate customer grouping alternatives** (different API parameters)
2. **Implement customer income extraction** from invoices if needed
3. **Add comprehensive error handling** for all API responses
4. **Create automated tests** for data parsing

### **Medium Term (Next week)**:
1. **Optimize Sankey diagram performance** with large datasets
2. **Add date range filtering** for Sankey data
3. **Implement data export functionality** (PNG/PDF)
4. **Add customer-specific income breakdowns**

---

## 🔍 **Debugging Information**

### **Key Log Patterns**:
```
✅ SUCCESS: "OAuth tokens stored successfully"
✅ SUCCESS: "Successfully retrieved P&L report with customer grouping"
❌ ERROR: "Parsing P&L report structure: ['Fault', 'time']"
❌ ERROR: "No 'Rows' found in response"
❌ ERROR: "Failed to parse P&L data - check API response structure"
```

### **API Endpoints Used**:
- **Primary**: `GET /v3/company/{realm_id}/reports/ProfitAndLoss?columns=customer`
- **Fallback**: `GET /v3/company/{realm_id}/reports/ProfitAndLoss` (standard)

### **Environment Details**:
- **Environment**: Production QuickBooks
- **Realm ID**: 9130351249176506
- **Company**: Eastlake Karate
- **OAuth Status**: ✅ Authenticated and working

---

## 📝 **Notes & Observations**

### **What We've Learned**:
1. **ProfitAndLossDetail is transaction-level** - not suitable for Sankey diagrams
2. **Customer grouping parameter causes API faults** - may not be supported
3. **Standard P&L reports work reliably** - good fallback option
4. **OAuth flow is robust** - no authentication issues

### **QuickBooks API Limitations**:
- Customer grouping may not be available for all account types
- Some parameters cause Fault responses even with HTTP 200
- Transaction-level reports are too granular for financial flow visualization

### **Success Metrics**:
- ✅ OAuth authentication: 100% success rate
- ✅ API connectivity: 100% success rate  
- ❌ Real data display: 0% (showing sample data)
- ❌ Customer grouping: 0% (causing faults)

---

## 🎯 **Success Criteria**

### **Definition of Done**:
- [ ] Sankey diagram displays real QuickBooks data (not sample data)
- [ ] Income sources show actual customer names or revenue categories
- [ ] Expense categories show real account names
- [ ] No Fault-related errors in logs
- [ ] Dashboard loads within 5 seconds with real data
- [ ] All financial amounts match QuickBooks reports

### **Acceptance Criteria**:
- [ ] User can see their actual financial flows
- [ ] Data updates when date range changes
- [ ] No sample/template data visible
- [ ] Error handling provides clear feedback
- [ ] Application is stable and reliable

---

**Last Updated**: October 28, 2025 - 04:15 UTC  
**Next Review**: After implementing fault detection fix
