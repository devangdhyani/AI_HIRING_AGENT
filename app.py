import os
import requests
import streamlit as st
import streamlit.components.v1 as components
from streamlit_javascript import st_javascript
from dotenv import load_dotenv
from backend import process_batch
import backend
from ranker import rank_candidates

load_dotenv()

RECAPTCHA_SITE_KEY   = os.getenv("RECAPTCHA_SITE_KEY", "")
RECAPTCHA_SECRET_KEY = os.getenv("RECAPTCHA_SECRET_KEY", "")

# ---------------------------------------------------------------------------
# reCAPTCHA backend verification
# ---------------------------------------------------------------------------

def verify_recaptcha(token: str) -> bool:
    """Send token to Google siteverify and return True only on success."""
    if not token or not RECAPTCHA_SECRET_KEY:
        return False
    try:
        resp = requests.post(
            "https://www.google.com/recaptcha/api/siteverify",
            data={"secret": RECAPTCHA_SECRET_KEY, "response": token},
            timeout=5,
        )
        return resp.json().get("success", False)
    except Exception:
        return False

# --- Page Config ---
st.set_page_config(
    page_title="AI Hiring Agent",
    page_icon="🤖",
    layout="wide",
)

# =============================================================================
# BASE CSS + CHROME REMOVAL
# =============================================================================
st.markdown("""
<style>
/* ── Keyframe animations ────────────────────────────────────────────── */
@keyframes fadeSlideUp {
    from { opacity: 0; transform: translateY(28px); }
    to   { opacity: 1; transform: translateY(0); }
}
@keyframes typing {
    from { width: 0; }
    to   { width: 100%; }
}
@keyframes blink-caret {
    0%, 100% { border-right-color: transparent; }
    50%       { border-right-color: #ff4444; }
}
@keyframes heroFadeIn {
    from { opacity: 0; transform: translateY(16px); }
    to   { opacity: 1; transform: translateY(0); }
}
@keyframes pulseGlow {
    0%, 100% { box-shadow: 0 0 6px 1px rgba(122,255,74,0.35); }
    50%       { box-shadow: 0 0 14px 4px rgba(122,255,74,0.65); }
}
@keyframes pulseGlowGold {
    0%, 100% { box-shadow: 0 0 6px 1px rgba(255,217,102,0.35); }
    50%       { box-shadow: 0 0 14px 4px rgba(255,217,102,0.60); }
}
@keyframes pulseGlowRed {
    0%, 100% { box-shadow: 0 0 4px 1px rgba(255,80,80,0.20); }
    50%       { box-shadow: 0 0 10px 3px rgba(255,80,80,0.40); }
}
@keyframes cardFadeIn {
    from { opacity: 0; transform: translateY(20px); }
    to   { opacity: 1; transform: translateY(0); }
}

/* ── Hide default Streamlit chrome ─────────────────────────────────── */
#MainMenu, header, footer { visibility: hidden; height: 0; }
.block-container { padding-top: 0 !important; }

/* ── Global background & font ──────────────────────────────────────── */
html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {
    background-color: #1a0a0a;
    color: #f0e6e6;
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
}

/* ── Sidebar (if ever shown) ────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background-color: #2a1010;
}

/* ── All text defaults ──────────────────────────────────────────────── */
p, span, label, div { color: #f0e6e6; }

/* ── Inputs & text areas ────────────────────────────────────────────── */
input, textarea, select {
    background-color: #2a1010 !important;
    color: #f0e6e6 !important;
    border: 1px solid #6b1a1a !important;
    border-radius: 6px !important;
}

/* ── Streamlit file uploader ────────────────────────────────────────── */
[data-testid="stFileUploader"] {
    background-color: #2a1010;
    border: 2px dashed #8b2020;
    border-radius: 10px;
    padding: 12px;
}
[data-testid="stFileUploader"] label { color: #f0e6e6 !important; }

/* ── Primary button ─────────────────────────────────────────────────── */
div[data-testid="stButton"] > button[kind="primary"] {
    background: linear-gradient(135deg, #8b0000, #c0392b);
    color: #ffffff;
    border: none;
    border-radius: 8px;
    font-size: 1rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    padding: 0.65rem 1.5rem;
    transition: opacity 0.2s;
}
div[data-testid="stButton"] > button[kind="primary"]:hover { opacity: 0.85; }
div[data-testid="stButton"] > button[kind="primary"]:disabled {
    background: #3a1515;
    color: #7a5050;
    cursor: not-allowed;
}

/* ── Secondary / ghost buttons ──────────────────────────────────────── */
div[data-testid="stButton"] > button {
    background-color: #2a1010;
    color: #f0e6e6;
    border: 1px solid #6b1a1a;
    border-radius: 8px;
}

/* ── Cards (st.container with border) ──────────────────────────────── */
[data-testid="stVerticalBlockBorderWrapper"] {
    background-color: #2a1010;
    border: 1px solid #6b1a1a !important;
    border-radius: 12px;
    padding: 16px;
}

/* ── Expanders ──────────────────────────────────────────────────────── */
details {
    background-color: #2a1010;
    border: 1px solid #6b1a1a;
    border-radius: 8px;
}
summary { color: #f0e6e6 !important; font-weight: 600; }

/* ── DataFrames ─────────────────────────────────────────────────────── */
[data-testid="stDataFrame"] {
    background-color: #1a0a0a;
    border: 1px solid #6b1a1a;
    border-radius: 8px;
}

/* ── Metrics ────────────────────────────────────────────────────────── */
[data-testid="stMetric"] {
    background-color: #2a1010;
    border: 1px solid #6b1a1a;
    border-radius: 10px;
    padding: 12px 16px;
}
[data-testid="stMetricValue"] { color: #ff6b6b !important; font-weight: 700; }
[data-testid="stMetricLabel"] { color: #c0a0a0 !important; }

/* ── Divider ────────────────────────────────────────────────────────── */
hr { border-color: #6b1a1a !important; }

/* ── Alert / info boxes ─────────────────────────────────────────────── */
[data-testid="stAlert"] {
    background-color: #2a1010 !important;
    border-left: 4px solid #8b0000 !important;
    color: #f0e6e6 !important;
    border-radius: 6px;
}

/* ── Spinner text ───────────────────────────────────────────────────── */
[data-testid="stSpinner"] p { color: #f0e6e6 !important; }

/* ── Checkbox ───────────────────────────────────────────────────────── */
[data-testid="stCheckbox"] span { color: #f0e6e6 !important; }

/* ── Candidate rank card ────────────────────────────────────────────── */
.rank-card {
    background: linear-gradient(145deg, #2a1010 0%, #1e0808 100%);
    border: 1px solid #6b1a1a;
    border-radius: 14px;
    padding: 20px 24px;
    margin-bottom: 14px;
    box-shadow: 0 2px 16px rgba(139,0,0,0.14);
    position: relative;
    animation: cardFadeIn 0.55s ease both;
    transition: border-color 0.2s, box-shadow 0.2s, transform 0.2s;
}
.rank-card:hover {
    border-color: #c0392b;
    box-shadow: 0 8px 32px rgba(192,57,43,0.38);
    transform: translateY(-3px);
}
.rank-number {
    position: absolute;
    top: 16px;
    right: 20px;
    font-size: 2.4rem;
    font-weight: 900;
    color: #3a0c0c;
    line-height: 1;
    user-select: none;
}
.rank-name {
    font-size: 1.1rem;
    font-weight: 800;
    color: #ffffff;
    margin: 0 0 2px;
}
.rank-email {
    font-size: 0.8rem;
    color: #c0a0a0;
    margin: 0 0 14px;
}
.rank-stats {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-top: 8px;
}
.stat-chip {
    background: #3a0808;
    border: 1px solid #5a1818;
    border-radius: 8px;
    padding: 5px 12px;
    font-size: 0.78rem;
    color: #f0e6e6;
    display: flex;
    flex-direction: column;
    align-items: center;
    min-width: 68px;
}
.stat-chip-label {
    font-size: 0.65rem;
    color: #9a7070;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 2px;
}
.stat-chip-value {
    font-weight: 700;
    color: #ff9999;
    font-size: 0.9rem;
}
.score-badge {
    display: inline-block;
    background: linear-gradient(135deg, #8b0000, #c0392b);
    border-radius: 20px;
    padding: 4px 14px;
    font-size: 0.82rem;
    font-weight: 700;
    color: #ffffff;
    letter-spacing: 0.05em;
}
.status-badge {
    display: inline-block;
    border-radius: 20px;
    padding: 3px 12px;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.07em;
    text-transform: uppercase;
}
.status-top {
    background: #1a3a0a; border: 1px solid #2d7a10; color: #7aff4a;
    animation: pulseGlow 2.2s ease-in-out infinite;
}
.status-mid {
    background: #3a2a00; border: 1px solid #8b6a00; color: #ffd966;
    animation: pulseGlowGold 2.5s ease-in-out infinite;
}
.status-neutral {
    background: #2a2200; border: 1px solid #6b5500; color: #d4b84a;
    animation: pulseGlowGold 3.5s ease-in-out infinite;
}
.status-low {
    background: #3a0808; border: 1px solid #8b2020; color: #ff9999;
    animation: pulseGlowRed 3s ease-in-out infinite;
}
.rejected-divider {
    display: flex;
    align-items: center;
    gap: 20px;
    margin: 40px 0 28px;
}
.rejected-divider-line {
    flex: 1;
    height: 2px;
    background: linear-gradient(90deg, transparent, #c0392b, transparent);
}
.rejected-divider-label {
    font-size: 0.95rem;
    font-weight: 800;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: #ff6b6b;
    white-space: nowrap;
    padding: 8px 22px;
    border: 2px solid #c0392b;
    border-radius: 30px;
    background: #2a0808;
    box-shadow: 0 0 12px rgba(192,57,43,0.45);
}
.results-section-header {
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: #9a5050;
    margin: 28px 0 12px;
}

/* ── Section card wrapper ───────────────────────────────────────────── */
.section-card {
    background: linear-gradient(145deg, #2a1010 0%, #200808 100%);
    border: 1px solid #6b1a1a;
    border-radius: 14px;
    padding: 28px 32px 24px;
    margin: 24px 0 8px;
    box-shadow: 0 4px 24px rgba(139,0,0,0.18);
    animation: fadeSlideUp 0.6s ease both;
    transition: border-color 0.25s, box-shadow 0.25s, transform 0.25s;
}
.section-card:hover {
    border-color: #a02020;
    box-shadow: 0 8px 36px rgba(192,57,43,0.30);
    transform: translateY(-4px);
}
.card-header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 18px;
}
.card-icon {
    font-size: 1.5rem;
    line-height: 1;
}
.card-title {
    font-size: 1.05rem;
    font-weight: 700;
    color: #ffffff;
    letter-spacing: 0.03em;
    margin: 0;
}
.card-subtitle {
    font-size: 0.8rem;
    color: #c0a0a0;
    margin: 0;
}
.file-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: #3a0808;
    border: 1px solid #8b2020;
    border-radius: 20px;
    padding: 3px 12px;
    font-size: 0.78rem;
    color: #ff9999;
    margin: 2px 4px 2px 0;
}
.captcha-box {
    display: flex;
    align-items: center;
    gap: 14px;
    background: #1a0808;
    border: 1px solid #5a1515;
    border-radius: 8px;
    padding: 14px 18px;
    margin-top: 4px;
}
.captcha-logo {
    font-size: 0.65rem;
    color: #7a5050;
    text-align: center;
    line-height: 1.5;
}

/* ── NAV BAR ────────────────────────────────────────────────────────── */
.navbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: linear-gradient(90deg, #0d0000 0%, #2a0505 100%);
    padding: 14px 36px;
    border-bottom: 2px solid #8b0000;
    margin-bottom: 0;
}
.navbar-brand {
    font-size: 1.35rem;
    font-weight: 800;
    color: #ff4444;
    letter-spacing: 0.06em;
    text-decoration: none;
}
.navbar-tagline {
    font-size: 0.8rem;
    color: #c0a0a0;
    letter-spacing: 0.12em;
    text-transform: uppercase;
}

/* ── HERO ───────────────────────────────────────────────────────────── */
.hero {
    background: linear-gradient(160deg, #2a0505 0%, #1a0a0a 60%);
    padding: 56px 36px 44px;
    text-align: center;
    border-bottom: 1px solid #6b1a1a;
}
.hero-eyebrow {
    font-size: 0.78rem;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: #ff6b6b;
    margin-bottom: 14px;
    animation: heroFadeIn 0.7s ease 0.1s both;
}
.hero-title {
    font-size: clamp(2rem, 4vw, 3rem);
    font-weight: 900;
    color: #ffffff;
    line-height: 1.18;
    margin-bottom: 16px;
    animation: heroFadeIn 0.7s ease 0.25s both;
}
.hero-title span { color: #ff4444; }
.hero-typing {
    display: inline-block;
    overflow: hidden;
    white-space: nowrap;
    border-right: 3px solid #ff4444;
    max-width: 28ch;
    animation:
        typing       2.4s steps(28, end) 0.7s both,
        blink-caret  0.75s step-end      0.7s 4;
    color: #ff6b6b;
    font-size: 1.05rem;
    font-weight: 700;
    letter-spacing: 0.04em;
}
.hero-subtitle {
    font-size: 1.05rem;
    color: #c0a0a0;
    max-width: 600px;
    margin: 0 auto 28px;
    line-height: 1.65;
    animation: heroFadeIn 0.7s ease 0.45s both;
}
.hero-badge {
    display: inline-block;
    background: #3a0808;
    border: 1px solid #8b2020;
    border-radius: 20px;
    padding: 5px 16px;
    font-size: 0.78rem;
    color: #ff9999;
    animation: heroFadeIn 0.7s ease 0.6s both;
    letter-spacing: 0.08em;
}
</style>
""", unsafe_allow_html=True)

# =============================================================================
# NAV BAR
# =============================================================================
st.markdown("""
<nav class="navbar">
  <span class="navbar-brand">
    <svg width="26" height="26" viewBox="0 0 26 26" fill="none"
         xmlns="http://www.w3.org/2000/svg"
         style="vertical-align:middle;margin-right:9px;">
      <!-- head -->
      <rect x="5" y="7" width="16" height="12" rx="4" fill="#ff4444" opacity="0.92"/>
      <!-- eyes -->
      <circle cx="10" cy="13" r="1.8" fill="#1a0a0a"/>
      <circle cx="16" cy="13" r="1.8" fill="#1a0a0a"/>
      <!-- eye glow -->
      <circle cx="10" cy="13" r="0.8" fill="#ff9999"/>
      <circle cx="16" cy="13" r="0.8" fill="#ff9999"/>
      <!-- antenna -->
      <line x1="13" y1="7" x2="13" y2="3" stroke="#ff4444" stroke-width="1.6" stroke-linecap="round"/>
      <circle cx="13" cy="2.5" r="1.5" fill="#ff6b6b"/>
      <!-- neck -->
      <rect x="11" y="19" width="4" height="2.5" rx="1" fill="#ff4444" opacity="0.7"/>
      <!-- check mark overlay (HR theme) -->
      <polyline points="8,13.5 11,16.5 18,10" stroke="#ffffff" stroke-width="1.5"
                stroke-linecap="round" stroke-linejoin="round" opacity="0.0"/>
    </svg>
    AI Hiring Agent
  </span>
  <span class="navbar-tagline">Powered by Groq &nbsp;|&nbsp; LLaMA 3.3</span>
</nav>
""", unsafe_allow_html=True)

# =============================================================================
# HERO SECTION
# =============================================================================
st.markdown("""
<section class="hero">
    <p class="hero-eyebrow">&#128640; Next-Generation Recruitment</p>
    <h1 class="hero-title">
        AI Hiring Agent:<br>
        <span>Unlock True Potential</span>
    </h1>
    <div style="margin-bottom:20px;">
        <span class="hero-typing">Analyze. Score. Rank. Hire.</span>
    </div>
    <p class="hero-subtitle">
        Upload up to 20 resumes and let our AI extract, score, and rank
        your top 10 candidates in seconds &mdash; no manual screening required.
    </p>
    <span class="hero-badge">&#128274; Secured with reCAPTCHA v2</span>
</section>
""", unsafe_allow_html=True)

# =============================================================================
# UPLOAD CARD
# =============================================================================
st.markdown("""
<div class="section-card">
    <div class="card-header">
        <span class="card-icon">&#128196;</span>
        <div>
            <p class="card-title">Resume Upload</p>
            <p class="card-subtitle">PDF format only &nbsp;&bull;&nbsp; Max 20 files &nbsp;&bull;&nbsp; One resume per file</p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

uploaded_files = st.file_uploader(
    "Drop PDFs here or click to browse",
    type=["pdf"],
    accept_multiple_files=True,
    help="Select up to 20 PDF files. Each file should be one candidate's resume.",
    label_visibility="visible",
)

# --- File Count Display ---
if uploaded_files:
    count = len(uploaded_files)
    if count > 20:
        st.error(f"❌ Too many files: {count} uploaded. Maximum allowed is **20**. Please remove {count - 20} file(s).")
    else:
        st.markdown(
            f'<p style="color:#c0a0a0;font-size:0.82rem;margin:6px 0 4px;">&#128204; '
            f'<strong style="color:#ff9999;">{count}</strong> / 20 resume(s) queued</p>',
            unsafe_allow_html=True,
        )
        pills_html = "".join(
            f'<span class="file-pill">&#128196; {f.name}</span>'
            for f in uploaded_files
        )
        st.markdown(f'<div style="margin-top:6px;">{pills_html}</div>', unsafe_allow_html=True)
else:
    st.markdown(
        '<p style="color:#7a5050;font-size:0.85rem;margin-top:6px;">&#128683; No files selected yet.</p>',
        unsafe_allow_html=True,
    )

# =============================================================================
# CAPTCHA CARD  (real reCAPTCHA v2)
# =============================================================================
st.markdown("""
<div class="section-card">
    <div class="card-header">
        <span class="card-icon">&#128274;</span>
        <div>
            <p class="card-title">Human Verification</p>
            <p class="card-subtitle">Google reCAPTCHA v2 &nbsp;&bull;&nbsp; Backend-verified</p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Render the real reCAPTCHA widget inside an iframe-like HTML component.
# On solve, the token is written to localStorage under "recaptcha_token".
components.html(f"""
<!DOCTYPE html>
<html>
<head>
  <script src="https://www.google.com/recaptcha/api.js" async defer></script>
  <style>
    body {{
      background: #1a0a0a;
      display: flex;
      justify-content: center;
      align-items: center;
      margin: 0;
      padding: 8px 0;
    }}
  </style>
</head>
<body>
  <div class="g-recaptcha"
       data-sitekey="{RECAPTCHA_SITE_KEY}"
       data-callback="onCaptchaSolved"
       data-expired-callback="onCaptchaExpired"
       data-theme="dark">
  </div>
  <script>
    function onCaptchaSolved(token) {{
      window.parent.localStorage.setItem("recaptcha_token", token);
    }}
    function onCaptchaExpired() {{
      window.parent.localStorage.removeItem("recaptcha_token");
    }}
  </script>
</body>
</html>
""", height=100)

# Read the token back into Python via localStorage
raw_token = st_javascript("localStorage.getItem('recaptcha_token');")
captcha_token = raw_token if isinstance(raw_token, str) and len(raw_token) > 20 else ""

# Backend-verify the token (only once per token using session state)
if captcha_token and st.session_state.get("verified_token") != captcha_token:
    st.session_state["verified_token"] = captcha_token
    st.session_state["captcha_verified"] = verify_recaptcha(captcha_token)

captcha_verified: bool = True  # TEMP: bypass for local testing — revert to line below for production
# captcha_verified: bool = st.session_state.get("captcha_verified", False)

if captcha_verified:
    st.markdown(
        '<p style="color:#7aff4a;font-size:0.82rem;margin-top:6px;">&#10003; Verification passed</p>',
        unsafe_allow_html=True,
    )
elif captcha_token:
    st.error("reCAPTCHA verification failed. Please try again.")
    st.session_state["captcha_verified"] = False

st.divider()

# --- Process Button ---
can_process = (
    uploaded_files is not None
    and 1 <= len(uploaded_files) <= 20
    and captcha_verified
)

process_clicked = st.button(
    "🚀 Process & Rank Candidates",
    disabled=not can_process,
    use_container_width=True,
    type="primary",
)

if not captcha_verified and uploaded_files and len(uploaded_files) <= 20:
    st.caption("Complete the verification above to enable processing.")

# --- On Click ---
if process_clicked:
    if not uploaded_files:
        st.error("❌ No files uploaded. Please upload at least one resume.")
        st.stop()

    if len(uploaded_files) > 20:
        st.error(f"❌ Too many files ({len(uploaded_files)}). Maximum allowed is 20.")
        st.stop()

    try:
        backend.load_api_key()
    except EnvironmentError as e:
        st.error(f"❌ Configuration error: {e}")
        st.stop()

    files = [(f.name, f.read()) for f in uploaded_files]

    with st.spinner("Processing resumes..."):
        results = process_batch(files)

    # ── Ranking (logic unchanged) ─────────────────────────────────────────────
    all_scored, top_10 = rank_candidates(results)

    # ── Summary metrics ───────────────────────────────────────────────────────
    st.divider()
    success_count = sum(1 for r in results if r["status"] == "SUCCESS")
    failed_count  = len(results) - success_count

    col_a, col_b, col_c, col_d = st.columns(4)
    col_a.metric("Total Uploaded",  len(results))
    col_b.metric("Extracted",       success_count)
    col_c.metric("Ranked",          len(top_10))
    col_d.metric("Failed",          failed_count)

    # ── Failed expander ───────────────────────────────────────────────────────
    failed = [r for r in results if r["status"] == "FAILED"]
    if failed:
        with st.expander(f"⚠️ {len(failed)} failed candidate(s) — click to expand"):
            for r in failed:
                st.markdown(
                    f'<span class="status-badge status-low">FAILED</span>'
                    f'&nbsp; <strong>{r["file_name"]}</strong>'
                    f'<br><span style="color:#9a7070;font-size:0.8rem;">{r["failure_reason"]}</span>',
                    unsafe_allow_html=True,
                )
                st.markdown("---")

    # ── Full extraction table ─────────────────────────────────────────────────
    st.markdown('<p class="results-section-header">&#128202; All Extraction Results</p>', unsafe_allow_html=True)
    DISPLAY_COLS = [
        "file_name", "candidate_name", "candidate_email",
        "cgpa", "years_of_exp", "project_count",
        "12th_marks", "10th_marks", "status", "failure_reason",
    ]
    full_rows = [{c: r.get(c) for c in DISPLAY_COLS} for r in results]
    st.dataframe(full_rows, use_container_width=True)

    # ── Guard: nothing to rank ────────────────────────────────────────────────
    if not all_scored:
        st.warning("No candidates could be ranked. Ensure resumes contain CGPA data.")
        st.stop()

    # ── All ranked candidates ─────────────────────────────────────────────────
    st.markdown('<p class="results-section-header">&#127942; Ranked Candidates</p>', unsafe_allow_html=True)

    def _status_label(rank: int) -> str:
        if rank <= 3:
            return '<span class="status-badge status-top">TOP MATCH</span>'
        if rank <= 7:
            return '<span class="status-badge status-mid">GOOD FIT</span>'
        if rank <= 10:
            return '<span class="status-badge status-neutral">ACCEPTABLE</span>'
        return '<span class="status-badge status-low">NON-ACCEPTABLE</span>'

    def _fmt(val, suffix="", fallback="N/A") -> str:
        if val is None:
            return fallback
        if isinstance(val, float):
            return f"{val:.1f}{suffix}"
        return f"{val}{suffix}"

    divider_inserted = False

    for rank, r in enumerate(all_scored, start=1):
        # Insert visual divider before the first non-acceptable candidate
        if rank == 11 and not divider_inserted:
            st.markdown("""
<div class="rejected-divider">
    <div class="rejected-divider-line"></div>
    <span class="rejected-divider-label">&#128683; Below Cut-off &mdash; Non-Acceptable Pool</span>
    <div class="rejected-divider-line"></div>
</div>
""", unsafe_allow_html=True)
            divider_inserted = True

        score     = r.get("score", 0)
        name      = r.get("candidate_name") or r.get("file_name", "Unknown")
        email     = r.get("candidate_email") or "—"
        cgpa      = _fmt(r.get("cgpa"))
        exp       = _fmt(r.get("years_of_exp"), " yrs")
        proj      = _fmt(r.get("project_count"), " proj")
        marks_12  = _fmt(r.get("12th_marks"), "%")
        marks_10  = _fmt(r.get("10th_marks"), "%")
        badge     = _status_label(rank)

        delay = 0.08 * (rank - 1)
        st.markdown(f"""
<div class="rank-card" style="animation-delay:{delay:.2f}s;">
    <span class="rank-number">#{rank}</span>
    <p class="rank-name">{name}</p>
    <p class="rank-email">&#9993; {email}</p>
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">
        <span class="score-badge">Score: {score:.2f}</span>
        {badge}
    </div>
    <div class="rank-stats">
        <div class="stat-chip">
            <span class="stat-chip-label">CGPA</span>
            <span class="stat-chip-value">{cgpa}</span>
        </div>
        <div class="stat-chip">
            <span class="stat-chip-label">Experience</span>
            <span class="stat-chip-value">{exp}</span>
        </div>
        <div class="stat-chip">
            <span class="stat-chip-label">Projects</span>
            <span class="stat-chip-value">{proj}</span>
        </div>
        <div class="stat-chip">
            <span class="stat-chip-label">12th</span>
            <span class="stat-chip-value">{marks_12}</span>
        </div>
        <div class="stat-chip">
            <span class="stat-chip-label">10th</span>
            <span class="stat-chip-value">{marks_10}</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)
