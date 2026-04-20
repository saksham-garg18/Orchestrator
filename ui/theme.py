STREAMLIT_THEME_CSS = """
<style>
/* ── Colour tokens ─────────────────────────────────────────────── */
:root {
    --bg0:      #060e16;
    --bg1:      #081726;
    --bg2:      #0a2240;
    --bg3:      #103672;
    --cyan:     #5ee7ff;
    --blue:     #2f6bff;
    --royal:    #1a34b8;
    --red:      #7e1d2f;
    --red-glow: rgba(126, 29, 47, 0.22);
    --text:     #e6f2ff;
    --muted:    #a0bcd8;
    --border:   rgba(94, 231, 255, 0.16);
}

/* ── App background ────────────────────────────────────────────── */
.stApp {
    background:
        radial-gradient(ellipse 80% 40% at 0% 0%,
            rgba(94,231,255,0.09), transparent),
        radial-gradient(ellipse 60% 30% at 100% 0%,
            rgba(47,107,255,0.11), transparent),
        radial-gradient(ellipse 55% 28% at 50% 105%,
            rgba(126,29,47,0.10), transparent),
        linear-gradient(160deg,
            var(--bg0) 0%,
            var(--bg1) 30%,
            var(--bg2) 65%,
            var(--royal) 100%);
    color: var(--text) !important;
}

/* ── Sidebar ───────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg,
        rgba(6,14,22,0.97) 0%,
        rgba(10,34,64,0.93) 100%) !important;
    border-right: 1px solid var(--border);
}
[data-testid="stSidebar"] * { color: var(--muted) !important; }
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 { color: var(--cyan) !important; }

/* ── Header bar ────────────────────────────────────────────────── */
[data-testid="stHeader"] {
    background: rgba(6,14,22,0.55) !important;
    backdrop-filter: blur(12px);
    border-bottom: 1px solid var(--border);
}

/* ── Typography ────────────────────────────────────────────────── */
h1 { color: var(--cyan)  !important; letter-spacing: -0.5px; }
h2 { color: var(--text)  !important; }
h3 { color: var(--muted) !important; }
p, li, label, div, span { color: var(--text) !important; }
.stCaption { color: var(--muted) !important; }

/* ── Buttons ───────────────────────────────────────────────────── */
.stButton > button,
.stDownloadButton > button {
    background: linear-gradient(135deg, var(--cyan) 0%, var(--blue) 100%);
    color: #020e18 !important;
    border: none;
    border-radius: 14px;
    font-weight: 700;
    letter-spacing: 0.3px;
    box-shadow: 0 6px 28px rgba(47,107,255,0.30);
    transition: box-shadow 0.18s ease, transform 0.15s ease;
}
.stButton > button:hover,
.stDownloadButton > button:hover {
    box-shadow: 0 10px 36px rgba(47,107,255,0.48);
    transform: translateY(-1px);
}
.stButton > button:active {
    transform: translateY(0);
    box-shadow: 0 4px 16px rgba(47,107,255,0.22);
}

/* ── Inputs & selects ──────────────────────────────────────────── */
.stTextInput input,
.stNumberInput input,
.stTextArea textarea,
.stSelectbox div[data-baseweb="select"] > div {
    background: rgba(8,23,38,0.78) !important;
    color: var(--text) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px;
}
.stSelectbox div[data-baseweb="select"] svg { fill: var(--muted); }

/* ── Sliders ───────────────────────────────────────────────────── */
[data-testid="stSlider"] div[role="slider"] {
    background: var(--cyan) !important;
    box-shadow: 0 0 8px var(--cyan);
}
[data-testid="stSlider"] div[data-testid="stSliderTrackFill"] {
    background: linear-gradient(90deg, var(--blue), var(--cyan)) !important;
}

/* ── File uploader ─────────────────────────────────────────────── */
div[data-testid="stFileUploader"] {
    background: rgba(8,23,38,0.55);
    border: 1.5px dashed rgba(94,231,255,0.32);
    border-radius: 18px;
    padding: 1rem;
    transition: border-color 0.2s;
}
div[data-testid="stFileUploader"]:hover {
    border-color: rgba(94,231,255,0.65);
}

/* ── Metrics ───────────────────────────────────────────────────── */
[data-testid="stMetric"] {
    background: rgba(8,23,38,0.60);
    border: 1px solid var(--border);
    border-radius: 18px;
    padding: 0.9rem 1rem;
    box-shadow:
        0 2px 12px rgba(0,0,0,0.18),
        inset 0 1px 0 rgba(94,231,255,0.07),
        inset 0 -1px 0 var(--red-glow);
}
[data-testid="stMetricLabel"] { color: var(--muted) !important; }
[data-testid="stMetricValue"] { color: var(--cyan)  !important; font-weight: 700; }

/* ── Checkboxes / radios ───────────────────────────────────────── */
.stCheckbox label, .stRadio label { color: var(--muted) !important; }
.stCheckbox input:checked + span,
.stRadio    input:checked + span { color: var(--cyan) !important; }

/* ── Divider ───────────────────────────────────────────────────── */
hr { border-color: rgba(94,231,255,0.14) !important; }

/* ── Expander ──────────────────────────────────────────────────── */
details {
    background: rgba(8,23,38,0.55);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 0.5rem 0.8rem;
}

/* ── Custom utility cards ──────────────────────────────────────── */
.af-card {
    background: linear-gradient(180deg,
        rgba(10,28,48,0.82),
        rgba(7,16,30,0.90));
    border: 1px solid var(--border);
    border-bottom: 1px solid var(--red-glow);
    border-radius: 22px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.8rem;
    box-shadow:
        0 12px 38px rgba(0,0,0,0.22),
        inset 0 1px 0 rgba(94,231,255,0.07);
}

.af-pill {
    display: inline-block;
    background: rgba(94,231,255,0.12);
    border: 1px solid rgba(94,231,255,0.28);
    border-radius: 99px;
    padding: 0.18rem 0.7rem;
    font-size: 0.78rem;
    color: var(--cyan) !important;
    letter-spacing: 0.3px;
}

.af-warn {
    color: var(--red) !important;
    background: var(--red-glow);
    border-left: 3px solid var(--red);
    border-radius: 0 8px 8px 0;
    padding: 0.4rem 0.8rem;
    font-size: 0.85rem;
}
</style>
"""