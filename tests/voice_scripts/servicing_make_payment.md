# Voice Test: Make Payment Flow

## Scenario
Customer wants to make a one-time payment.
Requires strong verification and explicit authorization.

## Test Customer
- Name: David Martinez
- Phone Last 4: 0188
- Loan Balance: ~$98,500
- Has payment method on file: Chase Bank ...4521

## Script

### 1. Basic Verification
[Basic verification flow - see servicing_balance_inquiry.md]

### 2. Payment Request
**Caller:** "I'd like to make a payment."

**Ivy:** "I can help with that. For security, can you confirm your date of birth and approximate loan balance?"

### 3. Strong Verification
**Caller:** "My birthday is March 15, 1985 and my balance is about $98,500."

**Expected:** `verify_customer_strong` is called.

### 4. Prepare Payment
**Caller:** "I want to pay $923."

**Expected:** `prepare_payment` is called with:
- amount: 923.00
- payment_method_id: "" (uses default)

**Ivy:** "To confirm: I'll charge $923 to the Chase Bank account ending in 4521 today, [date]. Do I have your authorization to proceed?"

### 5. Authorization
**Caller:** "Yes"

**Expected:** `confirm_payment` is called with:
- authorized: True

**Ivy:** "Your payment of $923 has been processed. Your confirmation number is REF[number]. Is there anything else I can help with?"

## Alternative: Payment Declined

### 5a. No Authorization
**Caller:** "Actually, wait - let me think about it."

**Expected:** `confirm_payment` is called with:
- authorized: False

**Ivy:** "No problem. The payment has been cancelled. Would you like to do something else?"

## Assertions
- [ ] Strong verification required before payment
- [ ] Payment prepared with full readback
- [ ] Explicit "yes" required before processing
- [ ] Confirmation number provided
- [ ] Balance updated after payment
- [ ] Payment cancelled gracefully if declined
