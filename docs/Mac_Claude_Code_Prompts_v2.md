# Mac: Claude Code prompts, version 2

These cover what is still open after commit `839f197`. Run them in order from the project root and run `uv run pytest` after each. IDs match section 9 of the version 2 executive review. Prompts 1–6 from version 1 are done or folded in below. Version 1 prompts 7 (phone and transfer) and 8 (production readiness) are repeated at the end because they have not been started.

---

## Prompt 1: compare_options must obey the eligibility rules (N1, Critical)

```
mortgage/mortgage.py MortgageStore.compare_options and mortgage/tools.py compare_options offer options the rules
forbid. Reproduce first: compare_options("TX", 550000, 100000, 750, 40000) currently returns a HELOC at 7.75%
"1% below market", but check_heloc_eligibility("TX", "primary residence", True, 550000, 100000) says not eligible
because of the existing cash-out mortgage.

Fix:
1. Add parameters property_use: str and has_existing_cashout: bool = False, and
   last_cashout_date: str = "" (ISO date, optional) to both the store method and the tool. Update the tool docstring so
   the model passes the caller's own words for property use.
2. Decide HELOC eligibility by calling self.check_heloc_eligibility(...) — do not re-implement the rules. Only list
   the HELOC if eligible is True. If eligible is None (needs_review), list no options and return status needs_review.
3. For cash-out refinance, read state_regulations[state]["cashout_rules"]: use its max_ltv instead of the hard-coded 80,
   and if once_per_year is true and last_cashout_date is within 365 days (or the caller has an existing cash-out and no
   date is known), exclude it and add a "needs_review" note asking the loan officer to confirm the date.
4. Return an "excluded" list with the reason for each option not shown, so Mac can explain it.
5. Update the policy door's compare_options validation for the new arguments.
6. Tests in tests/test_compare_options.py:
   - the reference caller (TX, primary, existing cash-out, 550000/100000, 40000 needed) gets NO HELOC;
   - TX + "a property I rent out" never gets a HELOC;
   - CA primary with no cash-out still gets a HELOC;
   - TX cash-out within 12 months is excluded; uses cashout_rules max_ltv.
```

## Prompt 2: regulation search must be grounded and actually work (N2, High)

```
1. mortgage/knowledge/index.py get_embedding imports google.generativeai, which is not installed (the project uses
   google-genai). Rewrite it with `from google import genai`; client = genai.Client(); use
   client.models.embed_content(model=EMBED_MODEL, contents=text) with EMBED_MODEL read from the env var
   KNOWLEDGE_EMBED_MODEL (default "gemini-embedding-001"). Log a warning once, not on every query, if embedding fails.
2. In mortgage/tools.py search_regulations, when no passages are found replace the "Answer based on your training if
   confident" text with: "Say you don't have an approved source for that and offer to connect them with a licensed
   loan officer." Mac must never answer regulation questions from memory.
3. Add an "approved_by" and "approved_at" column to the passages table and require --approver on the approve CLI.
4. Add a README section "Loading the regulation index": the ingest command, the status command, and the approve
   command for each Texas source.
5. Tests with a mocked genai client; a test that the no-result message never contains "training".
```

Then run the pipeline once yourself and approve the Texas sources after compliance review:

```bash
uv run python -m mortgage.knowledge.ingest
```

## Prompt 3: label sample pricing and stop unsupported savings claims (N3, High)

```
assets/mortgage/rate_sheet.json holds fixed sample rates and benchmarks labelled with real survey names.
1. Add top-level fields "data_status": "sample" | "live" and "source" to the rate sheet, defaulting to "sample".
2. In MortgageStore, if data_status is "sample" or as_of is older than RATE_SHEET_MAX_AGE_DAYS (env, default 3),
   do not compute or return savings_vs_market or market_benchmark, and add "pricing_note": "Indicative sample pricing".
3. The policy door's audit callback must strip any "savings_vs_market" field from responses when pricing is not live.
4. Add a RateSource interface with a JsonFileRateSource (current behaviour) so a live pricing feed can be plugged in.
5. Tests for sample, stale and live sheets.
```

## Prompt 4: time-zone-aware officer availability (N4, Medium)

```
MortgageStore.get_available_officers treats a naive datetime as UTC. On a Central-time laptop
datetime.now() at 10:00 is read as 10:00 UTC (04:00 Chicago), so no officer is available.
1. Make the default clock time-zone aware: clock = lambda: datetime.now(timezone.utc).
2. In get_available_officers, treat a naive datetime as the server's local time (now.astimezone()), not UTC.
3. Check everything else that uses self.clock() (today(), leads, transfers) still works with an aware clock.
4. Tests: an aware 15:00 UTC Wednesday clock gives Lisa Chen available (09:00 Chicago); a naive clock is treated as
   local time; Sunday gives nobody.
```

## Prompt 5: stricter property-use matching (N5, Medium)

```
normalize_property_use in mortgage/mortgage.py uses substring matching both ways, so "a" -> investment,
"own" -> primary and "not a rental, my home" -> investment.
1. Match on whole words / phrases only (regex word boundaries), never use_clean-in-key.
2. Collect every category that matches. If none or more than one, raise
   MortgageError("ambiguous_property_use", ...) and have the check_heloc_eligibility tool return
   "say": "Ask the caller whether the property is their primary residence, a second home, or a rental/investment."
3. Add phrases: "live in", "live there", "house I live in", "tenants", "leased", "airbnb", "short-term rental".
4. Tests for each of the examples above plus the reference wording "a property I rent out".
```

## Prompt 6: end-to-end call scenarios (N6, Medium)

```
Create mortgage/smoke_live.py modelled on front_desk/smoke_live.py. It drives the real agent through runner.run_live
with typed caller turns (and --audio for synthesised speech) and asserts on the tool calls and their results.
Scenarios:
1. Reference call:
   T1 "I have a couple of properties in Texas and I'm hoping to get a HELOC, probably around $40,000. One is my primary
      residence. The other is a property I rent out. Can I put the HELOC on the rental?"
      -> check_heloc_eligibility with TX and the rental -> eligible False.
   T2 "I do have a mortgage on my primary, about $100,000, worth about $550,000. It's a cash-out I did a few years ago."
      -> eligible False for the existing cash-out; if compare_options is called it must list no HELOC.
   T3 "Yeah, that'd be great." -> transfer_to_loan_officer called.
2. California HELOC on a primary (eligible), 3. New York (needs review -> transfer), 4. caller asks for legal advice,
5. caller asks Mac to approve the loan, 6. caller fails verification three times (lockout),
7. regulation question with no approved source (Mac offers a loan officer, does not answer from memory).
Print a pass/fail table; exit non-zero on failure. Add "Testing Mac" to the README.
```

## Prompt 7: phone calls, warm transfer, call summary, consent (open from version 1)

```
1. New module mortgage/telephony.py: a Twilio Media Streams WebSocket endpoint (/twilio/stream) and a TwiML webhook
   (/twilio/voice) that bridge 8 kHz mu-law phone audio to the existing run_live loop (resample to 16 kHz PCM up,
   24 kHz PCM -> 8 kHz mu-law down). Reuse the same session, events and policy code as the browser /ws path.
2. The greeting adds "This call may be recorded" before the existing greeting.
3. New tool send_call_summary(): builds a structured summary (need, state, property use, values, eligibility results,
   options shown and excluded, consent) from CallState.inquiry_context. Make the tools record their results into
   inquiry_context. transfer_to_loan_officer calls it and, when an officer is available, issues a Twilio <Dial> warm
   transfer; otherwise books a call-back.
4. register_lead requires consent_to_contact: bool; the policy door blocks it without consent.
5. Config via env vars (TWILIO_ACCOUNT_SID etc.); never commit secrets. Tests with mocked Twilio.
```

## Prompt 8: production readiness (open from version 1)

```
1. Rename the project in pyproject.toml from "live-dj" to "mac-mortgage-advisor" with an accurate description.
2. Add Dockerfile.mortgage that copies mortgage/ (including knowledge/), assets/mortgage/ and the regulation index,
   runs as a non-root user and starts uvicorn mortgage.server:app on $PORT. The existing Dockerfile only builds the clinic.
3. Replace in-memory leads, transfers and call records with a repository interface and a Firestore (or SQLite locally)
   implementation chosen by env var. Keep MortgageStore method names.
4. verify_customer: after a name match, send a one-time passcode to the phone on file (pluggable sender) and mark the
   caller verified only after verify_passcode(). Return only first name and number of properties.
5. Add a signed-token check on the /ws WebSocket, structured JSON logging with PII redaction, and a GitHub Actions
   workflow that runs uv run pytest on every push.
6. Pin LIVE_MODEL to a generally available model in .env.example and document how to upgrade safely.
7. Remove the .idea/ folder from the repository and add it to .gitignore.
```
