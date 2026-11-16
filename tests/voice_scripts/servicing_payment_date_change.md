# Voice Test: Payment Date Change Flow

## Scenario
Customer wants to change their monthly payment due date.
Requires strong verification.

## Test Customer
- Name: David Martinez
- Phone Last 4: 0188
- DOB: (any - we verify by balance)
- Loan Balance: ~$98,500

## Script

### 1. Basic Verification (same as balance inquiry)
[Basic verification flow - see servicing_balance_inquiry.md]

### 2. Payment Date Change Request
**Caller:** "Can I change my payment date to the 15th?"

**Expected:** Policy blocks until strong verification.

**Ivy:** "I can help with that. First, for security, can you confirm your date of birth and your approximate loan balance?"

### 3. Strong Verification
**Caller:** "March 15, 1985. My balance is around $98,000."

**Expected:** `verify_customer_strong` is called with:
- date_of_birth: "March 15, 1985"
- approximate_loan_balance: 98000

**Ivy:** "Thank you for verifying, David."

### 4. Process Date Change
**Expected:** `change_payment_date` is called with:
- new_payment_day: 15

**Ivy:** "I've updated your due date from the 1st to the 15th. Your next payment of $923 will be due on the 15th."

### 5. Observer Suggestion
**Observer suggests:** "Offer to schedule the next payment"

**Ivy:** "Would you like to schedule that payment now so nothing slips through the cracks?"

## Assertions
- [ ] Strong verification required before date change
- [ ] Date change succeeds with valid day (1-28)
- [ ] Confirmation of old and new dates
- [ ] Observer suggestion appears naturally
