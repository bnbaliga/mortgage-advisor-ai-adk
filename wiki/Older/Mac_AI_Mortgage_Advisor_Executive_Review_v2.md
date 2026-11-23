---
title: "Mac — AI Mortgage Advisor"
subtitle: "Scope, Requirements, Solution Design & Recommendations · Version 2"
date: "16 November 2026 · Draft for discussion · Confidential"
---

<div class="meta">

**HomeFirst AI Lending · Executive review, version 2.** Based on the current code (commit `839f197`, 15 November 2026). Version 1 (11 November) assessed commit `09980bf`.

</div>

# 1. Executive summary

**Mac** is an AI voice agent that answers home-buyer and homeowner calls, explains mortgage options, checks eligibility against state rules and hands qualified callers to a licensed loan officer. It is the front door of the HomeFirst proposition: by automating the origination process with AI, borrowers save **0.5% to 1% in interest** compared with traditional lenders.

**Progress since version 1 is strong.** In one week the team fixed 7 of the 14 findings in full and 4 in part, added two of the capabilities the requirement asks for (regulation search and option comparison), and grew the automated test suite from zero Mac tests to **135 Mac tests**. All 177 tests in the project pass.

<div class="callout">

**Key messages**

- **The Texas rule defect is fixed.** "A property I rent out", "rental" and "investment" are now all treated as investment property, and Mac declines the HELOC. Unknown states now go to a loan officer instead of being approved.
- **The new comparison tool has a critical flaw.** For the exact caller in the reference script (Texas, existing cash-out), `compare_options` offers a HELOC at 7.75%, "1% below market", which the eligibility check correctly rejects. Mac could contradict itself on the same call.
- **Regulation search is built but empty.** No approved documents are loaded yet, the embedding call uses a library that is not installed, and when nothing is found Mac is told to answer from its own training. That defeats the point of cited answers.
- **The savings figures use sample data.** The rate sheet has realistic-looking market benchmarks but no live feed. These numbers must not reach a caller until they come from approved pricing data.
- **Still not a product.** Phone calls, real transfer, call summary, persistent storage and production deployment remain open.
- **Recommendation:** close the six new findings (N1–N6) and load the Texas regulation sources (about 1–2 weeks), then start the 8-week Texas pilot as planned in version 1.

</div>

## Status at a glance

| Capability | v1 (11 Nov) | v2 (16 Nov) | Comment |
|---|---|---|---|
| Voice conversation with interruption | Working | Working | Unchanged |
| Reference call script, rule checks | Defect | Working | "Rent out" now blocked; existing cash-out blocked; transfer offered |
| Unknown states | Defect | Fixed | Returns "needs loan officer review" |
| Regulation knowledge from documents / websites | Gap | Partial | Pipeline and tool built; no approved content loaded |
| Best-option comparison and savings | Gap | Defect | Built, but offers products the rules forbid |
| Rate estimates | Partial | Built | Rate sheet by credit tier and LTV, disclaimer enforced in code |
| Transfer to licensed loan officer | Partial | Partial | Checks officer hours now; time-zone defect; still simulated |
| Phone (PSTN) channel | Gap | Gap | Not started |
| Automated tests for Mac | Gap | Partial | 135 unit tests; no live call-scenario tests yet |
| Production hosting, data and security | Gap | Gap | Not started |

# 2. Business context

## 2.1 The requirement

Build Mac, an AI mortgage lender that enables home buyers to get the best mortgage options and save 0.5% to 1% in interest compared with traditional lenders, because AI automates the origination process. Mac is an AI voice agent. Its knowledge comes from documents and website content (including regulations); web-scraping tools may be used.

## 2.2 What the saving means for a borrower

Illustration on a $400,000, 30-year fixed loan against a 6.50% traditional-lender rate (principal and interest only):

| Rate reduction | Rate | Monthly payment | Saved per month | Saved per year | Saved over 30 years |
|---|---|---|---|---|---|
| Baseline | 6.50% | $2,528 | — | — | — |
| 0.5% | 6.00% | $2,398 | $130 | $1,561 | $46,825 |
| 1.0% | 5.50% | $2,271 | $257 | $3,085 | $92,562 |

<p class="note">Illustrative only; lifetime figures assume the loan is held to term. The code can now compute savings against a benchmark (section 7.5), but the benchmark values are sample data. The claim must be backed by documented pricing data before it is used with customers or in advertising.</p>

## 2.3 Mac's role in the value chain

The saving comes from lower origination cost across the whole process. Mac contributes by handling first contact around the clock at low cost per call, screening out ineligible scenarios (such as the Texas HELOC restrictions) before a loan officer spends time on them, and handing over a complete summary so the loan officer starts where Mac stopped.

# 3. Scope

## 3.1 Phased scope

| Phase | Objective | In scope | Status |
|---|---|---|---|
| **1 Prototype** | Prove the voice experience and rule-checking pattern | Browser voice call, eligibility tools, simulated transfer, demo data | Built |
| **2a Harden** | Make the prototype safe and testable | Fix findings, test suite, regulation pipeline, rate sheet and comparison, persistent storage, deployable container | Partial |
| **2b Texas pilot (8 weeks)** | Prove value with real callers under supervision | Phone number, warm transfer with call summary, Texas HELOC and cash-out refinance enquiries, consent and recording disclosures, CRM hand-off, dashboard | Gap |
| **3 Scale** | Expand coverage and automation | More states and products, live pricing engine, Spanish, document upload and pre-qualification, LOS integration | Gap |

## 3.2 Out of scope (all phases unless approved)

- Mac approving, denying or committing to any loan, or locking a rate.
- Taking a formal loan application. Mac collects enquiry details only; applications go to a licensed loan officer.
- Legal or tax advice.
- Underwriting decisions, credit pulls or collecting full Social Security numbers by voice.
- Outbound marketing calls (these bring separate consent obligations).

# 4. Reference call: how Mac handles it now

The calling script was replayed against the v2 rule engine with the caller's own wording.

| Turn | Caller / Mac | What happens in the system (v2) | Status |
|---|---|---|---|
| 1 | Mac greets: "Hi, this is Mac, your AI Mortgage advisor…" | Greeting set in the persona and sent when the call connects | Built |
| 2 | Caller: two Texas properties, wants a ~$40k HELOC, asks about the rental | `check_heloc_eligibility("Texas", "a property I rent out")` | Built |
| 3 | Mac: Texas doesn't allow HELOCs on investment properties; asks about the primary residence | Normalised to TX + investment; returns not eligible plus alternatives | Fixed |
| 4 | Caller: $100k balance, worth ~$550k, existing cash-out | `check_heloc_eligibility(TX, "primary residence", existing cash-out, 550,000, 100,000)` | Built |
| 5 | Mac: no HELOC with an existing cash-out in Texas; offers refinance-then-HELOC or another cash-out refinance; offers a transfer | Not eligible with both alternatives; policy door adds the loan-officer offer | Built |
| 5b | If Mac also runs `compare_options` to "show the best option" | Offers the forbidden HELOC at 7.75% and a cash-out refinance, without checking the existing cash-out or the Texas once-a-year rule | Defect |
| 6 | Caller agrees; transfer | Selects Lisa Chen (Texas lending) if within her hours; otherwise promises a call-back. Still simulated | Partial |

<div class="callout warn">

**Regulatory note for compliance review.** Texas Constitution Art. XVI §50 allows home equity lending, including HELOCs, only on a homestead, caps combined loan-to-value at 80%, allows only one home equity loan on a homestead at a time (a Texas cash-out refinance counts as one) and no more than one in 12 months. The data now cites this source, carries a review date, and uses "12-day notice before closing" and "3-day right to cancel". Counsel should still approve the wording.

</div>

# 5. Functional requirements

Priority: **Must** for the Texas pilot, **Should** for the pilot if feasible, **Could** for later phases.

| ID | Requirement | Priority | v1 | v2 |
|---|---|---|---|---|
| FR-01 | Greet the caller, state that Mac is an AI advisor, give a call-recording disclosure | Must | Partial | Partial |
| FR-02 | Natural voice conversation; stop when interrupted and resume the thread | Must | Built | Built |
| FR-03 | Capture the enquiry: product, amount, state, property use, value, balance, existing loan type | Must | Partial | Partial |
| FR-04 | Check HELOC eligibility against state rules, including Texas homestead and existing cash-out restrictions | Must | Defect | Built |
| FR-05 | When not eligible, explain why and present alternatives | Must | Built | Built |
| FR-06 | Calculate equity, loan-to-value and maximum borrowing | Must | Built | Built |
| FR-07 | Describe products: conventional, FHA, VA, jumbo, HELOC, cash-out and rate-and-term refinance | Must | Built | Built |
| FR-08 | Rate estimates only with the required disclaimer | Must | Built | Built |
| FR-09 | Answer regulation questions from approved documents and website content, citing the source | Must | Gap | Partial |
| FR-10 | Refresh regulation knowledge on a schedule, with legal approval before publishing | Must | Gap | Partial |
| FR-11 | Never say a product is allowed in a state without approved rules; transfer instead | Must | Gap | Built |
| FR-12 | Transfer to an available licensed loan officer with the right specialty, or book a call-back | Must | Partial | Partial |
| FR-13 | Hand the loan officer a structured call summary | Must | Gap | Gap |
| FR-14 | Capture leads with explicit consent to be contacted | Must | Partial | Partial |
| FR-15 | Escalate to a human on request, for complaints, legal or tax questions, or distress | Must | Partial | Partial |
| FR-16 | Accept calls on a phone number | Must | Gap | Gap |
| FR-17 | Compare suitable options and show estimated savings against market rates | Should | Gap | Defect |
| FR-18 | Verify existing customers securely before discussing their accounts | Should | Partial | Partial |
| FR-19 | Supervisor view of live and past calls, actions and policy decisions | Should | Partial | Partial |
| FR-20 | Later phases: Spanish; pre-qualification with document upload and LOS hand-off | Could | Partial | Partial |

**Summary:** of 16 Must requirements, 7 are built (up from 5), 7 are partial and 2 are not started (phone channel and call summary). The Should requirement FR-17 is built but defective.

# 6. Technical requirements

| ID | Requirement | Target | v2 status |
|---|---|---|---|
| TR-01 | Responsiveness | Mac speaks within 1 s; stops within 300 ms when interrupted | Met |
| TR-02 | Availability | 99.9% in business hours; graceful "call you back" on failure | Not met |
| TR-03 | Scale | 100 concurrent calls in pilot; autoscaling | Not met |
| TR-04 | Data persistence | Leads, transfers, call records and audit trail stored durably | Not met |
| TR-05 | Security | Secrets manager; TLS; authenticated sessions; least privilege | Partial |
| TR-06 | Privacy (GLBA) | Personal data minimised, redacted, encrypted, retained per policy | Partial |
| TR-07 | Auditability | Every action, verdict and rule version recorded per call | Partial |
| TR-08 | Rule accuracy | 100% pass on a regulated-scenario suite before every release | Partial |
| TR-09 | Conversation quality | Automated call-scenario evaluations, including the reference call, in CI | Not met |
| TR-10 | Observability | Latency, errors, transfers, cost per call on a dashboard; alerts | Partial |
| TR-11 | Cost control | Token use and cost tracked per call | Met |
| TR-12 | Deployment | Container build and CI/CD for the Mac service | Not met |
| TR-13 | Model governance | Pinned, generally available model; regression tests before upgrades | Partial |

<p class="note">What moved: TR-07 now has a source and review date on each state rule; TR-08 has 135 unit tests (rules, policy, tools, comparison, knowledge) but no scenario that runs the full conversation. Technology: Python 3.11, FastAPI, Google ADK, Gemini Live (preview model gemini-3.1-flash-live-preview), SQLite + numpy for the regulation index, httpx / trafilatura / pypdf for ingestion.</p>

# 7. Solution design

## 7.1 Current architecture

![Figure 1. The build as of commit 839f197](images/current.png)

A browser streams microphone audio over a WebSocket to a FastAPI service running a Google ADK agent connected to the Gemini Live API. Mac now has 12 tools. Every tool call passes through the policy door, which validates inputs before the call and adds disclaimers and loan-officer hints after it. Structured rules and rates come from two JSON files; regulation passages come from a local SQLite index fed by the new ingestion pipeline.

## 7.2 Design decisions worth keeping

- **Rules in code, not in the prompt.** v2 went further: the Texas rules were removed from the AI prompt, and Mac is told to speak only from tool results.
- **Structured rules decide; search explains.** Eligibility comes from approved rules in `mortgage.json`; regulation search is for "why" questions and citations only.
- **Fail closed.** Unknown states and unknown property uses return "needs review" or an error, never "eligible".
- **Tools return instantly** and the back office sits behind one swappable store class.

## 7.3 Target architecture

![Figure 2. Target architecture: blue boxes now exist and need hardening; red boxes are still to build](images/target.png)

## 7.4 Regulation knowledge pipeline (FR-09, FR-10)

| Step | Built in v2 | Still needed |
|---|---|---|
| Collect | 5 approved sources in `sources.yaml`: Texas Const. Art. XVI §50, 7 TAC ch. 153, CFPB Reg Z §1026.40 and §1026.23, internal policy folder. Respects robots.txt, rate-limited, generic user agent | Run it; add a schedule (e.g. weekly) |
| Process | HTML and PDF text extraction, ~800-token passages with overlap, content hash | — |
| Approve | Changed sources become "pending review"; CLI command to approve; only approved passages are searchable | Name the compliance approver; record who approved and when |
| Index | SQLite + numpy with keyword fallback | Embedding call imports `google.generativeai`, which is not installed; switch to the `google-genai` client already in the project. Plan a move to Vertex AI Search for production |
| Answer | `search_regulations` returns top 3 passages with source | When nothing is found it says "answer based on your training"; it must offer a loan officer instead |

## 7.5 Option comparison (FR-17)

`compare_options` uses the new rate sheet (rates by product, credit tier and LTV band, with a market benchmark per product) to rank a HELOC, a cash-out refinance and a rate-and-term refinance, with monthly payment and "below market" figure. Two problems block its use with callers:

1. **It does not apply the eligibility rules.** It takes no property use and no "existing cash-out" input, so it offers the Texas HELOC the eligibility tool forbids, and it ignores the Texas one-in-12-months rule for cash-out refinances. It only checks the loan-to-value cap.
2. **The prices are sample data.** Benchmarks are labelled with real survey names (Freddie Mac PMMS, Bankrate) but are fixed numbers dated 5 October with no feed.

## 7.6 Tool catalogue

| Tool | Purpose | Status |
|---|---|---|
| check_heloc_eligibility | State rule check, property-use normalisation, max HELOC amount | Built |
| check_state_regulations | Returns the state rule set; unknown states go to review | Built |
| get_rate_estimate | Rate sheet by credit tier and LTV, benchmark, disclaimer | Built |
| calculate_equity | Equity, LTV, borrowing power at 80% / 85% | Built |
| get_mortgage_products, answer_faq, get_company_info | Product, FAQ and company facts (hours bug fixed) | Built |
| search_regulations (new) | Cited passages from approved sources | Partial |
| compare_options (new) | Ranked options with payments and savings | Defect |
| verify_customer | Name plus last 4 phone digits; 3-strike lockout | Partial |
| register_lead, transfer_to_loan_officer | Lead or transfer record; officer chosen by specialty and hours | Partial |
| send_call_summary | Structured hand-off to loan officer and CRM | Gap |

# 8. Compliance and risk

This section flags areas for review by compliance counsel. It is not legal advice.

| Area | Why it matters | Mitigation | v2 change |
|---|---|---|---|
| State lending rules | A wrong "yes" on Texas home equity can create an unenforceable lien | Approved, versioned rules; fail closed; scenario tests | Improved: rules cite source and review date; unknown states fail closed. New risk: comparison tool bypasses rules |
| Loan originator licensing (SAFE Act) | Only licensed originators may offer or negotiate terms | Keep Mac to education and pre-screening; counsel approves the boundary | Higher: Mac now quotes specific rates and payments per option |
| Advertising and UDAAP | "Save 0.5–1%" and "below market" claims must be substantiated | Documented pricing evidence; approved wording | Higher: the tool states "1% below market" from sample data |
| Fair lending (ECOA, Fair Housing Act) | Consistent treatment; no protected characteristics | Same rules for every caller; outcome monitoring | Rate tiers use credit score and LTV only |
| Privacy (GLBA), recording consent | Personal financial data; all-party consent states | Disclosure at greeting; redaction; retention policy | Unchanged |
| Contact consent (TCPA) | Call-backs need documented consent | Capture consent with each lead | Unchanged |
| AI accuracy | The model may misstate facts | Facts only from tools; scenario evaluations | Regression: search fallback invites answers from training |
| Web scraping | Terms of use and copyright of scraped sites | Approved source list; robots.txt; counsel review | New, handled reasonably |
| Identity | Weak check reveals property and credit details | One-time passcode; reveal minimum data | Unchanged |
| Model dependency | Preview model may change | Pin a GA version; regression suite | Unchanged |

# 9. Findings and recommended changes

## 9.1 Version 1 findings: progress

| # | v1 finding | v2 result | Status |
|---|---|---|---|
| 1 | "Rental" bypassed the Texas investment block | Property use normalised; tested with the caller's own words | Fixed |
| 2 | Unknown states returned "eligible" | Returns "needs review" (tested with New York) | Fixed |
| 3 | No regulation knowledge from documents or websites | Pipeline and tool built; corpus not loaded; see N2 | Partial |
| 4 | No option comparison or savings evidence | Tool and rate sheet built; see N1 and N3 | Partial |
| 5 | No tests for Mac | 135 Mac unit tests, all passing; no live call scenarios | Partial |
| 6 | Transfer simulated; no phone channel or summary | Not started | Open |
| 7 | Policy door promised more than it enforced | Input validation, disclaimer and transfer hint now enforced in code; verification list still empty | Fixed |
| 8 | Texas rules duplicated in the AI prompt | Removed from prompt | Fixed |
| 9 | Weak customer verification | Not started | Open |
| 10 | Officer availability ignored hours and time zone | Hours and time zone added; see N4 | Partial |
| 11 | Not deployable (in-memory data, Dockerfile builds the clinic app, project named "live-dj") | Not started | Open |
| 12 | Business-hours answer hard-coded | Reads from data | Fixed |
| 13 | Inconsistent state names | All 50 states + DC normalised to 2-letter codes | Fixed |
| 14 | "Cooling off period" wording | 12-day notice + 3-day right to cancel, with source citation | Fixed |

## 9.2 New findings in version 2

All were reproduced by running the v2 code.

| # | Finding | Recommendation | Priority |
|---|---|---|---|
| N1 | `compare_options` offers a HELOC to the reference caller (Texas, existing cash-out) at 7.75% "1% below market", and offers cash-out refinances without the Texas one-in-12-months check | Add property use and existing cash-out (with date) inputs; reuse `check_heloc_eligibility` and the state cash-out rules; never list an option the rules reject; tests for the reference caller | Critical |
| N2 | Regulation index is empty; embeddings import `google.generativeai` (not installed) so search is keyword-only; on no result Mac is told to "answer based on your training" | Use the `google-genai` client; load and approve the Texas sources; on no result, offer a loan officer | High |
| N3 | Savings and benchmark figures come from a fixed sample rate sheet labelled with real survey names | Mark as sample and suppress "below market" speech until a live, compliance-approved feed exists; add a staleness check on `as_of` | High |
| N4 | Officer availability treats the server's local time as UTC; on a Central-time laptop no officer is available at 10 am and all are at 4 pm | Use a time-zone-aware clock (`datetime.now(timezone.utc)`) and test with non-UTC clocks | Medium |
| N5 | Property-use matching is too loose: "a" becomes investment, "own" becomes primary, "not a rental, my home" becomes investment | Match whole words; if the phrase is ambiguous or matches more than one category, return "ask the caller" | Medium |
| N6 | No end-to-end call test: the reference script is not replayed through the live agent | Add `mortgage/smoke_live.py` with the reference call and failure scenarios, as in version 1 prompt 4 | Medium |

# 10. Roadmap, success measures and decisions

## 10.1 Roadmap (updated)

| Phase | Timing | Deliverables | Exit criteria |
|---|---|---|---|
| 2a Harden, finish | Next 1–2 weeks | N1–N6; load and approve Texas regulation sources; choose pricing data source | 100% rule-test pass including the reference call; compliance sign-off on wording |
| 2a Harden, platform | In parallel, 2–3 weeks | Persistent storage, Mac container, CI, passcode verification | Deployed to a staging environment |
| 2b Texas pilot | 8 weeks after 2a | Phone number, warm transfer with call summary, CRM leads, consent and disclosures, dashboard | Pilot measures met for 4 consecutive weeks; zero compliance incidents |
| 3 Scale | Following quarter | More states and products, live pricing engine, Spanish, LOS integration | Business case confirmed by pilot data |

## 10.2 Success measures

| Measure | Pilot target (proposed) |
|---|---|
| Rule accuracy on the regulated-scenario suite | 100% |
| Comparison never offers an option the rules reject | 100% |
| Calls resolved or correctly routed without human help | ≥ 70% |
| Time from "yes, transfer me" to a loan officer | < 60 seconds in business hours |
| Loan officer rating of the hand-off summary | ≥ 4 out of 5 |
| Caller satisfaction | ≥ 4.3 out of 5 |
| Rate saving delivered on funded loans | 0.5–1.0% versus documented market benchmark |
| Compliance incidents | Zero |

## 10.3 Decisions requested

1. Approve finishing Phase 2a (1–2 weeks) and then the Texas pilot (HELOC and cash-out refinance enquiries).
2. Assign compliance counsel to approve rules, regulation sources, scripts, disclosures and the licensing boundary for rate quotes.
3. Choose the pricing data source used for rates and to evidence the 0.5–1% saving.
4. Choose the telephony provider and CRM / LOS systems for hand-off.
5. Confirm the pilot loan-officer team and their hours.

# Appendix A: What changed in the code (09980bf → 839f197)

| Area | Change |
|---|---|
| `mortgage/mortgage.py` | State normalisation for 50 states + DC; property-use normalisation; fail-closed "needs review"; rate sheet lookup by credit tier and LTV; `compare_options` with payment maths; officer hours and time zones |
| `mortgage/policy.py` | Input validation for rate estimates and comparisons; unknown-state block; disclaimer and transfer hint returned as a new response |
| `mortgage/persona.py` | Texas rules removed; "speak only from tool results"; guidance on when to use regulation search |
| `mortgage/tools.py` | `search_regulations` and `compare_options` added (12 tools); hours bug fixed; errors returned cleanly |
| `mortgage/knowledge/` (new) | Source list, scraper and PDF ingestion, chunking, change detection, approval CLI, SQLite + numpy index |
| `assets/mortgage/` | Rule sources and review dates; notice and rescission days; officer hours; new `rate_sheet.json` |
| `tests/` | 5 new test files, 135 tests (rules 24, policy 23, tools 21, comparison 42, knowledge 25) |

# Appendix B: Glossary

| Term | Meaning |
|---|---|
| HELOC | Home equity line of credit: a revolving credit line secured by the home |
| Cash-out refinance | Replacing the mortgage with a larger one and taking the difference in cash |
| Rate-and-term refinance | Replacing the mortgage to change the rate or term without taking cash |
| LTV / CLTV | Loan-to-value / combined loan-to-value: loan balances as a percentage of the home's value |
| Homestead | The owner's primary residence; Texas home equity rules apply only to homesteads |
| LOS | Loan origination system, such as Encompass |
| ADK | Google's Agent Development Kit, the framework Mac is built on |
| RAG | Retrieval-augmented generation: the AI answers from retrieved, approved passages |
| Policy door | The code every Mac action passes through, which can allow, block or annotate it |
| NMLS | Nationwide Multistate Licensing System, which licenses loan originators |
