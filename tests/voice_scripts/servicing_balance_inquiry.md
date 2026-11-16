# Voice Test: Balance Inquiry Flow

## Scenario
Existing customer calls to check their loan balance.

## Test Customer
- Name: David Martinez
- Phone Last 4: 0188
- Loan Balance: ~$98,500

## Script

### 1. Call Connects
**Ivy:** "Hi, this is Ivy with HomeFirst AI servicing. This call may be recorded for quality. May I have your name to pull up your account?"

### 2. Customer Provides Name
**Caller:** "Hi, this is David Martinez."

**Ivy:** "Thank you David. For security, what are the last 4 digits of your phone number?"

### 3. Basic Verification
**Caller:** "0188"

**Expected:** `verify_customer` is called with:
- full_name: "David Martinez"
- phone_last_4: "0188"

**Ivy:** "I've got your account. How can I help you today?"

### 4. Balance Inquiry
**Caller:** "What's my loan balance?"

**Expected:** `get_loan_balance` is called.

**Ivy:** "Your current balance is $98,500. Your next payment of $923 is due December 1st."

### 5. Follow-up
**Ivy:** "Is there anything else I can help you with today?"

**Caller:** "No, that's all. Thank you."

**Ivy:** "You're welcome, David. Have a great day!"

## Assertions
- [ ] Ivy greets with servicing-specific greeting
- [ ] Basic verification required before balance
- [ ] Balance returned with next payment info
- [ ] Amounts spoken clearly
- [ ] Autopay suggestion if not enabled
