# Mac: Claude Code prompts, version 3 (multi-agent architecture)

These implement `wiki/Mac_Multi_Agent_Architecture.md`. Run them in order from the repository root and run `uv run pytest` after each. Paths refer to the `src/backend/mortgage_advisor` layout.

---

## Prompt 1: Spike — live transfer between agents

```
Create a throwaway spike in archive/spikes/live_transfer/ (not in src/) to prove ADK sub-agent transfer in a
bidirectional run_live session:
- root agent "ccs" with Gemini(speech_config voice "Aoede") and a tool route_caller(destination) that sets
  tool_context.actions.transfer_to_agent; sub-agents "lo" (voice "Charon") and "servicing" (voice "Kore") with
  disallow_transfer_to_peers=True.
- Before transferring, write a dict to tool_context.state["handoff"]; each sub-agent's instruction function reads it
  and greets the caller using it.
- Reuse the existing WebSocket server pattern from src/backend/mortgage_advisor/api/routes.py.
Measure and log: silence between the last CCS audio chunk and the first sub-agent audio chunk; whether the sub-agent's
voice changes; whether the sub-agent knows earlier conversation without the handoff dict.
Write the findings to wiki/spike_live_transfer.md.
```

## Prompt 2: Multi-agent core (CCS coordinator, LO Agent, Servicing Agent)

```
Replace the single-agent persona switch with real ADK agents.
1. agent/agents/ccs.py: ccs_agent (root). Female voice from env CCS_VOICE (default "Aoede"). Instruction: greeting
   with AI and recording disclosure, menu (1 new loan, 2 existing loan, 3 general information), answers option 3 itself.
   Tools: route_caller, get_company_info, get_mortgage_products, answer_faq, search_regulations, request_human.
2. agent/agents/lo.py: lo_agent "Mac", male voice from LO_VOICE (default "Charon"), origination tools plus
   return_to_menu. Move the Mac instruction from agent/personas/origination.py and add the licensing boundary.
3. agent/agents/servicing.py: servicing_agent "Ivy", voice SERVICING_VOICE (default "Kore"), servicing tools plus
   return_to_menu and route_caller (for refinance).
4. agent/routing.py: route_caller(destination: "loan_officer" | "servicing") and return_to_menu() tools. They write a
   handoff packet (need, state, property, values, eligibility results, verification tier, consents, open questions)
   to tool_context.state["handoff"] and set tool_context.actions.transfer_to_agent. Sub-agents use
   disallow_transfer_to_peers=True.
5. Each agent's Gemini model gets its own speech_config; remove speech_config from RUN_CONFIG in api/dependencies.py.
6. policy.py: enforce AGENT_TOOL_ACCESS (block, don't just log) using the agent name from tool_context.
7. Remove agent/graph.py and CallState.active_agent; update agent/agent.py so root_agent = ccs_agent.
8. Tests: routing tool sets transfer and packet; each agent's tool list; policy blocks out-of-list tools.
9. Frontend: show the active agent name from a new "agent" event sent by routes.py when event.author changes.
```

## Prompt 3: Servicing verification tiers, recast and refinance

```
1. verify_loan(loan_number, property_address, borrower_last_name) -> Tier 1 when all three match the servicing DB
   (normalise address: case, punctuation, street suffixes). Count failures toward the 3-attempt lockout.
2. verify_passcode flow for Tier 2: send_passcode() generates a 6-digit code with 5-minute expiry via a pluggable
   sender (console sender locally); verify_passcode(code). Until OTP is wired, allow date of birth + SSN last 4 as
   Tier 2 behind env VERIFICATION_TIER2_MODE=otp|dob_ssn4, and actually check date of birth.
3. Map tools to tiers in policy.py: Tier 1 for balance, history, payoff, recast quote; Tier 2 for payments, autopay,
   payment methods, due-date change, recast request.
4. get_recast_quote(lump_sum): eligibility by loan type from data/mortgage/servicing_policy.json (min lump sum, fee,
   eligible types), new payment = re-amortised remaining balance at the same rate and remaining term. Return as
   estimate. submit_recast_request(lump_sum, consent): Tier 2 + consent; creates a request record.
5. check_refinance_interest(): compare the loan rate with rate_sheet.json for the loan's product; return the
   difference and a "say" offering Mac; never quote refinance terms.
6. Tests for each tier, address normalisation, recast maths, eligibility and the refinance handoff.
```

## Prompt 4: Guardrails

```
1. agent/guardrails/scope_policy.md: the global scope policy from section 8.2 of the architecture doc.
   Register ADK GlobalInstructionPlugin with it on the Runner in api/dependencies.py.
2. agent/guardrails/monitor.py: classify_turn(text) -> on_topic | off_topic | injection | abuse using a small Gemini
   text model (env GUARD_MODEL), with a rules pre-check for obvious injection phrases. In routes.py, run it
   asynchronously on each final input transcription; on off_topic/injection send a steering note into the
   LiveRequestQueue ("Caller asked something outside scope; politely refuse and offer the menu") and publish a
   "guardrail" event to the action log. Never block the audio path.
3. Output monitor: same classifier on final output transcriptions; log and alert on violations.
4. Tests with recorded transcripts for each class; monitor failures must not break the call.
```

## Prompt 5: PII redaction

```
1. core/pii.py: redact(text) with patterns and validators for card numbers (Luhn), SSN, loan numbers (format from
   data), phone, email, dates of birth, street addresses (number + street suffix). Returns text with [CARD], [SSN],
   [LOAN#] etc. Pure Python, no network.
2. agent/plugins/pii_redaction.py: ADK BasePlugin using on_event_callback to redact input/output transcription text
   before it is sent to the browser, stored in the session or logged. Register it on the Runner.
3. Use core/pii.redact in policy.py logging and in routes.py before sending transcripts.
4. Optional async step: a hook to send stored transcripts to Presidio or Sensitive Data Protection (interface only).
5. Tests: every pattern; a leak test that runs a scripted call through the plugin and asserts no raw card, SSN or
   loan number appears in captured logs or events.
```

## Prompt 6: Evaluation module

```
Create evals/ as described in section 9.3 of wiki/Mac_Multi_Agent_Architecture.md:
1. Eval sets (ADK .evalset.json format) for ccs_routing, lo_agent (include the Texas reference call), servicing
   (verification tiers, recast, refinance handoff), handoffs and guardrails (red-team), at least 8 cases each.
2. test_config.json with metrics: tool_trajectory_avg_score, final_response_match_v2,
   rubric_based_final_response_quality_v1, safety_v1, multi_turn_task_success_v1, with thresholds from section 9.5.
3. personas/ for the LLM-backed user simulator (first-time buyer, Texas homeowner, stressed past-due borrower,
   adversarial caller).
4. evals/test_evals.py using google.adk.evaluation.AgentEvaluator so `uv run pytest evals` runs them; mark them
   so the default `uv run pytest` (unit + integration) stays fast and free.
5. GitHub Actions workflow: unit tests on every push; evals on pull requests (needs GOOGLE_API_KEY secret).
6. evals/README.md: how to add a case, run locally, read results.
```

## Prompt 7: Session store and observability

```
1. Replace InMemorySessionService with DatabaseSessionService when SESSION_DB_URL is set (Cloud SQL Postgres or
   SQLite locally); keep in-memory as the default for tests.
2. Move CallState (verification tier, lockout, handoff packet, consents) into ADK session state so it survives
   restarts and is shared across agents.
3. Enable ADK OpenTelemetry export to Cloud Trace when running on Cloud Run; add the BigQuery agent analytics plugin
   behind env BQ_ANALYTICS_DATASET, after the PII redaction plugin.
4. Tests for state round-trip through the database session service.
```
