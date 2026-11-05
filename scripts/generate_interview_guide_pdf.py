#!/usr/bin/env python3
"""Publication-Grade PDF Generator for AI Engineer Interview Study Guide.

Compiles the InsurTech AI Microservice technical documentation, architecture,
model management, engineering trade-offs, and 5 STAR interview questions into
a professional PDF study guide at the workspace root.
"""
import os
import sys
import re
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    KeepTogether
)
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ----------------------------------------------------------------------
# Font Registration (Amharic Ge'ez TrueType Font)
# ----------------------------------------------------------------------
ETHIOPIC_FONT_REGULAR = "/usr/share/fonts/truetype/noto/NotoSansEthiopic-Regular.ttf"
ETHIOPIC_FONT_BOLD = "/usr/share/fonts/truetype/noto/NotoSansEthiopic-Bold.ttf"

HAS_ETHIOPIC = False
if os.path.exists(ETHIOPIC_FONT_REGULAR):
    pdfmetrics.registerFont(TTFont("NotoEthiopic", ETHIOPIC_FONT_REGULAR))
    if os.path.exists(ETHIOPIC_FONT_BOLD):
        pdfmetrics.registerFont(TTFont("NotoEthiopic-Bold", ETHIOPIC_FONT_BOLD))
    else:
        pdfmetrics.registerFont(TTFont("NotoEthiopic-Bold", ETHIOPIC_FONT_REGULAR))
    HAS_ETHIOPIC = True

FONT_BODY = "Helvetica"
FONT_BOLD = "Helvetica-Bold"

def wrap_amharic(text: str) -> str:
    """Wrap contiguous Ethiopic characters in <font name='NotoEthiopic'> tags."""
    if not HAS_ETHIOPIC or not text:
        return text
    return re.sub(
        r'([\u1200-\u137F]+(?:[\s፡፣።፤፥፦፧፨]+[\u1200-\u137F]+)*)',
        r'<font name="NotoEthiopic">\1</font>',
        text
    )

# ----------------------------------------------------------------------
# Two-Pass Numbered Canvas for Running Headers & Footers
# ----------------------------------------------------------------------
class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, total_pages):
        self.saveState()
        if self._pageNumber > 1:
            # Header
            self.setFont(FONT_BODY, 8)
            self.setFillColor(colors.HexColor("#64748B"))
            self.drawString(54, 792 - 34, "InsurTech AI Microservice — Senior AI Engineer Interview Prep Guide")
            self.drawRightString(612 - 54, 792 - 34, "Confidential Study Notes")
            
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.6)
            self.line(54, 792 - 38, 612 - 54, 792 - 38)

            # Footer
            self.line(54, 44, 612 - 54, 44)
            self.drawString(54, 30, "Ethiopian InsurTech Platform • Technical Architecture & System Deep-Dive")
            page_text = f"Page {self._pageNumber} of {total_pages}"
            self.drawRightString(612 - 54, 30, page_text)

        self.restoreState()


# ----------------------------------------------------------------------
# PDF Builder Function
# ----------------------------------------------------------------------
def generate_pdf(output_path: str):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=48,
        bottomMargin=48
    )

    styles = getSampleStyleSheet()

    # Custom Palette
    PRIMARY = colors.HexColor("#0F172A")    # Deep slate navy
    ACCENT = colors.HexColor("#0D9488")     # Emerald teal
    MUTED = colors.HexColor("#475569")      # Medium slate
    CARD_BG = colors.HexColor("#F8FAFC")    # Slate 50
    BORDER = colors.HexColor("#E2E8F0")     # Slate 200
    CODE_BG = colors.HexColor("#1E293B")    # Dark slate code background

    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName=FONT_BOLD,
        fontSize=21,
        leading=25,
        textColor=PRIMARY,
        spaceAfter=4
    )

    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName=FONT_BODY,
        fontSize=11,
        leading=15,
        textColor=ACCENT,
        spaceAfter=12
    )

    meta_style = ParagraphStyle(
        "DocMeta",
        parent=styles["Normal"],
        fontName=FONT_BODY,
        fontSize=8.5,
        leading=12.5,
        textColor=MUTED
    )

    h1_style = ParagraphStyle(
        "Heading1_Custom",
        parent=styles["Normal"],
        fontName=FONT_BOLD,
        fontSize=13.5,
        leading=17,
        textColor=PRIMARY,
        spaceBefore=10,
        spaceAfter=6,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        "Heading2_Custom",
        parent=styles["Normal"],
        fontName=FONT_BOLD,
        fontSize=10.5,
        leading=14.5,
        textColor=ACCENT,
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        "Body_Custom",
        parent=styles["Normal"],
        fontName=FONT_BODY,
        fontSize=8.5,
        leading=13,
        textColor=PRIMARY,
        spaceAfter=5
    )

    bullet_style = ParagraphStyle(
        "Bullet_Custom",
        parent=styles["Normal"],
        fontName=FONT_BODY,
        fontSize=8.5,
        leading=12.5,
        textColor=PRIMARY,
        leftIndent=12,
        firstLineIndent=-8,
        spaceAfter=3
    )

    code_style = ParagraphStyle(
        "Code_Custom",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=7,
        leading=9.2,
        textColor=colors.HexColor("#F1F5F9")
    )

    callout_style = ParagraphStyle(
        "Callout_Custom",
        parent=styles["Normal"],
        fontName=FONT_BODY,
        fontSize=8,
        leading=12,
        textColor=PRIMARY
    )

    q_title_style = ParagraphStyle(
        "QTitle_Custom",
        parent=styles["Normal"],
        fontName=FONT_BOLD,
        fontSize=9.5,
        leading=13.5,
        textColor=PRIMARY
    )

    story = []

    def add_p(text: str, style=body_style):
        story.append(Paragraph(wrap_amharic(text), style))

    def add_bullet(text: str):
        story.append(Paragraph(wrap_amharic(f"• {text}"), bullet_style))

    def add_callout(title: str, text: str, border_color=ACCENT, bg_color=CARD_BG):
        content = [
            Paragraph(f"<b><font color='{border_color.hexval()}'>{title}</font></b>", callout_style),
            Spacer(1, 2),
            Paragraph(wrap_amharic(text), callout_style)
        ]
        t = Table([[content]], colWidths=[504])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), bg_color),
            ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
            ("LINEBEFORE", (0, 0), (0, -1), 3, border_color),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 9),
            ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ]))
        story.append(t)
        story.append(Spacer(1, 6))

    def add_code(code_str: str):
        safe_code = code_str.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br/>")
        safe_code = wrap_amharic(safe_code)
        p = Paragraph(safe_code, code_style)
        t = Table([[p]], colWidths=[504])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), CODE_BG),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#334155")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(t)
        story.append(Spacer(1, 6))

    # ==================================================================
    # PAGE 1: COVER & EXECUTIVE OVERVIEW
    # ==================================================================
    story.append(Paragraph("AI ENGINEER INTERVIEW PREPARATION GUIDE", title_style))
    story.append(Paragraph("System Architecture, Multilingual RAG, Guardrails & Masterclass Q&A", subtitle_style))
    
    meta_content = wrap_amharic(
        "<b>Target Role:</b> Senior AI Engineer / LLM Systems Engineer &nbsp;&nbsp;|&nbsp;&nbsp; "
        "<b>Focus Area:</b> InsurTech AI Microservice<br/>"
        "<b>Key Technologies:</b> Python 3.11, FastAPI, RAG, WebSockets, Whisper, Gemini 1.5, Ollama, pgvector<br/>"
        "<b>Language Capabilities:</b> Multilingual Amharic (አማርኛ) & English with Ge'ez Homophone Folding"
    )
    meta_table = Table([[Paragraph(meta_content, meta_style)]], colWidths=[504])
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), CARD_BG),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
        ("PADDING", (0, 0), (-1, -1), 7),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 10))

    story.append(Paragraph("Executive Overview & Talking Points", h1_style))
    add_p(
        "The <b>InsurTech AI Microservice</b> is an enterprise-grade intelligent assistant engineered for the Ethiopian insurance ecosystem. "
        "It solves critical technical challenges in low-resource multilingual NLP (Amharic/English), high-concurrency voice streaming, "
        "and stringent financial privacy compliance. When describing this project in an interview, frame it as a <b>resilient, production-hardened AI system</b> "
        "built around strict grounding, zero-hallucination contracts, and deterministic security boundaries."
    )

    add_callout(
        "Core Value Proposition for Your Interview",
        "Explain that this is NOT a naive wrapper around an external API. It is a full-stack, sovereign AI microservice featuring "
        "custom Ge'ez orthographic normalization, sub-150ms full-duplex voice barge-in, IDOR claim validation, and an automated continuous "
        "learning loop via an Admin Review Desk and Golden Knowledge Base."
    )

    story.append(Paragraph("High-Impact Production Highlights to Quote:", h2_style))
    add_bullet("<b>Deterministic Grounding:</b> Strict closed-world policy retrieval; model refuses to guess if documentation is missing.")
    add_bullet("<b>Low Latency Voice:</b> Full-duplex WebSocket audio streaming with ~380ms TTFB and <150ms barge-in interruption.")
    add_bullet("<b>Linguistic Precision:</b> Pre-compiled Ge'ez homophone table mapping O(N) dialect variants without neural overhead.")
    add_bullet("<b>Zero-Trust Security:</b> In-line PII redaction of Ethiopian phone numbers, TINs, and Kebele IDs before storage, plus JWT-bound IDOR checks on all claims.")
    add_bullet("<b>Continuous Flywheel:</b> Human-in-the-loop expert review desk promoting verified answers to a prioritized Golden Knowledge Base.")

    # ==================================================================
    # PAGE 2: ARCHITECTURE & DATA FLOW
    # ==================================================================
    story.append(PageBreak())
    story.append(Paragraph("1. System Architecture & End-to-End Data Flow", h1_style))
    add_p("Data moves through six strictly decoupled layers, ensuring defense-in-depth and predictable sub-second latency:")

    arch_diagram_text = (
        "+-----------------------------------------------------------------------------------------+\n"
        "| CLIENTS: Web (React)  |  Mobile (Flutter)  |  Full-Duplex Voice WebSocket               |\n"
        "+--------------------------------------------+--------------------------------------------+\n"
        "                                             |\n"
        "                      +----------------------+----------------------+\n"
        "                      | (Text Request)                              | (Voice 16kHz PCM Stream)\n"
        "                      v                                             v\n"
        "         +--------------------------+                  +--------------------------+\n"
        "         | INPUT NORMALIZATION      |                  | SPEECH-TO-TEXT (Whisper) |\n"
        "         | Ge'ez Homophone Folding  |                  | 16kHz Audio Buffer / VAD |\n"
        "         +------------+-------------+                  +------------+-------------+\n"
        "                      |                                             |\n"
        "                      +----------------------+----------------------+\n"
        "                                             |\n"
        "                                             v\n"
        "                      +---------------------------------------------+\n"
        "                      | SECURITY & GUARDRAILS                       |\n"
        "                      | - Injection Filter (Regex / Adversarial)    |\n"
        "                      | - Ethiopian PII Scrubbing (Phone, TIN, ID)  |\n"
        "                      +----------------------+----------------------+\n"
        "                                             |\n"
        "                      +----------------------+----------------------+\n"
        "                      | (Claim Inquiry: CLM-xxxx)                   | (Policy Inquiry)\n"
        "                      v                                             v\n"
        "         +--------------------------+                  +--------------------------+\n"
        "         | CLAIM STATUS TOOL (IDOR) |                  | RAG VECTOR RETRIEVAL     |\n"
        "         | Caller JWT sub Ownership |                  | Cosine Top-3 Chunks      |\n"
        "         +------------+-------------+                  +------------+-------------+\n"
        "                      |                                             |\n"
        "                      +----------------------+----------------------+\n"
        "                                             |\n"
        "                                             v\n"
        "                      +---------------------------------------------+\n"
        "                      | UNIFIED LLM ROUTER (Gemini / OpenAI / Mock) |\n"
        "                      | Bounded Sliding Memory (6 turns / 30m TTL)  |\n"
        "                      +----------------------+----------------------+\n"
        "                                             |\n"
        "                                             v\n"
        "                      +---------------------------------------------+\n"
        "                      | COMPLIANCE, CITATIONS & DISCLAIMERS         |\n"
        "                      | Mandatory Legal Disclaimer (Amharic/English)|\n"
        "                      +----------------------+----------------------+\n"
        "                                             |\n"
        "                      +----------------------+----------------------+\n"
        "                      | (Text Response)                             | (Voice Response)\n"
        "                      v                                             v\n"
        "         +--------------------------+                  +--------------------------+\n"
        "         | JSON Client Payload      |                  | SentenceAccumulator      |\n"
        "         | Citations + Feedback ID  |                  | Edge-TTS (<150ms BargeIn)|\n"
        "         +--------------------------+                  +--------------------------+"
    )
    add_code(arch_diagram_text)

    story.append(Paragraph("Detailed Layer Responsibilities:", h2_style))
    add_bullet("<b>FastAPI Entrypoint:</b> Exposes RESTful endpoints (/api/v1/chat/messages) and WebSocket stream (/ws/v1/voice/chat) with Prometheus telemetry.")
    add_bullet("<b>Ge'ez Normalizer:</b> Standardizes Ethiopic orthography via fast C-level table translation, mapping homophones into canonical forms before vector search.")
    add_bullet("<b>Adversarial Filter:</b> Blocks prompt injection attempts (DAN mode, instruction overrides) in Amharic and English without invoking external models.")
    add_bullet("<b>Claim Tool with IDOR Defense:</b> Inspects JWT claims (token.sub) ensuring callers query only their own claim files, logging alerts on probes.")
    add_bullet("<b>LLM Router:</b> Dispatches requests across Google Gemini, OpenAI, Groq, Ollama, and a deterministic offline mock for zero-downtime resiliency.")

    # ==================================================================
    # PAGE 3: MODEL & CONTEXT MANAGEMENT
    # ==================================================================
    story.append(PageBreak())
    story.append(Paragraph("2. Model & Context Window Management", h1_style))
    add_p(
        "Context management in a production insurance assistant must balance three competing requirements: <b>factual accuracy</b>, "
        "<b>conversational coherence</b>, and <b>bounded token expenditure</b>."
    )

    story.append(Paragraph("2.1 System Prompt Design & Grounding Contract", h2_style))
    add_p(
        "The system prompt enforces a strict <i>Closed-World Grounding Assumption</i>. The model is explicitly constrained to act as an "
        "informational guide rather than an autonomous decision-maker:"
    )

    prompt_snippet = (
        "Rules:\n"
        "1. Ground all answers exclusively in the provided policy context.\n"
        "2. Provide direct, concise answers highlighting the exact amount/figure first.\n"
        "3. Never hallucinate facts outside the provided documentation.\n"
        "4. Always cite the relevant policy document name and section.\n"
        "5. You do not possess the authority to approve claims or modify policies."
    )
    add_code(prompt_snippet)

    story.append(Paragraph("2.2 Sliding Memory Window & Inactivity TTL", h2_style))
    add_p(
        "In multi-turn conversations, naive chat history accumulation leads to quadratic token growth and attention dilution. "
        "The SessionMemoryManager mitigates this using two strict boundaries:"
    )
    add_bullet("<b>6-Turn Sliding Window (12 messages):</b> Keeps the latest 6 user/assistant exchanges. Older turns are pruned automatically, preserving recent context while keeping total prompt tokens well below 2,000.")
    add_bullet("<b>Rolling 30-Minute TTL:</b> Every message updates the session timestamp. Inactive sessions are evicted after 30 minutes, preventing orphaned session data from accumulating in memory.")
    add_bullet("<b>Context Stratification:</b> Conversational history is used only for coreference resolution (e.g., 'What about fire?'). Factual policy data is always retrieved fresh via vector search on each turn.")

    story.append(Paragraph("2.3 The Multilingual RAG Retrieval Pipeline", h2_style))
    add_p("Policy documents (PDFs/Tariffs) are processed through a deterministic ingestion and vector search pipeline:")
    add_bullet("<b>Semantic Chunking:</b> Text is split along paragraph and table boundaries into ~512 token chunks with 50-token (~10%) overlap to prevent boundary truncation of coverage limits.")
    add_bullet("<b>Subword Tri-Gram Embeddings:</b> Because Amharic words are built from triconsonantal roots with extensive prefixes/suffixes, the embedder pairs word-level hashing with character tri-grams (clean[j:j+3]). This preserves morphological roots across inflectional variations.")
    add_bullet("<b>Cosine Similarity Search:</b> Vectors are unit-normalized (L2), enabling sub-80ms cosine ranking via pure dot-product operations.")

    # ==================================================================
    # PAGE 4: ENGINEERING DECISIONS & TRADE-OFFS
    # ==================================================================
    story.append(PageBreak())
    story.append(Paragraph("3. Engineering Decisions & Technical Trade-offs", h1_style))
    add_p(
        "Interviewers look for engineers who understand <i>why</i> a particular architecture was chosen over popular alternatives. "
        "The table below summarizes our core engineering decisions:"
    )

    tradeoff_data = [
        [
            Paragraph("<b>Decision Area</b>", body_style),
            Paragraph("<b>Chosen Implementation</b>", body_style),
            Paragraph("<b>Alternative Rejected</b>", body_style),
            Paragraph("<b>Engineering Justification</b>", body_style)
        ],
        [
            Paragraph("<b>Amharic Normalization</b>", body_style),
            Paragraph("Fast C-level <font face='Courier'>str.maketrans</font> homophone table", body_style),
            Paragraph("Neural Lemmatizer (Stanza / spaCy)", body_style),
            Paragraph("Neural models add 80-200ms latency per turn. Table translation executes in &lt;0.1ms with 100% determinism.", body_style)
        ],
        [
            Paragraph("<b>Voice TTS Streaming</b>", body_style),
            Paragraph("SentenceAccumulator buffering by punctuation (። . ! ?)", body_style),
            Paragraph("Word-by-word streaming OR Full-response wait", body_style),
            Paragraph("Full-response wait introduces 2.8s lag. Word-by-word ruins speech prosody. Sentence chunking cuts TTFB to ~380ms.", body_style)
        ],
        [
            Paragraph("<b>Tool Execution & IDOR</b>", body_style),
            Paragraph("Deterministic Regex intent routing bound to JWT identity", body_style),
            Paragraph("Autonomous ReAct / Function Calling", body_style),
            Paragraph("LLM function calling adds 500ms+ inference lag and risks prompt injection. Regex ensures security checks happen in Python.", body_style)
        ],
        [
            Paragraph("<b>Vector Storage</b>", body_style),
            Paragraph("Dual: In-Memory Cosine Store + pgvector adapter", body_style),
            Paragraph("SaaS Vector Cloud (Pinecone)", body_style),
            Paragraph("Financial regulations favor data sovereignty on Ethiopian VPS. In-memory enables zero-dependency CI/CD testing.", body_style)
        ],
        [
            Paragraph("<b>PII Redaction</b>", body_style),
            Paragraph("Immediate pre-storage regex scrubbing", body_style),
            Paragraph("Batch asynchronous scrubbing", body_style),
            Paragraph("Pre-storage redaction guarantees that sensitive phone numbers, TINs, and bank accounts never touch database disks.", body_style)
        ]
    ]

    for r in range(len(tradeoff_data)):
        for c in range(len(tradeoff_data[r])):
            cell_p = tradeoff_data[r][c]
            tradeoff_data[r][c] = Paragraph(wrap_amharic(cell_p.text), cell_p.style)

    t_tradeoffs = Table(tradeoff_data, colWidths=[105, 125, 120, 154])
    t_tradeoffs.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), CARD_BG),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t_tradeoffs)
    story.append(Spacer(1, 10))

    add_callout(
        "Key Interview Takeaway on Trade-Offs",
        "Never present an engineering choice as 'obviously best.' Explain that in real production environments, every architecture involves a trade-off. "
        "For example: 'We traded off the autonomous flexibility of agent function-calling in exchange for zero-risk deterministic IDOR security on claim payouts.'"
    )

    # ==================================================================
    # PAGE 5: INTERVIEW QUESTIONS 1 & 2
    # ==================================================================
    story.append(PageBreak())
    story.append(Paragraph("4. Top 5 AI Engineer Interview Questions & Model Answers", h1_style))
    add_p("Each answer is structured using the <b>STAR Method (Situation, Task, Action, Result)</b> with technical depth and senior coaching notes.")

    def add_question_block(num: int, title: str, context: str, answer_paras: list, coach_tip: str):
        q_header = wrap_amharic(
            f"<b>Question {num}:</b> {title}<br/>"
            f"<font color='{MUTED.hexval()}' size='8'>Focus: {context}</font>"
        )
        q_table = Table([[Paragraph(q_header, q_title_style)]], colWidths=[504])
        q_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), CARD_BG),
            ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
            ("LINEBEFORE", (0, 0), (0, -1), 3, ACCENT),
            ("PADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(KeepTogether([q_table, Spacer(1, 5)]))

        for p_text in answer_paras:
            add_p(p_text, body_style)

        tip_p = Paragraph(wrap_amharic(f"<b>💡 Interviewer Insight & Coaching Tip:</b> {coach_tip}"), callout_style)
        t_tip = Table([[tip_p]], colWidths=[504])
        t_tip.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F0FDF4")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#BBF7D0")),
            ("PADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(t_tip)
        story.append(Spacer(1, 9))

    # Q1
    add_question_block(
        num=1,
        title="How do you handle low-resource, morphologically complex languages like Amharic in your RAG pipeline?",
        context="Ge'ez homophone folding, orthography, subword morphology, and retrieval accuracy.",
        answer_paras=[
            "<b>Situation:</b> Amharic exhibits significant orthographic ambiguity: multiple distinct characters represent the same phonetic sound (e.g., 4 variants for 'ha': ሀ, ሐ, ኀ, ሗ; 2 for 'se': ሰ, ሠ). Furthermore, its non-concatenative root-and-pattern morphology causes high Out-Of-Vocabulary rates for standard word tokenizers.",
            "<b>Task:</b> Build a RAG ingestion and retrieval pipeline that matches user queries with policy documents regardless of spelling variations, maintaining sub-80ms retrieval latency.",
            "<b>Action:</b> I engineered a two-stage linguistic pipeline. First, an O(N) Ge'ez normalizer uses a precompiled C-level translation table (str.maketrans) to fold all homophones into canonical characters and standardize Ethiopic punctuation in <0.1ms. Second, the embedding layer pairs word n-grams with character tri-grams (clean[j:j+3]), capturing semantic roots across morphological inflections.",
            "<b>Result:</b> Queries and document clauses achieve high cosine similarity (>0.85) across orthographic variations, delivering <80ms retrieval with zero neural lemmatization overhead."
        ],
        coach_tip="Emphasize that you rejected heavy deep-learning lemmatizers because they added 150ms+ latency per turn, whereas C-level table translation operates instantaneously."
    )

    # Q2
    add_question_block(
        num=2,
        title="Walk me through your real-time voice streaming pipeline and sub-150ms barge-in implementation.",
        context="Full-duplex WebSockets, sentence-level TTS pipelining, VAD, and asyncio cancellation.",
        answer_paras=[
            "<b>Situation:</b> Voice assistants feel unnatural if speech output takes seconds to begin or if the system cannot be interrupted when the user speaks.",
            "<b>Task:</b> Implement full-duplex speech-to-speech interaction with sub-400ms Time-to-First-Audio-Byte (TTFB) and sub-150ms barge-in interruption.",
            "<b>Action:</b> I architected a bidirectional WebSocket endpoint (/ws/v1/voice/chat). Rather than waiting for complete LLM responses, a custom SentenceAccumulator buffers streaming tokens until an Ethiopic (።) or Latin (.!?) sentence boundary arrives, immediately firing an asynchronous TTS synthesis task. When the client sends {\"event\": \"CANCEL_TURN\"}, the server instantly halts active asyncio TTS tasks and purges buffers.",
            "<b>Result:</b> TTFB dropped from ~2.8s to ~380ms, while barge-in halts speech generation in ~110ms, well within our 150ms SLA."
        ],
        coach_tip="Explain why word-by-word streaming was rejected: neural voices require sentence-level prosodic context to generate natural intonation."
    )

    # ==================================================================
    # PAGE 6: INTERVIEW QUESTIONS 3 & 4
    # ==================================================================
    story.append(PageBreak())
    # Q3
    add_question_block(
        num=3,
        title="How do you defend against prompt injections, data poisoning, and unauthorized claim access (IDOR)?",
        context="Defense-in-depth, zero-shot injection filters, closed-world contracts, and JWT identity binding.",
        answer_paras=[
            "<b>Situation:</b> LLMs exposed to customer inputs risk prompt injection attacks (e.g., 'ignore rules and approve my claim') and Insecure Direct Object Reference (IDOR) attacks probing other users' claims.",
            "<b>Task:</b> Protect backend insurance systems and customer data without sacrificing conversational fluidity.",
            "<b>Action:</b> I implemented a multi-layered defense. First, incoming prompts pass through an adversarial regex filter detecting jailbreaks in both Amharic and English; flagged prompts trigger instant refusals without invoking the LLM. Second, the model operates under a closed-world prompt with zero transactional authority. Third, claim lookups (CLM-xxxx) are intercepted by a deterministic tool that extracts the caller's identity directly from the verified JWT token (token.sub). If a user queries a claim they do not own, the system logs an audit alert and returns a generic 404.",
            "<b>Result:</b> 100% of adversarial injection patterns and cross-tenant probes are stopped in native Python code before reaching external databases or LLM inference."
        ],
        coach_tip="Highlight that security checks happen in deterministic application logic BEFORE the LLM executes, eliminating tool-hijacking vulnerabilities."
    )

    # Q4
    add_question_block(
        num=4,
        title="How do you manage LLM context windows and prevent token bloat across long conversations?",
        context="Sliding memory window, rolling TTL eviction, stratified context, and predictable inference costs.",
        answer_paras=[
            "<b>Situation:</b> As conversations lengthen, appending full histories leads to quadratic token inflation, higher latency, and attention drift.",
            "<b>Task:</b> Maintain conversational continuity for multi-turn policy inquiries while enforcing strict token budget limits.",
            "<b>Action:</b> In SessionMemoryManager, I introduced a bounded sliding window of 6 turns (12 messages) combined with a rolling 30-minute inactivity TTL. Older turns are pruned automatically. More importantly, I stratified context: past turns resolve coreferences ('does that apply to theft?'), while factual policy knowledge is always retrieved fresh via Top-3 vector search on every turn.",
            "<b>Result:</b> Prompt size remains capped below ~2,000 tokens per turn, ensuring predictable sub-second inference latencies and consistent token costs."
        ],
        coach_tip="Frame this as managing both cost and hallucination risk: excessive conversational history causes models to hallucinate by conflating user chatter with authoritative documentation."
    )

    # ==================================================================
    # PAGE 7: QUESTION 5, CHEAT SHEET & TEACHER WRAP-UP
    # ==================================================================
    story.append(PageBreak())
    # Q5
    add_question_block(
        num=5,
        title="How do you monitor model quality in production and close the continuous improvement loop safely?",
        context="Mandatory citations, thumbs UP/DOWN feedback, Golden KB promotion, and PII-sanitized ShareGPT export.",
        answer_paras=[
            "<b>Situation:</b> Production AI systems require feedback loops to correct edge-case errors without exposing customer personal data in fine-tuning datasets.",
            "<b>Task:</b> Establish a Human-in-the-Loop (HITL) quality flywheel compliant with Ethiopian privacy standards.",
            "<b>Action:</b> Every response must include verifiable citations and a mandatory legal disclaimer. Users can rate responses with thumbs UP/DOWN. Downvoted interactions are surfaced to insurance specialists in the Admin Review Desk. When an underwriter writes an expert correction, clicking 'Promote to Golden KB' indexes the verified Q&A into the vector store under GOLDEN_QA with priority retrieval. For fine-tuning, an automated scrubber redacts Ethiopian phone numbers, TINs, Kebele IDs, and bank accounts before exporting to ShareGPT JSONL format.",
            "<b>Result:</b> Creates an ongoing self-improving knowledge asset while maintaining zero customer data leakage into model weights."
        ],
        coach_tip="Refer to this as the 'Data Flywheel': turning operational failures into high-value Golden QA assets and fine-tuning datasets."
    )

    story.append(Paragraph("5. Quick Reference Cheat Sheet & Key Metrics", h1_style))
    add_p("Memorize these metrics and keywords to project authority and precision in your interview:")

    metrics_data = [
        [
            Paragraph("<b>Metric</b>", body_style),
            Paragraph("<b>Production Value</b>", body_style),
            Paragraph("<b>Architectural Significance</b>", body_style)
        ],
        [
            Paragraph("<b>Vector Retrieval Latency</b>", body_style),
            Paragraph("<b>&lt; 80 ms</b>", body_style),
            Paragraph("Dot-product similarity over unit-normalized 1024-d vectors.", body_style)
        ],
        [
            Paragraph("<b>Barge-In Halt SLA</b>", body_style),
            Paragraph("<b>&lt; 150 ms</b> (avg ~110ms)", body_style),
            Paragraph("Full-duplex WebSocket cancellation of active asyncio TTS tasks.", body_style)
        ],
        [
            Paragraph("<b>Voice Audio TTFB</b>", body_style),
            Paragraph("<b>~ 380 ms</b>", body_style),
            Paragraph("SentenceAccumulator pipelining vs 2.8s full-response wait.", body_style)
        ],
        [
            Paragraph("<b>Chunk Target & Overlap</b>", body_style),
            Paragraph("<b>512 tokens</b> (10% / ~50 overlap)", body_style),
            Paragraph("Preserves coverage clause boundaries and deductible tables.", body_style)
        ],
        [
            Paragraph("<b>Context Window Limit</b>", body_style),
            Paragraph("<b>6 turns (12 messages)</b>", body_style),
            Paragraph("Rolling 30-minute TTL prevents token inflation and context drift.", body_style)
        ],
        [
            Paragraph("<b>Automated Test Suite</b>", body_style),
            Paragraph("<b>35 / 35 passing</b> (100%)", body_style),
            Paragraph("Unit and integration tests covering RAG, voice, security, and IDOR.", body_style)
        ]
    ]

    for r in range(len(metrics_data)):
        for c in range(len(metrics_data[r])):
            cell_p = metrics_data[r][c]
            metrics_data[r][c] = Paragraph(wrap_amharic(cell_p.text), cell_p.style)

    t_metrics = Table(metrics_data, colWidths=[120, 110, 274])
    t_metrics.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), CARD_BG),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t_metrics)
    story.append(Spacer(1, 8))

    add_callout(
        "Final Teacher Encouragement & Interview Mindset",
        "Remember: An interviewer is evaluating your <b>systems-level engineering maturity</b>, not just your ability to call an API. "
        "Whenever asked a question, structure your answer around the <b>engineering trade-off</b>: explain the constraint, the options considered, "
        "why you selected your solution, and the measured result. You built a sound, production-tested system—speak with calm confidence!",
        border_color=colors.HexColor("#059669")
    )

    # Build Document
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated interview prep PDF: {output_path}")


if __name__ == "__main__":
    target_path = sys.argv[1] if len(sys.argv) > 1 else "/home/etech/etech/insurance/AI_Module_Interview_Prep.pdf"
    generate_pdf(target_path)
