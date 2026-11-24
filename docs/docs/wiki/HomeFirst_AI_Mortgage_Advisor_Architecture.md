# HomeFirst AI Mortgage Advisor

**Technical Architecture & Implementation Guide**

Version 1.1 | November 2026 | Confidential

---

# 1. Problem Statement

## 1.1 The Challenge

Traditional mortgage origination is expensive, time-consuming, and limited to business hours. Borrowers face:

- **Long wait times** to speak with loan officers
- **Inconsistent information** about eligibility and rates
- **Limited availability** outside business hours
- **Higher costs** passed on through interest rates

Lenders face:

- **High cost per call** for trained loan officers handling basic inquiries
- **Compliance risk** from inconsistent rule application
- **Missed opportunities** from after-hours calls going to voicemail

## 1.2 The Solution

**HomeFirst AI Mortgage Advisor** is a real-time voice AI system that:

1. **Answers calls 24/7** with natural voice conversation
2. **Screens eligibility** against state-specific lending rules
3. **Provides rate estimates** with required disclaimers
4. **Routes qualified callers** to licensed loan officers
5. **Services existing borrowers** with account information and payments

**Value Proposition:** By automating origination with AI, borrowers save **0.5% to 1% in interest** compared with traditional lenders.

## 1.3 Use Cases

| Use Case | Actor | Description |
|----------|-------|-------------|
| New Loan Inquiry | Prospective Borrower | HELOC, refinance, or purchase questions |
| Eligibility Check | Prospective Borrower | State-specific rule validation (e.g., Texas restrictions) |
| Rate Estimate | Prospective Borrower | Rates by credit tier and LTV with disclaimers |
| Account Balance | Existing Borrower | Check balance, payoff quote, payment history |
| Make Payment | Existing Borrower | One-time payment with authorization |
| Autopay Management | Existing Borrower | Setup, modify, or cancel autopay |

---

# 2. What We Have Implemented (Phase 1)

## 2.1 Multi-Agent Voice System

We have built a **production-ready voice AI system** with three specialized agents:

| Agent | Name | Role | Tools |
|-------|------|------|-------|
| **Triage** | Sam | Greets callers, asks qualifying questions, routes to specialist | 5 tools |
| **Origination** | Mac | Handles new loans, refinancing, HELOC, rate questions | 13 tools |
| **Servicing** | Ivy | Handles existing loan questions, payments, account management | 15 tools |

## 2.2 Implemented Capabilities

### Voice & Conversation
- Real-time, interruptible voice conversation
- Live captions and typed input fallback
- Sub-second response times
- Natural persona switching during calls

### Origination (Mac)
- HELOC eligibility with state rules (TX, CA, FL)
- Rate estimates by credit tier and LTV
- Equity and borrowing power calculations
- Product comparisons with alternatives
- Lead registration and loan officer transfer

### Servicing (Ivy)
- Two-level identity verification (basic + strong)
- Balance, payoff quotes, payment history
- Due date changes (1st-28th)
- Autopay setup and management
- Secure card capture (keypad only, never voice)
- One-time payments with read-back authorization

### Compliance & Security
- Policy door checks every tool call
- State rule enforcement (fail-closed)
- PII redaction in logs
- Payment authorization flow
- Verification lockout after 3 failures

## 2.3 Test Coverage

- **242 automated tests** passing
- Unit tests for all tools and policy rules
- State regulation scenario tests
- Payment authorization flow tests

---

# 3. High-Level Technical Architecture

## 3.1 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CALLER'S BROWSER                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ Microphone  │  │   Speaker   │  │  Captions   │  │  Agent UI   │        │
│  └──────┬──────┘  └──────▲──────┘  └──────▲──────┘  └──────▲──────┘        │
│         │                │                │                │                │
│         └────────────────┴────────────────┴────────────────┘                │
│                                   │                                          │
│                          WebSocket (wss://)                                  │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                         HOMEFIRST VOICE SERVICE                              │
│                           (FastAPI + Google ADK)                             │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                        MULTI-AGENT ROUTER                              │ │
│  │  ┌──────────┐      ┌──────────┐      ┌──────────┐                     │ │
│  │  │   SAM    │ ───► │   MAC    │      │   IVY    │                     │ │
│  │  │ (Triage) │      │(Lending) │      │(Servicing)│                    │ │
│  │  └──────────┘      └──────────┘      └──────────┘                     │ │
│  │       │                  │                 │                           │ │
│  │       └──────────────────┴─────────────────┘                           │ │
│  │                          │                                              │ │
│  │                   ┌──────▼──────┐                                      │ │
│  │                   │ POLICY DOOR │  ◄── Validates every tool call       │ │
│  │                   └──────┬──────┘                                      │ │
│  │                          │                                              │ │
│  │    ┌─────────────────────┼─────────────────────┐                       │ │
│  │    ▼                     ▼                     ▼                       │ │
│  │ ┌──────┐           ┌──────────┐          ┌──────────┐                 │ │
│  │ │Tools │           │ Mortgage │          │ Servicing│                 │ │
│  │ │ (29) │           │  Store   │          │ Database │                 │ │
│  │ └──────┘           └──────────┘          └──────────┘                 │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────┬───────────────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                         GOOGLE GEMINI LIVE API                               │
│                    (gemini-2.0-flash-live-preview)                           │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  • Bidirectional audio streaming                                       │ │
│  │  • Real-time speech recognition                                        │ │
│  │  • Natural language understanding                                      │ │
│  │  • Text-to-speech synthesis                                            │ │
│  │  • Function calling for tools                                          │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────┘
```

## 3.2 Key Design Principles

| Principle | Implementation |
|-----------|----------------|
| **Rules in Code, Not Prompts** | State lending rules enforced by tools, not AI instructions |
| **Fail Closed** | Unknown states/inputs route to loan officer, never approved |
| **Facts from Tools Only** | AI never invents rates, rules, or account data |
| **Persona Switching** | Single agent with dynamic instructions for seamless transfers |
| **Policy Door** | Every tool call validated before and after execution |

---

# 4. Detailed Technical Architecture

## 4.1 Component Diagram

```
┌────────────────────────────────────────────────────────────────────────────────┐
│                              VOICE SERVICE LAYER                                │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐            │
│  │   server.py     │    │    agent.py     │    │   persona.py    │            │
│  │                 │    │                 │    │                 │            │
│  │ • WebSocket     │───►│ • ADK Agent     │───►│ • Sam (triage)  │            │
│  │ • Audio bridge  │    │ • 29 tools      │    │ • Mac (lending) │            │
│  │ • Transcripts   │    │ • Policy hooks  │    │ • Ivy (service) │            │
│  │ • Usage tracking│    │ • run_live()    │    │ • Dynamic switch│            │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘            │
│           │                      │                      │                      │
│           ▼                      ▼                      ▼                      │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐            │
│  │   events.py     │    │   routing.py    │    │   policy.py     │            │
│  │                 │    │                 │    │                 │            │
│  │ • Event bus     │    │ • AgentType     │    │ • Tool access   │            │
│  │ • UI updates    │    │ • Intent detect │    │ • Verification  │            │
│  │ • Agent changes │    │ • Handoff logic │    │ • Input checks  │            │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘            │
│                                                                                 │
├────────────────────────────────────────────────────────────────────────────────┤
│                              DOMAIN LAYER                                       │
├────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────────────────────┐    ┌─────────────────────────────────┐   │
│  │          ORIGINATION            │    │           SERVICING             │   │
│  │                                 │    │                                 │   │
│  │  ┌───────────┐  ┌───────────┐  │    │  ┌───────────┐  ┌───────────┐  │   │
│  │  │mortgage.py│  │  tools.py │  │    │  │servicing. │  │servicing_ │  │   │
│  │  │           │  │           │  │    │  │   py      │  │ tools.py  │  │   │
│  │  │• Rules    │  │• 14 tools │  │    │  │• Loans    │  │• 15 tools │  │   │
│  │  │• Products │  │• Eligiblty│  │    │  │• Payments │  │• Balance  │  │   │
│  │  │• Officers │  │• Rates    │  │    │  │• Autopay  │  │• Autopay  │  │   │
│  │  │• Pricing  │  │• Leads    │  │    │  │• Methods  │  │• Payments │  │   │
│  │  └───────────┘  └───────────┘  │    │  └───────────┘  └───────────┘  │   │
│  │                                 │    │                                 │   │
│  │  ┌───────────────────────────┐ │    │  ┌───────────────────────────┐ │   │
│  │  │     mortgage.json         │ │    │  │      database.py          │ │   │
│  │  │     rate_sheet.json       │ │    │  │      (SQLite)             │ │   │
│  │  └───────────────────────────┘ │    │  └───────────────────────────┘ │   │
│  └─────────────────────────────────┘    └─────────────────────────────────┘   │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │                         KNOWLEDGE LAYER                                  │  │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐            │  │
│  │  │sources.   │  │ ingest.py │  │ index.py  │  │  search   │            │  │
│  │  │  yaml     │  │           │  │           │  │regulations│            │  │
│  │  │• TX rules │  │• Web fetch│  │• SQLite   │  │• Citations│            │  │
│  │  │• CA rules │  │• PDF parse│  │• Vectors  │  │• Sources  │            │  │
│  │  │• FL rules │  │• Approval │  │• Search   │  │           │            │  │
│  │  └───────────┘  └───────────┘  └───────────┘  └───────────┘            │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
└────────────────────────────────────────────────────────────────────────────────┘
```

## 4.2 Multi-Agent Routing Flow

```
                              ┌─────────────────┐
                              │  Caller Dials   │
                              └────────┬────────┘
                                       │
                                       ▼
                              ┌─────────────────┐
                              │   SAM (Triage)  │
                              │                 │
                              │ "Hi, this is    │
                              │  Sam with       │
                              │  HomeFirst..."  │
                              └────────┬────────┘
                                       │
                              ┌────────▼────────┐
                              │ Qualifying      │
                              │ Questions:      │
                              │                 │
                              │ "New loan or    │
                              │  existing?"     │
                              └────────┬────────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    │                  │                  │
                    ▼                  │                  ▼
         ┌──────────────────┐         │       ┌──────────────────┐
         │ "I want a new    │         │       │ "Question about  │
         │  loan/refinance" │         │       │  my mortgage"    │
         └────────┬─────────┘         │       └────────┬─────────┘
                  │                   │                │
                  ▼                   │                ▼
         ┌──────────────────┐         │       ┌──────────────────┐
         │ transfer_to_     │         │       │ transfer_to_     │
         │ specialist       │         │       │ specialist       │
         │ ("origination")  │         │       │ ("servicing")    │
         └────────┬─────────┘         │       └────────┬─────────┘
                  │                   │                │
                  ▼                   │                ▼
         ┌──────────────────┐         │       ┌──────────────────┐
         │   MAC (Lending)  │         │       │  IVY (Servicing) │
         │                  │         │       │                  │
         │ • HELOC check    │         │       │ • Verify ID      │
         │ • Rate estimates │         │       │ • Balance info   │
         │ • Compare options│         │       │ • Make payments  │
         │ • Register leads │         │       │ • Autopay mgmt   │
         └──────────────────┘         │       └──────────────────┘
                                      │
                              ┌───────▼───────┐
                              │ General Q&A   │
                              │ (Sam handles) │
                              │               │
                              │ • Company info│
                              │ • Products    │
                              │ • FAQs        │
                              └───────────────┘
```

## 4.3 Policy Door - Tool Call Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         TOOL CALL LIFECYCLE                              │
└─────────────────────────────────────────────────────────────────────────┘

   Agent requests tool call
            │
            ▼
   ┌────────────────────┐
   │  BEFORE CALLBACK   │
   │  (policy.py)       │
   │                    │
   │  □ Check agent has │◄─── Sam can't use get_loan_balance
   │    tool access     │     Mac can't use prepare_payment
   │                    │
   │  □ Validate inputs │◄─── State must be valid
   │                    │     Credit score in range
   │                    │
   │  □ Check verify    │◄─── Balance needs basic verify
   │    requirements    │     Payments need strong verify
   │                    │
   │  □ Check lockout   │◄─── 3 failed verifications = locked
   │                    │
   └─────────┬──────────┘
             │
             ▼ ALLOW or BLOCK
   ┌────────────────────┐
   │   EXECUTE TOOL     │
   │                    │
   │   mortgage.py or   │
   │   servicing.py     │
   │   functions        │
   └─────────┬──────────┘
             │
             ▼
   ┌────────────────────┐
   │  AFTER CALLBACK    │
   │  (policy.py)       │
   │                    │
   │  □ Add disclaimers │◄─── "Rates are estimates only..."
   │                    │
   │  □ Suggest LO      │◄─── Eligibility issues → offer transfer
   │    transfer        │
   │                    │
   │  □ Redact PII      │◄─── Phone, SSN, card numbers
   │    in logs         │
   │                    │
   │  □ Log action      │◄─── Audit trail
   │                    │
   └─────────┬──────────┘
             │
             ▼
   Return result to agent
```

---

# 5. Tools Catalogue & Orchestration

## 5.1 Tools by Agent

### Sam (Triage Agent) - 5 Tools

| Tool | Purpose | When Used |
|------|---------|-----------|
| `get_company_info` | Company hours, location, contact | "What are your hours?" |
| `get_mortgage_products` | List available products | "What loans do you offer?" |
| `answer_faq` | Common questions | "How do I apply?" |
| `verify_customer` | Basic ID check | Caller claims existing account |
| `transfer_to_specialist` | Route to Mac or Ivy | After qualifying questions |

### Mac (Origination Agent) - 13 Tools

| Tool | Purpose | When Used |
|------|---------|-----------|
| `check_heloc_eligibility` | State rules for HELOC | "Can I get a HELOC in Texas?" |
| `check_state_regulations` | Get state-specific rules | "What are Texas rules?" |
| `get_rate_estimate` | Rate by credit/LTV | "What rate can I get?" |
| `calculate_equity` | Equity and LTV | "How much can I borrow?" |
| `compare_options` | Rank products | "What's my best option?" |
| `search_regulations` | Cited regulation answers | "Why can't I get a HELOC?" |
| `get_mortgage_products` | Product details | "Tell me about HELOCs" |
| `answer_faq` | Common questions | General inquiries |
| `get_company_info` | Company information | Hours, contact |
| `verify_customer` | Basic verification | Existing customer check |
| `verify_customer_strong` | Strong verification | Before account access |
| `register_lead` | Create lead record | Capture interested caller |
| `transfer_to_loan_officer` | Connect to human LO | "I want to apply" |

### Ivy (Servicing Agent) - 15 Tools

| Tool | Purpose | Verification Required |
|------|---------|----------------------|
| `get_loan_balance` | Current balance, next payment | Basic |
| `get_payment_history` | Past payments | Basic |
| `get_payoff_quote` | Payoff amount | Basic |
| `get_autopay_status` | Autopay details | Basic |
| `get_payment_methods` | Saved payment methods | Basic |
| `change_payment_date` | Move due date (1st-28th) | Strong |
| `setup_autopay` | Enable autopay | Strong |
| `cancel_autopay` | Disable autopay | Strong |
| `initiate_secure_card_capture` | Start keypad card entry | Strong |
| `complete_secure_card_capture` | Finish card capture | Strong |
| `add_bank_account` | Add bank for payments | Strong |
| `set_default_payment_method` | Set preferred method | Strong |
| `remove_payment_method` | Delete saved method | Strong |
| `prepare_payment` | Stage payment for auth | Strong |
| `confirm_payment` | Execute after "yes" | Strong + Authorization |

## 5.2 Tool Orchestration Example

**Scenario:** Existing customer wants to make a payment

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Caller: "I want to make a payment on my mortgage"                       │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 1. SAM: Routes to Ivy                                                   │
│    Tool: transfer_to_specialist("servicing", "wants to make payment")   │
│    Result: CallState.active_agent = "servicing"                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 2. IVY: "I can help with that. May I have your name?"                   │
│    Caller: "John Smith"                                                 │
│    Tool: verify_customer("John Smith", "1234")                          │
│    Result: identity_strength = "basic"                                  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 3. IVY: Shows balance, requests strong verification for payment         │
│    Tool: verify_customer_strong(dob, balance_estimate)                  │
│    Result: identity_strength = "strong"                                 │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 4. IVY: Gets payment methods                                            │
│    Tool: get_payment_methods()                                          │
│    Result: [{bank: "Chase ****5678"}, {card: "Visa ****1234"}]          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 5. IVY: Prepares payment                                                │
│    Tool: prepare_payment(amount=1500, method="bank_5678", date="today") │
│    Result: pending_authorization = {amount: 1500, method: "****5678"}   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 6. IVY: "To confirm, $1,500 from Chase ending 5678 today. Authorize?"   │
│    Caller: "Yes"                                                        │
│    Tool: confirm_payment(authorized=True)                               │
│    Result: confirmation_number = "PMT-ABC123"                           │
└─────────────────────────────────────────────────────────────────────────┘
```

---

# 6. GCP Hosting Architecture

## 6.1 Production Deployment Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              GOOGLE CLOUD PLATFORM                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                         GLOBAL LOAD BALANCER                           │ │
│  │                     (Cloud Load Balancing + CDN)                       │ │
│  │                                                                        │ │
│  │  • SSL termination (managed certificates)                              │ │
│  │  • WebSocket support for voice streaming                               │ │
│  │  • DDoS protection                                                     │ │
│  └───────────────────────────────┬────────────────────────────────────────┘ │
│                                  │                                           │
│                                  ▼                                           │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                           CLOUD RUN                                    │ │
│  │                    (Serverless Containers)                             │ │
│  │                                                                        │ │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐    │ │
│  │  │  Voice Service   │  │  Voice Service   │  │  Voice Service   │    │ │
│  │  │   Instance 1     │  │   Instance 2     │  │   Instance N     │    │ │
│  │  │                  │  │                  │  │                  │    │ │
│  │  │ • FastAPI        │  │ • FastAPI        │  │ • FastAPI        │    │ │
│  │  │ • ADK Agent      │  │ • ADK Agent      │  │ • ADK Agent      │    │ │
│  │  │ • WebSocket      │  │ • WebSocket      │  │ • WebSocket      │    │ │
│  │  └──────────────────┘  └──────────────────┘  └──────────────────┘    │ │
│  │                                                                        │ │
│  │  Auto-scaling: 0 to 100 instances based on concurrent connections      │ │
│  └───────────────────────────────┬────────────────────────────────────────┘ │
│                                  │                                           │
│         ┌────────────────────────┼────────────────────────────┐             │
│         │                        │                            │             │
│         ▼                        ▼                            ▼             │
│  ┌──────────────┐    ┌────────────────────┐    ┌────────────────────┐      │
│  │ CLOUD SQL    │    │   SECRET MANAGER   │    │  CLOUD STORAGE     │      │
│  │ (PostgreSQL) │    │                    │    │                    │      │
│  │              │    │  • API keys        │    │  • Rate sheets     │      │
│  │  • Loans     │    │  • DB credentials  │    │  • Regulation docs │      │
│  │  • Customers │    │  • Service accounts│    │  • Call recordings │      │
│  │  • Payments  │    │                    │    │                    │      │
│  │  • Leads     │    │                    │    │                    │      │
│  └──────────────┘    └────────────────────┘    └────────────────────┘      │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                         VERTEX AI                                      │ │
│  │                                                                        │ │
│  │  ┌──────────────────────────────────────────────────────────────────┐ │ │
│  │  │                    GEMINI LIVE API                                │ │ │
│  │  │               (gemini-2.0-flash-live-preview)                     │ │ │
│  │  │                                                                   │ │ │
│  │  │  • Bidirectional audio streaming                                  │ │ │
│  │  │  • Real-time speech recognition                                   │ │ │
│  │  │  • Function calling                                               │ │ │
│  │  │  • Text-to-speech                                                 │ │ │
│  │  └──────────────────────────────────────────────────────────────────┘ │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                      MONITORING & LOGGING                              │ │
│  │                                                                        │ │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐          │ │
│  │  │ Cloud Logging  │  │ Cloud Monitor  │  │  Error Report  │          │ │
│  │  │                │  │                │  │                │          │ │
│  │  │ • Call logs    │  │ • Latency      │  │ • Exceptions   │          │ │
│  │  │ • Tool calls   │  │ • Error rates  │  │ • Alerts       │          │ │
│  │  │ • PII redacted │  │ • Token usage  │  │                │          │ │
│  │  └────────────────┘  └────────────────┘  └────────────────┘          │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

## 6.2 Network Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              INTERNET                                        │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CLOUD ARMOR (WAF)                                    │
│                                                                              │
│  • Rate limiting (prevent abuse)                                             │
│  • IP blocking (known bad actors)                                            │
│  • OWASP rules                                                               │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           VPC NETWORK                                        │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    PUBLIC SUBNET                                     │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │  Cloud Run (Voice Services)                                  │   │   │
│  │  │  - Ingress: Internal + Load Balancer only                    │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│                                    │ VPC Connector                           │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    PRIVATE SUBNET                                    │   │
│  │  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐           │   │
│  │  │   Cloud SQL   │  │ Memorystore   │  │  Filestore    │           │   │
│  │  │  (Private IP) │  │   (Redis)     │  │  (NFS)        │           │   │
│  │  └───────────────┘  └───────────────┘  └───────────────┘           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

# 7. Architectural Concerns & Security

## 7.1 Current Implementation Status

| Concern | Status | Implementation |
|---------|--------|----------------|
| PII Redaction in Logs | **Implemented** | `policy.py` redacts phone, SSN, card numbers |
| Conversation Guardrails | **Implemented** | Persona instructions restrict topics |
| Cross-Account Protection | **Implemented** | Verification required before account access |
| Tool Access Control | **Implemented** | Per-agent tool allow-lists in `policy.py` |
| Payment Authorization | **Implemented** | Read-back + explicit "yes" required |
| State Rule Enforcement | **Implemented** | Unknown states fail closed |
| Card Number Protection | **Implemented** | Voice capture blocked; keypad only |

## 7.2 PII Redaction

**Current Implementation:**

```python
# policy.py - Sensitive arguments redacted in logs
_SENSITIVE_ARGS = {"full_name", "phone", "phone_last_4", "email", "dob", "ssn"}

def _redact_for_log(args: dict) -> dict:
    """Redact sensitive fields for logging."""
    return {
        k: "***" if k in _SENSITIVE_ARGS else v
        for k, v in args.items()
    }
```

**What's Logged:**
- Tool name and timestamp
- Non-sensitive arguments
- Result status (success/failure)
- Policy verdict (allow/block)

**What's NOT Logged:**
- Full names
- Phone numbers
- Dates of birth
- Card numbers
- Account numbers

## 7.3 Conversation Guardrails

**Current Implementation:**

Each persona has explicit boundaries in their instructions:

```
SAM (Triage):
- "Never try to answer detailed mortgage questions — transfer to Mac"
- "Never access account details beyond basic verification — transfer to Ivy"
- "Never process payments or make account changes"

MAC (Origination):
- "Never approve a loan, lock a rate, or take an application"
- "Never give legal or tax advice"
- "Only speak facts from tool results"

IVY (Servicing):
- "Never process payment without read-back and explicit authorization"
- "Never reveal account info without verification"
- "Never change account without strong verification"
```

## 7.4 Cross-Account Protection (Non-Customer Asking About Another User's Loan)

**Current Implementation:**

```
┌─────────────────────────────────────────────────────────────────┐
│                   VERIFICATION FLOW                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Caller: "What's John Smith's balance?"                          │
│                           │                                      │
│                           ▼                                      │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Ivy: "I can look that up. First, may I verify           │    │
│  │       you're John Smith? What are the last 4 digits     │    │
│  │       of your phone number on file?"                    │    │
│  └─────────────────────────────────────────────────────────┘    │
│                           │                                      │
│           ┌───────────────┴───────────────┐                     │
│           │                               │                     │
│           ▼                               ▼                     │
│    Correct: "1234"               Wrong: "5678"                  │
│           │                               │                     │
│           ▼                               ▼                     │
│    verify_customer()              verify_customer()             │
│    Returns: MATCH                 Returns: NO MATCH             │
│           │                               │                     │
│           ▼                               ▼                     │
│    identity_strength              failed_verifications++        │
│    = "basic"                              │                     │
│           │                               ▼                     │
│           ▼                        ┌──────────────┐             │
│    Can access balance              │ 3 failures?  │             │
│                                    └──────┬───────┘             │
│                                           │                     │
│                              ┌────────────┴────────────┐        │
│                              │                         │        │
│                              ▼                         ▼        │
│                           No: Retry              Yes: LOCKED    │
│                                                        │        │
│                                                        ▼        │
│                                               "I'm unable to    │
│                                                verify you.      │
│                                                Let me transfer  │
│                                                to a loan        │
│                                                officer."        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Key Protections:**
1. No account data revealed until verification passes
2. Verification tied to specific customer record
3. 3-failure lockout prevents brute force
4. Lockout persists for entire call
5. Strong verification (DOB + balance) required for changes/payments

## 7.5 Phase 2 Security Enhancements

The following security features are planned for Phase 2:

### 7.5.1 Voice PII Detection & Redaction

```
┌─────────────────────────────────────────────────────────────────┐
│                 VOICE PII DETECTION (Phase 2)                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Caller Audio ──► Speech-to-Text ──► PII Detector ──► Redacted  │
│                                           │            Transcript│
│                                           │                      │
│                                           ▼                      │
│                                   ┌───────────────┐              │
│                                   │ Detect:       │              │
│                                   │ • SSN patterns│              │
│                                   │ • Card numbers│              │
│                                   │ • Account #s  │              │
│                                   │ • DOB         │              │
│                                   └───────────────┘              │
│                                           │                      │
│                                           ▼                      │
│                                   Replace with [REDACTED]        │
│                                   in stored transcripts          │
│                                                                  │
│  Implementation:                                                 │
│  • Google Cloud DLP API for PII detection                        │
│  • Real-time processing before storage                           │
│  • Configurable sensitivity levels                               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 7.5.2 Enhanced Conversation Guardrails

```
┌─────────────────────────────────────────────────────────────────┐
│              TOPIC BOUNDARY ENFORCEMENT (Phase 2)                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  User Message ──► Intent Classifier ──► Topic Router             │
│                                              │                   │
│                     ┌────────────────────────┼──────────────┐    │
│                     │                        │              │    │
│                     ▼                        ▼              ▼    │
│              ┌──────────┐            ┌──────────┐    ┌──────────┐│
│              │ Mortgage │            │ Off-Topic│    │ Harmful  ││
│              │ Related  │            │          │    │          ││
│              └────┬─────┘            └────┬─────┘    └────┬─────┘│
│                   │                       │               │      │
│                   ▼                       ▼               ▼      │
│              Process                 "I can only      Block +    │
│              normally                help with        Log +      │
│                                      mortgage         Alert      │
│                                      questions"                  │
│                                                                  │
│  Off-Topic Categories:                                           │
│  • General knowledge questions                                   │
│  • Other financial products (crypto, stocks)                     │
│  • Personal advice                                               │
│  • Entertainment                                                 │
│                                                                  │
│  Harmful Categories:                                             │
│  • Attempts to extract system prompts                            │
│  • Jailbreak attempts                                            │
│  • Requests for other customers' data                            │
│  • Social engineering attempts                                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 7.5.3 Agent Evaluations

```
┌─────────────────────────────────────────────────────────────────┐
│                  AGENT EVALUATION FRAMEWORK (Phase 2)            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    AUTOMATED TEST SUITE                     │ │
│  │                                                             │ │
│  │  1. Rule Accuracy Tests (existing: 242 tests)               │ │
│  │     • State regulation compliance                           │ │
│  │     • Eligibility decisions                                 │ │
│  │     • Rate calculations                                     │ │
│  │                                                             │ │
│  │  2. Conversation Scenario Tests (Phase 2)                   │ │
│  │     • Reference call scripts replayed                       │ │
│  │     • Edge cases (angry caller, confused caller)            │ │
│  │     • Multi-turn conversations                              │ │
│  │                                                             │ │
│  │  3. Safety Tests (Phase 2)                                  │ │
│  │     • Prompt injection attempts                             │ │
│  │     • Cross-account access attempts                         │ │
│  │     • Off-topic steering attempts                           │ │
│  │                                                             │ │
│  │  4. Performance Tests                                        │ │
│  │     • Response latency < 1 second                           │ │
│  │     • Interruption handling < 300ms                         │ │
│  │                                                             │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    LLM-AS-JUDGE EVALUATION                  │ │
│  │                                                             │ │
│  │  For each test conversation:                                │ │
│  │                                                             │ │
│  │  ┌─────────────────────────────────────────────────────┐   │ │
│  │  │ Evaluator LLM scores on:                             │   │ │
│  │  │                                                      │   │ │
│  │  │ • Accuracy: Did agent provide correct information?   │   │ │
│  │  │ • Helpfulness: Did agent address caller's need?      │   │ │
│  │  │ • Safety: Did agent stay within boundaries?          │   │ │
│  │  │ • Compliance: Were disclaimers provided?             │   │ │
│  │  │ • Tone: Was agent professional and empathetic?       │   │ │
│  │  └─────────────────────────────────────────────────────┘   │ │
│  │                                                             │ │
│  │  Scores aggregated into dashboards                          │ │
│  │  Regressions trigger alerts                                 │ │
│  │                                                             │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    HUMAN REVIEW QUEUE                       │ │
│  │                                                             │ │
│  │  Calls flagged for human review:                            │ │
│  │  • Low confidence scores                                    │ │
│  │  • Caller complaints                                        │ │
│  │  • Safety triggers                                          │ │
│  │  • Random sample (5%)                                       │ │
│  │                                                             │ │
│  │  Reviewers score and provide feedback                       │ │
│  │  Feedback used to improve prompts and rules                 │ │
│  │                                                             │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

# 8. Phase 2 Roadmap

## 8.1 Planned Capabilities

| Feature | Description | Priority |
|---------|-------------|----------|
| **Telephony (PSTN)** | Phone number access via Twilio/Google Voice | Must |
| **Warm Transfer** | Live handoff to loan officer with context | Must |
| **Call Recording** | Recorded calls with consent, stored securely | Must |
| **Voice PII Redaction** | Real-time PII detection in transcripts | Must |
| **Agent Evaluations** | Automated conversation testing in CI/CD | Should |
| **LO Agent** | AI assistant for licensed loan officers | Should |
| **MCP Integration** | Connect to LOS, CRM, pricing systems | Should |
| **Spanish Language** | Bilingual support | Could |

## 8.2 Telephony Architecture (Phase 2)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PHASE 2: TELEPHONY                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│     ┌───────────┐                                                           │
│     │  Caller   │                                                           │
│     │  (Phone)  │                                                           │
│     └─────┬─────┘                                                           │
│           │ PSTN                                                             │
│           ▼                                                                  │
│     ┌───────────────┐                                                       │
│     │    Twilio     │                                                       │
│     │  or Google    │                                                       │
│     │    Voice      │                                                       │
│     └───────┬───────┘                                                       │
│             │ SIP/WebRTC                                                     │
│             ▼                                                                │
│     ┌───────────────────────────────────────────────────────────────────┐   │
│     │                    VOICE GATEWAY SERVICE                           │   │
│     │                                                                    │   │
│     │  • Media transcoding (PSTN ↔ WebSocket)                           │   │
│     │  • Call recording with consent                                     │   │
│     │  • DTMF capture for secure card entry                              │   │
│     │  • Warm transfer to loan officer                                   │   │
│     │                                                                    │   │
│     └───────────────────────────────┬───────────────────────────────────┘   │
│                                     │                                        │
│                                     ▼                                        │
│     ┌───────────────────────────────────────────────────────────────────┐   │
│     │              EXISTING VOICE SERVICE (Cloud Run)                    │   │
│     │                                                                    │   │
│     │  Sam ──► Mac / Ivy ──► Gemini Live API                            │   │
│     │                                                                    │   │
│     └───────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

# 9. Summary

## 9.1 What We've Built

- **3 specialized AI agents** (Sam, Mac, Ivy) with distinct roles
- **29 tools** covering origination and servicing workflows
- **Real-time voice** with sub-second response times
- **State-specific rules** (TX, CA, FL) with fail-closed design
- **Identity verification** with 2 levels and lockout protection
- **Payment authorization** with read-back and explicit consent
- **Policy door** validating every tool call
- **242 automated tests** ensuring accuracy

## 9.2 Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Persona switching vs A2A | Seamless voice transfers without audio gaps |
| Rules in code, not prompts | Guaranteed compliance, testable |
| Fail closed | Unknown states/inputs never approved |
| Tool-based facts | AI never invents rates or rules |
| Strong verification for payments | Prevent unauthorized transactions |

## 9.3 Phase 2 Priorities

1. **Telephony** - Phone access for broader reach
2. **Voice PII redaction** - Enhanced privacy protection
3. **Agent evaluations** - Automated quality assurance
4. **Warm transfer** - Seamless handoff to humans
5. **MCP integration** - Connect to production systems

---

**Document Control**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | Nov 17, 2026 | Engineering | Initial document |
| 1.1 | Nov 23, 2026 | Engineering | Added Sam (triage agent), multi-agent routing |

---

*Confidential - HomeFirst AI Lending*
