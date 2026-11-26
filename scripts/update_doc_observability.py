"""Add Observability section to the HomeFirst AI Documentation."""

from docx import Document
from docx.shared import Pt
from docx.enum.style import WD_STYLE_TYPE
from copy import deepcopy


def add_observability_section():
    doc = Document('docs/HomeFirst_AI_Documentation.docx')

    # Find the paragraph just before "4. Policy Door Pattern" or "3. Multi-Agent"
    insert_before_idx = None
    for i, para in enumerate(doc.paragraphs):
        text = para.text.strip()
        if text.startswith('4. Policy Door') or text.startswith('3. Multi-Agent'):
            insert_before_idx = i
            print(f"Found insertion point before: {text[:40]}")
            break

    if insert_before_idx is None:
        # Fallback: find after Technical Architecture Details
        for i, para in enumerate(doc.paragraphs):
            if 'Technical Architecture Details' in para.text:
                insert_before_idx = i + 20  # Some paragraphs after
                break

    if insert_before_idx is None:
        print("Could not find insertion point!")
        return

    # Content to add
    observability_content = [
        ("2.2 Observability and Monitoring", "Heading 3"),
        ("The system includes comprehensive LLM observability using Langfuse, an open-source platform for monitoring AI applications.", "Normal"),
        ("", "Normal"),
        ("Trace Collection:", "Normal"),
        ("• OpenTelemetry Integration: ADK's native traces are exported to Langfuse via OTLP protocol", "Normal"),
        ("• Session Tracking: Each voice call creates a unique trace with session ID for end-to-end visibility", "Normal"),
        ("• Tool Call Logging: All policy door validations and tool executions are recorded with inputs/outputs", "Normal"),
        ("• Token Usage: Input/output tokens tracked by modality (audio vs text) for cost analysis", "Normal"),
        ("", "Normal"),
        ("Metrics Captured:", "Normal"),
        ("• Cost per call based on Gemini API pricing (audio input $0.70/1M, audio output $2.10/1M tokens)", "Normal"),
        ("• Latency measurements for voice response times", "Normal"),
        ("• Agent handoff patterns and frequencies between Sam, Mac, and Ivy", "Normal"),
        ("• Verification success/failure rates for identity checks", "Normal"),
        ("• Tool call durations and error rates for performance monitoring", "Normal"),
        ("", "Normal"),
        ("Privacy Controls:", "Normal"),
        ("• PII Redaction: Sensitive fields (name, phone, SSN, DOB) are automatically redacted before export", "Normal"),
        ("• Session-scoped: Traces are isolated per call with no cross-session data leakage", "Normal"),
        ("• Configurable: Observability can be disabled via OTEL_SDK_DISABLED=true environment variable", "Normal"),
        ("", "Normal"),
        ("Dashboard Access:", "Normal"),
        ("• Langfuse Cloud dashboard at https://us.cloud.langfuse.com (or self-hosted option available)", "Normal"),
        ("• Real-time trace viewing during active calls for debugging", "Normal"),
        ("• Historical analysis for quality improvement and compliance auditing", "Normal"),
        ("", "Normal"),
    ]

    # Get the target paragraph's XML element
    target_para = doc.paragraphs[insert_before_idx]
    target_element = target_para._p
    parent = target_element.getparent()

    # Find the index of target in parent
    target_idx = list(parent).index(target_element)

    # Insert new paragraphs before the target
    for text, style_name in reversed(observability_content):
        # Create new paragraph by adding to document then moving
        new_para = doc.add_paragraph(text)

        # Try to set style
        try:
            if style_name == "Heading 3":
                new_para.style = 'Heading 3'
            else:
                new_para.style = 'Normal'
        except:
            pass

        # Move the new paragraph's element to the correct position
        new_element = new_para._p
        parent.remove(new_element)
        parent.insert(target_idx, new_element)

    # Save the document
    doc.save('docs/HomeFirst_AI_Documentation.docx')
    print("✓ Observability section added to HomeFirst_AI_Documentation.docx")
    print(f"  Inserted before paragraph {insert_before_idx}")


if __name__ == "__main__":
    add_observability_section()
