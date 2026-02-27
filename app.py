import streamlit as st
import base64
from datetime import datetime, timezone
from io import BytesIO

st.set_page_config(page_title="CLC Timetable", page_icon="📅", layout="wide", initial_sidebar_state="collapsed")

@st.cache_resource
def get_client():
    from supabase import create_client
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

def get_timetable():
    try:
        result = get_client().table("timetable_store").select("*").order("uploaded_at", desc=True).limit(1).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        st.error(f"Database error: {e}")
        return None

def save_timetable(filename, file_b64, label, uploaded_by):
    try:
        get_client().table("timetable_store").insert({
            "filename": filename, "file_data": file_b64, "label": label,
            "uploaded_by": uploaded_by, "uploaded_at": datetime.now(timezone.utc).isoformat()
        }).execute()
        return True
    except Exception as e:
        st.error(f"Save failed: {e}")
        return False

def get_all_timetables():
    try:
        result = get_client().table("timetable_store").select("id, filename, label, uploaded_by, uploaded_at").order("uploaded_at", desc=True).execute()
        return result.data or []
    except:
        return []

def verify_admin(password):
    return password == st.secrets.get("ADMIN_PASSWORD", "CLC2026admin")

def fmt_date(iso):
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%d %b %Y, %I:%M %p").replace(" 0", " ")
    except:
        return iso or ""

def pdf_to_images(pdf_bytes):
    """Convert PDF bytes to list of PIL images using pdf2image."""
    try:
        from pdf2image import convert_from_bytes
        images = convert_from_bytes(pdf_bytes, dpi=150)
        return images
    except Exception as e:
        return None

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Serif+Display&display=swap');
*,*::before,*::after{box-sizing:border-box}
:root{--navy:#1a2e44;--navy-mid:#2d4f72;--navy-light:#e8edf3;--navy-border:#c5d3e0;--green:#059669;--green-light:#d1fae5;--white:#ffffff;--bg:#f4f6f9;--ink:#1a2332;--ink-light:#6b7f94;--radius:12px}
html,body,[class*="css"]{font-family:'DM Sans',sans-serif!important;background:var(--bg)!important}
.block-container{padding:0!important;max-width:100%!important}
header{display:none!important}
.app-header{background:linear-gradient(135deg,var(--navy) 0%,var(--navy-mid) 100%);padding:28px 48px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px}
.app-header-left{display:flex;align-items:center;gap:16px}
.app-header-icon{width:48px;height:48px;background:rgba(255,255,255,0.12);border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:24px}
.app-header-title{font-family:'DM Serif Display',serif;font-size:24px;color:white;line-height:1.1}
.app-header-sub{font-size:13px;color:rgba(255,255,255,0.55);margin-top:2px}
.app-header-badge{background:rgba(255,255,255,0.12);border:1px solid rgba(255,255,255,0.2);border-radius:20px;padding:5px 14px;font-size:12px;font-weight:600;color:rgba(255,255,255,0.8)}
.main-wrap{max-width:960px;margin:0 auto;padding:32px 24px 60px}
.card-header{background:linear-gradient(90deg,var(--navy-light),#f0f4f8);padding:16px 24px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid var(--navy-border);border-radius:14px 14px 0 0}
.card-wrap{background:var(--white);border:1px solid var(--navy-border);border-radius:14px;overflow:hidden;margin-bottom:20px}
.card-title{font-size:15px;font-weight:700;color:var(--navy)}
.card-meta{font-size:12px;color:var(--ink-light);margin-top:2px}
.badge-green{background:var(--green-light);color:var(--green);font-size:11px;font-weight:700;padding:4px 10px;border-radius:20px}
.section-label{font-size:11px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:var(--ink-light);margin:28px 0 12px}
.history-row{background:var(--white);border:1px solid var(--navy-border);border-radius:10px;padding:12px 16px;margin-bottom:8px}
.history-label{font-size:14px;font-weight:600;color:var(--ink)}
.history-meta{font-size:12px;color:var(--ink-light);margin-top:2px}
.admin-panel{background:var(--white);border:1px solid var(--navy-border);border-radius:16px;padding:24px 28px;margin-bottom:20px}
.no-tt{text-align:center;padding:48px 24px;color:var(--ink-light)}
.no-tt-icon{font-size:48px;margin-bottom:12px}
.no-tt h3{font-size:18px;font-weight:600;color:var(--navy);margin-bottom:6px}
.stButton>button{border-radius:8px!important;font-weight:600!important;font-family:'DM Sans',sans-serif!important}
.stButton>button[kind="primary"]{background:var(--navy)!important;border-color:var(--navy)!important;color:white!important}
.stDownloadButton>button{background:var(--navy)!important;color:white!important;border-radius:8px!important;font-weight:600!important;width:100%}
div[data-testid="stExpander"]{border:1px solid var(--navy-border)!important;border-radius:var(--radius)!important}
.timetable-img{width:100%;border-radius:0 0 12px 12px;display:block;}
.page-divider{border:none;border-top:2px dashed var(--navy-border);margin:8px 0;}
</style>
""", unsafe_allow_html=True)

if "admin_authed" not in st.session_state:
    st.session_state.admin_authed = False

st.markdown("""
<div class="app-header">
  <div class="app-header-left">
    <div class="app-header-icon">📅</div>
    <div>
      <div class="app-header-title">CLC Timetable</div>
      <div class="app-header-sub">Cowandilla Learning Centre — LBU</div>
    </div>
  </div>
  <div class="app-header-badge">Always the latest version</div>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="main-wrap">', unsafe_allow_html=True)

current = get_timetable()

if current:
    label    = current.get("label") or current.get("filename", "Current Timetable")
    filename = current.get("filename", "timetable.pdf")
    uploaded = fmt_date(current.get("uploaded_at", ""))
    uploader = current.get("uploaded_by", "Admin")

    try:
        pdf_bytes = base64.b64decode(current["file_data"])
        has_pdf = True
    except:
        has_pdf = False
        pdf_bytes = None

    st.markdown(f"""
    <div class="card-wrap">
      <div class="card-header">
        <div>
          <div class="card-title">📄 {label}</div>
          <div class="card-meta">Uploaded {uploaded} by {uploader}</div>
        </div>
        <span class="badge-green">✅ Current Version</span>
      </div>
    </div>""", unsafe_allow_html=True)

    if has_pdf:
        # Convert PDF to images for universal browser compatibility
        with st.spinner("Loading timetable..."):
            images = pdf_to_images(pdf_bytes)

        if images:
            st.markdown('<div class="card-wrap">', unsafe_allow_html=True)
            for i, img in enumerate(images):
                # Convert PIL image to bytes
                buf = BytesIO()
                img.save(buf, format="PNG")
                img_bytes = buf.getvalue()
                img_b64 = base64.b64encode(img_bytes).decode()

                if i > 0:
                    st.markdown('<hr class="page-divider">', unsafe_allow_html=True)

                st.markdown(
                    f'<img src="data:image/png;base64,{img_b64}" class="timetable-img" alt="Timetable page {i+1}">',
                    unsafe_allow_html=True
                )
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.warning("⚠️ Could not render timetable as image. Please download below.")

        # Always show download button
        st.download_button(
            label=f"⬇  Download {filename}",
            data=pdf_bytes,
            file_name=filename,
            mime="application/pdf",
            use_container_width=True
        )
    else:
        st.warning("Could not load timetable data — please ask admin to re-upload.")

else:
    st.markdown("""<div class="card-wrap"><div class="no-tt">
      <div class="no-tt-icon">📅</div>
      <h3>No timetable uploaded yet</h3>
      <p>Admin will upload the current timetable here. Check back soon.</p>
    </div></div>""", unsafe_allow_html=True)

st.markdown('<div class="section-label">🔐 Admin</div>', unsafe_allow_html=True)

if not st.session_state.admin_authed:
    with st.expander("Admin Login"):
        with st.form("admin_login"):
            pw = st.text_input("Admin password", type="password",
                               label_visibility="collapsed", placeholder="Enter admin password…")
            if st.form_submit_button("Login", type="primary"):
                if verify_admin(pw):
                    st.session_state.admin_authed = True
                    st.rerun()
                else:
                    st.error("Incorrect password.")
else:
    st.markdown('<div class="admin-panel">', unsafe_allow_html=True)
    st.markdown("### 📤 Upload New Timetable")
    with st.form("upload_form", clear_on_submit=False):
        lbl  = st.text_input("Label (e.g. Term 1 Week 6)", placeholder="Term 1 · Week 6 · 2 Mar 2026")
        file = st.file_uploader("Choose PDF", type=["pdf"], label_visibility="collapsed")
        c1, c2 = st.columns(2)
        with c1:
            submitted = st.form_submit_button("✓ Upload & Set as Current", type="primary", use_container_width=True)
        with c2:
            logout = st.form_submit_button("Logout", use_container_width=True)
        if submitted:
            if not file:
                st.error("Please choose a PDF file.")
            elif not lbl.strip():
                st.error("Please add a label.")
            else:
                file.seek(0)
                raw = file.read()
                b64data = base64.b64encode(raw).decode("utf-8")
                if save_timetable(file.name, b64data, lbl.strip(), "Admin"):
                    st.success(f"✅ Timetable updated — {lbl.strip()}")
                    st.rerun()
        if logout:
            st.session_state.admin_authed = False
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    all_tt = get_all_timetables()
    if len(all_tt) > 1:
        st.markdown('<div class="section-label">🗂 Previous Versions</div>', unsafe_allow_html=True)
        for tt in all_tt[1:]:
            st.markdown(f"""<div class="history-row">
              <div class="history-label">📄 {tt.get('label') or tt.get('filename','')}</div>
              <div class="history-meta">Uploaded {fmt_date(tt.get('uploaded_at',''))} · {tt.get('filename','')}</div>
            </div>""", unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)
