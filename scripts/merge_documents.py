#!/usr/bin/env python3
"""
Document Merger Script

Merges HomeFirst_AI_Complete_Documentation.docx with the structure and styling from
Mac_Mortgage_Advisor_Requirements_Phase1_Phase2.docx.

Creates a comprehensive document with:
- Mac's professional structure (title page, numbered sections, tables)
- HomeFirst's technical content (architecture, ADRs, ROI)
- Best content from both documents

Usage:
    uv run python scripts/merge_documents.py
"""

from pathlib import Path
from docx import Document
from docx.shared import Inches, Pt, RGBColor, Cm, Twips
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml.ns import qn, nsmap
from docx.oxml import OxmlElement


# =============================================================================
# STYLING CONSTANTS (Based on Mac document)
# =============================================================================

HEADING_COLOR = RGBColor(0x1F, 0x38, 0x64)  # Dark navy blue
TABLE_HEADER_BG = "1F3864"
TABLE_HEADER_TEXT = RGBColor(0xFF, 0xFF, 0xFF)
BODY_FONT = "Calibri"
HEADING_FONT = "Calibri"


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def set_cell_shading(cell, color_hex: str):
    """Set background color of a table cell."""
    shading = OxmlElement('w:shd')
    shading.set(qn('w:fill'), color_hex)
    cell._tc.get_or_add_tcPr().append(shading)


def set_table_borders(table):
    """Add borders to a table."""
    tbl = table._tbl
    tblPr = tbl.tblPr if tbl.tblPr is not None else OxmlElement('w:tblPr')
    tblBorders = OxmlElement('w:tblBorders')
    for border_name in ['top', 'left', 'bottom', 'right', 'insideH', 'insideV']:
        border = OxmlElement(f'w:{border_name}')
        border.set(qn('w:val'), 'single')
        border.set(qn('w:sz'), '4')
        border.set(qn('w:color'), 'CCCCCC')
        tblBorders.append(border)
    tblPr.append(tblBorders)
    if tbl.tblPr is None:
        tbl.insert(0, tblPr)


def add_heading(doc, text, level=1):
    """Add a styled heading."""
    para = doc.add_paragraph()
    run = para.add_run(text)
    run.font.name = HEADING_FONT
    run.font.color.rgb = HEADING_COLOR
    run.font.bold = True

    if level == 1:
        run.font.size = Pt(26)
        para.space_before = Pt(24)
        para.space_after = Pt(12)
    elif level == 2:
        run.font.size = Pt(16)
        para.space_before = Pt(18)
        para.space_after = Pt(8)
    elif level == 3:
        run.font.size = Pt(13)
        para.space_before = Pt(12)
        para.space_after = Pt(6)
    else:
        run.font.size = Pt(11)
        run.font.bold = True
        para.space_before = Pt(10)
        para.space_after = Pt(4)

    return para


def add_para(doc, text, bold=False):
    """Add a body paragraph."""
    para = doc.add_paragraph()
    run = para.add_run(text)
    run.font.name = BODY_FONT
    run.font.size = Pt(11)
    run.font.bold = bold
    para.space_after = Pt(8)
    return para


def add_bullet(doc, text):
    """Add a bullet point."""
    para = doc.add_paragraph(style='List Bullet')
    para.clear()
    run = para.add_run(text)
    run.font.name = BODY_FONT
    run.font.size = Pt(11)
    return para


def add_table(doc, headers, rows):
    """Add a styled table."""
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.LEFT

    # Header row
    for i, header in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = header
        set_cell_shading(cell, TABLE_HEADER_BG)
        for para in cell.paragraphs:
            for run in para.runs:
                run.font.bold = True
                run.font.color.rgb = TABLE_HEADER_TEXT
                run.font.size = Pt(10)
                run.font.name = BODY_FONT

    # Data rows
    for row_idx, row_data in enumerate(rows):
        for col_idx, cell_text in enumerate(row_data):
            cell = table.rows[row_idx + 1].cells[col_idx]
            cell.text = str(cell_text) if cell_text else ""
            for para in cell.paragraphs:
                for run in para.runs:
                    run.font.size = Pt(10)
                    run.font.name = BODY_FONT

    set_table_borders(table)
    doc.add_paragraph()  # Space after table
    return table


def add_title_page(doc, title, subtitle, date, version):
    """Create a professional title page."""
    # Push down
    for _ in range(8):
        doc.add_paragraph()

    # Main title
    para = doc.add_paragraph()
    run = para.add_run(title)
    run.font.name = HEADING_FONT
    run.font.size = Pt(36)
    run.font.color.rgb = HEADING_COLOR
    run.font.bold = True

    # Subtitle
    para = doc.add_paragraph()
    run = para.add_run(subtitle)
    run.font.name = BODY_FONT
    run.font.size = Pt(14)
    run.font.color.rgb = HEADING_COLOR

    # Line
    para = doc.add_paragraph()
    para.add_run("─" * 60)

    # Date and version
    para = doc.add_paragraph()
    run = para.add_run(f"{date} · {version}")
    run.font.name = BODY_FONT
    run.font.size = Pt(11)
    run.font.color.rgb = RGBColor(0x60, 0x60, 0x60)

    doc.add_page_break()


def add_header_footer(doc, header_text):
    """Add header and footer."""
    for section in doc.sections:
        # Header
        header = section.header
        para = header.paragraphs[0] if header.paragraphs else header.add_paragraph()
        para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        run = para.add_run(header_text)
        run.font.size = Pt(9)
        run.font.color.rgb = RGBColor(0x80, 0x80, 0x80)

        # Footer
        footer = section.footer
        para = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
        para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        run = para.add_run("Confidential draft")
        run.font.size = Pt(9)
        run.font.color.rgb = RGBColor(0x80, 0x80, 0x80)


def set_margins(doc):
    """Set page margins."""
    for section in doc.sections:
        section.top_margin = Cm(2.5)
        section.bottom_margin = Cm(2.5)
        section.left_margin = Cm(2.5)
        section.right_margin = Cm(2.5)


# =============================================================================
# MAIN DOCUMENT CREATION
# =============================================================================

def create_merged_document(output_path: Path):
    """Create the merged document with best of both sources."""

    doc = Document()
    set_margins(doc)

    # Title page (Mac style)
    add_title_page(
        doc,
        "HomeFirst AI",
        "Voice AI Mortgage Advisor · Use Cases, Scope and Requirements · Phase 1 and Phase 2",
        "24 November 2026",
        "Version 1.0 · Draft for review"
    )

    add_header_footer(doc, "HomeFirst AI · Use Cases, Scope & Requirements · Phase 1 and Phase 2")

    # =========================================================================
    # 1. INTRODUCTION (Mac structure + HomeFirst content)
    # =========================================================================
    add_heading(doc, "1. Introduction", 1)

    add_heading(doc, "1.1 Purpose", 2)
    add_para(doc, "This document defines the use cases, scope and requirements for HomeFirst AI, a voice AI agent for mortgage origination and servicing. It is the reference for product, engineering, compliance and operations teams.")

    add_heading(doc, "1.2 Product Summary", 2)
    add_para(doc, "HomeFirst AI is a production-ready, voice-powered AI system built on Google Agent Development Kit (ADK) and Gemini Live API. It enables natural, conversational interactions for mortgage inquiries and loan servicing.")
    add_para(doc, "The system hosts three AI personas: Sam (triage), Mac (origination) and Ivy (servicing). Mac helps home buyers and homeowners find the right mortgage, checks eligibility against state rules, and connects qualified callers to a licensed loan officer. Ivy helps existing borrowers with balances, payments and autopay. By automating origination with AI, HomeFirst aims to save borrowers 0.5% to 1% in interest compared with traditional lenders.")

    add_heading(doc, "1.3 Objectives", 2)
    add_table(doc,
        ["#", "Objective", "Measure"],
        [
            ["O1", "Answer mortgage enquiries around the clock", "Calls handled without a human; caller satisfaction"],
            ["O2", "Screen eligibility correctly before a loan officer spends time", "100% accuracy on regulated test scenarios"],
            ["O3", "Hand qualified callers to a loan officer with full context", "Time to loan officer; loan officer rating of the handoff"],
            ["O4", "Serve existing borrowers securely", "Zero unauthorised account changes or payments"],
            ["O5", "Lower origination cost to fund the 0.5-1% rate saving", "Cost per call versus human-handled cost"],
        ]
    )

    add_heading(doc, "1.4 Key Features", 2)
    add_bullet(doc, "Multi-Agent System: Three specialized personas (Sam, Mac, Ivy) with seamless voice handoffs")
    add_bullet(doc, "Voice-First: Native Gemini Live API with barge-in support and <500ms latency")
    add_bullet(doc, "Policy Door: Every tool call validated for compliance before and after execution")
    add_bullet(doc, "State Rules: Texas, California, Florida HELOC regulations enforced in code")
    add_bullet(doc, "Two-Level Verification: Basic and strong identity checks based on action sensitivity")
    add_bullet(doc, "Payment Authorization: Three-step flow (Prepare → Read-back → Confirm) with explicit consent")
    add_bullet(doc, "Fail-Closed Design: Unknown states always route to human agents")

    add_heading(doc, "1.5 Conventions", 2)
    add_para(doc, "Requirement IDs: UC = use case, FR = functional requirement, BR = business rule, NFR = non-functional requirement. Phase 2 items carry a P2- prefix. Priority uses Must, Should, Could. Phase 1 status is Built (in the code and tested), Partial (in the code with a known gap) or Planned.")

    add_heading(doc, "1.6 Assumptions", 2)
    add_bullet(doc, "CCS Agent means the current customer-facing voice agent: Mac for origination and Ivy for servicing.")
    add_bullet(doc, "LO Agent is a new AI agent (Phase 2) that supports, and works under, a licensed loan officer. It does not replace one.")
    add_bullet(doc, "Phase 1 runs as a web voice client; phone (PSTN) access is a later phase.")
    add_bullet(doc, "Card capture, loan officer transfer and loan origination system (LOS) updates are simulated in Phase 1.")

    # =========================================================================
    # 2. STAKEHOLDERS AND ACTORS
    # =========================================================================
    add_heading(doc, "2. Stakeholders and Actors", 1)

    add_table(doc,
        ["Actor", "Type", "Description"],
        [
            ["Prospective borrower", "Human", "Home buyer or homeowner asking about a new loan, refinance or HELOC"],
            ["Existing borrower", "Human", "Customer with a loan serviced by HomeFirst"],
            ["Sam (Triage Agent)", "AI agent", "Initial greeting, caller routing, intent classification, quick answers"],
            ["Mac (CCS Agent, origination)", "AI agent", "Answers enquiries, screens eligibility, compares options, registers leads, transfers"],
            ["Ivy (CCS Agent, servicing)", "AI agent", "Verifies identity; handles balances, payoff, autopay, payments and payment methods"],
            ["LO Agent (Phase 2)", "AI agent", "Continues qualified conversations under a licensed loan officer"],
            ["Licensed loan officer (LO)", "Human", "NMLS-licensed originator who takes applications and makes offers"],
            ["Compliance officer", "Human", "Approves regulation sources, rules and scripts"],
            ["Operations supervisor", "Human", "Monitors calls, actions, policy verdicts and cost"],
            ["External systems", "System", "Gemini Live API; in Phase 2, LOS, CRM, pricing engine and calendars via MCP"],
        ]
    )

    # =========================================================================
    # 3. SCOPE
    # =========================================================================
    add_heading(doc, "3. Scope", 1)

    add_heading(doc, "3.1 Phase 1 Scope (Current Release)", 2)
    add_table(doc,
        ["Area", "In Scope"],
        [
            ["Voice", "Real-time, interruptible voice conversation in the browser with captions and typed fallback"],
            ["Origination (Mac)", "Products, rate estimates, HELOC eligibility with state rules, equity, option comparison, regulation questions with citations, lead registration, transfer request"],
            ["Servicing (Ivy)", "Two-level identity verification, balance, payoff quote, payment history, due-date change, autopay, one-time payment with read-back and authorisation, payment method management"],
            ["Compliance", "Policy checks on every action, fail-closed state rules, disclaimers, regulation knowledge pipeline with approval step"],
            ["Operations", "Live action log, policy verdicts, token and cost tracking"],
            ["States", "Texas, California and Florida rules on file; all other states routed to a loan officer"],
        ]
    )

    add_heading(doc, "3.2 Out of Scope for Phase 1", 2)
    add_bullet(doc, "Phone (PSTN) calls and real call transfer")
    add_bullet(doc, "Live pricing feed; rates come from a sample rate sheet")
    add_bullet(doc, "Writing to a real LOS or CRM")
    add_bullet(doc, "Taking a formal loan application, approving loans, locking rates")
    add_bullet(doc, "Collections and welcome-call personas (defined in code for a later phase)")
    add_bullet(doc, "Legal or tax advice")

    add_heading(doc, "3.3 Phase 2 Scope (Planned)", 2)
    add_table(doc,
        ["Feature", "Summary"],
        [
            ["MCP integration", "Connect agents to back-office systems through MCP servers, and publish Mac's governed tools as an MCP server"],
            ["LO Agent", "A new AI agent that continues the conversation after screening: scenario review, pre-qualification estimate, document checklist, application intake draft and scheduling, under a licensed loan officer"],
            ["CCS → LO Agent transfer", "A warm, in-call transfer from the CCS Agent to the LO Agent that carries the full context, with consent and a fallback to a human loan officer"],
        ]
    )
    add_para(doc, "Phone channel, persistent production storage, live pricing and additional states are expected to follow, and are not scheduled in this document.")

    # =========================================================================
    # 4. MULTI-AGENT ARCHITECTURE
    # =========================================================================
    add_heading(doc, "4. Multi-Agent Architecture", 1)

    add_para(doc, "The system uses persona switching (not agent-to-agent routing) for seamless voice handoffs with zero audio gaps. A single Google ADK agent runs a Gemini Live session and loads its instructions from a function on every turn, so the active persona can change during a call.")

    add_heading(doc, "4.1 Agent Personas", 2)

    add_heading(doc, "Sam - Triage Agent", 3)
    add_bullet(doc, "Initial greeting and caller routing")
    add_bullet(doc, "Intent classification")
    add_bullet(doc, "Quick answers to general questions")

    add_heading(doc, "Mac - Origination Specialist", 3)
    add_bullet(doc, "HELOC eligibility with state rules (TX, CA, FL)")
    add_bullet(doc, "Rate estimates with required disclaimers")
    add_bullet(doc, "Equity calculations and option comparison")
    add_bullet(doc, "Lead capture and loan officer transfer")

    add_heading(doc, "Ivy - Servicing Specialist", 3)
    add_bullet(doc, "Two-level identity verification (basic and strong)")
    add_bullet(doc, "Balance, payoff quote and payment history")
    add_bullet(doc, "One-time payments with three-step authorization")
    add_bullet(doc, "Autopay setup, cancellation and management")

    add_heading(doc, "4.2 Components", 2)
    add_table(doc,
        ["Component", "File(s)", "Responsibility"],
        [
            ["Voice service", "mortgage/server.py", "WebSocket bridge, Live session, transcripts, usage, event feed"],
            ["Agent", "mortgage/agent.py", "ADK agent with 28 tools and the policy callbacks"],
            ["Personas", "mortgage/persona.py, personas/", "Mac and Ivy instructions; persona selected from call state"],
            ["Routing", "mortgage/routing.py", "Intent detection and persona hand-off logic"],
            ["Policy door", "mortgage/policy.py", "Verification levels, lockout, payment authorisation, input checks, disclaimers"],
            ["Observer", "mortgage/observer.py", "Suggestions from tool results; risk flags"],
            ["Origination domain", "mortgage/mortgage.py, tools.py", "Rules, normalisation, pricing, comparison, officers"],
            ["Servicing domain", "mortgage/servicing.py, database.py", "Loans, schedules, payments, methods in SQLite"],
            ["Regulation knowledge", "mortgage/knowledge/", "Source list, ingestion, approval, search index"],
            ["Data", "assets/mortgage/", "mortgage.json, rate_sheet.json, servicing_seed.json"],
        ]
    )

    add_heading(doc, "4.3 Tool Catalogue", 2)
    add_table(doc,
        ["Agent", "Tools"],
        [
            ["Mac (13)", "get_company_info, get_mortgage_products, check_heloc_eligibility, check_state_regulations, get_rate_estimate, calculate_equity, compare_options, search_regulations, answer_faq, verify_customer, verify_customer_strong, register_lead, transfer_to_loan_officer"],
            ["Ivy (15)", "get_loan_balance, get_payment_history, get_payoff_quote, change_payment_date, get_autopay_status, setup_autopay, cancel_autopay, get_payment_methods, initiate_secure_card_capture, complete_secure_card_capture, add_bank_account, set_default_payment_method, remove_payment_method, prepare_payment, confirm_payment"],
        ]
    )

    # =========================================================================
    # 5. POLICY DOOR PATTERN
    # =========================================================================
    add_heading(doc, "5. Policy Door Pattern", 1)

    add_para(doc, "The Policy Door ensures compliance by validating every tool call before and after execution. This is the core compliance mechanism that enforces business rules deterministically in code, not in prompts.")

    add_heading(doc, "5.1 Before Callback (Validation)", 2)
    add_bullet(doc, "Agent access control (Sam can't use payment tools)")
    add_bullet(doc, "Input validation (state codes, credit scores, amounts)")
    add_bullet(doc, "Verification level check (basic vs strong required)")
    add_bullet(doc, "Lockout status check (3 failures = locked for the call)")

    add_heading(doc, "5.2 After Callback (Enrichment)", 2)
    add_bullet(doc, "Add required disclaimers to rate estimates")
    add_bullet(doc, "Suggest loan officer transfer for complex cases")
    add_bullet(doc, "Redact PII in audit logs")
    add_bullet(doc, "Record action for compliance trail")

    # =========================================================================
    # 6. PHASE 1 USE CASES
    # =========================================================================
    add_heading(doc, "6. Phase 1 Use Cases", 1)

    add_heading(doc, "6.1 Use Case Summary", 2)
    add_table(doc,
        ["ID", "Use Case", "Primary Actor", "Agent", "Status"],
        [
            ["UC-01", "Start a call and greet the caller", "Any caller", "Sam/Mac/Ivy", "Built"],
            ["UC-02", "Check HELOC eligibility (reference call)", "Prospective borrower", "Mac", "Built"],
            ["UC-03", "Compare mortgage options", "Prospective borrower", "Mac", "Partial"],
            ["UC-04", "Get a rate estimate", "Prospective borrower", "Mac", "Built"],
            ["UC-05", "Calculate equity and borrowing power", "Prospective borrower", "Mac", "Built"],
            ["UC-06", "Ask a regulation question", "Prospective borrower", "Mac", "Partial"],
            ["UC-07", "Ask about products, company or FAQs", "Any caller", "Mac", "Built"],
            ["UC-08", "Register a lead for follow-up", "Prospective borrower", "Mac", "Built"],
            ["UC-09", "Request a licensed loan officer", "Any caller", "Mac/Ivy", "Partial"],
            ["UC-10", "Verify identity (basic and strong)", "Existing borrower", "Ivy", "Partial"],
            ["UC-11", "Check balance, payoff or payment history", "Existing borrower", "Ivy", "Built"],
            ["UC-12", "Change the payment due date", "Existing borrower", "Ivy", "Built"],
            ["UC-13", "Set up or cancel autopay", "Existing borrower", "Ivy", "Built"],
            ["UC-14", "Make a one-time payment", "Existing borrower", "Ivy", "Built"],
            ["UC-15", "Manage payment methods", "Existing borrower", "Ivy", "Built"],
            ["UC-16", "Receive proactive suggestions (observer)", "Mac/Ivy", "System", "Built"],
            ["UC-17", "Maintain regulation knowledge", "Compliance officer", "System", "Partial"],
            ["UC-18", "Monitor a call", "Operations supervisor", "System", "Built"],
        ]
    )

    add_heading(doc, "6.2 Key Use Case: UC-02 Check HELOC Eligibility", 2)
    add_table(doc,
        ["Item", "Detail"],
        [
            ["Actor", "Prospective borrower"],
            ["Trigger", "Caller asks whether they can get a HELOC on a property"],
            ["Preconditions", "Call connected; Mac has greeted the caller"],
            ["Main flow", "1. Caller describes properties, state and amount. 2. Mac calls check_heloc_eligibility with the state and the caller's own words for property use. 3. The system normalises property use and applies state rules. 4. Mac explains outcome and asks about alternatives if not eligible. 5. Mac offers alternatives or a licensed loan officer."],
            ["Alternate flows", "State without rules on file: Mac says it can't confirm and offers a loan officer. Property use unclear: Mac asks the caller to clarify."],
            ["Rules", "BR-01 to BR-05"],
        ]
    )

    add_heading(doc, "6.3 Key Use Case: UC-14 Make a One-Time Payment", 2)
    add_table(doc,
        ["Item", "Detail"],
        [
            ["Actor", "Existing borrower (strong verification required)"],
            ["Trigger", "Caller asks to make a payment"],
            ["Main flow", "1. Caller asks to pay. 2. If needed, Ivy starts secure keypad card capture (never by voice). 3. prepare_payment sets amount, method and date. 4. Ivy reads back amount, last 4 digits and date and asks for authorisation. 5. Only after a clear 'yes' does confirm_payment(authorized=True) run. 6. Ivy gives the confirmation number."],
            ["Alternate flows", "Caller declines: payment cancelled. confirm_payment without a prepared payment or without authorisation is blocked."],
            ["Rules", "BR-10 to BR-12"],
        ]
    )

    # =========================================================================
    # 7. PHASE 1 FUNCTIONAL REQUIREMENTS
    # =========================================================================
    add_heading(doc, "7. Phase 1 Functional Requirements", 1)

    add_heading(doc, "7.1 Conversation and Voice", 2)
    add_table(doc,
        ["ID", "Requirement", "Priority", "Status"],
        [
            ["FR-01", "Hold a real-time voice conversation; stop speaking when interrupted and resume the thread", "Must", "Built"],
            ["FR-02", "Greet the caller, state that the agent is an AI, and give the persona's greeting", "Must", "Built"],
            ["FR-03", "Show live captions for both sides and accept typed input", "Should", "Built"],
            ["FR-04", "Speak numbers clearly and explain jargon (LTV, CLTV, DTI)", "Must", "Built"],
            ["FR-05", "Use tool results for every fact; never invent rates, products or rules", "Must", "Built"],
            ["FR-06", "Switch between Mac and Ivy during a call based on the caller's need", "Should", "Partial"],
        ]
    )

    add_heading(doc, "7.2 Origination (Mac)", 2)
    add_table(doc,
        ["ID", "Requirement", "Priority", "Status"],
        [
            ["FR-10", "Check HELOC eligibility using state rules, property use and existing cash-out", "Must", "Built"],
            ["FR-11", "Explain why a product is not available and present alternatives", "Must", "Built"],
            ["FR-12", "Treat states with no approved rules as 'needs loan officer review', never as eligible", "Must", "Built"],
            ["FR-13", "Calculate equity, loan-to-value and maximum borrowing", "Must", "Built"],
            ["FR-14", "Give rate estimates by product, credit tier and LTV band, always with the disclaimer", "Must", "Built"],
            ["FR-15", "Compare eligible options with rate, payment and payment type; list excluded options", "Should", "Partial"],
            ["FR-16", "Describe products and answer FAQs and company questions", "Must", "Built"],
            ["FR-17", "Register a lead with name, phone, enquiry type, state and summary, and assign an officer", "Must", "Built"],
        ]
    )

    add_heading(doc, "7.3 Servicing (Ivy)", 2)
    add_table(doc,
        ["ID", "Requirement", "Priority", "Status"],
        [
            ["FR-30", "Provide balance, next payment, past-due status and payoff quote", "Must", "Built"],
            ["FR-31", "Provide payment history", "Must", "Built"],
            ["FR-32", "Change the monthly due date (1st to 28th)", "Should", "Built"],
            ["FR-33", "Show, set up and cancel autopay", "Must", "Built"],
            ["FR-34", "Capture card details by secure keypad entry; never by voice", "Must", "Built"],
            ["FR-35", "Add bank accounts, set a default method, remove a method", "Should", "Built"],
            ["FR-36", "Take a one-time payment only after read-back and explicit authorisation", "Must", "Built"],
            ["FR-37", "Offer hardship options empathetically on past-due accounts", "Should", "Built"],
        ]
    )

    add_heading(doc, "7.4 Identity and Security", 2)
    add_table(doc,
        ["ID", "Requirement", "Priority", "Status"],
        [
            ["FR-40", "Basic verification (name + phone last 4) before any account information", "Must", "Built"],
            ["FR-41", "Strong verification (date of birth + approximate balance) before changes or payments", "Must", "Partial"],
            ["FR-42", "Lock verification after three failed attempts and offer a human", "Must", "Built"],
            ["FR-43", "Read back only the last 4 digits of any card or account", "Must", "Built"],
            ["FR-44", "Redact personal data in logs", "Must", "Built"],
            ["FR-45", "Restrict each persona to its own tool set", "Should", "Partial"],
        ]
    )

    # =========================================================================
    # 8. BUSINESS RULES
    # =========================================================================
    add_heading(doc, "8. Business Rules", 1)

    add_table(doc,
        ["ID", "Rule", "Source / Owner"],
        [
            ["BR-01", "Texas home equity lending (including HELOCs) is allowed only on a homestead; never on investment property", "Texas Const. Art. XVI §50"],
            ["BR-02", "Texas: no HELOC while an existing home equity loan (including a Texas cash-out refinance) is on the homestead", "Texas Const. Art. XVI §50"],
            ["BR-03", "Texas: combined loan-to-value at most 80%", "Texas Const. Art. XVI §50"],
            ["BR-04", "Texas: 12-day notice before closing and 3-day right to cancel after closing", "Texas Const. Art. XVI §50; Reg Z"],
            ["BR-05", "Texas cash-out refinance: at most one in 12 months; 80% LTV cap", "Texas Const. Art. XVI §50"],
            ["BR-06", "Any state without approved rules: no eligibility answer; route to a loan officer", "HomeFirst policy"],
            ["BR-07", "Every rate statement carries the rate disclaimer; rates are estimates only", "Reg Z advertising; HomeFirst policy"],
            ["BR-08", "The AI never approves a loan, locks a rate, takes an application or gives legal or tax advice", "SAFE Act; HomeFirst policy"],
            ["BR-09", "Basic verification before account data; strong verification before changes or payments", "HomeFirst security policy"],
            ["BR-10", "No card number is captured by voice", "PCI DSS"],
            ["BR-11", "Payments need read-back and an explicit 'yes' before processing", "HomeFirst policy; Reg E"],
            ["BR-12", "Due date may be set between the 1st and 28th", "Servicing policy"],
        ]
    )
    add_para(doc, "Rules BR-01 to BR-05 and the related wording must be approved by compliance counsel before customer use.", bold=True)

    # =========================================================================
    # 9. PAYMENT AUTHORIZATION FLOW
    # =========================================================================
    add_heading(doc, "9. Payment Authorization Flow", 1)

    add_para(doc, "Payments require explicit three-step authorization to prevent accidental transactions.")

    add_heading(doc, "Step 1: PREPARE", 2)
    add_bullet(doc, "Caller states payment intent")
    add_bullet(doc, "Tool stages payment details (amount, method, date)")
    add_bullet(doc, "Sets pending_authorization flag in call state")

    add_heading(doc, "Step 2: READ-BACK", 2)
    add_bullet(doc, "Agent reads back all payment details")
    add_bullet(doc, "Amount, account (last 4 digits only), payment method, date")
    add_bullet(doc, "Explicitly asks for authorization")

    add_heading(doc, "Step 3: CONFIRM", 2)
    add_bullet(doc, "Caller verbally confirms 'yes'")
    add_bullet(doc, "Payment executed via confirm_payment(authorized=True)")
    add_bullet(doc, "Confirmation number provided to caller")

    add_para(doc, "Security: confirm_payment without a prepared payment or without explicit authorization is blocked by the policy door.")

    # =========================================================================
    # 10. SECURITY & IDENTITY VERIFICATION
    # =========================================================================
    add_heading(doc, "10. Security & Identity Verification", 1)

    add_para(doc, "The system implements two levels of identity verification based on action sensitivity.")

    add_heading(doc, "10.1 Basic Verification", 2)
    add_para(doc, "Required for: Balance inquiries, payment history, account information")
    add_bullet(doc, "Full name on account")
    add_bullet(doc, "Last 4 digits of phone number on file")

    add_heading(doc, "10.2 Strong Verification", 2)
    add_para(doc, "Required for: Payments, autopay changes, sensitive operations")
    add_bullet(doc, "Date of birth")
    add_bullet(doc, "Approximate loan balance (within $5,000)")

    add_heading(doc, "10.3 Lockout Protection", 2)
    add_bullet(doc, "3 failed attempts = account locked for the call")
    add_bullet(doc, "Automatic transfer offered to human agent")
    add_bullet(doc, "Security event logged for review")

    add_heading(doc, "10.4 Security Requirements", 2)
    add_table(doc,
        ["Requirement", "Implementation"],
        [
            ["Data in transit", "TLS 1.3"],
            ["Data at rest", "AES-256 (Cloud SQL)"],
            ["PII handling", "Redaction in logs, tokenization"],
            ["Card data", "Secure keypad only, never voice"],
            ["Session management", "Per-call state, cleared at end"],
            ["Audit logging", "All actions and policy verdicts recorded"],
        ]
    )

    # =========================================================================
    # 11. NON-FUNCTIONAL REQUIREMENTS
    # =========================================================================
    add_heading(doc, "11. Non-Functional Requirements", 1)

    add_heading(doc, "11.1 Performance Requirements", 2)
    add_table(doc,
        ["Metric", "Target", "Measurement"],
        [
            ["Voice-to-voice latency", "< 500ms", "End of speech to start of response"],
            ["Tool execution time", "< 200ms", "Single tool call"],
            ["Barge-in response", "< 300ms", "Stop speaking when interrupted"],
            ["Agent start speaking", "< 1s", "After caller finishes"],
        ]
    )

    add_heading(doc, "11.2 Availability & Recovery", 2)
    add_table(doc,
        ["Metric", "Target", "Description"],
        [
            ["Uptime (Production)", "99.9%", "8.76 hours downtime/year"],
            ["RTO", "15 minutes", "Maximum recovery time"],
            ["RPO", "1 hour", "Maximum data loss"],
        ]
    )

    add_heading(doc, "11.3 Scalability", 2)
    add_table(doc,
        ["Resource", "Minimum", "Maximum", "Trigger"],
        [
            ["Cloud Run instances", "0", "100", "CPU > 70%"],
            ["vCPU per instance", "1", "1", "Fixed"],
            ["Memory per instance", "512MB", "512MB", "Fixed"],
            ["Concurrent connections", "1", "1000", "Per instance"],
        ]
    )

    add_heading(doc, "11.4 Monitoring & SLAs", 2)
    add_table(doc,
        ["Metric", "Alert Threshold", "SLA Target"],
        [
            ["Error rate", "> 1%", "< 0.1%"],
            ["P95 latency", "> 1000ms", "< 500ms"],
            ["Availability", "< 99.9%", "99.9%"],
        ]
    )

    # =========================================================================
    # 12. GCP DEPLOYMENT ARCHITECTURE
    # =========================================================================
    add_heading(doc, "12. GCP Deployment Architecture", 1)

    add_para(doc, "The system deploys as serverless containers on Google Cloud Run with auto-scaling.")

    add_table(doc,
        ["Component", "Purpose"],
        [
            ["Global Load Balancer", "SSL termination, WebSocket support, DDoS protection"],
            ["Cloud Run", "Serverless containers with 0-100 auto-scaling"],
            ["Cloud SQL (PostgreSQL)", "Persistent storage for leads, payments, audit"],
            ["Cloud Memorystore (Redis)", "Session state, rate limiting"],
            ["Secret Manager", "API keys, credentials"],
            ["Cloud Monitoring", "Metrics, alerts, dashboards"],
        ]
    )

    # =========================================================================
    # 13. BUSINESS IMPACT & ROI
    # =========================================================================
    add_heading(doc, "13. Business Impact & ROI", 1)

    add_heading(doc, "13.1 Value Metrics", 2)
    add_table(doc,
        ["Metric", "Before", "After", "Improvement"],
        [
            ["Cost per inquiry", "$45", "$5", "89% reduction"],
            ["After-hours capture", "0%", "100%", "Full coverage"],
            ["Lead qualification time", "15 min", "3 min", "80% faster"],
            ["Compliance accuracy", "95%", "100%", "Zero violations"],
        ]
    )

    add_heading(doc, "13.2 Annual Savings: $540,000", 2)
    add_bullet(doc, "Reduced call center staff (3 FTE): $180,000")
    add_bullet(doc, "After-hours lead capture: $240,000")
    add_bullet(doc, "Faster lead qualification: $120,000")

    add_heading(doc, "13.3 ROI Metrics", 2)
    add_bullet(doc, "Payback period: 5 months")
    add_bullet(doc, "Year 1 ROI: 157%")
    add_bullet(doc, "5-Year NPV: $1.8M")

    # =========================================================================
    # 14. PHASE 2 REQUIREMENTS (PLANNED)
    # =========================================================================
    add_heading(doc, "14. Phase 2 Requirements (Planned)", 1)

    add_heading(doc, "14.1 Overview", 2)
    add_para(doc, "Phase 2 adds three capabilities on the Phase 1 foundation. MCP connects the agents to real systems and shares Mac's governed tools with other agents. The LO Agent carries a qualified caller further toward an application. The CCS → LO Agent transfer moves the caller between agents in the same call without losing context.")

    add_heading(doc, "14.2 Phase 2 Use Cases", 2)
    add_table(doc,
        ["ID", "Use Case", "Primary Actor", "Priority"],
        [
            ["P2-UC-01", "Agent reads and writes back-office data through MCP (LOS, CRM, pricing, calendars)", "CCS/LO Agent", "Must"],
            ["P2-UC-02", "Another agent uses Mac's eligibility and comparison tools through MCP", "External agent", "Should"],
            ["P2-UC-03", "Warm transfer from the CCS Agent to the LO Agent", "Prospective borrower", "Must"],
            ["P2-UC-04", "LO Agent gives a pre-qualification estimate and document checklist", "Prospective borrower", "Must"],
            ["P2-UC-05", "LO Agent drafts an application intake record for a licensed LO to review", "Prospective borrower", "Should"],
            ["P2-UC-06", "LO Agent books a meeting with a licensed LO", "Prospective borrower", "Must"],
            ["P2-UC-07", "LO Agent escalates to a licensed LO (warm transfer or call-back)", "Prospective borrower", "Must"],
            ["P2-UC-08", "Transfer fails or LO Agent unavailable; caller routed to human or call-back", "Any caller", "Must"],
        ]
    )

    add_heading(doc, "14.3 MCP Integration Requirements", 2)
    add_table(doc,
        ["ID", "Requirement", "Priority"],
        [
            ["P2-FR-01", "Consume MCP servers with ADK McpToolset for LOS, CRM, pricing engine, LO calendars", "Must"],
            ["P2-FR-02", "Apply the same policy door to MCP tools as to native tools", "Must"],
            ["P2-FR-03", "Allow-list MCP tools per agent; tools not on the list are never exposed", "Must"],
            ["P2-FR-04", "Authenticate to MCP servers with OAuth 2.1 from secret manager", "Must"],
            ["P2-FR-07", "Publish Mac's governed tools as an MCP server using ADK to_mcp_server", "Should"],
        ]
    )

    add_heading(doc, "14.4 LO Agent Requirements", 2)
    add_table(doc,
        ["ID", "Requirement", "Priority"],
        [
            ["P2-FR-20", "Separate ADK agent with its own persona, instructions and tool allow-list", "Must"],
            ["P2-FR-21", "Introduce itself as an AI assistant working with the HomeFirst loan officer team", "Must"],
            ["P2-FR-23", "Provide a non-binding pre-qualification estimate with disclaimers", "Must"],
            ["P2-FR-24", "Provide a document checklist for the product and caller's situation", "Must"],
            ["P2-FR-26", "Book a meeting or call-back with a licensed LO via calendar MCP server", "Must"],
            ["P2-FR-28", "Never approve, deny, lock a rate, or offer or negotiate loan terms", "Must"],
        ]
    )

    add_heading(doc, "14.5 Handoff Packet", 2)
    add_table(doc,
        ["Field", "Description"],
        [
            ["call_id, handoff_id, timestamp", "Identifiers and time of the handoff"],
            ["from_agent, to_agent, reason", "Source, target and why the transfer happened"],
            ["caller", "First name, callback phone, verification level, lead ID"],
            ["need", "Product interest, amount, purpose, in one sentence"],
            ["property", "State, property use, estimated value, balance, existing loan type"],
            ["eligibility", "Each check run, its outcome, issues and rule source"],
            ["options", "Options shown and options excluded, with reasons"],
            ["consents", "Recording disclosure, contact consent, transfer consent"],
            ["open_questions", "What the caller asked that is still unanswered"],
        ]
    )

    # =========================================================================
    # 15. ARCHITECTURE DECISION RECORDS
    # =========================================================================
    add_heading(doc, "15. Architecture Decision Records (ADRs)", 1)

    add_heading(doc, "ADR-0001: Persona Switching Over Agent-to-Agent Routing", 2)
    add_para(doc, "Status: Accepted | Date: 2026-11-01")
    add_para(doc, "Decision: Use persona switching (dynamic instructions) instead of multi-agent routing for voice handoffs.")
    add_para(doc, "Rationale:")
    add_bullet(doc, "Zero audio gaps during transfers")
    add_bullet(doc, "Conversation context preserved")
    add_bullet(doc, "Single ADK agent simplifies architecture")
    add_bullet(doc, "Faster response times")

    add_heading(doc, "ADR-0002: Rules in Code, Not Prompts", 2)
    add_para(doc, "Status: Accepted | Date: 2026-11-01")
    add_para(doc, "Decision: Enforce business rules in Python code (tools), not in prompt instructions.")
    add_para(doc, "Rationale:")
    add_bullet(doc, "Deterministic behavior")
    add_bullet(doc, "Testable and auditable")
    add_bullet(doc, "LLM cannot bypass rules")
    add_bullet(doc, "State laws (TX, CA, FL) enforced by tools")

    add_heading(doc, "ADR-0003: Two-Level Identity Verification", 2)
    add_para(doc, "Status: Accepted | Date: 2026-11-05")
    add_para(doc, "Decision: Implement Basic and Strong verification levels based on action sensitivity.")
    add_para(doc, "Rationale:")
    add_bullet(doc, "Balance security with user experience")
    add_bullet(doc, "Reduce friction for read-only actions")
    add_bullet(doc, "Strong verification required for financial transactions")

    add_heading(doc, "ADR-0004: Fail-Closed Design", 2)
    add_para(doc, "Status: Accepted | Date: 2026-11-01")
    add_para(doc, "Decision: Route all unknown or error states to human agents.")
    add_para(doc, "Rationale:")
    add_bullet(doc, "Safety-first approach")
    add_bullet(doc, "Regulatory compliance")
    add_bullet(doc, "Customer trust")

    add_heading(doc, "ADR-0005: Three-Step Payment Authorization", 2)
    add_para(doc, "Status: Accepted | Date: 2026-11-10")
    add_para(doc, "Decision: Require PREPARE → READ-BACK → CONFIRM flow for all payments.")
    add_para(doc, "Rationale:")
    add_bullet(doc, "Prevent accidental payments")
    add_bullet(doc, "Explicit verbal consent")
    add_bullet(doc, "Regulatory compliance (CFPB)")

    add_heading(doc, "ADR-0006: Gemini Live API Selection", 2)
    add_para(doc, "Status: Accepted | Date: 2026-10-25")
    add_para(doc, "Decision: Use Gemini Live API (AI Studio) for voice AI implementation.")
    add_para(doc, "Rationale:")
    add_bullet(doc, "Native bidirectional audio streaming")
    add_bullet(doc, "Sub-200ms latency")
    add_bullet(doc, "Built-in function calling")
    add_bullet(doc, "Barge-in support")

    # =========================================================================
    # 16. GETTING STARTED
    # =========================================================================
    add_heading(doc, "16. Getting Started", 1)

    add_heading(doc, "16.1 Quick Start", 2)
    add_para(doc, "# Clone and setup")
    add_para(doc, "git clone <repository>")
    add_para(doc, "cd mortgage-advisor-ai-adk")
    add_para(doc, "uv sync")
    add_para(doc, "")
    add_para(doc, "# Configure")
    add_para(doc, "cp .env.example .env")
    add_para(doc, "# Edit .env and add GOOGLE_API_KEY")
    add_para(doc, "")
    add_para(doc, "# Run")
    add_para(doc, "uv run uvicorn mortgage.server:app --port 8000")

    add_heading(doc, "16.2 Development Commands", 2)
    add_table(doc,
        ["Command", "Description"],
        [
            ["uv run pytest", "Run tests with coverage"],
            ["uv run ruff check mortgage/", "Lint code"],
            ["uv run ruff format mortgage/", "Format code"],
            ["uv run mypy mortgage/", "Type check"],
        ]
    )

    add_heading(doc, "16.3 API Endpoints", 2)
    add_table(doc,
        ["Endpoint", "Method", "Description"],
        [
            ["/health", "GET", "Comprehensive health check"],
            ["/healthz", "GET", "Kubernetes liveness probe"],
            ["/readyz", "GET", "Kubernetes readiness probe"],
            ["/info", "GET", "Application info"],
            ["/metrics", "GET", "Prometheus metrics"],
            ["/ws", "WebSocket", "Voice WebSocket connection"],
        ]
    )

    # =========================================================================
    # 17. APPENDIX
    # =========================================================================
    add_heading(doc, "17. Appendix", 1)

    add_heading(doc, "17.1 Glossary", 2)
    add_table(doc,
        ["Term", "Meaning"],
        [
            ["ADK", "Google Agent Development Kit, the framework the agents are built on"],
            ["CCS Agent", "The current customer-facing voice agent: Mac (origination) and Ivy (servicing)"],
            ["LO Agent", "Phase 2 AI agent that supports licensed loan officers in the call"],
            ["LO", "Licensed loan officer (NMLS mortgage loan originator)"],
            ["MCP", "Model Context Protocol, a standard for connecting AI agents to tools and data"],
            ["Handoff packet", "Structured summary passed between agents at transfer"],
            ["Policy door", "Code that checks every tool call before and after it runs"],
            ["HELOC", "Home equity line of credit"],
            ["LTV / CLTV", "Loan-to-value / combined loan-to-value"],
            ["LOS", "Loan origination system"],
            ["SAFE Act", "US law requiring mortgage loan originators to be licensed or registered"],
        ]
    )

    add_heading(doc, "17.2 Test Coverage", 2)
    add_bullet(doc, "200 automated tests")
    add_bullet(doc, "Unit tests for all tools")
    add_bullet(doc, "Integration tests for flows")
    add_bullet(doc, "Policy validation tests")

    add_heading(doc, "17.3 Compliance Considerations", 2)
    add_bullet(doc, "State lending regulations (TX, CA, FL)")
    add_bullet(doc, "CFPB payment authorization rules")
    add_bullet(doc, "PII handling and redaction")
    add_bullet(doc, "Audit logging requirements")

    add_heading(doc, "17.4 Open Questions", 2)
    add_bullet(doc, "Which LOS, CRM, pricing engine and calendar systems will the MCP servers front?")
    add_bullet(doc, "Should the LO Agent have its own name and voice, or present as part of the loan officer team?")
    add_bullet(doc, "Which licensed LOs act as LO of record for LO Agent conversations?")
    add_bullet(doc, "What does compliance allow the LO Agent to say about pre-qualification amounts?")
    add_bullet(doc, "Should Ivy (servicing) callers also be able to reach the LO Agent for refinance?")

    # Footer
    doc.add_paragraph()
    para = doc.add_paragraph()
    run = para.add_run("Document generated: November 2026 · HomeFirst AI v1.0")
    run.font.size = Pt(9)
    run.font.color.rgb = RGBColor(0x80, 0x80, 0x80)
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Save
    doc.save(output_path)
    print(f"Merged document saved to: {output_path}")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    output_path = Path(__file__).parent.parent / "docs" / "HomeFirst_AI_Complete_Documentation_Merged.docx"

    print("=" * 60)
    print("Creating Merged Document")
    print("=" * 60)
    print()
    print("Combining:")
    print("  - Mac document structure (title page, sections, tables)")
    print("  - HomeFirst content (architecture, ADRs, ROI)")
    print()

    create_merged_document(output_path)

    print()
    print("=" * 60)
    print("Complete!")
    print("=" * 60)
