---
title: "Mac — AI Mortgage Advisor"
subtitle: "Use Cases, Scope and Requirements · Phase 1 (current release) and Phase 2 (planned)"
date: "23 November 2026 · Version 1.1 · Updated with multi-agent triage"
---

::: meta
**HomeFirst AI Lending.** Phase 1 describes the system as built in the `mortgage-advisor-ai-adk` repository. **Version 1.1** adds the Sam (triage) agent for caller routing. Phase 2 describes planned capabilities: MCP integration, an LO Agent, and transfer from the CCS Agent to the LO Agent.
:::

# 1. Introduction

## 1.1 Purpose

This document defines the use cases, scope and requirements for Mac, an AI voice agent for mortgage origination and servicing. It is the reference for product, engineering, compliance and operations teams.

## 1.2 Product summary

Mac is a real-time voice agent that helps home buyers and homeowners find the right mortgage, checks eligibility against state rules, and connects qualified callers to a licensed loan officer. The same service hosts **Ivy**, a servicing persona that helps existing borrowers with balances, payments and autopay. A new **triage agent (Sam)** greets all callers, asks qualifying questions, and routes them to the appropriate specialist—Mac for new loans or Ivy for existing loan servicing. By automating origination with AI, HomeFirst aims to save borrowers **0.5% to 1% in interest** compared with traditional lenders.

## 1.3 Objectives

| # | Objective | Measure |
|---|---|---|
| O1 | Answer mortgage enquiries around the clock | Calls handled without a human; caller satisfaction |
| O2 | Screen eligibility correctly before a loan officer spends time | 100% accuracy on regulated test scenarios |
| O3 | Hand qualified callers to a loan officer with full context | Time to loan officer; loan officer rating of the hand-off |
| O4 | Serve existing borrowers securely | Zero unauthorised account changes or payments |
| O5 | Lower origination cost to fund the 0.5–1% rate saving | Cost per call versus human-handled cost |

## 1.4 Conventions

Requirement IDs: **UC** use case, **FR** functional requirement, **BR** business rule, **NFR** non-functional requirement. Phase 2 items carry a **P2-** prefix. Priority uses **Must**, **Should**, **Could**. Phase 1 status is **Built** (in the code and tested), **Partial** (in the code with a known gap) or **Planned**.

## 1.5 Assumptions

- **CCS Agent** means the current customer-facing voice agent: Mac for origination and Ivy for servicing.
- **LO Agent** is a new AI agent that supports, and works under, a licensed loan officer. It does not replace one.
- Phase 1 runs as a web voice client; phone (PSTN) access is a later phase.
- Card capture, loan officer transfer and loan origination system (LOS) updates are simulated in Phase 1.

# 2. Stakeholders and actors

| Actor | Type | Description |
|---|---|---|
| Prospective borrower | Human | Home buyer or homeowner asking about a new loan, refinance or HELOC |
| Existing borrower | Human | Customer with a loan serviced by HomeFirst |
| Sam (CCS Agent, triage) | AI agent | Greets callers, asks qualifying questions, routes to Mac or Ivy |
| Mac (CCS Agent, origination) | AI agent | Answers enquiries, screens eligibility, compares options, registers leads, transfers |
| Ivy (CCS Agent, servicing) | AI agent | Verifies identity; handles balances, payoff, autopay, payments and payment methods |
| LO Agent (Phase 2) | AI agent | Continues qualified conversations under a licensed loan officer |
| Licensed loan officer (LO) | Human | NMLS-licensed originator who takes applications and makes offers |
| Compliance officer | Human | Approves regulation sources, rules and scripts |
| Operations supervisor | Human | Monitors calls, actions, policy verdicts and cost |
| External systems | System | Gemini Live API; in Phase 2, LOS, CRM, pricing engine and calendars via MCP |

# 3. Scope

## 3.1 Phase 1 scope (current release)

| Area | In scope |
|---|---|
| Voice | Real-time, interruptible voice conversation in the browser with captions and typed fallback |
| Origination (Mac) | Products, rate estimates, HELOC eligibility with state rules, equity, option comparison, regulation questions with citations, lead registration, transfer request |
| Servicing (Ivy) | Two-level identity verification, balance, payoff quote, payment history, due-date change, autopay, one-time payment with read-back and authorisation, payment method management |
| Compliance | Policy checks on every action, fail-closed state rules, disclaimers, regulation knowledge pipeline with approval step |
| Operations | Live action log, policy verdicts, token and cost tracking |
| States | Texas, California and Florida rules on file; all other states routed to a loan officer |

## 3.2 Out of scope for Phase 1

- Phone (PSTN) calls and real call transfer.
- Live pricing feed; rates come from a sample rate sheet.
- Writing to a real LOS or CRM.
- Taking a formal loan application, approving loans, locking rates.
- Collections and welcome-call personas (defined in code for a later phase).
- Legal or tax advice.

## 3.3 Phase 2 scope (planned)

| Feature | Summary |
|---|---|
| MCP integration | Connect agents to back-office systems through MCP servers, and publish Mac's governed tools as an MCP server |
| LO Agent | A new AI agent that continues the conversation after screening: scenario review, pre-qualification estimate, document checklist, application intake draft and scheduling, under a licensed loan officer |
| CCS → LO Agent transfer | A warm, in-call transfer from the CCS Agent to the LO Agent that carries the full context, with consent and a fallback to a human loan officer |

Phone channel, persistent production storage, live pricing and additional states are expected to follow, and are not scheduled in this document.

# 4. Phase 1 use cases

## 4.1 Use case summary

| ID | Use case | Primary actor | Agent | Status |
|---|---|---|---|---|
| UC-01 | Start a call, greet and triage the caller | Any caller | Sam | Built |
| UC-01a | Transfer caller to specialist (Mac or Ivy) | Any caller | Sam | Built |
| UC-02 | Check HELOC eligibility (reference call) | Prospective borrower | Mac | Built |
| UC-03 | Compare mortgage options | Prospective borrower | Mac | Partial |
| UC-04 | Get a rate estimate | Prospective borrower | Mac | Built |
| UC-05 | Calculate equity and borrowing power | Prospective borrower | Mac | Built |
| UC-06 | Ask a regulation question | Prospective borrower | Mac | Partial |
| UC-07 | Ask about products, company or FAQs | Any caller | Mac | Built |
| UC-08 | Register a lead for follow-up | Prospective borrower | Mac | Built |
| UC-09 | Request a licensed loan officer | Any caller | Mac / Ivy | Partial |
| UC-10 | Verify identity (basic and strong) | Existing borrower | Ivy | Partial |
| UC-11 | Check balance, payoff or payment history | Existing borrower | Ivy | Built |
| UC-12 | Change the payment due date | Existing borrower | Ivy | Built |
| UC-13 | Set up or cancel autopay | Existing borrower | Ivy | Built |
| UC-14 | Make a one-time payment | Existing borrower | Ivy | Built |
| UC-15 | Manage payment methods | Existing borrower | Ivy | Built |
| UC-16 | Receive proactive suggestions (observer) | Mac / Ivy | System | Built |
| UC-17 | Maintain regulation knowledge | Compliance officer | System | Partial |
| UC-18 | Monitor a call | Operations supervisor | System | Built |

## 4.2 Key use case specifications

### UC-02 Check HELOC eligibility (reference call)

| Item | Detail |
|---|---|
| Actor | Prospective borrower |
| Trigger | Caller asks whether they can get a HELOC on a property |
| Preconditions | Call connected; Mac has greeted the caller |
| Main flow | 1. Caller describes properties, state and amount ("a couple of properties in Texas… around $40,000… one is a property I rent out"). 2. Mac calls `check_heloc_eligibility` with the state and the caller's own words for property use. 3. The system normalises "rent out" to investment and applies Texas rules: not eligible. 4. Mac explains and asks about the primary residence. 5. Caller gives balance ($100,000), value ($550,000) and an existing cash-out. 6. Mac checks again: not eligible because of the existing cash-out. 7. Mac offers alternatives (refinance then HELOC, or another cash-out refinance) and offers a licensed loan officer. 8. Caller agrees; UC-09 follows. |
| Alternate flows | State without rules on file: Mac says it can't confirm and offers a loan officer. Property use unclear: Mac asks the caller to clarify. |
| Postconditions | Eligibility outcome and alternatives logged in the action log |
| Rules | BR-01 to BR-05 |

### UC-03 Compare mortgage options

| Item | Detail |
|---|---|
| Actor | Prospective borrower |
| Trigger | Caller asks for their best option |
| Main flow | 1. Mac gathers state, property value, balance, credit score, cash needed, property use and existing cash-out. 2. The policy door blocks the call until property use and existing cash-out are known. 3. `compare_options` runs the eligibility rules first, then prices HELOC, cash-out refinance and rate-and-term refinance from the rate sheet. 4. Mac presents eligible options with rate, payment and payment type, and explains excluded options. |
| Alternate flows | No eligible option: Mac offers a loan officer. Unknown state: blocked, loan officer offered. |
| Rules | BR-01 to BR-07 |
| Known gap | Rates and "below market" figures come from sample data (see 9.2) |

### UC-09 Request a licensed loan officer

| Item | Detail |
|---|---|
| Actor | Any caller |
| Trigger | Caller asks for a person, wants to apply, or Mac reaches the limit of what it may do |
| Main flow | 1. Mac calls `transfer_to_loan_officer` with a reason and specialty. 2. The system selects an officer with the specialty who is working now in their time zone. 3. Mac says who will help; a transfer record is created. |
| Alternate flows | No officer available: Mac promises a call-back within one business hour |
| Phase 1 limit | The transfer is a record only; no call is connected. Phase 2 adds the LO Agent transfer (P2-UC-03). |

### UC-10 Verify identity

| Item | Detail |
|---|---|
| Actor | Existing borrower |
| Main flow | 1. Basic: name and last 4 digits of phone (`verify_customer`). Unlocks balance, history, payoff, autopay status, payment methods. 2. Strong: date of birth and approximate loan balance within $5,000 (`verify_customer_strong`). Unlocks changes, autopay, payment methods and payments. |
| Alternate flows | Three failed attempts lock verification for the call; Ivy offers a loan officer |
| Known gap | Date of birth is collected but not yet checked (see 9.2) |

### UC-14 Make a one-time payment

| Item | Detail |
|---|---|
| Actor | Existing borrower (strong verification) |
| Main flow | 1. Caller asks to pay. 2. If needed, Ivy starts secure keypad card capture or adds a bank account; card numbers are never taken by voice. 3. `prepare_payment` sets amount, method and date. 4. Ivy reads back amount, last 4 digits and date and asks for authorisation. 5. Only after a clear "yes" does `confirm_payment(authorized=True)` run. 6. Ivy gives the confirmation number. |
| Alternate flows | Caller declines: payment cancelled. `confirm_payment` without a prepared payment or without authorisation is blocked. |
| Rules | BR-10 to BR-12 |

# 5. Phase 1 functional requirements

## 5.1 Conversation and voice

| ID | Requirement | Priority | Status |
|---|---|---|---|
| FR-01 | Hold a real-time voice conversation; stop speaking when interrupted and resume the thread | Must | Built |
| FR-02 | Greet the caller, state that the agent is an AI, and give the persona's greeting | Must | Built |
| FR-03 | Show live captions for both sides and accept typed input | Should | Built |
| FR-04 | Speak numbers clearly and explain jargon (LTV, CLTV, DTI) | Must | Built |
| FR-05 | Use tool results for every fact; never invent rates, products or rules | Must | Built |
| FR-06 | Route callers through Sam (triage) to Mac or Ivy based on the caller's need; switch personas during a call | Should | Built |

## 5.2 Origination (Mac)

| ID | Requirement | Priority | Status |
|---|---|---|---|
| FR-10 | Check HELOC eligibility using state rules, property use (caller's own words) and existing cash-out | Must | Built |
| FR-11 | Explain why a product is not available and present alternatives | Must | Built |
| FR-12 | Treat states with no approved rules as "needs loan officer review", never as eligible | Must | Built |
| FR-13 | Calculate equity, loan-to-value and maximum borrowing | Must | Built |
| FR-14 | Give rate estimates by product, credit tier and LTV band, always with the disclaimer | Must | Built |
| FR-15 | Compare eligible options with rate, payment and payment type; list excluded options with reasons | Should | Partial |
| FR-16 | Describe products and answer FAQs and company questions | Must | Built |
| FR-17 | Register a lead with name, phone, enquiry type, state and summary, and assign an officer | Must | Built |

## 5.3 Regulation knowledge

| ID | Requirement | Priority | Status |
|---|---|---|---|
| FR-20 | Ingest approved web and document sources (robots.txt respected, rate limited) | Must | Built |
| FR-21 | Detect changes to sources and hold changed content for compliance approval | Must | Built |
| FR-22 | Answer regulation questions only from approved passages, with the source named | Must | Partial |
| FR-23 | Never decide eligibility from search results; use structured rules | Must | Built |

## 5.4 Servicing (Ivy)

| ID | Requirement | Priority | Status |
|---|---|---|---|
| FR-30 | Provide balance, next payment, past-due status and payoff quote | Must | Built |
| FR-31 | Provide payment history | Must | Built |
| FR-32 | Change the monthly due date (1st to 28th) | Should | Built |
| FR-33 | Show, set up and cancel autopay | Must | Built |
| FR-34 | Capture card details by secure keypad entry; never by voice | Must | Built |
| FR-35 | Add bank accounts, set a default method, remove a method | Should | Built |
| FR-36 | Take a one-time payment only after read-back and explicit authorisation | Must | Built |
| FR-37 | Offer hardship options empathetically on past-due accounts | Should | Built |

## 5.5 Identity and security

| ID | Requirement | Priority | Status |
|---|---|---|---|
| FR-40 | Basic verification (name + phone last 4) before any account information | Must | Built |
| FR-41 | Strong verification (date of birth + approximate balance) before changes or payments | Must | Partial |
| FR-42 | Lock verification after three failed attempts and offer a human | Must | Built |
| FR-43 | Read back only the last 4 digits of any card or account | Must | Built |
| FR-44 | Redact personal data in logs | Must | Built |
| FR-45 | Restrict each persona to its own tool set | Should | Partial |

## 5.6 Hand-off, monitoring and observer

| ID | Requirement | Priority | Status |
|---|---|---|---|
| FR-50 | Select an available officer by specialty, day and working hours in the officer's time zone | Must | Partial |
| FR-51 | Create a transfer record or promise a call-back | Must | Built |
| FR-52 | Show every action and policy verdict to the supervisor view | Should | Built |
| FR-53 | Track tokens and estimated cost per call and per server | Should | Built |
| FR-54 | Suggest helpful talking points from tool results (autopay, hardship, equity) | Could | Built |

# 6. Business rules

| ID | Rule | Source / owner |
|---|---|---|
| BR-01 | Texas home equity lending (including HELOCs) is allowed only on a homestead; never on investment property | Texas Const. Art. XVI §50 |
| BR-02 | Texas: no HELOC while an existing home equity loan (including a Texas cash-out refinance) is on the homestead | Texas Const. Art. XVI §50 |
| BR-03 | Texas: combined loan-to-value at most 80% | Texas Const. Art. XVI §50 |
| BR-04 | Texas: 12-day notice before closing and 3-day right to cancel after closing | Texas Const. Art. XVI §50; Reg Z |
| BR-05 | Texas cash-out refinance: at most one in 12 months; 80% LTV cap | Texas Const. Art. XVI §50 |
| BR-06 | Any state without approved rules: no eligibility answer; route to a loan officer | HomeFirst policy |
| BR-07 | Every rate statement carries the rate disclaimer; rates are estimates only | Reg Z advertising; HomeFirst policy |
| BR-08 | The AI never approves a loan, locks a rate, takes an application or gives legal or tax advice | SAFE Act; HomeFirst policy |
| BR-09 | Basic verification before account data; strong verification before changes or payments | HomeFirst security policy |
| BR-10 | No card number is captured by voice | PCI DSS |
| BR-11 | Payments need read-back and an explicit "yes" before processing | HomeFirst policy; Reg E |
| BR-12 | Due date may be set between the 1st and 28th | Servicing policy |

<p class="note">Rules BR-01 to BR-05 and the related wording must be approved by compliance counsel before customer use.</p>

# 7. Non-functional requirements

| ID | Category | Requirement | Phase 1 |
|---|---|---|---|
| NFR-01 | Latency | Agent starts speaking within 1 s; stops within 300 ms of an interruption; tools return in under 50 ms | Built |
| NFR-02 | Accuracy | 100% pass on regulated rule and policy tests before each release | Built |
| NFR-03 | Testability | Unit tests for every tool and policy rule; end-to-end call scenarios | Partial |
| NFR-04 | Security | No secrets in source control; PII redacted in logs; payment data tokenised | Partial |
| NFR-05 | Privacy | Personal data minimised; per-call state cleared at call end | Built |
| NFR-06 | Auditability | Every action, verdict and rule source recorded per call | Partial |
| NFR-07 | Observability | Token use and cost per call | Built |
| NFR-08 | Availability | Graceful "call you back" message on model or network failure | Partial |
| NFR-09 | Scalability | Single process in Phase 1; stateless design ready for horizontal scale | Partial |
| NFR-10 | Maintainability | Rules and rates in data files; back office behind swappable store classes | Built |

# 8. Phase 1 solution design

## 8.1 Architecture

![Figure 1. Phase 1 architecture](images/phase1.png)

The browser streams microphone audio over a WebSocket to a FastAPI service. A single Google ADK agent runs a Gemini Live session (`run_live`) and loads its instructions from a function on every turn, enabling **dynamic persona switching** between three agents: Sam (triage), Mac (origination) and Ivy (servicing).

**Multi-agent routing flow:**

```
Caller connects
      ↓
Sam (Triage) greets: "Hi, this is Sam with HomeFirst. How can I help you today?"
      ↓
Sam asks qualifying questions
      ↓
  ┌────────────┴────────────┐
  ↓                         ↓
"New loan"              "Existing loan"
  ↓                         ↓
transfer_to_specialist   transfer_to_specialist
  ↓                         ↓
Mac (Loan Officer)      Ivy (Servicing)
```

This design uses **persona switching** rather than the A2A (Agent-to-Agent) protocol. A single underlying agent changes its instructions and tool access based on `CallState.active_agent`. This approach is optimal for real-time voice because:

- No audio gaps during "transfer" (same WebSocket, same Live session)
- Seamless conversation continuity
- Sub-second persona switches
- Shared call state across all personas

Every tool call passes through the policy door before and after it runs. An observer reads tool results and adds talking points to the persona's instructions.

## 8.2 Components

| Component | File(s) | Responsibility |
|---|---|---|
| Voice service | `mortgage/server.py` | WebSocket bridge, Live session, transcripts, usage, event feed |
| Agent | `mortgage/agent.py` | ADK agent with 29 tools and the policy callbacks |
| Personas | `mortgage/persona.py`, `personas/triage.py`, `personas/origination.py`, `personas/servicing.py` | Sam, Mac and Ivy instructions; persona selected from `CallState.active_agent` |
| Routing | `mortgage/routing.py` | `AgentType` enum (TRIAGE, ORIGINATION, SERVICING), intent detection and persona hand-off logic |
| Policy door | `mortgage/policy.py` | Verification levels, lockout, payment authorisation, input checks, disclaimers |
| Observer | `mortgage/observer.py` | Suggestions from tool results; risk flags |
| Origination domain | `mortgage/mortgage.py`, `tools.py` | Rules, normalisation, pricing, comparison, officers |
| Servicing domain | `mortgage/servicing.py`, `servicing_tools.py`, `database.py` | Loans, schedules, payments, methods in SQLite |
| Regulation knowledge | `mortgage/knowledge/` | Source list, ingestion, approval, search index |
| Data | `assets/mortgage/` | `mortgage.json`, `rate_sheet.json`, `servicing_seed.json` |

## 8.3 Tool catalogue

| Agent | Tools |
|---|---|
| Sam (5) | `get_company_info`, `get_mortgage_products`, `answer_faq`, `verify_customer`, `transfer_to_specialist` |
| Mac (13) | `get_company_info`, `get_mortgage_products`, `check_heloc_eligibility`, `check_state_regulations`, `get_rate_estimate`, `calculate_equity`, `compare_options`, `search_regulations`, `answer_faq`, `verify_customer`, `verify_customer_strong`, `register_lead`, `transfer_to_loan_officer` |
| Ivy (15) | `get_loan_balance`, `get_payment_history`, `get_payoff_quote`, `change_payment_date`, `get_autopay_status`, `setup_autopay`, `cancel_autopay`, `get_payment_methods`, `initiate_secure_card_capture`, `complete_secure_card_capture`, `add_bank_account`, `set_default_payment_method`, `remove_payment_method`, `prepare_payment`, `confirm_payment` |

Sam has limited tools by design—only basic information and the `transfer_to_specialist` tool to route callers. This prevents Sam from accidentally handling tasks meant for Mac or Ivy.

## 8.4 Technology

Python 3.11+, FastAPI, Google ADK 2.8, Gemini Live API (`gemini-3.1-flash-live-preview`), SQLite, numpy, httpx, trafilatura, pypdf, pytest. Browser client in plain JavaScript with an AudioWorklet.

# 9. Phase 1 acceptance and open items

## 9.1 Acceptance criteria

1. The reference Texas HELOC call completes with correct outcomes at each turn and ends in a loan officer offer.
2. No option, eligibility answer or rate is given for a state without approved rules.
3. No account data before basic verification; no change or payment before strong verification.
4. No payment without read-back and explicit authorisation.
5. All automated tests pass. Today: **242 tests pass**, 204 of them for Mac and Ivy.

## 9.2 Open items to close before a pilot

| # | Item | Affects | Status |
|---|---|---|---|
| 1 | ~~Persona routing is written but not connected, so a live call stays with Mac; Ivy cannot take over~~ | FR-06 | **CLOSED** — Sam (triage) now greets all callers and routes to Mac or Ivy via `transfer_to_specialist` |
| 2 | Strong verification accepts date of birth but does not check it; only the balance is compared | FR-41 | Open |
| 3 | Persona tool restrictions are logged, not enforced | FR-45 | Open |
| 4 | Regulation search has no approved content loaded, uses a missing embedding library, and on no result tells the agent to answer from training | FR-22 | Open |
| 5 | Rate sheet and market benchmarks are sample data, yet are used for "below market" statements | FR-15 | Open |
| 6 | Officer availability treats a server's local time as UTC | FR-50 | Open |
| 7 | Property-use matching is loose (for example "a" matches investment) | FR-10 | Open |
| 8 | No end-to-end call scenario tests | NFR-03 | Open |
| 9 | `.env` and `mortgage/.adk/session.db` are committed; add a `.gitignore` (the `.env` holds only a placeholder key today) | NFR-04 | Open |

# 10. Phase 2 requirements (planned)

## 10.1 Overview

![Figure 2. Phase 2 architecture](images/phase2.png)

Phase 2 adds three capabilities on the Phase 1 foundation. **MCP** connects the agents to real systems and shares Mac's governed tools with other agents. The **LO Agent** carries a qualified caller further toward an application. The **CCS → LO Agent transfer** moves the caller between agents in the same call without losing context. All three keep the Phase 1 principle: the model decides what to ask; code decides what is allowed.

## 10.2 Phase 2 use cases

| ID | Use case | Primary actor | Priority |
|---|---|---|---|
| P2-UC-01 | Agent reads and writes back-office data through MCP (LOS, CRM, pricing, calendars) | CCS / LO Agent | Must |
| P2-UC-02 | Another agent or tool uses Mac's eligibility and comparison tools through MCP | External agent | Should |
| P2-UC-03 | Warm transfer from the CCS Agent to the LO Agent | Prospective borrower | Must |
| P2-UC-04 | LO Agent gives a pre-qualification estimate and document checklist | Prospective borrower | Must |
| P2-UC-05 | LO Agent drafts an application intake record for a licensed LO to review | Prospective borrower | Should |
| P2-UC-06 | LO Agent books a meeting with a licensed LO | Prospective borrower | Must |
| P2-UC-07 | LO Agent escalates to a licensed LO (warm transfer or call-back) | Prospective borrower | Must |
| P2-UC-08 | Transfer fails or LO Agent is unavailable; caller is routed to a human or call-back | Any caller | Must |

### P2-UC-03 Warm transfer: CCS Agent → LO Agent

![Figure 3. Transfer sequence](images/handoff.png)

| Item | Detail |
|---|---|
| Trigger | Caller asks for a loan officer, wants to proceed after eligibility screening, or the request goes beyond the CCS Agent's scope |
| Preconditions | Handoff criteria met (P2-BR-01); LO Agent available |
| Main flow | 1. CCS Agent calls `request_lo_handoff` with a reason. 2. The transfer orchestrator checks criteria, verification and availability. 3. CCS Agent explains who the LO Agent is and asks permission. 4. On "yes", the orchestrator builds the handoff packet. 5. The LO Agent becomes active, greets the caller by name and restates the need in one sentence. 6. The caller continues without repeating details. |
| Alternate flows | Caller declines: stay with the CCS Agent. LO Agent unavailable or transfer fails: offer a licensed LO or call-back (P2-UC-08). Caller asks to go back: return to the CCS Agent with the packet updated. |
| Postconditions | Handoff recorded with packet, time and outcome; the UI shows the active agent |

## 10.3 MCP integration requirements

| ID | Requirement | Priority |
|---|---|---|
| P2-FR-01 | Consume MCP servers with ADK `McpToolset` (Streamable HTTP) for LOS, CRM, pricing engine, LO calendars and document service | Must |
| P2-FR-02 | Apply the same policy door to MCP tools as to native tools (before and after callbacks) | Must |
| P2-FR-03 | Allow-list MCP tools per agent; tools not on the list are never exposed to the model | Must |
| P2-FR-04 | Authenticate to MCP servers with OAuth 2.1 or service credentials from a secret manager; no secrets in prompts or code | Must |
| P2-FR-05 | Keep the voice responsive: MCP calls that may exceed 1.5 s run asynchronously, and the agent says it is checking | Must |
| P2-FR-06 | Send only the fields a tool needs; redact personal data in MCP logs | Must |
| P2-FR-07 | Publish Mac's governed tools (eligibility, state rules, compare options, regulation search) as an MCP server using ADK `to_mcp_server` | Should |
| P2-FR-08 | Replace the sample rate sheet with the pricing engine through MCP; record source and timestamp on every quote | Must |
| P2-FR-09 | Record every MCP call, its result code and latency in the audit log | Must |

## 10.4 LO Agent requirements

| ID | Requirement | Priority |
|---|---|---|
| P2-FR-20 | Separate ADK agent with its own persona, instructions and tool allow-list | Must |
| P2-FR-21 | Introduce itself as an AI assistant working with the HomeFirst loan officer team, and name the licensed LO of record | Must |
| P2-FR-22 | Review the caller's scenario from the handoff packet without asking for details already given | Must |
| P2-FR-23 | Provide a non-binding pre-qualification estimate (loan amount range, estimated payment) with disclaimers | Must |
| P2-FR-24 | Provide a document checklist for the product and the caller's situation | Must |
| P2-FR-25 | Draft an application intake record in the LOS (via MCP) for a licensed LO to review; never submit an application | Should |
| P2-FR-26 | Book a meeting or call-back with a licensed LO via the calendar MCP server | Must |
| P2-FR-27 | Escalate to a licensed LO on request, on a complaint, or when asked to approve, lock or negotiate | Must |
| P2-FR-28 | Never approve, deny, lock a rate, or offer or negotiate loan terms | Must |

<p class="note">Regulatory note: under the SAFE Act, taking a residential mortgage application and offering or negotiating terms are licensed loan originator activities. The LO Agent's exact boundary must be approved by compliance counsel before build; P2-FR-25 and P2-FR-23 are the items most likely to need adjustment.</p>

## 10.5 CCS → LO Agent transfer requirements

| ID | Requirement | Priority |
|---|---|---|
| P2-FR-40 | Provide a `request_lo_handoff` tool to the CCS Agent; the transfer decision is made in code by the orchestrator | Must |
| P2-FR-41 | Ask the caller's permission before transferring and tell them who they are moving to | Must |
| P2-FR-42 | Build a handoff packet (10.6) and give it to the LO Agent before it speaks | Must |
| P2-FR-43 | Carry verification level, lockout state and consent flags across the transfer; never upgrade verification by transfer | Must |
| P2-FR-44 | Keep silence during the switch under 2 seconds, using a short bridge line | Must |
| P2-FR-45 | Fall back to a licensed LO or call-back if the LO Agent is unavailable or the switch fails | Must |
| P2-FR-46 | Support a return to the CCS Agent with the packet updated | Should |
| P2-FR-47 | Show the active agent and the handoff in the call UI and supervisor view | Should |
| P2-FR-48 | Store the packet and transfer record durably and link them to the lead | Must |

## 10.6 Handoff packet

| Field | Description |
|---|---|
| `call_id`, `handoff_id`, `timestamp` | Identifiers and time of the handoff |
| `from_agent`, `to_agent`, `reason` | Source, target and why the transfer happened |
| `caller` | First name, callback phone, verification level (none / basic / strong), lead ID |
| `need` | Product interest, amount, purpose, in one sentence |
| `property` | State, property use, estimated value, balance, existing loan type, last cash-out date |
| `eligibility` | Each check run, its outcome, issues and rule source |
| `options` | Options shown and options excluded, with reasons and pricing source |
| `consents` | Recording disclosure, contact consent, transfer consent |
| `open_questions` | What the caller asked that is still unanswered |
| `transcript_ref` | Pointer to the stored transcript, not the transcript itself |

## 10.7 Phase 2 business rules

| ID | Rule |
|---|---|
| P2-BR-01 | Transfer to the LO Agent only when the caller's state has approved rules, the need is an origination product, and the caller agrees |
| P2-BR-02 | The LO Agent works under a named licensed LO of record, shown on the lead |
| P2-BR-03 | Any request to apply, approve, lock or negotiate goes to a licensed human LO |
| P2-BR-04 | Verification is never carried up: strong verification must be done by the caller, not inferred from a transfer |
| P2-BR-05 | MCP write actions (LOS draft, CRM update, booking) need the caller's consent in the same call |

## 10.8 Technical approach

| Topic | Approach |
|---|---|
| Multi-agent structure | Model the CCS Agent and LO Agent as ADK agents under one root (`sub_agents`) and use `transfer_to_agent`, with the orchestrator deciding through the policy door |
| Live session | Prove early (spike) that agent transfer works in a bidirectional `run_live` session. Voice is set per Live session, so a distinct LO Agent voice means reconnecting the model session behind the same caller connection, seeded with the packet |
| Fallback design | If in-session transfer is not reliable, extend the Phase 1 persona switch (`CallState.active_agent`) and connect the existing `routing.py` |
| State | Move call state, packets and transfer records from memory to a persistent store keyed by call ID |
| MCP | Add the `mcp` package; one `McpToolset` per back-office server; tool filters per agent; MCP servers run as separate services |
| Testing | Contract tests per MCP server with mocks; transfer scenarios in the end-to-end call suite; packet schema validation |

## 10.9 Phase 2 non-functional requirements

| ID | Requirement |
|---|---|
| P2-NFR-01 | Transfer switch completes with under 2 s of silence in 95% of transfers |
| P2-NFR-02 | MCP tool calls: p95 under 1.5 s or handled asynchronously |
| P2-NFR-03 | Packet completeness: 100% of required fields present on every transfer |
| P2-NFR-04 | Zero LO Agent statements that approve, lock or negotiate terms in the evaluation suite |
| P2-NFR-05 | All MCP credentials in a secret manager; least-privilege scopes per agent |
| P2-NFR-06 | Full audit trail: handoffs, MCP calls and policy verdicts retrievable per call |

## 10.10 Dependencies and prerequisites

1. Close Phase 1 open items 1–4 (routing, date-of-birth check, tool restrictions, grounded regulation search).
2. Persistent store for call state and handoff packets.
3. MCP servers or adapters for the chosen LOS, CRM, pricing engine and calendar systems.
4. Compliance approval of the LO Agent boundary, scripts and disclosures.
5. Named licensed LOs for the pilot, with calendars available to the agent.

## 10.11 Delivery sequence

| Step | Content | Exit criteria |
|---|---|---|
| P2.0 Foundation | Phase 1 open items; persistent store; `mcp` dependency; transfer spike in `run_live` | Spike decision recorded; open items closed |
| P2.1 MCP | Client toolsets for pricing and calendar first, then LOS and CRM; Mac tools as MCP server | Contract tests pass; policy door applied to MCP tools |
| P2.2 LO Agent | Persona, tools, boundaries, escalation | Evaluation suite: zero boundary violations |
| P2.3 Transfer | Orchestrator, packet, consent, fallback, UI | Transfer scenarios pass; silence under 2 s |
| P2.4 Pilot readiness | Monitoring, audit, compliance sign-off | Sign-off; supervised pilot starts |

# 11. Open questions

1. Which LOS, CRM, pricing engine and calendar systems will the MCP servers front, and who builds them?
2. Should the LO Agent have its own name and voice, or present as part of the loan officer team without a persona name?
3. Which licensed LOs act as LO of record for LO Agent conversations?
4. What does compliance allow the LO Agent to say about pre-qualification amounts and rates?
5. Should Ivy (servicing) callers also be able to reach the LO Agent, for example for a refinance?
6. What is the target for transfers that end with a booked meeting or completed intake draft?

# Appendix: Glossary

| Term | Meaning |
|---|---|
| ADK | Google Agent Development Kit, the framework the agents are built on |
| CCS Agent | The current customer-facing voice agent: Sam (triage), Mac (origination) and Ivy (servicing) |
| Persona switching | Architecture pattern where a single ADK agent dynamically changes its instructions and tool access based on call state, enabling seamless "transfers" between personas without audio gaps |
| LO Agent | Phase 2 AI agent that supports licensed loan officers in the call |
| LO | Licensed loan officer (NMLS mortgage loan originator) |
| MCP | Model Context Protocol, a standard for connecting AI agents to tools and data |
| Handoff packet | Structured summary passed between agents at transfer |
| Policy door | Code that checks every tool call before and after it runs |
| HELOC | Home equity line of credit |
| LTV / CLTV | Loan-to-value / combined loan-to-value |
| LOS | Loan origination system |
| SAFE Act | US law requiring mortgage loan originators to be licensed or registered |
