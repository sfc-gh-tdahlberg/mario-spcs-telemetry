from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml.ns import qn
from lxml import etree
import copy, os

TEMPLATE = os.path.join(os.path.dirname(__file__), "presentation_template/presetation_template.pptx")
OUTPUT   = os.path.join(os.path.dirname(__file__), "Super_Mario_SPCS_Telemetry_Presentation.pptx")

prs = Presentation(TEMPLATE)
W = prs.slide_width   # 10"
H = prs.slide_height  # 5.62"

# Remove the 4 existing template placeholder slides
NS = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
sldIdLst = prs.slides._sldIdLst
while len(sldIdLst):
    r_id = sldIdLst[0].get(f'{{{NS}}}id')
    prs.part.drop_rel(r_id)
    del sldIdLst[0]

# ── Colour palette ────────────────────────────────────────────────────────────
SF_BLUE    = RGBColor(0x29, 0xB5, 0xE8)
SF_NAVY    = RGBColor(0x11, 0x56, 0x7F)
SF_DARK    = RGBColor(0x06, 0x0D, 0x1A)
SF_CARD    = RGBColor(0x0F, 0x1F, 0x38)
WHITE      = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT_GRAY = RGBColor(0xCC, 0xD9, 0xEE)
MED_GRAY   = RGBColor(0x6B, 0x8A, 0xB8)
MARIO_RED  = RGBColor(0xE8, 0x40, 0x40)
MARIO_YEL  = RGBColor(0xFF, 0xD7, 0x00)
MARIO_GRN  = RGBColor(0x3D, 0xD6, 0x8C)
MARIO_PUR  = RGBColor(0xA7, 0x8B, 0xFA)
CARD_BG    = RGBColor(0x0A, 0x16, 0x28)

# ── Layout shortcuts ─────────────────────────────────────────────────────────
LAY_COVER   = prs.slide_layouts[0]   # 1_Cover 02 (clean branded cover)
LAY_CONTENT = prs.slide_layouts[6]   # 1_Cover 02 6 (blank-ish, used in existing deck)
LAY_DIVIDER = prs.slide_layouts[12]  # Summit22 - Divider
LAY_THANKYOU= prs.slide_layouts[25]  # Thank You
LAY_BLANK   = prs.slide_layouts[2]   # 1_Blank (footer only)

# ── Primitive helpers ─────────────────────────────────────────────────────────
def bg(slide, color=SF_DARK):
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = color

def rect(slide, l, t, w, h, fill=SF_CARD, line=None, radius=None):
    if radius:
        sh = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, l, t, w, h)
        sh.adjustments[0] = radius
    else:
        sh = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, l, t, w, h)
    sh.fill.solid(); sh.fill.fore_color.rgb = fill
    if line: sh.line.color.rgb = line; sh.line.width = Pt(1.5)
    else:    sh.line.fill.background()
    return sh

def txt(slide, l, t, w, h, text, sz=16, color=WHITE, bold=False, align=PP_ALIGN.LEFT, wrap=True, italic=False):
    tb = slide.shapes.add_textbox(l, t, w, h)
    tf = tb.text_frame; tf.word_wrap = wrap
    p = tf.paragraphs[0]; p.text = text
    p.alignment = align
    r = p.runs[0]
    r.font.size = Pt(sz); r.font.color.rgb = color
    r.font.bold = bold;   r.font.italic = italic
    return tb

def bullet_list(slide, l, t, w, h, items, sz=14, color=LIGHT_GRAY, bullet="▸ "):
    tb = slide.shapes.add_textbox(l, t, w, h)
    tf = tb.text_frame; tf.word_wrap = True
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = f"{bullet}{item}"
        p.font.size = Pt(sz); p.font.color.rgb = color
        p.space_after = Pt(5)
    return tb

def accent_bar(slide, color=SF_BLUE, height=Inches(0.055)):
    rect(slide, 0, 0, W, height, fill=color)

def section_label(slide, text, color=SF_BLUE):
    txt(slide, Inches(0.5), Inches(0.12), Inches(9), Inches(0.45),
        text, sz=10, color=color, bold=True)

def slide_title(slide, text, y=Inches(0.22), sz=30, color=WHITE):
    txt(slide, Inches(0.5), y, W - Inches(1), Inches(0.6), text, sz=sz, color=color, bold=True)

def footer_line(slide, text, color=MED_GRAY):
    txt(slide, Inches(0.5), H - Inches(0.38), W - Inches(1), Inches(0.32),
        text, sz=10, color=color, italic=True)

def card(slide, l, t, w, h, title, body, accent=SF_BLUE, title_sz=15, body_sz=12):
    rect(slide, l, t, w, h, fill=CARD_BG, line=accent, radius=0.04)
    rect(slide, l, t, w, Inches(0.055), fill=accent)
    txt(slide, l + Inches(0.18), t + Inches(0.12), w - Inches(0.36), Inches(0.38),
        title, sz=title_sz, color=accent, bold=True)
    tb = slide.shapes.add_textbox(l + Inches(0.18), t + Inches(0.55), w - Inches(0.36), h - Inches(0.65))
    tf = tb.text_frame; tf.word_wrap = True
    for i, line in enumerate(body.split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = line; p.font.size = Pt(body_sz); p.font.color.rgb = LIGHT_GRAY
        p.space_after = Pt(3)


# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 1 — COVER
# ══════════════════════════════════════════════════════════════════════════════
sl = prs.slides.add_slide(LAY_COVER)
bg(sl, RGBColor(0x06, 0x0D, 0x1A))

# Background gradient bands
rect(sl, 0, 0, W, Inches(0.5), fill=SF_BLUE)
rect(sl, 0, H - Inches(0.5), W, Inches(0.5), fill=SF_NAVY)

# Decorative pixel blocks (Mario theme)
for i, (c, pos) in enumerate([(MARIO_RED, 0.3), (MARIO_YEL, 0.9), (MARIO_GRN, 1.5), (SF_BLUE, 2.1)]):
    rect(sl, W - Inches(1.3 - i*0.18), Inches(1.2), Inches(0.22), Inches(0.22), fill=c)

txt(sl, Inches(0.6), Inches(0.7), W - Inches(1.2), Inches(0.55),
    "🍄  SUPER MARIO SPCS TELEMETRY", sz=36, color=WHITE, bold=True, align=PP_ALIGN.CENTER)
txt(sl, Inches(0.6), Inches(1.38), W - Inches(1.2), Inches(0.55),
    "Real-time Game Analytics · Snowpark Container Services · OpenTelemetry",
    sz=17, color=SF_BLUE, align=PP_ALIGN.CENTER)

# Divider
rect(sl, Inches(2), Inches(2.1), W - Inches(4), Inches(0.04), fill=SF_BLUE)

# Feature pills
pills = [("🐳 SPCS Container", MARIO_RED), ("📡 OpenTelemetry", SF_BLUE),
         ("⚡ Interactive Tables", MARIO_GRN), ("🤖 Cortex AI", MARIO_PUR), ("📊 React + Streamlit", MARIO_YEL)]
for i, (label, col) in enumerate(pills):
    x = Inches(0.35 + i * 1.86)
    rect(sl, x, Inches(2.35), Inches(1.75), Inches(0.42), fill=CARD_BG, line=col, radius=0.08)
    txt(sl, x + Inches(0.12), Inches(2.42), Inches(1.52), Inches(0.32), label, sz=11, color=col, bold=True, align=PP_ALIGN.CENTER)

txt(sl, Inches(0.6), Inches(3.05), W - Inches(1.2), Inches(0.4),
    "20-Minute Demo Session  ·  Snowflake Solutions Engineering", sz=13, color=MED_GRAY, align=PP_ALIGN.CENTER)
txt(sl, Inches(0.6), Inches(3.5), W - Inches(1.2), Inches(0.4),
    "github.com/sfc-gh-tdahlberg/mario-spcs-telemetry",
    sz=12, color=SF_BLUE, align=PP_ALIGN.CENTER, italic=True)


# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 2 — AGENDA
# ══════════════════════════════════════════════════════════════════════════════
sl = prs.slides.add_slide(LAY_CONTENT)
bg(sl); accent_bar(sl)
section_label(sl, "AGENDA")
slide_title(sl, "What We'll Cover in 20 Minutes", sz=26)

agenda = [
    ("01", "What We Built",        "The complete project in 90 seconds",            SF_BLUE,    Inches(0.5),  Inches(1.1)),
    ("02", "Architecture Deep Dive","Data flow from game to dashboard",              MARIO_GRN,  Inches(0.5),  Inches(2.05)),
    ("03", "Player Identity",       "How SPCS auth flows into telemetry data",       MARIO_YEL,  Inches(0.5),  Inches(3.0)),
    ("04", "Real-time Pipeline",    "Interactive Tables + Cortex AI intelligence",   MARIO_PUR,  Inches(0.5),  Inches(3.95)),
    ("🎮", "LIVE DEMO",             "Play Mario · watch the dashboard update",       MARIO_RED,  Inches(5.2),  Inches(1.1)),
    ("05", "Key Learnings",         "What surprised us building this",               MED_GRAY,   Inches(5.2),  Inches(2.05)),
]

for num, title, sub, col, lx, ly in agenda:
    rect(sl, lx, ly, Inches(4.4), Inches(0.78), fill=CARD_BG, line=col, radius=0.04)
    rect(sl, lx, ly, Inches(0.45), Inches(0.78), fill=col, radius=0.02)
    txt(sl, lx + Inches(0.05), ly + Inches(0.18), Inches(0.36), Inches(0.38),
        num, sz=13, color=SF_DARK if col != MED_GRAY else WHITE, bold=True, align=PP_ALIGN.CENTER)
    txt(sl, lx + Inches(0.55), ly + Inches(0.08), Inches(3.7), Inches(0.34), title, sz=15, color=col, bold=True)
    txt(sl, lx + Inches(0.55), ly + Inches(0.44), Inches(3.7), Inches(0.28), sub, sz=11, color=MED_GRAY)

footer_line(sl, "Each section ~2 min · Demo ~10 min · Q&A at end")


# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 3 — WHAT WE BUILT
# ══════════════════════════════════════════════════════════════════════════════
sl = prs.slides.add_slide(LAY_CONTENT)
bg(sl); accent_bar(sl)
section_label(sl, "WHAT WE BUILT")
slide_title(sl, "Five Components. One Snowflake Account.", sz=26)

components = [
    ("🎮", "Game on SPCS",        "HTML5 Super Mario running in a\nSnowpark Container with public\ningress and authentication",  MARIO_RED),
    ("📡", "Telemetry Pipeline",  "Browser JS → nginx → Python sidecar\n→ OpenTelemetry OTLP gRPC\n→ SPCS Event Table",         SF_BLUE),
    ("⚡", "Real-time Tables",    "6 Interactive Tables with 1-min lag,\nInteractive Warehouse, player\nsessions and events",     MARIO_GRN),
    ("🤖", "Cortex AI",           "Semantic View over 6 tables,\n10 VQRs via FastGen, and a\nCortex Agent for NL queries",      MARIO_PUR),
    ("📊", "Dashboards",          "Streamlit SiS + React Next.js app\nwith live charts, leaderboard,\nand platform metrics",    MARIO_YEL),
]

for i, (icon, title, desc, col) in enumerate(components):
    x = Inches(0.35 + i * 1.86)
    y = Inches(1.05)
    rect(sl, x, y, Inches(1.72), Inches(3.45), fill=CARD_BG, line=col, radius=0.05)
    rect(sl, x, y, Inches(1.72), Inches(0.055), fill=col)
    txt(sl, x, y + Inches(0.2), Inches(1.72), Inches(0.5), icon, sz=26, align=PP_ALIGN.CENTER)
    txt(sl, x + Inches(0.12), y + Inches(0.78), Inches(1.5), Inches(0.42), title, sz=14, color=col, bold=True, align=PP_ALIGN.CENTER)
    tb = sl.shapes.add_textbox(x + Inches(0.14), y + Inches(1.28), Inches(1.46), Inches(2.1))
    tf = tb.text_frame; tf.word_wrap = True
    for j, line in enumerate(desc.split("\n")):
        p = tf.paragraphs[0] if j == 0 else tf.add_paragraph()
        p.text = line; p.font.size = Pt(11); p.font.color.rgb = LIGHT_GRAY
        p.space_after = Pt(3)
        p.alignment = PP_ALIGN.CENTER

footer_line(sl, "All components run inside a single Snowflake account · Zero external infrastructure")


# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 4 — ARCHITECTURE
# ══════════════════════════════════════════════════════════════════════════════
sl = prs.slides.add_slide(LAY_CONTENT)
bg(sl); accent_bar(sl)
section_label(sl, "ARCHITECTURE")
slide_title(sl, "End-to-End Data Flow", sz=26)

# Flow nodes
nodes = [
    (Inches(0.25), Inches(1.5),  Inches(1.5), Inches(1.15), "🌐",  "Browser\nPlayer",           SF_BLUE),
    (Inches(2.05), Inches(1.5),  Inches(1.5), Inches(1.15), "🔐",  "SPCS Ingress\n+ Auth",       MARIO_GRN),
    (Inches(3.85), Inches(1.5),  Inches(1.5), Inches(1.15), "⚙️",  "nginx\n:8080",               SF_BLUE),
    (Inches(3.85), Inches(3.1),  Inches(1.5), Inches(1.15), "🐱",  "Tomcat\nGame :8888",         MARIO_RED),
    (Inches(5.65), Inches(1.5),  Inches(1.6), Inches(1.15), "🐍",  "Python Sidecar\nOTel :9090", MARIO_YEL),
    (Inches(7.55), Inches(1.5),  Inches(1.7), Inches(1.15), "📋",  "Event Table\nevent_db",      MARIO_GRN),
    (Inches(7.55), Inches(3.1),  Inches(1.7), Inches(1.15), "⚡",  "Interactive\nTables 6x",    MARIO_PUR),
    (Inches(7.55), Inches(4.3),  Inches(1.7), Inches(0.85), "🤖",  "Cortex AI",                  SF_BLUE),
]
for l, t, w, h, icon, label, col in nodes:
    rect(sl, l, t, w, h, fill=CARD_BG, line=col, radius=0.05)
    rect(sl, l, t, w, Inches(0.045), fill=col)
    txt(sl, l, t + Inches(0.1), w, Inches(0.42), icon, sz=20, align=PP_ALIGN.CENTER)
    txt(sl, l + Inches(0.08), t + Inches(0.55), w - Inches(0.16), Inches(0.58), label, sz=10, color=LIGHT_GRAY, align=PP_ALIGN.CENTER)

# Arrows (simple text arrows)
arrows = [
    (Inches(1.77), Inches(1.95), "GET pixel"),
    (Inches(3.58), Inches(1.95), "header"),
    (Inches(5.37), Inches(1.95), "OTLP gRPC"),
    (Inches(4.62), Inches(2.68), "proxy"),
    (Inches(7.55), Inches(2.68), "1-min lag"),
]
for x, y, lbl in arrows:
    txt(sl, x, y - Inches(0.2), Inches(0.22), Inches(0.2), "►", sz=11, color=SF_BLUE, align=PP_ALIGN.CENTER)
    txt(sl, x - Inches(0.12), y + Inches(0.02), Inches(0.46), Inches(0.2), lbl, sz=7, color=MED_GRAY, align=PP_ALIGN.CENTER)

# Right panel: consumers
txt(sl, Inches(7.55), Inches(2.7), Inches(1.7), Inches(0.28), "▼  SQL Views", sz=8, color=MED_GRAY, align=PP_ALIGN.CENTER)
consumers = ["📊 Streamlit", "⚛️ React App", "🤖 Cortex Agent"]
for i, c in enumerate(consumers):
    rect(sl, Inches(7.6), Inches(5.08 + i * 0.0), Inches(1.6), Inches(0.28), fill=CARD_BG)
    txt(sl, Inches(7.6), Inches(5.1 + i * 0.0), Inches(1.6), Inches(0.25), c, sz=9, color=SF_BLUE, align=PP_ALIGN.CENTER)

footer_line(sl, "Single Docker container: nginx (8080) → Tomcat (8888) + Python sidecar (9090) · All inside SPCS · event_db.event_sh.my_events")


# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 5 — CONTAINER INTERNALS
# ══════════════════════════════════════════════════════════════════════════════
sl = prs.slides.add_slide(LAY_CONTENT)
bg(sl); accent_bar(sl)
section_label(sl, "CONTAINER DEEP DIVE")
slide_title(sl, "What's Inside the Docker Image", sz=26)

layers = [
    (Inches(0.5),  MARIO_GRN,  "🌐  nginx  :8080",           "Public SPCS ingress · exact location = /telemetry match · Forwards Sf-Context-Current-User header to sidecar"),
    (Inches(1.55), MARIO_RED,  "🐱  Tomcat 9  :8888",         "HTML5 Super Mario game · telemetry.js injected at build time · jQuery bundled locally (CDN blocked by SPCS egress)"),
    (Inches(2.6),  MARIO_YEL,  "🐍  Python Sidecar  :9090",   "OTel TracerProvider + MeterProvider · GET tracking pixel /telemetry?d=... · /whoami endpoint · BatchSpanProcessor 5s"),
    (Inches(3.65), SF_BLUE,    "📡  OpenTelemetry OTLP gRPC", "Spans → record_attributes · Metrics → 90+ platform types · Logs → service messages · all → event_db.event_sh.my_events"),
]
for y, col, title, desc in layers:
    rect(sl, Inches(0.5), y, W - Inches(1.0), Inches(0.88), fill=CARD_BG, radius=0.03)
    rect(sl, Inches(0.5), y, Inches(0.12), Inches(0.88), fill=col)
    txt(sl, Inches(0.75), y + Inches(0.08), Inches(3.2), Inches(0.42), title, sz=16, color=col, bold=True)
    txt(sl, Inches(0.75), y + Inches(0.5), W - Inches(1.4), Inches(0.34), desc, sz=12, color=LIGHT_GRAY)

footer_line(sl, "Resources: 500m–1 vCPU  ·  512Mi–2Gi RAM  ·  CPU_X64_XS  ·  1 node  ·  AUTO_RESUME = TRUE")


# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 6 — PLAYER IDENTITY
# ══════════════════════════════════════════════════════════════════════════════
sl = prs.slides.add_slide(LAY_CONTENT)
bg(sl); accent_bar(sl)
section_label(sl, "PLAYER IDENTITY")
slide_title(sl, "From Login to Leaderboard: How We Track Players", sz=24)

steps = [
    ("1", "SPCS Ingress Auth",      "Browser auth cookie",                      SF_BLUE),
    ("2", "Header Injection",       "Sf-Context-Current-User: THOMAS",           MARIO_GRN),
    ("3", "nginx Forwarding",       "proxy_set_header Sf-Context-Current-User",  MARIO_YEL),
    ("4", "Sidecar /whoami",        "_get_player_name() extracts header",        MARIO_RED),
    ("5", "Browser Fetch",          "telemetry.js calls /whoami at init",        MARIO_PUR),
    ("6", "Event Payload",          "player_name in every send() call",          SF_BLUE),
    ("7", "OTel Span Attr",         "record_attributes:player_name::STRING",     MARIO_GRN),
]
for i, (num, title, sub, col) in enumerate(steps):
    x = Inches(0.32 + i * 1.32)
    y = Inches(1.12)
    rect(sl, x, y, Inches(1.2), Inches(1.3), fill=CARD_BG, line=col, radius=0.05)
    rect(sl, x, y, Inches(1.2), Inches(0.045), fill=col)
    sh = sl.shapes.add_shape(MSO_SHAPE.OVAL, x + Inches(0.38), y + Inches(0.14), Inches(0.45), Inches(0.45))
    sh.fill.solid(); sh.fill.fore_color.rgb = col; sh.line.fill.background()
    sh.text_frame.paragraphs[0].text = num
    sh.text_frame.paragraphs[0].font.size = Pt(16); sh.text_frame.paragraphs[0].font.bold = True
    sh.text_frame.paragraphs[0].font.color.rgb = SF_DARK
    sh.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
    txt(sl, x + Inches(0.06), y + Inches(0.68), Inches(1.1), Inches(0.32), title, sz=10, color=col, bold=True, align=PP_ALIGN.CENTER)
    txt(sl, x + Inches(0.06), y + Inches(1.0), Inches(1.1), Inches(0.28), sub, sz=8, color=MED_GRAY, align=PP_ALIGN.CENTER)

# Priority table
ty = Inches(2.75)
rect(sl, Inches(0.5), ty, W - Inches(1.0), Inches(1.45), fill=CARD_BG, radius=0.04)
txt(sl, Inches(0.7), ty + Inches(0.12), Inches(3), Inches(0.35), "Player Name Priority Chain", sz=13, color=LIGHT_GRAY, bold=True)
chain = [("1  Header",       "Sf-Context-Current-User",              MARIO_GRN, "Most reliable — injected by SPCS ingress"),
         ("2  Browser",      "data.player_name from /whoami",         MARIO_YEL, "Fallback — fetched at game init"),
         ("3  Default",      '"unknown"',                             MARIO_RED, "Last resort if both sources fail")]
for j, (pri, src, col, note) in enumerate(chain):
    xy = ty + Inches(0.55 + j * 0.28)
    txt(sl, Inches(0.7), xy, Inches(1.0), Inches(0.26), pri, sz=11, color=col, bold=True)
    txt(sl, Inches(1.75), xy, Inches(2.8), Inches(0.26), src, sz=11, color=WHITE)
    txt(sl, Inches(4.6), xy, Inches(5.2), Inches(0.26), note, sz=10, color=MED_GRAY)

footer_line(sl, "Key fix: telemetry.js was calling /whoami for the banner but NOT including player_name in event payloads — fixed by adding it to every send()")


# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 7 — REAL-TIME PIPELINE
# ══════════════════════════════════════════════════════════════════════════════
sl = prs.slides.add_slide(LAY_CONTENT)
bg(sl); accent_bar(sl)
section_label(sl, "DIS_MARIO REAL-TIME PIPELINE")
slide_title(sl, "Interactive Tables: Near-Realtime at Query Speed", sz=24)

# Left: table list
tables = [
    ("GAME_EVENTS_LIVE",       "EVENT_TIME",     "All game spans + player_name"),
    ("EVENT_TIMELINE_LIVE",    "MINUTE",         "Event counts per minute"),
    ("KEY_PRESSES_LIVE",       "KEY_NAME",       "Key press aggregates"),
    ("DEATHS_BY_LEVEL_LIVE",   "LEVEL",          "Deaths by level"),
    ("POWERUPS_LIVE",          "POWERUP_TYPE",   "Powerup spawn counts"),
    ("PLAYER_SESSIONS_LIVE",   "SESSION_START",  "Per-player session summaries"),
]
for i, (name, cluster, desc) in enumerate(tables):
    y = Inches(1.08 + i * 0.71)
    rect(sl, Inches(0.4), y, Inches(5.5), Inches(0.62), fill=CARD_BG, radius=0.03)
    rect(sl, Inches(0.4), y, Inches(0.1), Inches(0.62), fill=MARIO_PUR)
    txt(sl, Inches(0.62), y + Inches(0.06), Inches(2.6), Inches(0.28), name, sz=11, color=WHITE, bold=True)
    txt(sl, Inches(0.62), y + Inches(0.34), Inches(2.6), Inches(0.24), desc, sz=10, color=MED_GRAY)
    rect(sl, Inches(3.3), y + Inches(0.14), Inches(1.1), Inches(0.3), fill=RGBColor(0x1A, 0x2B, 0x4A), radius=0.04)
    txt(sl, Inches(3.32), y + Inches(0.14), Inches(1.06), Inches(0.3), f"⚡ {cluster}", sz=8, color=SF_BLUE, align=PP_ALIGN.CENTER)
    txt(sl, Inches(4.5), y + Inches(0.18), Inches(1.4), Inches(0.26), "1 min lag", sz=9, color=MARIO_GRN)

# Right: key facts
kfacts = [
    ("⚡", "Interactive Warehouse",  "DIS_MARIO_IWH\nXSMALL · 24h auto-suspend\nSub-second query latency"),
    ("🔄", "Refresh Warehouse",      "DIS_MARIO_WH\nXSMALL · 60s auto-suspend\nFor background refreshes"),
    ("🤖", "Cortex Intelligence",    "Semantic View MARIO_TELEMETRY\n10 VQRs via FastGen\nCortex Agent: MARIO_INTELLIGENCE"),
]
for i, (icon, title, body) in enumerate(kfacts):
    card(sl, Inches(6.2), Inches(1.08 + i * 1.48), Inches(3.5), Inches(1.35),
         f"{icon}  {title}", body, accent=SF_BLUE, title_sz=13, body_sz=11)

footer_line(sl, "CREATE INTERACTIVE TABLE syntax (not DYNAMIC) · ALTER INTERACTIVE TABLE … SET WAREHOUSE = DIS_MARIO_IWH")


# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 8 — DASHBOARDS & AI
# ══════════════════════════════════════════════════════════════════════════════
sl = prs.slides.add_slide(LAY_CONTENT)
bg(sl); accent_bar(sl)
section_label(sl, "DASHBOARDS & AI")
slide_title(sl, "Four Ways to Consume the Data", sz=26)

dashboards = [
    ("📊", "Streamlit — Legacy",   "MARIO_DB.PUBLIC.MARIO_TELEMETRY_DASHBOARD",
     "Event table views · Leaderboard filtered to last 24h · 5 tabs: Leaderboard, Events, Deaths, Controls, Platform Metrics",
     MARIO_RED, Inches(0.35), Inches(1.1)),
    ("⚡", "Streamlit — Live",     "DIS_MARIO.PUBLIC.DIS_MARIO_TELEMETRY_DASHBOARD",
     "Interactive Tables · 10s cache TTL · Player dropdown filter · 6 KPI cards · Real-time event streaming",
     MARIO_GRN, Inches(0.35), Inches(2.62)),
    ("⚛️", "React App",            "Next.js 16.2.3 · Port 3456 locally",
     "JWT auth locally · OAuth token in SPCS · 5s polling · Animated Data Pipeline tab · Recharts visualizations",
     SF_BLUE, Inches(5.15), Inches(1.1)),
    ("🤖", "Cortex Agent",         "DIS_MARIO.PUBLIC.MARIO_INTELLIGENCE",
     "Natural language → SQL via Semantic View MARIO_TELEMETRY · 10 VQRs · model: auto · 900s / 400k token budget",
     MARIO_PUR, Inches(5.15), Inches(2.62)),
]
for icon, title, subtitle, body, col, x, y in dashboards:
    rect(sl, x, y, Inches(4.45), Inches(1.35), fill=CARD_BG, line=col, radius=0.05)
    rect(sl, x, y, Inches(4.45), Inches(0.05), fill=col)
    txt(sl, x + Inches(0.14), y + Inches(0.1), Inches(0.45), Inches(0.45), icon, sz=22)
    txt(sl, x + Inches(0.65), y + Inches(0.1), Inches(3.65), Inches(0.3), title, sz=14, color=col, bold=True)
    txt(sl, x + Inches(0.65), y + Inches(0.42), Inches(3.65), Inches(0.24), subtitle, sz=9, color=MED_GRAY, italic=True)
    tb = sl.shapes.add_textbox(x + Inches(0.14), y + Inches(0.7), Inches(4.2), Inches(0.62))
    tf = tb.text_frame; tf.word_wrap = True
    p = tf.paragraphs[0]; p.text = body; p.font.size = Pt(11); p.font.color.rgb = LIGHT_GRAY

footer_line(sl, "Branding: Snowflake logotype SVG · 'Powered by Cortex Code' badge · Animated polar bear 🐻‍❄️ on all dashboards")


# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 9 — SNOWFLAKE FEATURES SHOWCASED
# ══════════════════════════════════════════════════════════════════════════════
sl = prs.slides.add_slide(LAY_CONTENT)
bg(sl); accent_bar(sl)
section_label(sl, "SNOWFLAKE FEATURES")
slide_title(sl, "Snowflake Platform Features in This Demo", sz=26)

features = [
    ("Snowpark Container Services",  "Docker container with public ingress, auto-resume, platform monitoring, ingress header injection",     MARIO_RED),
    ("SPCS Event Tables",           "Unified OTel store for spans, metrics, and logs — OTLP gRPC exporter from Python SDK",                SF_BLUE),
    ("Interactive Tables",          "Sub-second latency, 1-min target lag, cluster keys, Interactive Warehouse — real-time dashboards",    MARIO_GRN),
    ("Cortex AI — Analyst",         "Semantic View with 6 tables, FastGen-generated VQRs, natural language to SQL queries",                MARIO_PUR),
    ("Cortex AI — Agents",          "Custom orchestration tool, response instructions, MARIO_INTELLIGENCE agent over MARIO_TELEMETRY",     SF_BLUE),
    ("Streamlit in Snowsight",      "Container runtime, SYSTEM_COMPUTE_POOL_CPU, pip packages, snow CLI deployment",                      MARIO_YEL),
    ("Semi-structured JSON",        "record:name::STRING, record_attributes:player_name::STRING — variant extraction at query time",       MARIO_GRN),
]
for i, (title, desc, col) in enumerate(features):
    y = Inches(1.05 + i * 0.64)
    rect(sl, Inches(0.4), y, W - Inches(0.8), Inches(0.56), fill=CARD_BG, radius=0.03)
    rect(sl, Inches(0.4), y, Inches(0.1), Inches(0.56), fill=col)
    txt(sl, Inches(0.62), y + Inches(0.06), Inches(2.8), Inches(0.28), title, sz=13, color=col, bold=True)
    txt(sl, Inches(0.62), y + Inches(0.3), Inches(8.8), Inches(0.24), desc, sz=11, color=MED_GRAY)

footer_line(sl, "Zero external infrastructure · No extra accounts · All data stays in Snowflake")


# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 10 — DEMO DIVIDER
# ══════════════════════════════════════════════════════════════════════════════
sl = prs.slides.add_slide(LAY_DIVIDER)
bg(sl, RGBColor(0x06, 0x0D, 0x1A))

rect(sl, 0, 0, W, Inches(0.08), fill=MARIO_RED)
rect(sl, 0, H - Inches(0.08), W, Inches(0.08), fill=MARIO_RED)

txt(sl, Inches(0.7), Inches(0.9), W - Inches(1.4), Inches(0.45),
    "🎮  LIVE DEMO", sz=38, color=MARIO_RED, bold=True, align=PP_ALIGN.CENTER)

rect(sl, Inches(2), Inches(1.6), W - Inches(4), Inches(0.05), fill=MARIO_RED)

demo_steps = [
    "Open game URL · Press S to start · Play Mario 🍄",
    "Watch events flow → telemetry.js → sidecar → event table",
    "Refresh Streamlit dashboard · see your name in the leaderboard",
    "Ask Cortex Agent: 'Who died the most on level 1-1?'",
]
for i, step in enumerate(demo_steps):
    rect(sl, Inches(1.5), Inches(1.85 + i * 0.72), W - Inches(3.0), Inches(0.6), fill=CARD_BG, radius=0.05)
    txt(sl, Inches(1.5), Inches(1.88 + i * 0.72), Inches(0.55), Inches(0.55), str(i + 1), sz=22, color=MARIO_RED, bold=True, align=PP_ALIGN.CENTER)
    txt(sl, Inches(2.15), Inches(1.95 + i * 0.72), W - Inches(3.7), Inches(0.4), step, sz=14, color=WHITE)

txt(sl, Inches(0.5), H - Inches(0.7), W - Inches(1), Inches(0.4),
    "ei53mb-sfseeurope-eu-demo200.snowflakecomputing.app",
    sz=12, color=SF_BLUE, align=PP_ALIGN.CENTER, italic=True)


# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 11 — KEY LEARNINGS
# ══════════════════════════════════════════════════════════════════════════════
sl = prs.slides.add_slide(LAY_CONTENT)
bg(sl); accent_bar(sl)
section_label(sl, "KEY LEARNINGS")
slide_title(sl, "What Surprised Us Building This", sz=26)

learnings = [
    ("🐳", "Always --no-cache",
     "Docker silently reuses stale cached layers even when files change. suspend/resume does NOT re-pull the image — use ALTER SERVICE FROM SPECIFICATION.",
     MARIO_RED),
    ("📍", "nginx exact match matters",
     "location /telemetry is a prefix match — it catches /telemetry.js, routing your JS file to the Python sidecar. Always use location = /telemetry.",
     MARIO_YEL),
    ("👤", "Browser must send player_name",
     "The sidecar reads Sf-Context-Current-User but the browser JS was calling /whoami only for the banner — not including player_name in event payloads.",
     SF_BLUE),
    ("📦", "Bundle all dependencies",
     "SPCS blocks external egress. CDN URLs fail silently at runtime. Bundle jQuery and all JS libs inside the Docker image during build.",
     MARIO_GRN),
    ("🔑", "JWT for headless auth",
     "EXTERNALBROWSER auth doesn't work in headless Node.js (React API routes). Use SNOWFLAKE_JWT keypair. snow spcs image-registry login handles MFA.",
     MARIO_PUR),
]
for i, (icon, title, desc, col) in enumerate(learnings):
    row, col_idx = divmod(i, 3)
    x = Inches(0.35 + col_idx * 3.18)
    y = Inches(1.1 + row * 1.75)
    if i == 3:   x = Inches(0.35 + 0 * 3.18)
    if i == 4:   x = Inches(0.35 + 1 * 3.18)
    h = Inches(1.62)
    rect(sl, x, y, Inches(3.0), h, fill=CARD_BG, line=col, radius=0.05)
    rect(sl, x, y, Inches(3.0), Inches(0.05), fill=col)
    txt(sl, x + Inches(0.14), y + Inches(0.1), Inches(0.38), Inches(0.38), icon, sz=20)
    txt(sl, x + Inches(0.56), y + Inches(0.1), Inches(2.3), Inches(0.38), title, sz=13, color=col, bold=True)
    tb = sl.shapes.add_textbox(x + Inches(0.14), y + Inches(0.56), Inches(2.75), Inches(1.02))
    tf = tb.text_frame; tf.word_wrap = True
    p = tf.paragraphs[0]; p.text = desc; p.font.size = Pt(10); p.font.color.rgb = LIGHT_GRAY

footer_line(sl, "Full learnings documented in README.md and docs/index.html · github.com/sfc-gh-tdahlberg/mario-spcs-telemetry")


# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 12 — THANK YOU
# ══════════════════════════════════════════════════════════════════════════════
sl = prs.slides.add_slide(LAY_THANKYOU)
bg(sl, RGBColor(0x06, 0x0D, 0x1A))

rect(sl, 0, 0, W, Inches(0.08), fill=SF_BLUE)
rect(sl, 0, H - Inches(0.08), W, Inches(0.08), fill=SF_BLUE)

txt(sl, Inches(0.5), Inches(0.5), W - Inches(1), Inches(0.65),
    "Thanks for playing 🍄", sz=38, color=WHITE, bold=True, align=PP_ALIGN.CENTER)
txt(sl, Inches(0.5), Inches(1.22), W - Inches(1), Inches(0.38),
    "Questions? Let's talk about SPCS, Interactive Tables, Cortex AI, or anything else.",
    sz=15, color=MED_GRAY, align=PP_ALIGN.CENTER)

rect(sl, Inches(2), Inches(1.78), W - Inches(4), Inches(0.04), fill=SF_BLUE)

links = [
    ("🎮", "Game",           "ei53mb-sfseeurope-eu-demo200.snowflakecomputing.app", SF_BLUE),
    ("💻", "GitHub",         "github.com/sfc-gh-tdahlberg/mario-spcs-telemetry",   MARIO_GRN),
    ("📖", "HTML Docs",      "docs/index.html — full architecture reference",       MARIO_YEL),
    ("🤖", "Cortex Agent",   "DIS_MARIO.PUBLIC.MARIO_INTELLIGENCE in Snowsight",    MARIO_PUR),
]
for i, (icon, label, val, col) in enumerate(links):
    x = Inches(0.45 + i * 2.28)
    rect(sl, x, Inches(2.05), Inches(2.1), Inches(1.2), fill=CARD_BG, line=col, radius=0.06)
    txt(sl, x, Inches(2.15), Inches(2.1), Inches(0.45), icon, sz=22, align=PP_ALIGN.CENTER)
    txt(sl, x + Inches(0.1), Inches(2.62), Inches(1.92), Inches(0.26), label, sz=13, color=col, bold=True, align=PP_ALIGN.CENTER)
    txt(sl, x + Inches(0.06), Inches(2.9), Inches(2.0), Inches(0.35), val, sz=8, color=MED_GRAY, align=PP_ALIGN.CENTER)

txt(sl, Inches(0.5), Inches(3.45), W - Inches(1), Inches(0.5),
    "Built entirely with ✨ Cortex Code · Snowflake Solutions Engineering",
    sz=13, color=MED_GRAY, align=PP_ALIGN.CENTER, italic=True)


# ── Save ─────────────────────────────────────────────────────────────────────
prs.save(OUTPUT)
print(f"✅  Saved → {OUTPUT}")
print(f"   Slides: {len(prs.slides)}")
