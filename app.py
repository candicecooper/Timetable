"""
CLC Timetable — Cowandilla Learning Centre
==========================================
- PyMuPDF (fitz) for PDF rendering — no poppler needed
- Per-program tabs: General, JP, PY, SY
- Auto term/week display in header
- Admin: upload, delete old versions
- Mobile-responsive layout
"""

import streamlit as st
import base64
from datetime import datetime, timezone, date
from io import BytesIO

st.set_page_config(
    page_title="CLC Timetable",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── SA School Calendar 2026 ───────────────────────────────────────────────────
# (term_number, first_monday, total_weeks)
SA_TERMS = [
    (1, date(2026, 1, 26), 11),
    (2, date(2026, 4, 27), 10),
    (3, date(2026, 7, 20), 10),
    (4, date(2026, 10, 12), 9),
]

def get_term_week_label() -> str:
    """Return e.g. 'Term 1 · Week 5' or 'School Holidays' based on today's date."""
    today = date.today()
    for term_num, first_mon, total_weeks in SA_TERMS:
        term_end = date.fromordinal(first_mon.toordinal() + total_weeks * 7 - 1)
        if first_mon <= today <= term_end:
            week_num = (today - first_mon).days // 7 + 1
            return f"Term {term_num}  ·  Week {week_num}"
    # Check if before first term
    if today < SA_TERMS[0][1]:
        return "Week 0 — Pre-Term"
    return "School Holidays"

# ── Supabase ──────────────────────────────────────────────────────────────────
@st.cache_resource
def get_client():
    from supabase import create_client
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

PROGRAMS = ["General", "JP", "PY", "SY"]
PROGRAM_LABELS = {
    "General": "📋 All Staff",
    "JP":      "🟢 Junior Primary",
    "PY":      "🔵 Primary Years",
    "SY":      "🟣 Senior Years",
}

def get_timetable(program: str):
    """Return the latest timetable row for a given program."""
    try:
        result = (
            get_client()
            .table("timetable_store")
            .select("*")
            .eq("program", program)
            .order("uploaded_at", desc=True)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None
    except Exception as e:
        st.error(f"Database error: {e}")
        return None

def get_all_timetables(program: str):
    """Return all rows for a program (id + meta, no file_data) ordered newest first."""
    try:
        result = (
            get_client()
            .table("timetable_store")
            .select("id, filename, label, uploaded_by, uploaded_at, program")
            .eq("program", program)
            .order("uploaded_at", desc=True)
            .execute()
        )
        return result.data or []
    except Exception:
        return []

def save_timetable(filename, file_b64, label, program, uploaded_by="Admin"):
    try:
        get_client().table("timetable_store").insert({
            "filename":    filename,
            "file_data":   file_b64,
            "label":       label,
            "program":     program,
            "uploaded_by": uploaded_by,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
        }).execute()
        return True
    except Exception as e:
        st.error(f"Save failed: {e}")
        return False

def delete_timetable(row_id: int):
    try:
        get_client().table("timetable_store").delete().eq("id", row_id).execute()
        return True
    except Exception as e:
        st.error(f"Delete failed: {e}")
        return False

def verify_admin(password: str) -> bool:
    return password == st.secrets.get("ADMIN_PASSWORD", "CLC2026admin")

def fmt_date(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%-d %b %Y, %-I:%M %p")
    except Exception:
        return iso or ""

# ── PDF rendering via PyMuPDF (no poppler required) ───────────────────────────
def pdf_to_images(pdf_bytes: bytes) -> list | None:
    """Convert PDF bytes → list of base64 PNG strings via PyMuPDF."""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        images = []
        for page in doc:
            mat = fitz.Matrix(2.0, 2.0)   # 2× scale ≈ 150 dpi equivalent
            pix = page.get_pixmap(matrix=mat, alpha=False)
            images.append(base64.b64encode(pix.tobytes("png")).decode())
        doc.close()
        return images
    except Exception:
        return None

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Serif+Display&display=swap');
*,*::before,*::after{box-sizing:border-box}
:root{
  --navy:#1a2e44;--navy-mid:#2d4f72;--navy-light:#e8edf3;--navy-border:#c5d3e0;
  --green:#059669;--green-light:#d1fae5;
  --red:#dc2626;--red-light:#fee2e2;
  --white:#ffffff;--bg:#f4f6f9;--ink:#1a2332;--ink-light:#6b7f94;--radius:12px
}
html,body,[class*="css"]{font-family:'DM Sans',sans-serif!important;background:var(--bg)!important}
.block-container{padding:0!important;max-width:100%!important}
header{display:none!important}

/* ── Header ── */
.app-header{
  background:linear-gradient(135deg,var(--navy) 0%,var(--navy-mid) 100%);
  padding:22px 32px;
  display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;
}
.app-header-left{display:flex;align-items:center;gap:14px}
.app-header-icon{
  width:44px;height:44px;min-width:44px;
  background:rgba(255,255,255,0.12);border-radius:10px;
  display:flex;align-items:center;justify-content:center;font-size:22px;
}
.app-header-title{
  font-family:'DM Serif Display',serif;font-size:22px;
  color:white;line-height:1.1;
}
.app-header-sub{font-size:12px;color:rgba(255,255,255,0.55);margin-top:2px}
.header-badges{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.badge-white{
  background:rgba(255,255,255,0.12);
  border:1px solid rgba(255,255,255,0.2);
  border-radius:20px;padding:4px 12px;
  font-size:11px;font-weight:600;color:rgba(255,255,255,0.85);
  white-space:nowrap;
}
.badge-term{
  background:rgba(200,168,75,0.25);
  border:1px solid rgba(200,168,75,0.4);
  border-radius:20px;padding:4px 12px;
  font-size:11px;font-weight:700;color:#f0d080;
  white-space:nowrap;
}

/* ── Layout ── */
.main-wrap{max-width:980px;margin:0 auto;padding:28px 16px 60px}

/* ── Cards ── */
.card-wrap{
  background:var(--white);border:1px solid var(--navy-border);
  border-radius:14px;overflow:hidden;margin-bottom:18px;
}
.card-header{
  background:linear-gradient(90deg,var(--navy-light),#f0f4f8);
  padding:14px 20px;
  display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;
  border-bottom:1px solid var(--navy-border);
}
.card-title{font-size:14px;font-weight:700;color:var(--navy)}
.card-meta{font-size:11px;color:var(--ink-light);margin-top:2px}
.badge-green{
  background:var(--green-light);color:var(--green);
  font-size:11px;font-weight:700;padding:3px 10px;border-radius:20px;
  white-space:nowrap;
}

/* ── Timetable image ── */
.timetable-img{width:100%;display:block}
.page-divider{border:none;border-top:2px dashed var(--navy-border);margin:4px 0}

/* ── Empty state ── */
.no-tt{text-align:center;padding:48px 20px;color:var(--ink-light)}
.no-tt-icon{font-size:44px;margin-bottom:10px}
.no-tt h3{font-size:17px;font-weight:600;color:var(--navy);margin-bottom:6px}

/* ── Section label ── */
.section-label{
  font-size:10px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;
  color:var(--ink-light);margin:24px 0 10px;
}

/* ── History rows ── */
.history-row{
  background:var(--white);border:1px solid var(--navy-border);
  border-radius:10px;padding:10px 14px;margin-bottom:7px;
  display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:6px;
}
.history-label{font-size:13px;font-weight:600;color:var(--ink)}
.history-meta{font-size:11px;color:var(--ink-light);margin-top:1px}

/* ── Admin panel ── */
.admin-panel{
  background:var(--white);border:1px solid var(--navy-border);
  border-radius:14px;padding:20px 24px;margin-bottom:18px;
}

/* ── Buttons ── */
.stButton>button{border-radius:8px!important;font-weight:600!important;font-family:'DM Sans',sans-serif!important}
.stButton>button[kind="primary"]{background:var(--navy)!important;border-color:var(--navy)!important;color:white!important}
.stDownloadButton>button{
  background:var(--navy)!important;color:white!important;
  border-radius:8px!important;font-weight:600!important;width:100%;
}
div[data-testid="stExpander"]{border:1px solid var(--navy-border)!important;border-radius:var(--radius)!important}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"]{gap:4px;background:transparent}
.stTabs [data-baseweb="tab"]{
  background:#e8edf3;border-radius:8px 8px 0 0;
  color:var(--navy);font-weight:600;padding:8px 18px;border:none;font-size:13px;
}
.stTabs [aria-selected="true"]{background:var(--navy-mid)!important;color:#fff!important}

/* ── Mobile ── */
@media(max-width:600px){
  .app-header{padding:16px 16px}
  .app-header-title{font-size:18px}
  .main-wrap{padding:16px 10px 40px}
  .admin-panel{padding:16px 14px}
  .card-header{padding:12px 14px}
  .stTabs [data-baseweb="tab"]{padding:6px 10px;font-size:12px}
}
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
if "admin_authed" not in st.session_state:
    st.session_state.admin_authed = False

# ── Header ────────────────────────────────────────────────────────────────────
term_label = get_term_week_label()

st.markdown(f"""
<div class="app-header">
  <div class="app-header-left">
    <div class="app-header-icon">📅</div>
    <div>
      <div class="app-header-title">CLC Timetable</div>
      <div class="app-header-sub">Cowandilla Learning Centre — LBU</div>
    </div>
  </div>
  <div class="header-badges">
    <span class="badge-term">📆 {term_label}</span>
    <span class="badge-white">Always the latest version</span>
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="main-wrap">', unsafe_allow_html=True)

# ── Helper: render one program's timetable ────────────────────────────────────
def render_timetable_view(program: str):
    current = get_timetable(program)

    if current:
        label    = current.get("label") or current.get("filename", "Current Timetable")
        filename = current.get("filename", "timetable.pdf")
        uploaded = fmt_date(current.get("uploaded_at", ""))
        uploader = current.get("uploaded_by", "Admin")

        try:
            pdf_bytes = base64.b64decode(current["file_data"])
            has_pdf   = True
        except Exception:
            has_pdf   = False
            pdf_bytes = None

        st.markdown(f"""
        <div class="card-wrap">
          <div class="card-header">
            <div>
              <div class="card-title">📄 {label}</div>
              <div class="card-meta">Uploaded {uploaded} by {uploader}</div>
            </div>
            <span class="badge-green">✅ Current</span>
          </div>
        </div>""", unsafe_allow_html=True)

        if has_pdf:
            with st.spinner("Loading timetable…"):
                images = pdf_to_images(pdf_bytes)

            if images:
                st.markdown('<div class="card-wrap">', unsafe_allow_html=True)
                for i, img_b64 in enumerate(images):
                    if i > 0:
                        st.markdown('<hr class="page-divider">', unsafe_allow_html=True)
                    st.markdown(
                        f'<img src="data:image/png;base64,{img_b64}" '
                        f'class="timetable-img" alt="Page {i+1}">',
                        unsafe_allow_html=True,
                    )
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.warning("⚠️ Could not render PDF as image. Please download below.")

            st.download_button(
                label=f"⬇  Download {filename}",
                data=pdf_bytes,
                file_name=filename,
                mime="application/pdf",
                use_container_width=True,
                key=f"dl_{program}",
            )
        else:
            st.warning("Could not load timetable data — please ask admin to re-upload.")

    else:
        prog_label = PROGRAM_LABELS.get(program, program)
        st.markdown(f"""<div class="card-wrap"><div class="no-tt">
          <div class="no-tt-icon">📅</div>
          <h3>No timetable uploaded yet</h3>
          <p>{prog_label} timetable will appear here once uploaded by admin.</p>
        </div></div>""", unsafe_allow_html=True)


# ── Program tabs ──────────────────────────────────────────────────────────────
tab_labels = [PROGRAM_LABELS[p] for p in PROGRAMS]
tabs = st.tabs(tab_labels)

for tab, program in zip(tabs, PROGRAMS):
    with tab:
        render_timetable_view(program)


# ── Admin section ─────────────────────────────────────────────────────────────
st.markdown('<div class="section-label">🔐 Admin</div>', unsafe_allow_html=True)

if not st.session_state.admin_authed:
    with st.expander("Admin Login"):
        with st.form("admin_login"):
            pw = st.text_input(
                "Admin password", type="password",
                label_visibility="collapsed", placeholder="Enter admin password…",
            )
            if st.form_submit_button("Login", type="primary"):
                if verify_admin(pw):
                    st.session_state.admin_authed = True
                    st.rerun()
                else:
                    st.error("Incorrect password.")
else:
    # ── Upload panel ──
    st.markdown('<div class="admin-panel">', unsafe_allow_html=True)
    st.markdown("### 📤 Upload New Timetable")

    with st.form("upload_form", clear_on_submit=False):
        col_prog, col_lbl = st.columns([1, 2])
        with col_prog:
            prog_choice = st.selectbox(
                "Program",
                options=PROGRAMS,
                format_func=lambda p: PROGRAM_LABELS[p],
            )
        with col_lbl:
            lbl = st.text_input("Label", placeholder="e.g. Term 1 · Week 6 · 2 Mar 2026")

        file = st.file_uploader("Choose PDF", type=["pdf"], label_visibility="collapsed")

        c1, c2 = st.columns(2)
        with c1:
            submitted = st.form_submit_button(
                "✓ Upload & Set as Current", type="primary", use_container_width=True
            )
        with c2:
            logout = st.form_submit_button("Logout", use_container_width=True)

        if submitted:
            if not file:
                st.error("Please choose a PDF file.")
            elif not lbl.strip():
                st.error("Please add a label.")
            else:
                file.seek(0)
                raw    = file.read()
                b64data = base64.b64encode(raw).decode("utf-8")
                if save_timetable(file.name, b64data, lbl.strip(), prog_choice):
                    st.success(f"✅ {PROGRAM_LABELS[prog_choice]} timetable updated — {lbl.strip()}")
                    st.rerun()
        if logout:
            st.session_state.admin_authed = False
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Version history with delete ──
    for program in PROGRAMS:
        all_tt = get_all_timetables(program)
        if not all_tt:
            continue

        prog_label = PROGRAM_LABELS[program]
        st.markdown(
            f'<div class="section-label">🗂 {prog_label} — Version History</div>',
            unsafe_allow_html=True,
        )

        for i, tt in enumerate(all_tt):
            row_id   = tt.get("id")
            tt_label = tt.get("label") or tt.get("filename", "")
            tt_meta  = f"Uploaded {fmt_date(tt.get('uploaded_at', ''))} · {tt.get('filename', '')}"
            is_current = (i == 0)

            col_info, col_del = st.columns([5, 1])
            with col_info:
                badge = '<span class="badge-green">Current</span>' if is_current else ""
                st.markdown(f"""
                <div class="history-row">
                  <div>
                    <div class="history-label">📄 {tt_label} {badge}</div>
                    <div class="history-meta">{tt_meta}</div>
                  </div>
                </div>""", unsafe_allow_html=True)
            with col_del:
                if not is_current:
                    if st.button("🗑", key=f"del_{row_id}", help="Delete this version"):
                        if delete_timetable(row_id):
                            st.success("Deleted.")
                            st.rerun()
                else:
                    st.markdown("<div style='padding:10px 0;text-align:center;color:#9aa5b4;font-size:11px'>active</div>", unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)
