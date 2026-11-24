#!/usr/bin/env python3
"""Generate professional architecture diagrams for HomeFirst AI documentation."""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

# Professional color scheme (matching the reference image)
COLORS = {
    "header_blue": "#1e3a5f",  # Dark blue for headers
    "header_teal": "#0d7377",  # Teal for headers
    "header_green": "#14532d",  # Dark green for headers
    "bg_blue": "#e8f4fc",  # Light blue background
    "bg_teal": "#e6f7f7",  # Light teal background
    "bg_green": "#ecfdf5",  # Light green background
    "bg_yellow": "#fef9e7",  # Light yellow background
    "bg_orange": "#fff7ed",  # Light orange background
    "bg_gray": "#f8fafc",  # Very light gray
    "text_dark": "#1e293b",  # Dark text
    "text_gray": "#64748b",  # Gray text
    "border": "#cbd5e1",  # Border color
    "white": "#ffffff",
    "accent": "#0ea5e9",  # Accent blue
}


def create_header_box(
    ax, x, y, width, height, header, header_color, bg_color, content_lines=None, fontsize=9
):
    """Create a professional box with header and content."""
    # Main box background
    box = FancyBboxPatch(
        (x, y),
        width,
        height,
        boxstyle="round,pad=0.01,rounding_size=0.02",
        facecolor=bg_color,
        edgecolor=COLORS["border"],
        linewidth=1,
    )
    ax.add_patch(box)

    # Header bar
    header_height = 0.35
    header_box = FancyBboxPatch(
        (x, y + height - header_height),
        width,
        header_height,
        boxstyle="round,pad=0.01,rounding_size=0.02",
        facecolor=header_color,
        edgecolor="none",
    )
    ax.add_patch(header_box)

    # Cover bottom corners of header
    cover = Rectangle(
        (x, y + height - header_height), width, 0.1, facecolor=header_color, edgecolor="none"
    )
    ax.add_patch(cover)

    # Header text
    ax.text(
        x + 0.15,
        y + height - header_height / 2,
        header,
        ha="left",
        va="center",
        fontsize=fontsize + 1,
        fontweight="bold",
        color="white",
    )

    # Content lines
    if content_lines:
        line_height = 0.22
        start_y = y + height - header_height - 0.25
        for i, line in enumerate(content_lines):
            ax.text(
                x + 0.15,
                start_y - i * line_height,
                f"• {line}",
                ha="left",
                va="top",
                fontsize=fontsize,
                color=COLORS["text_dark"],
                wrap=True,
            )


def create_simple_box(
    ax, x, y, width, height, text, bg_color, text_color=None, fontsize=9, bold=False
):
    """Create a simple box with text."""
    box = FancyBboxPatch(
        (x, y),
        width,
        height,
        boxstyle="round,pad=0.01,rounding_size=0.02",
        facecolor=bg_color,
        edgecolor=COLORS["border"],
        linewidth=1,
    )
    ax.add_patch(box)

    ax.text(
        x + width / 2,
        y + height / 2,
        text,
        ha="center",
        va="center",
        fontsize=fontsize,
        fontweight="bold" if bold else "normal",
        color=text_color or COLORS["text_dark"],
    )


def diagram_1_system_architecture():
    """Phase 1 architecture diagram matching reference style."""
    fig, ax = plt.subplots(1, 1, figsize=(14, 8))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 8)
    ax.axis("off")

    # Title
    ax.text(
        7,
        7.7,
        "Phase 1 Architecture: Multi-Agent Voice System",
        ha="center",
        va="center",
        fontsize=14,
        fontweight="bold",
        color=COLORS["text_dark"],
    )

    # Column headers
    ax.text(
        2.3,
        7.3,
        "CALLER",
        ha="center",
        va="center",
        fontsize=10,
        fontweight="bold",
        color=COLORS["text_gray"],
    )
    ax.text(
        7,
        7.3,
        "VOICE SERVICE - FASTAPI + GOOGLE ADK",
        ha="center",
        va="center",
        fontsize=10,
        fontweight="bold",
        color=COLORS["text_gray"],
    )
    ax.text(
        12,
        7.3,
        "MODEL & DATA",
        ha="center",
        va="center",
        fontsize=10,
        fontweight="bold",
        color=COLORS["text_gray"],
    )

    # CALLER column
    create_header_box(
        ax,
        0.3,
        5.4,
        4,
        1.7,
        "Web Voice Client",
        COLORS["header_blue"],
        COLORS["bg_blue"],
        [
            "Mic: 16 kHz in, voice 24 kHz out",
            "Captions: live transcription",
            "Barge-in: instant interrupt",
        ],
    )

    create_header_box(
        ax,
        0.3,
        3.4,
        4,
        1.8,
        "Call State Panel",
        COLORS["header_blue"],
        COLORS["bg_blue"],
        [
            "Identity: verification status",
            "Agent: current persona indicator",
            "Session: tokens and cost meter",
            "Actions: tool calls displayed",
        ],
    )

    # VOICE SERVICE column
    create_header_box(
        ax,
        4.5,
        5.9,
        2.4,
        1.2,
        "Sam - Triage",
        COLORS["header_teal"],
        COLORS["bg_teal"],
        ["Greeting and routing", "Qualifying questions"],
    )

    create_header_box(
        ax,
        7,
        5.9,
        2.5,
        1.2,
        "Mac - Origination",
        COLORS["header_teal"],
        COLORS["bg_teal"],
        ["HELOC, rates, equity", "State rules, leads"],
    )

    create_header_box(
        ax,
        4.5,
        4.5,
        2.4,
        1.2,
        "Ivy - Servicing",
        COLORS["header_teal"],
        COLORS["bg_teal"],
        ["Balance, payments", "Autopay, verification"],
    )

    create_header_box(
        ax,
        7,
        4.5,
        2.5,
        1.2,
        "Policy Door",
        COLORS["header_teal"],
        COLORS["bg_yellow"],
        ["Before/after every tool", "Verification, validation"],
    )

    create_header_box(
        ax,
        4.5,
        2.9,
        5,
        1.4,
        "Tool Orchestration Layer",
        COLORS["header_teal"],
        COLORS["bg_teal"],
        [
            "29 tools: 14 origination + 15 servicing",
            "Facts from tools only - AI never invents data",
            "Fail-closed: unknown states route to human",
        ],
    )

    # MODEL & DATA column
    create_header_box(
        ax,
        10,
        5.9,
        3.7,
        1.2,
        "Gemini Live API",
        COLORS["header_green"],
        COLORS["bg_green"],
        ["Native audio streaming", "Function calling, TTS"],
    )

    create_header_box(
        ax,
        10,
        4.5,
        3.7,
        1.2,
        "Mortgage Data",
        COLORS["header_green"],
        COLORS["bg_green"],
        ["Products, rate sheets", "State rules (TX, CA, FL)"],
    )

    create_header_box(
        ax,
        10,
        2.9,
        3.7,
        1.4,
        "Servicing Database",
        COLORS["header_green"],
        COLORS["bg_green"],
        ["Customer accounts", "Loan balances, payment history", "Payment methods, autopay"],
    )

    # Connecting lines (arrows)
    # Caller to Voice Service
    ax.annotate(
        "",
        xy=(4.5, 5.5),
        xytext=(4.3, 5.5),
        arrowprops={"arrowstyle": "->", "color": COLORS["text_gray"], "lw": 1.5},
    )

    # Voice Service to Model
    ax.annotate(
        "",
        xy=(10, 5.5),
        xytext=(9.5, 5.5),
        arrowprops={"arrowstyle": "<->", "color": COLORS["text_gray"], "lw": 1.5},
    )

    # Key features box at bottom
    key_box = FancyBboxPatch(
        (0.3, 0.3),
        13.4,
        2.3,
        boxstyle="round,pad=0.01,rounding_size=0.03",
        facecolor=COLORS["bg_gray"],
        edgecolor=COLORS["border"],
        linewidth=1,
    )
    ax.add_patch(key_box)

    ax.text(
        7,
        2.4,
        "KEY DESIGN PRINCIPLES",
        ha="center",
        va="center",
        fontsize=11,
        fontweight="bold",
        color=COLORS["header_blue"],
    )

    principles = [
        ("Rules in Code", "State laws enforced by tools, not prompts"),
        ("Fail Closed", "Unknown inputs route to human"),
        ("Persona Switching", "Seamless transfers, zero audio gaps"),
        ("Policy Door", "Every tool call validated"),
        ("Two-Level Auth", "Basic view, Strong for transactions"),
    ]

    for i, (title, desc) in enumerate(principles):
        x = 1 + (i % 5) * 2.6
        y = 1.5 if i < 5 else 0.8
        ax.text(
            x,
            y,
            f"{title}:",
            ha="left",
            va="center",
            fontsize=8,
            fontweight="bold",
            color=COLORS["header_teal"],
        )
        ax.text(x, y - 0.35, desc, ha="left", va="center", fontsize=7, color=COLORS["text_gray"])

    plt.tight_layout()
    plt.savefig(
        "images/01_system_architecture.png",
        dpi=200,
        bbox_inches="tight",
        facecolor="white",
        edgecolor="none",
    )
    plt.close()
    print("Created: 01_system_architecture.png")


def diagram_2_multi_agent_flow():
    """Multi-agent routing flow."""
    fig, ax = plt.subplots(1, 1, figsize=(12, 8))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 8)
    ax.axis("off")

    # Title
    ax.text(
        6,
        7.7,
        "Multi-Agent Routing Flow",
        ha="center",
        va="center",
        fontsize=14,
        fontweight="bold",
        color=COLORS["text_dark"],
    )

    # Caller
    create_simple_box(
        ax, 4.5, 6.8, 3, 0.6, "Caller Connects", COLORS["bg_gray"], fontsize=10, bold=True
    )

    # Arrow down
    ax.annotate(
        "",
        xy=(6, 6.3),
        xytext=(6, 6.8),
        arrowprops={"arrowstyle": "->", "color": COLORS["text_gray"], "lw": 2},
    )

    # SAM Triage
    create_header_box(
        ax,
        3.5,
        5.0,
        5,
        1.2,
        "SAM - Triage Agent",
        "#059669",
        "#d1fae5",
        [
            '"Hi, this is Sam with HomeFirst. How can I help?"',
            "Routes to specialist based on intent",
        ],
    )

    # Branch arrows
    ax.annotate(
        "",
        xy=(3, 4.3),
        xytext=(4.5, 5.0),
        arrowprops={"arrowstyle": "->", "color": COLORS["text_gray"], "lw": 1.5},
    )
    ax.annotate(
        "",
        xy=(9, 4.3),
        xytext=(7.5, 5.0),
        arrowprops={"arrowstyle": "->", "color": COLORS["text_gray"], "lw": 1.5},
    )

    # Intent labels
    ax.text(
        3.2,
        4.6,
        '"New loan"',
        ha="center",
        va="center",
        fontsize=8,
        color=COLORS["text_gray"],
        style="italic",
    )
    ax.text(
        8.8,
        4.6,
        '"My account"',
        ha="center",
        va="center",
        fontsize=8,
        color=COLORS["text_gray"],
        style="italic",
    )

    # MAC Agent
    create_header_box(
        ax,
        0.5,
        2.3,
        5,
        1.8,
        "MAC - Origination Specialist",
        COLORS["header_teal"],
        COLORS["bg_teal"],
        [
            "HELOC eligibility with state rules",
            "Rate estimates with disclaimers",
            "Equity calculations",
            "Lead capture and LO transfer",
        ],
    )

    # IVY Agent
    create_header_box(
        ax,
        6.5,
        2.3,
        5,
        1.8,
        "IVY - Servicing Specialist",
        "#7c3aed",
        "#ede9fe",
        [
            "Two-level identity verification",
            "Balance and payment history",
            "One-time payments with authorization",
            "Autopay setup and management",
        ],
    )

    # Key insight
    key_box = FancyBboxPatch(
        (1.5, 0.4),
        9,
        1.5,
        boxstyle="round,pad=0.01,rounding_size=0.03",
        facecolor="#fef3c7",
        edgecolor="#f59e0b",
        linewidth=2,
    )
    ax.add_patch(key_box)

    ax.text(
        6,
        1.6,
        "KEY: Persona Switching (not Agent-to-Agent)",
        ha="center",
        va="center",
        fontsize=11,
        fontweight="bold",
        color="#92400e",
    )
    ax.text(
        6,
        1.1,
        "Single ADK agent with dynamic instructions = zero audio gaps during transfers",
        ha="center",
        va="center",
        fontsize=9,
        color="#92400e",
    )
    ax.text(
        6,
        0.7,
        "Conversation context preserved across all personas",
        ha="center",
        va="center",
        fontsize=9,
        color="#92400e",
    )

    plt.tight_layout()
    plt.savefig(
        "images/02_multi_agent_flow.png",
        dpi=200,
        bbox_inches="tight",
        facecolor="white",
        edgecolor="none",
    )
    plt.close()
    print("Created: 02_multi_agent_flow.png")


def diagram_3_policy_door():
    """Policy door flow."""
    fig, ax = plt.subplots(1, 1, figsize=(10, 10))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")

    # Title
    ax.text(
        5,
        9.7,
        "Policy Door - Tool Call Lifecycle",
        ha="center",
        va="center",
        fontsize=14,
        fontweight="bold",
        color=COLORS["text_dark"],
    )

    # Agent requests
    create_simple_box(
        ax, 2.5, 8.8, 5, 0.6, "Agent Requests Tool Call", COLORS["bg_gray"], fontsize=10, bold=True
    )

    ax.annotate(
        "",
        xy=(5, 8.3),
        xytext=(5, 8.8),
        arrowprops={"arrowstyle": "->", "color": COLORS["text_gray"], "lw": 2},
    )

    # BEFORE Callback
    create_header_box(
        ax,
        1,
        5.8,
        8,
        2.3,
        "BEFORE CALLBACK (policy.py)",
        "#c2410c",
        "#fff7ed",
        [
            "Check agent has tool access (Sam can't use payments)",
            "Validate inputs (state codes, credit scores)",
            "Check verification level (basic vs strong)",
            "Check lockout status (3 failures = locked)",
            "Reject if any check fails → Block with message",
        ],
    )

    ax.annotate(
        "",
        xy=(5, 5.3),
        xytext=(5, 5.8),
        arrowprops={"arrowstyle": "->", "color": COLORS["text_gray"], "lw": 2},
    )
    ax.text(
        5.3, 5.55, "ALLOW", ha="left", va="center", fontsize=8, color="#059669", fontweight="bold"
    )

    # Execute Tool
    create_simple_box(
        ax, 2.5, 4.4, 5, 0.7, "Execute Tool Function", "#d1fae5", fontsize=10, bold=True
    )

    ax.annotate(
        "",
        xy=(5, 3.9),
        xytext=(5, 4.4),
        arrowprops={"arrowstyle": "->", "color": COLORS["text_gray"], "lw": 2},
    )

    # AFTER Callback
    create_header_box(
        ax,
        1,
        1.5,
        8,
        2.2,
        "AFTER CALLBACK (policy.py)",
        "#059669",
        "#d1fae5",
        [
            "Add disclaimers to rate estimates",
            "Suggest loan officer transfer for complex cases",
            "Redact PII in logs (names, phones, SSN)",
            "Log action for audit trail",
        ],
    )

    ax.annotate(
        "",
        xy=(5, 1.0),
        xytext=(5, 1.5),
        arrowprops={"arrowstyle": "->", "color": COLORS["text_gray"], "lw": 2},
    )

    # Return result
    create_simple_box(
        ax, 2.5, 0.3, 5, 0.6, "Return Result to Agent", COLORS["bg_gray"], fontsize=10, bold=True
    )

    plt.tight_layout()
    plt.savefig(
        "images/03_policy_door.png",
        dpi=200,
        bbox_inches="tight",
        facecolor="white",
        edgecolor="none",
    )
    plt.close()
    print("Created: 03_policy_door.png")


def diagram_4_gcp_deployment():
    """GCP deployment architecture."""
    fig, ax = plt.subplots(1, 1, figsize=(14, 9))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 9)
    ax.axis("off")

    # Title
    ax.text(
        7,
        8.7,
        "GCP Production Deployment",
        ha="center",
        va="center",
        fontsize=14,
        fontweight="bold",
        color=COLORS["text_dark"],
    )

    # GCP outer box
    gcp_box = FancyBboxPatch(
        (0.3, 0.3),
        13.4,
        8.0,
        boxstyle="round,pad=0.02,rounding_size=0.05",
        facecolor="#eff6ff",
        edgecolor="#3b82f6",
        linewidth=2,
    )
    ax.add_patch(gcp_box)
    ax.text(
        1,
        8.1,
        "GOOGLE CLOUD PLATFORM",
        ha="left",
        va="center",
        fontsize=11,
        fontweight="bold",
        color="#1d4ed8",
    )

    # Load Balancer
    create_header_box(
        ax,
        1,
        6.6,
        12,
        1.2,
        "Global Load Balancer + Cloud CDN",
        "#1d4ed8",
        "#dbeafe",
        [
            "SSL termination with managed certificates",
            "WebSocket support for voice streaming • DDoS protection",
        ],
    )

    ax.annotate(
        "",
        xy=(7, 6.1),
        xytext=(7, 6.6),
        arrowprops={"arrowstyle": "->", "color": COLORS["text_gray"], "lw": 2},
    )

    # Cloud Run
    run_box = FancyBboxPatch(
        (1, 4.0),
        12,
        2.0,
        boxstyle="round,pad=0.01,rounding_size=0.03",
        facecolor="white",
        edgecolor="#059669",
        linewidth=2,
    )
    ax.add_patch(run_box)
    ax.text(
        7,
        5.8,
        "CLOUD RUN - Serverless Containers (Auto-scaling 0-100)",
        ha="center",
        va="center",
        fontsize=10,
        fontweight="bold",
        color="#059669",
    )

    # Instances
    for i, label in enumerate(["Instance 1", "Instance 2", "Instance N"]):
        x = 2.5 + i * 3.5
        create_simple_box(
            ax,
            x,
            4.3,
            2.8,
            1.2,
            f"Voice Service\n{label}\n• FastAPI • ADK • WebSocket",
            COLORS["bg_teal"],
            fontsize=8,
        )

    ax.annotate(
        "",
        xy=(7, 3.5),
        xytext=(7, 4.0),
        arrowprops={"arrowstyle": "->", "color": COLORS["text_gray"], "lw": 2},
    )

    # Data layer
    create_header_box(
        ax,
        1,
        1.8,
        3.5,
        1.5,
        "Cloud SQL (PostgreSQL)",
        "#1d4ed8",
        "#dbeafe",
        ["Loans, customers", "Payments, leads"],
    )

    create_header_box(
        ax, 5, 1.8, 3.5, 1.5, "Secret Manager", "#dc2626", "#fee2e2", ["API keys", "DB credentials"]
    )

    create_header_box(
        ax,
        9,
        1.8,
        3.8,
        1.5,
        "Cloud Storage",
        "#059669",
        "#d1fae5",
        ["Rate sheets", "Regulation docs"],
    )

    # Gemini API
    create_header_box(
        ax,
        3.5,
        0.5,
        7,
        1.1,
        "Vertex AI - Gemini Live API",
        "#7c3aed",
        "#ede9fe",
        ["Bidirectional audio • Speech recognition • Function calling • TTS"],
    )

    plt.tight_layout()
    plt.savefig(
        "images/04_gcp_deployment.png",
        dpi=200,
        bbox_inches="tight",
        facecolor="white",
        edgecolor="none",
    )
    plt.close()
    print("Created: 04_gcp_deployment.png")


def diagram_5_payment_flow():
    """Three-step payment authorization."""
    fig, ax = plt.subplots(1, 1, figsize=(12, 9))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 9)
    ax.axis("off")

    # Title
    ax.text(
        6,
        8.7,
        "Three-Step Payment Authorization Flow",
        ha="center",
        va="center",
        fontsize=14,
        fontweight="bold",
        color=COLORS["text_dark"],
    )

    # Step 1
    step1_box = FancyBboxPatch(
        (0.5, 5.8),
        11,
        2.5,
        boxstyle="round,pad=0.01,rounding_size=0.03",
        facecolor=COLORS["bg_teal"],
        edgecolor=COLORS["header_teal"],
        linewidth=2,
    )
    ax.add_patch(step1_box)

    ax.text(
        1.3,
        8.0,
        "1",
        ha="center",
        va="center",
        fontsize=16,
        fontweight="bold",
        color="white",
        bbox={"boxstyle": "circle", "facecolor": COLORS["header_teal"]},
    )
    ax.text(
        2.3,
        8.0,
        "PREPARE",
        ha="left",
        va="center",
        fontsize=12,
        fontweight="bold",
        color=COLORS["header_teal"],
    )

    ax.text(
        1,
        7.4,
        'Caller: "I want to pay $1,750"',
        ha="left",
        va="center",
        fontsize=10,
        color=COLORS["text_dark"],
    )
    ax.text(
        1,
        6.9,
        'Tool: prepare_payment(amount=1750, method="Chase ****5678")',
        ha="left",
        va="center",
        fontsize=9,
        color=COLORS["text_gray"],
        family="monospace",
    )
    ax.text(
        1,
        6.3,
        "Result: Payment staged, pending_authorization set",
        ha="left",
        va="center",
        fontsize=9,
        color=COLORS["text_gray"],
    )

    ax.annotate(
        "",
        xy=(6, 5.3),
        xytext=(6, 5.8),
        arrowprops={"arrowstyle": "->", "color": COLORS["text_gray"], "lw": 2},
    )

    # Step 2
    step2_box = FancyBboxPatch(
        (0.5, 3.0),
        11,
        2.1,
        boxstyle="round,pad=0.01,rounding_size=0.03",
        facecolor="#fff7ed",
        edgecolor="#c2410c",
        linewidth=2,
    )
    ax.add_patch(step2_box)

    ax.text(
        1.3,
        4.8,
        "2",
        ha="center",
        va="center",
        fontsize=16,
        fontweight="bold",
        color="white",
        bbox={"boxstyle": "circle", "facecolor": "#c2410c"},
    )
    ax.text(
        2.3,
        4.8,
        "READ-BACK",
        ha="left",
        va="center",
        fontsize=12,
        fontweight="bold",
        color="#c2410c",
    )

    ax.text(
        1,
        4.2,
        'Ivy: "So I have a payment of $1,750 from your Chase account ending in 5678,',
        ha="left",
        va="center",
        fontsize=10,
        color=COLORS["text_dark"],
    )
    ax.text(
        1,
        3.75,
        '       scheduled for today. Do I have your authorization to proceed?"',
        ha="left",
        va="center",
        fontsize=10,
        color=COLORS["text_dark"],
        fontweight="bold",
    )

    ax.annotate(
        "",
        xy=(6, 2.5),
        xytext=(6, 3.0),
        arrowprops={"arrowstyle": "->", "color": COLORS["text_gray"], "lw": 2},
    )

    # Step 3
    step3_box = FancyBboxPatch(
        (0.5, 0.5),
        11,
        1.8,
        boxstyle="round,pad=0.01,rounding_size=0.03",
        facecolor="#d1fae5",
        edgecolor="#059669",
        linewidth=2,
    )
    ax.add_patch(step3_box)

    ax.text(
        1.3,
        2.0,
        "3",
        ha="center",
        va="center",
        fontsize=16,
        fontweight="bold",
        color="white",
        bbox={"boxstyle": "circle", "facecolor": "#059669"},
    )
    ax.text(
        2.3, 2.0, "CONFIRM", ha="left", va="center", fontsize=12, fontweight="bold", color="#059669"
    )

    ax.text(
        1,
        1.5,
        'Caller: "Yes"  →  confirm_payment(authorized=True)',
        ha="left",
        va="center",
        fontsize=10,
        color=COLORS["text_dark"],
    )
    ax.text(
        1,
        1.0,
        'Ivy: "Payment confirmed. Your confirmation number is PMT-ABC123."',
        ha="left",
        va="center",
        fontsize=10,
        color="#059669",
        fontweight="bold",
    )

    plt.tight_layout()
    plt.savefig(
        "images/05_payment_flow.png",
        dpi=200,
        bbox_inches="tight",
        facecolor="white",
        edgecolor="none",
    )
    plt.close()
    print("Created: 05_payment_flow.png")


def diagram_6_security():
    """Security and verification."""
    fig, ax = plt.subplots(1, 1, figsize=(12, 8))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 8)
    ax.axis("off")

    # Title
    ax.text(
        6,
        7.7,
        "Two-Level Identity Verification & Security",
        ha="center",
        va="center",
        fontsize=14,
        fontweight="bold",
        color=COLORS["text_dark"],
    )

    # Basic Verification
    create_header_box(
        ax,
        0.3,
        4.5,
        5.5,
        2.8,
        "BASIC VERIFICATION",
        COLORS["header_teal"],
        COLORS["bg_teal"],
        [
            "Required for: Balance, payment history, account info",
            "",
            "Verification method:",
            "  • Full name",
            "  • Last 4 digits of phone on file",
        ],
    )

    # Strong Verification
    create_header_box(
        ax,
        6.2,
        4.5,
        5.5,
        2.8,
        "STRONG VERIFICATION",
        "#c2410c",
        "#fff7ed",
        [
            "Required for: Payments, autopay, date changes",
            "",
            "Additional verification:",
            "  • Date of birth",
            "  • Approximate loan balance (within $5,000)",
        ],
    )

    # Arrow
    ax.annotate(
        "",
        xy=(6.0, 5.9),
        xytext=(5.6, 5.9),
        arrowprops={"arrowstyle": "->", "color": COLORS["text_gray"], "lw": 2},
    )
    ax.text(5.8, 6.3, "Upgrade", ha="center", va="center", fontsize=8, color=COLORS["text_gray"])

    # Lockout flow
    lockout_box = FancyBboxPatch(
        (1.5, 0.5),
        9,
        3.6,
        boxstyle="round,pad=0.01,rounding_size=0.03",
        facecolor="#fee2e2",
        edgecolor="#dc2626",
        linewidth=2,
    )
    ax.add_patch(lockout_box)

    ax.text(
        6,
        3.85,
        "VERIFICATION LOCKOUT",
        ha="center",
        va="center",
        fontsize=12,
        fontweight="bold",
        color="#dc2626",
    )

    ax.text(
        2,
        3.3,
        '• Attempt 1: Wrong  →  "That doesn\'t match. Try again."',
        ha="left",
        va="center",
        fontsize=9,
        color=COLORS["text_dark"],
    )
    ax.text(
        2,
        2.8,
        '• Attempt 2: Wrong  →  "Still not matching. One more try."',
        ha="left",
        va="center",
        fontsize=9,
        color=COLORS["text_dark"],
    )
    ax.text(
        2,
        2.3,
        "• Attempt 3: Wrong  →  LOCKED",
        ha="left",
        va="center",
        fontsize=9,
        fontweight="bold",
        color="#dc2626",
    )

    ax.text(
        2,
        1.6,
        '→ "For your security, let me transfer you to a loan officer."',
        ha="left",
        va="center",
        fontsize=9,
        color="#dc2626",
        style="italic",
    )
    ax.text(
        2,
        1.1,
        "→ Lockout logged for security review",
        ha="left",
        va="center",
        fontsize=9,
        color="#dc2626",
        style="italic",
    )

    plt.tight_layout()
    plt.savefig(
        "images/06_security.png", dpi=200, bbox_inches="tight", facecolor="white", edgecolor="none"
    )
    plt.close()
    print("Created: 06_security.png")


def diagram_7_roi():
    """ROI and business impact."""
    fig, ax = plt.subplots(1, 1, figsize=(12, 8))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 8)
    ax.axis("off")

    # Title
    ax.text(
        6,
        7.7,
        "Business Impact & ROI",
        ha="center",
        va="center",
        fontsize=14,
        fontweight="bold",
        color=COLORS["text_dark"],
    )

    # Before
    create_header_box(
        ax,
        0.3,
        4.3,
        5.5,
        3.0,
        "BEFORE",
        "#dc2626",
        "#fee2e2",
        [
            "Cost per inquiry: $45",
            "After-hours capture: 0%",
            "Response time: 48 hours",
            "Lead qualification: 15%",
            "Missed opportunities",
        ],
    )

    # After
    create_header_box(
        ax,
        6.2,
        4.3,
        5.5,
        3.0,
        "AFTER",
        "#059669",
        "#d1fae5",
        [
            "Cost per inquiry: $5 (89% reduction)",
            "After-hours capture: 100%",
            "Response time: Instant (99% reduction)",
            "Lead qualification: 40% (167% increase)",
            "24/7 availability",
        ],
    )

    # Arrow
    ax.annotate(
        "",
        xy=(6.0, 5.8),
        xytext=(5.6, 5.8),
        arrowprops={"arrowstyle": "->", "color": COLORS["text_gray"], "lw": 3},
    )

    # ROI Summary
    roi_box = FancyBboxPatch(
        (0.3, 0.5),
        11.4,
        3.5,
        boxstyle="round,pad=0.01,rounding_size=0.03",
        facecolor="#eff6ff",
        edgecolor="#1d4ed8",
        linewidth=2,
    )
    ax.add_patch(roi_box)

    ax.text(
        6,
        3.75,
        "ANNUAL VALUE",
        ha="center",
        va="center",
        fontsize=12,
        fontweight="bold",
        color="#1d4ed8",
    )

    ax.text(
        1,
        3.1,
        "• Reduced call center staff (3 FTE):",
        ha="left",
        va="center",
        fontsize=10,
        color=COLORS["text_dark"],
    )
    ax.text(
        7, 3.1, "$180,000", ha="right", va="center", fontsize=10, fontweight="bold", color="#1d4ed8"
    )

    ax.text(
        1,
        2.6,
        "• After-hours lead capture:",
        ha="left",
        va="center",
        fontsize=10,
        color=COLORS["text_dark"],
    )
    ax.text(
        7, 2.6, "$240,000", ha="right", va="center", fontsize=10, fontweight="bold", color="#1d4ed8"
    )

    ax.text(
        1,
        2.1,
        "• Faster lead qualification:",
        ha="left",
        va="center",
        fontsize=10,
        color=COLORS["text_dark"],
    )
    ax.text(
        7, 2.1, "$120,000", ha="right", va="center", fontsize=10, fontweight="bold", color="#1d4ed8"
    )

    ax.plot([1, 7], [1.7, 1.7], color="#1d4ed8", linewidth=1)
    ax.text(
        1,
        1.3,
        "TOTAL ANNUAL SAVINGS:",
        ha="left",
        va="center",
        fontsize=11,
        fontweight="bold",
        color="#1d4ed8",
    )
    ax.text(
        7, 1.3, "$540,000", ha="right", va="center", fontsize=14, fontweight="bold", color="#059669"
    )

    # Key metrics sidebar
    ax.text(9, 3.1, "Payback:", ha="left", va="center", fontsize=9, color=COLORS["text_dark"])
    ax.text(
        11.3,
        3.1,
        "5 months",
        ha="right",
        va="center",
        fontsize=10,
        fontweight="bold",
        color="#1d4ed8",
    )

    ax.text(9, 2.5, "Year 1 ROI:", ha="left", va="center", fontsize=9, color=COLORS["text_dark"])
    ax.text(
        11.3, 2.5, "157%", ha="right", va="center", fontsize=10, fontweight="bold", color="#1d4ed8"
    )

    ax.text(9, 1.9, "5-Year NPV:", ha="left", va="center", fontsize=9, color=COLORS["text_dark"])
    ax.text(
        11.3, 1.9, "$1.8M", ha="right", va="center", fontsize=10, fontweight="bold", color="#1d4ed8"
    )

    plt.tight_layout()
    plt.savefig(
        "images/07_roi.png", dpi=200, bbox_inches="tight", facecolor="white", edgecolor="none"
    )
    plt.close()
    print("Created: 07_roi.png")


def main():
    """Generate all diagrams."""
    Path("images").mkdir(exist_ok=True)

    print("Generating professional architecture diagrams...")
    diagram_1_system_architecture()
    diagram_2_multi_agent_flow()
    diagram_3_policy_door()
    diagram_4_gcp_deployment()
    diagram_5_payment_flow()
    diagram_6_security()
    diagram_7_roi()
    print("\nAll diagrams generated successfully!")
    print(f"Output: {Path('images').absolute()}")


if __name__ == "__main__":
    main()
