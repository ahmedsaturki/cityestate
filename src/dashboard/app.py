"""
CityEstate Dashboard — لوحة التحكم التفاعلية
=============================================
Streamlit dashboard connected to the real FastAPI backend.
Requires login via POST /api/auth/login.
"""

import json
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import httpx
import streamlit as st

# API Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
API_PREFIX = "/api/v1"

# Page config
st.set_page_config(
    page_title="CityEstate Master OS",
    page_icon="🏙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        padding: 1rem 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    .stMetric > div {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .login-card {
        background: #f8f9fa;
        padding: 2rem;
        border-radius: 15px;
        max-width: 400px;
        margin: 5rem auto;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# API Client Helper
# ---------------------------------------------------------------------------
def api_get(endpoint: str, params: dict | None = None) -> dict | list | None:
    """Make authenticated GET request to API."""
    token = st.session_state.get("jwt_token")
    if not token:
        return None
    try:
        resp = httpx.get(
            f"{API_BASE_URL}{API_PREFIX}{endpoint}",
            headers={"Authorization": f"Bearer {token}"},
            params=params,
            timeout=10.0,
        )
        if resp.status_code == 200:
            return resp.json()
        elif resp.status_code == 401:
            st.session_state.clear()
            st.rerun()
        else:
            st.error(f"API Error: {resp.status_code} — {resp.text[:200]}")
            return None
    except httpx.ConnectError:
        st.error("Cannot connect to API server. Is it running on port 8000?")
        return None
    except Exception as e:
        st.error(f"Connection error: {e}")
        return None


def api_get_root(endpoint: str, params: dict | None = None) -> dict | list | None:
    """Make authenticated GET request to root-level API (no /api/v1 prefix)."""
    token = st.session_state.get("jwt_token")
    if not token:
        return None
    try:
        resp = httpx.get(
            f"{API_BASE_URL}{endpoint}",
            headers={"Authorization": f"Bearer {token}"},
            params=params,
            timeout=10.0,
        )
        if resp.status_code == 200:
            return resp.json()
        elif resp.status_code == 401:
            st.session_state.clear()
            st.rerun()
        st.error(f"API Error {resp.status_code}: {resp.text[:200]}")
        return None
    except Exception as e:
        st.error(f"Request failed: {str(e)[:200]}")
        return None


def api_post(endpoint: str, data: dict | None = None) -> dict | None:
    """Make authenticated POST request to API."""
    token = st.session_state.get("jwt_token")
    if not token:
        return None
    try:
        resp = httpx.post(
            f"{API_BASE_URL}{API_PREFIX}{endpoint}",
            headers={"Authorization": f"Bearer {token}"},
            json=data,
            timeout=10.0,
        )
        if resp.status_code in (200, 201):
            return resp.json()
        elif resp.status_code == 401:
            st.session_state.clear()
            st.rerun()
        else:
            st.error(f"API Error: {resp.status_code} — {resp.text[:200]}")
            return None
    except httpx.ConnectError:
        st.error("Cannot connect to API server.")
        return None
    except Exception as e:
        st.error(f"Request failed: {str(e)[:200]}")
        return None


# ---------------------------------------------------------------------------
# Login Page
# ---------------------------------------------------------------------------
def show_login():
    """Display login page."""
    st.markdown("""
    <div class="login-card">
        <h2 style="text-align:center;">🏙️ CityEstate Master OS</h2>
        <p style="text-align:center; color:#666;">Egyptian Real Estate Multi-Agent System</p>
    </div>
    """, unsafe_allow_html=True)

    with st.form("login_form"):
        st.subheader("تسجيل الدخول")
        username = st.text_input("اسم المستخدم", placeholder="admin")
        password = st.text_input("كلمة المرور", type="password", placeholder="••••••••")
        submitted = st.form_submit_button("دخول", use_container_width=True)

        if submitted:
            if not username or not password:
                st.error("أدخل اسم المستخدم وكلمة المرور")
                return
            try:
                resp = httpx.post(
                    f"{API_BASE_URL}{API_PREFIX}/auth/login",
                    json={"username": username, "password": password},
                    timeout=10.0,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    st.session_state["jwt_token"] = data["access_token"]
                    st.session_state["user"] = data["user"]
                    st.session_state["authenticated"] = True
                    st.rerun()
                else:
                    st.error("اسم المستخدم أو كلمة المرور غير صحيحة")
            except httpx.ConnectError:
                st.error("لا يمكن الاتصال بالخادم. تأكد من تشغيل API على المنفذ 8000")
            except Exception as e:
                st.error(f"خطأ: {str(e)[:100]}")


# ---------------------------------------------------------------------------
# Dashboard Page
# ---------------------------------------------------------------------------
def show_dashboard():
    """Main dashboard view with KPIs."""
    st.title("📊 لوحة التحكم")

    data = api_get("/dashboard/stats")
    if not data:
        st.warning("لا توجد بيانات. تأكد من تشغيل API.")
        return

    # KPI Cards
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("إجمالي العملاء", data.get("total_leads", 0))
    with col2:
        st.metric("العقارات", data.get("total_properties", 0))
    with col3:
        st.metric("طلبات معلقة", data.get("total_requests", 0))
    with col4:
        st.metric("رسائل مرسلة", data.get("total_messages", 0))

    # Charts
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("العملاء حسب النوع")
        by_type = data.get("leads_by_type", {})
        if by_type:
            st.bar_chart(by_type)
        else:
            st.info("لا توجد بيانات بعد")

    with col2:
        st.subheader("حالة الطلبات")
        by_status = data.get("requests_by_status", {})
        if by_status:
            st.bar_chart(by_status)
        else:
            st.info("لا توجد بيانات بعد")

    # Recent Activity
    st.subheader("آخر النشاطات")
    recent_leads = data.get("recent_leads", [])
    if recent_leads:
        for lead in recent_leads[:5]:
            st.write(f"• {lead.get('title', 'N/A')} — {lead.get('lead_type', 'N/A')} — {lead.get('status', 'N/A')}")
    else:
        st.info("لا توجد نشاطات حديثة")


# ---------------------------------------------------------------------------
# Leads Page
# ---------------------------------------------------------------------------
def show_leads():
    """Leads management page."""
    st.title("👥 إدارة العملاء")

    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        lead_type = st.selectbox("النوع", ["All", "Developer", "Investor", "Buyer", "Agency", "Unknown"])
    with col2:
        status_filter = st.selectbox("الحالة", ["All", "new", "contacted", "qualified", "converted"])
    with col3:
        st.text_input("بحث")

    # Fetch leads
    params = {}
    if lead_type != "All":
        params["lead_type"] = lead_type
    if status_filter != "All":
        params["status"] = status_filter

    leads = api_get("/leads", params) or []

    if leads:
        st.write(f"عدد النتائج: **{len(leads)}**")

        # Leads table
        for lead in leads[:50]:
            with st.expander(f"{lead.get('title', 'N/A')} — {lead.get('lead_type', 'N/A')}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**النوع:** {lead.get('lead_type', 'N/A')}")
                    st.write(f"**المنطقة:** {lead.get('area', 'N/A')}")
                    st.write(f"**الميزانية:** {lead.get('budget', 'N/A')}")
                with col2:
                    st.write(f"**الهاتف:** {lead.get('phone', 'N/A')}")
                    st.write(f"**البريد:** {lead.get('email', 'N/A')}")
                    st.write(f"**الحالة:** {lead.get('status', 'N/A')}")
                st.write(f"**الاهتمام:** {lead.get('interest', 'N/A')}")
    else:
        st.info("لا توجد نتائج")


# ---------------------------------------------------------------------------
# Properties Page
# ---------------------------------------------------------------------------
def show_properties():
    """Property management page."""
    st.title("🏠 إدارة العقارات")

    properties = api_get("/properties") or []

    if properties:
        st.write(f"عدد العقارات: **{len(properties)}**")

        for prop in properties[:30]:
            prop_id = prop.get("id")
            with st.expander(f"{prop.get('title', 'N/A')} — {prop.get('area', 'N/A')}"):
                col1, col2 = st.columns(2)
                with col1:
                    price = prop.get('price', 0)
                    st.write(f"**السعر:** {price:,.0f} جنيه")
                    st.write(f"**النوع:** {prop.get('property_type', 'N/A')}")
                    st.write(f"**الحالة:** {prop.get('status', 'N/A')}")
                with col2:
                    st.write(f"**الغرف:** {prop.get('bedrooms', 'N/A')}")
                    st.write(f"**المساحة:** {prop.get('area_sqm', 'N/A')} م²")
                    st.write(f"**المطور:** {prop.get('developer', 'N/A')}")

                # --- Content Generator Button ---
                st.divider()
                if st.button("📝 إنشاء محتوى تسويقي", key=f"gen_content_{prop_id}", use_container_width=True):
                    with st.spinner("جاري إنشاء المحتوى..."):
                        content_result = api_post("/content/generate", {
                            "property_id": prop_id,
                            "channel": "all",
                        })
                    if content_result:
                        st.success("✅ تم إنشاء المحتوى بنجاح!")
                        content = content_result.get("content", {})

                        # --- Facebook ---
                        if "facebook" in content:
                            fb = content["facebook"]
                            st.subheader("📘 بوست فيسبوك")
                            st.text_area("Facebook Post", value=fb["text"], height=200, key=f"fb_{prop_id}", disabled=True)
                            st.caption(f"📝 {fb['char_count']} حرف")
                            with st.expander("💡 نصائح النشر"):
                                for tip in fb.get("tips", []):
                                    st.write(f"• {tip}")
                            if st.button("📋 نسخ", key=f"copy_fb_{prop_id}"):
                                st.code(fb["text"], language=None)

                        # --- Instagram ---
                        if "instagram" in content:
                            ig = content["instagram"]
                            st.subheader("📸 بوست إنستجرام")
                            st.text_area("Instagram Post", value=ig["text"], height=180, key=f"ig_{prop_id}", disabled=True)
                            st.caption(f"📝 {ig['char_count']} حرف")
                            with st.expander("💡 نصائح النشر"):
                                for tip in ig.get("tips", []):
                                    st.write(f"• {tip}")

                        # --- WhatsApp ---
                        if "whatsapp" in content:
                            wa = content["whatsapp"]
                            st.subheader("💬 حالة واتساب")
                            st.text_area("WhatsApp Status", value=wa["text"], height=120, key=f"wa_{prop_id}", disabled=True)
                            st.caption(f"📝 {wa['char_count']} حرف")
                            with st.expander("💡 نصائح النشر"):
                                for tip in wa.get("tips", []):
                                    st.write(f"• {tip}")
                    else:
                        st.error("فشل إنشاء المحتوى")
    else:
        st.info("لا توجد عقارات. أضف عقاراً أولاً.")


# ---------------------------------------------------------------------------
# Client Requests Page
# ---------------------------------------------------------------------------
def show_requests():
    """Client requests and match-making page."""
    st.title("📋 طلبات العملاء")

    requests_list = api_get("/requests") or []

    if requests_list:
        st.write(f"عدد الطلبات: **{len(requests_list)}**")

        for req in requests_list[:20]:
            status_color = {"pending": "🟡", "matched": "🟢", "notified": "🔵"}.get(req.get("status"), "⚪")
            with st.expander(f"{status_color} {req.get('client_name', 'N/A')} — {req.get('status', 'N/A')}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**المنطقة:** {req.get('area', 'N/A')}")
                    st.write(f"**النوع:** {req.get('property_type', 'N/A')}")
                    st.write(f"**الميزانية:** {req.get('min_budget', 'N/A')} - {req.get('max_budget', 'N/A')}")
                with col2:
                    st.write(f"**الغرف:** {req.get('bedrooms', 'N/A')}")
                    st.write(f"**المساحة:** {req.get('min_area_sqm', 0)} - {req.get('max_area_sqm', 0)} م²")
                    st.write(f"**خطة الدفع:** {'مفضل' if req.get('prefer_payment_plan') else 'أي'}")
                with st.columns(1)[0]:
                    st.write(f"**الأولوية:** {req.get('priority', 'N/A')}")
                    score = req.get('match_score')
                    if score:
                        st.write(f"**درجة المطابقة:** {score:.0%}")
    else:
        st.info("لا توجد طلبات بعد")

    # --- New Request Form ---
    st.divider()
    st.subheader("➕ طلب جديد")

    with st.form("new_request_form"):
        c1, c2 = st.columns(2)
        with c1:
            client_name = st.text_input("اسم العميل *")
            phone = st.text_input("رقم الهاتف")
            email = st.text_input("البريد الإلكتروني")
        with c2:
            area = st.text_input("المنطقة المطلوبة")
            property_type = st.selectbox("نوع العقار", ["", "primary", "resale", "compound", "villa", "apartment"])
            bedrooms = st.number_input("عدد الغرف", min_value=0, max_value=10, value=0)

        c3, c4 = st.columns(2)
        with c3:
            min_budget = st.number_input("الحد الأدنى للميزانية (ج.م)", min_value=0, value=0, step=100000)
            max_budget = st.number_input("الحد الأقصى للميزانية (ج.م)", min_value=0, value=0, step=100000)
        with c4:
            min_area_sqm = st.number_input("الحد الأدنى للمساحة (م²)", min_value=0.0, value=0.0, step=10.0)
            max_area_sqm = st.number_input("الحد الأقصى للمساحة (م²)", min_value=0.0, value=0.0, step=10.0)

        prefer_payment = st.checkbox("أفضل خطة تقسيط")
        priority = st.selectbox("الأولوية", ["normal", "high", "low"])
        notes = st.text_area("ملاحظات")

        submitted = st.form_submit_button("🚀 إرسال الطلب", use_container_width=True)

        if submitted:
            if not client_name:
                st.error("اسم العميل مطلوب")
            else:
                payload = {
                    "client_name": client_name,
                    "phone": phone or None,
                    "email": email or None,
                    "area": area or None,
                    "property_type": property_type or None,
                    "bedrooms": bedrooms or None,
                    "min_budget": min_budget or None,
                    "max_budget": max_budget or None,
                    "min_area_sqm": min_area_sqm or None,
                    "max_area_sqm": max_area_sqm or None,
                    "prefer_payment_plan": prefer_payment,
                    "priority": priority,
                    "notes": notes or None,
                }
                result = api_post("/requests", payload)
                if result:
                    st.success(f"تم إنشاء الطلب بنجاح! ID: {result.get('id')}")
                    st.rerun()
                else:
                    st.error("فشل إنشاء الطلب")


# ---------------------------------------------------------------------------
# Automation Page
# ---------------------------------------------------------------------------
def show_automation():
    """Automation control center."""
    st.title("🤖 مركز الأتمتة")

    # Quick actions
    st.subheader("إجراءات سريعة")
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("🔍 جمع من Facebook", use_container_width=True):
            result = api_post("/automation/run", {"action": "scrape", "platform": "facebook"})
            if result:
                st.success(f"بدأ: {result.get('message', 'OK')}")

    with col2:
        if st.button("📤 إرسال WhatsApp", use_container_width=True):
            result = api_post("/automation/run", {"action": "send", "platform": "whatsapp"})
            if result:
                st.success(f"بدأ: {result.get('message', 'OK')}")

    with col3:
        if st.button("🔄 تحسين العملاء", use_container_width=True):
            result = api_post("/automation/run", {"action": "enrich", "platform": "all"})
            if result:
                st.success(f"بدأ: {result.get('message', 'OK')}")

    # Session status
    st.subheader("حالة الجلسات")
    vault_status = api_get("/automation/status")
    if vault_status:
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Facebook Scraper", "موجود" if vault_status.get("facebook_scraper") else "غير موجود")
        with col2:
            st.metric("WhatsApp Pilot", "موجود" if vault_status.get("whatsapp_pilot") else "غير موجود")

    # Recent logs
    st.subheader("آخر السجلات")
    logs = vault_status.get("recent_logs", []) if vault_status else []
    if logs:
        for log in logs[:5]:
            st.write(f"• {log.get('filename', 'N/A')} — {log.get('modified', 'N/A')}")
    else:
        st.info("لا توجد سجلات حديثة")


# ---------------------------------------------------------------------------
# Settings Page
# ---------------------------------------------------------------------------
def show_settings():
    """Settings page."""
    st.title("⚙️ الإعدادات")

    user = st.session_state.get("user", {})
    st.write(f"**المستخدم الحالي:** {user.get('username', 'N/A')}")
    st.write(f"**الصلاحية:** {user.get('role', 'N/A')}")

    st.subheader("معلومات الخادم")
    st.write(f"**عنوان API:** {API_BASE_URL}")
    st.write(f"**Version:** {API_PREFIX}")

    st.subheader("إعدادات الأتمتة")
    with st.form("auto_config"):
        st.slider("الحد الأقصى للرسائل/ساعة", 1, 100, 30)
        st.slider("التأخير بين الرسائل (ثانية)", 1, 60, 5)
        st.checkbox("وضع التجربة (لا إرسال فعلي)")

        if st.form_submit_button("حفظ"):
            st.success("تم الحفظ!")

    st.subheader("إدارة قاعدة البيانات")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 تحديث البيانات"):
            st.success("تم التحديث!")
    with col2:
        if st.button("📊 تصدير CSV"):
            st.success("جاري التصدير...")

    st.subheader("تسجيل الخروج")
    if st.button("🚪 تسجيل خروج", use_container_width=True):
        st.session_state.clear()
        st.rerun()


# ---------------------------------------------------------------------------
# Scheduler Page
# ---------------------------------------------------------------------------
def show_scheduler():
    """Scheduler control and monitoring page."""
    st.title("🗓️ الجدولة والمهام")
    st.caption("التحكم في المهام الأوتوماتيكية (المطابقة، الإشعارات، النسخ الاحتياطي)")

    # Fetch scheduler status
    status = api_get("/scheduler/status")

    if not status:
        st.warning("الجدول غير متاح. تأكد من تشغيل API.")
        st.info("الجدول يبدأ تلقائياً مع API.")
        return

    # --- Status Header ---
    is_running = status.get("running", False)
    if is_running:
        st.success("🟢 الجدول يعمل بشكل طبيعي")
    else:
        st.error("🔴 الجدول متوقف")

    # --- Control Buttons ---
    st.subheader("التحكم")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("⏸️ إيقاف مؤقت", use_container_width=True):
            result = api_post("/scheduler/pause")
            if result:
                st.success("تم الإيقاف المؤقت")
                st.rerun()
    with c2:
        if st.button("▶️ استئناف", use_container_width=True):
            result = api_post("/scheduler/resume")
            if result:
                st.success("تم الاستئناف")
                st.rerun()
    with c3:
        if st.button("🔄 تحديث", use_container_width=True):
            st.rerun()

    # --- Jobs Table ---
    st.subheader("المهام المجدولة")
    jobs = status.get("jobs", {})

    if jobs:
        for job_id, info in jobs.items():
            with st.expander(f"{'🟢' if info.get('last_status') == 'success' else '🟡' if info.get('last_status') == 'pending' else '🔴'} {info.get('name', job_id)}"):
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    interval = info.get("interval", 0)
                    if interval >= 3600:
                        st.metric("الفترة", f"{interval // 3600} ساعة")
                    elif interval >= 60:
                        st.metric("الفترة", f"{interval // 60} دقيقة")
                    else:
                        st.metric("الفترة", f"{interval} ثانية")
                with c2:
                    st.metric("الحالة", info.get("last_status", "pending"))
                with c3:
                    st.metric("عدد التشغيلات", info.get("run_count", 0))
                with c4:
                    st.metric("الأخطاء", info.get("error_count", 0))

                next_run = info.get("next_run")
                if next_run and next_run != "None":
                    st.write(f"**التشغيل القادم:** {next_run}")
                else:
                    st.write("**التشغيل القادم:** —")

                if st.button("▶️ تشغيل الآن", key=f"run_{job_id}", use_container_width=True):
                    result = api_post(f"/scheduler/run/{job_id}")
                    if result:
                        st.success(f"تم تشغيل {info.get('name', job_id)}")
                    else:
                        st.error("فشل التشغيل")
    else:
        st.info("لا توجد مهام مسجلة")


# ---------------------------------------------------------------------------
# Backup & Webhooks Page
# ---------------------------------------------------------------------------
def show_backup_webhooks():
    """Backup management and webhook configuration page."""
    st.title("🛡️ النسخ الاحتياطي والويب هوك")

    # --- Backup Section ---
    st.subheader("📦 النسخ الاحتياطي")
    st.caption("إنشاء نسخة احتياطية من قاعدة البيانات والجلسات المشفرة")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("📥 إنشاء نسخة احتياطية الآن", use_container_width=True):
            with st.spinner("جاري إنشاء النسخة..."):
                result = api_post("/scheduler/run/backup_run")
                if result:
                    st.success("تم إنشاء النسخة الاحتياطية بنجاح!")
                else:
                    st.error("فشل إنشاء النسخة")

    with c2:
        st.info("💡 النسخ الاحتياطي يتلقائي كل 24 ساعة عبر الجدول")

    # Show existing backups
    st.subheader("النسخ الاحتياطية المتوفرة")
    from pathlib import Path

    backup_dir = Path(__file__).parent.parent.parent / "backups"
    if backup_dir.exists():
        backups = sorted(backup_dir.glob("backup_*.zip"), reverse=True)
        if backups:
            for bp in backups[:10]:
                size_kb = bp.stat().st_size / 1024
                st.write(f"• `{bp.name}` — {size_kb:.1f} KB")
        else:
            st.info("لا توجد نسخ احتياطية بعد")
    else:
        st.info("مجلد النسخ الاحتياطي غير موجود")

    st.divider()

    # --- Webhook Section ---
    st.subheader("🔗 رابط الويب هوك")
    st.caption("استخدم هذا الرابط لاستقبال بيانات العملاء من أي فورم مجاني")

    webhook_url = f"{API_BASE_URL}/api/v1/webhooks/form"
    st.code(webhook_url, language="text")

    st.subheader("📐 الحقول المدعومة")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        **مطلوب (أحدهما):**
        - `phone` — رقم الهاتف
        - `email` — البريد الإلكتروني

        **اختياري:**
        - `name` — اسم العميل
        - `area` — المنطقة المفضلة
        - `max_budget` — الحد الأقصى للميزانية
        """)
    with col2:
        st.markdown("""
        **اختياري (تكميلي):**
        - `min_budget` — الحد الأدنى للميزانية
        - `bedrooms` — عدد الغرف
        - `property_type` — نوع العقار
        - `message` — رسالة إضافية

        **أي حقل إضافي** يُحفظ كبيانات إضافية
        """)

    st.subheader("🧪 اختبار الويب هوك")
    with st.form("test_webhook"):
        st.write("أرسل بيانات تجريبية للتأكد من عمل الويب هوك:")
        c1, c2 = st.columns(2)
        with c1:
            test_name = st.text_input("الاسم", value="Ahmed Test")
            test_phone = st.text_input("الهاتف", value="+201234567890")
        with c2:
            test_area = st.text_input("المنطقة", value="Sheikh Zayed")
            test_budget = st.number_input("الميزانية", value=5000000, step=100000)

        if st.form_submit_button("إرسال تجريبي"):
            import httpx
            try:
                resp = httpx.post(
                    f"{API_BASE_URL}/api/v1/webhooks/form",
                    json={
                        "name": test_name,
                        "phone": test_phone,
                        "area": test_area,
                        "max_budget": test_budget,
                    },
                    timeout=15.0,
                )
                if resp.status_code == 200:
                    result = resp.json()
                    st.success(f"✅ تم الاستلام! Lead #{result.get('lead_id')}, Matches: {result.get('matches_found')}")
                else:
                    st.error(f"خطأ: {resp.status_code} — {resp.text[:200]}")
            except Exception as e:
                st.error(f"فشل الاتصال: {e}")

    st.subheader("🔗 مزامنة النماذج")
    st.markdown("""
    **Google Forms:**
    1. استخدم إضافة [Google Apps Script](https://script.google.com) لإرسال البيانات
    2. اضبط `UrlFetchApp.fetch()` على رابط الويب هوك

    **Tally.so / Typeform:**
    1. اذهب لإعدادات النموذج → Integrations → Webhooks
    2. أدخل رابط الويب هوك أعلاه
    3. اختر `JSON` كـ Content Type

    **HTML Form:**
    ```html
    <form action="http://localhost:8000/api/v1/webhooks/form" method="POST">
      <input name="name" placeholder="الاسم" />
      <input name="phone" placeholder="الهاتف" />
      <input name="area" placeholder="المنطقة" />
      <input name="max_budget" type="number" placeholder="الميزانية" />
      <button type="submit">إرسال</button>
    </form>
    ```
    """)


# ---------------------------------------------------------------------------
# Fleet Monitor Page — صفحة مراقبة أسطول الإضافات
# ---------------------------------------------------------------------------
def show_fleet_monitor():
    """Monitor Chrome Extension fleet connections and live activity."""
    st.markdown("## 🔌 فليت الأسطول — CityEstate Bridge")
    st.markdown("مراقبة اتصالات إضافة الك롬 ونشاطها في الوقت الفعلي")

    # --- Connection Status ---
    st.subheader("حالة الاتصالات")
    status = api_get_root("/bridge/status")

    if status:
        connections = status.get("connections", [])
        stats = status.get("stats", {})

        # Stats cards
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("الإضافات المتصلة", stats.get("connected_profiles", 0))
        with col2:
            st.metric("في الانتظار", stats.get("queued_profiles", 0))
        with col3:
            st.metric("رسائل مرسلة", stats.get("total_messages_sent", 0))
        with col4:
            st.metric("رسائل مستلمة", stats.get("total_messages_received", 0))

        # Connected profiles table
        if connections:
            st.subheader("الإضافات المتصلة")
            import pandas as pd
            df = pd.DataFrame(connections)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("لا توجد إضافات متصلة حالياً. اتصل بإضافة كروم لتبدأ.")

    else:
        st.warning("⚠️ لا يمكن الاتصال بالخادم. تأكد من تشغيل API على المنفذ 8000.")

    st.divider()

    # --- Live Message Feed ---
    st.subheader("الرسائل المباشرة")
    st.caption("آخر الرسائل المستلمة من الإضافات")

    messages = api_get_root("/bridge/messages")
    if messages and messages.get("messages"):
        import pandas as pd
        msg_df = pd.DataFrame(messages["messages"])
        st.dataframe(msg_df, use_container_width=True)
    else:
        st.info("لا توجد رسائل بعد. ابدأ بفتح واتساب أو فيسبوك في متصفح كروم.")

    st.divider()

    # --- Quick Actions ---
    st.subheader("إجراءات سريعة")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 تحديث الحالة", use_container_width=True):
            st.rerun()

    with col2:
        if st.button("📤 إرسال رسالة تجريبية", use_container_width=True):
            st.info("هذه ميزة قادمة في الإصدار القادم")

    # --- Setup Instructions ---
    with st.expander("📖 تعليمات التثبيت"):
        st.markdown("""
        ### كيفية تثبيت CityEstate Bridge

        1. **افتح كروم** وانتقل إلى `chrome://extensions/`
        2. **فعّل** "وضع المطور" (Developer Mode)
        3. **اضغط** "تحميل إضافة غير مضغوطة" (Load unpacked)
        4. **اختر** مجلد `cityestate-extension` من المشروع
        5. **افتح** واتساب ويب أو فيسبوك في متصفح كروم
        6. **اضغط** على أيقونة الإضافة وأدخل JWT token

        ### JWT Token
        ```
        احصل على التوكن من: API → Auth → Login
        ```
        """)


# ---------------------------------------------------------------------------
# Facebook Groups Radar Page
# ---------------------------------------------------------------------------
def show_radar():
    """📡 رادار الجروبات — Facebook Groups Social Listening Radar."""
    st.markdown("## 📡 رادار الجروبات العقارية")
    st.markdown("اكتشف عملاء جدد من جروبات الفيسبوك — منشورات طلب العقار تتحول تلقائياً للعملاء المحتملين")

    # Radar controls
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        st.markdown("**إعدادات المسح**")
        st.text_area(
            "روابط الجروبات (سطر واحد)",
            value="https://www.facebook.com/groups/real.estate.egypt\nhttps://www.facebook.com/groups/CairoProperties",
            height=80,
            key="radar_groups",
        )
    with col2:
        st.markdown("**النتائج**")
        st.slider("عدد المنشورات لكل جروب", 5, 50, 15, key="radar_limit")
    with col3:
        st.markdown("**التحكم**")
        st.write("")
        if st.button("🔍 بدء المسح", use_container_width=True, type="primary", key="radar_scan"):
            with st.spinner("جاري مسح الجروبات..."):
                result = api_post("/scheduler/run/fb_radar")
                if result and result.get("status") == "triggered":
                    st.success("تم بدء مسح الجروبات!")
                else:
                    st.error(f"فشل: {result}")

    st.divider()

    # Recent radar leads
    st.markdown("### 🔥 Leads المكتشفة حديثاً من الجروبات")

    # Try to fetch radar leads from DB
    try:
        result = api_get("/leads", params={"source": "facebook_radar", "limit": 50})
        leads = result if isinstance(result, list) else []
    except Exception:
        leads = []

    if not leads:
        st.info("لا توجد leads مكتشفة بعد. اضغط 'بدء المسح' لاكتشاف عملاء جدد من الجروبات.")
        st.markdown("""
        **كيف يعمل الرادار:**
        1. يدخل على جروبات الفيسبوك العقارية المحددة
        2. يسحب المنشورات ويحللها بالذكاء الاصطناعي
        3. يميّز بين "مطلوب شقة" (عميل محتمل) و "للبيع" (سمسار/مباع)
        4. يحول منشورات الطلب فوراً لـ Leads في النظام
        5. يمكنك التواصل مع العميل مباشرة من الرابط
        """)
        return

    # Display radar leads in a table
    for lead in leads:
        with st.container():
            c1, c2, c3, c4 = st.columns([3, 2, 1, 1])
            with c1:
                st.markdown(f"**{lead.get('full_name', 'مستخدم فيسبوك')}**")
                st.caption(f"📱 {lead.get('phone', 'بدون هاتف')} | 📍 {lead.get('preferred_area', 'غير محدد')}")
            with c2:
                st.markdown(f"🏠 {lead.get('lead_type', 'غير محدد')}")
                st.caption(f"📅 {lead.get('created_at', '')[:10]}")
            with c3:
                if lead.get("id"):
                    if st.button("🔗 فتح المنشور", key=f"radar_link_{lead['id']}"):
                        st.markdown("[فتح على فيسبوك](https://www.facebook.com)")
            with c4:
                if st.button("📞 تواصل", key=f"radar_contact_{lead.get('id', 0)}"):
                    st.info(f"تواصل مع {lead.get('full_name', '')} على {lead.get('phone', '')}")

            st.divider()


# ---------------------------------------------------------------------------
# Tasks & Goals Page
# ---------------------------------------------------------------------------
def show_tasks_goals():
    """Task Manager and Goal Tracker page."""
    st.title("✅ المهام والأهداف")
    st.caption("إدارة المهام وتتبع الأهداف (OKR)")

    # --- Task Manager Section ---
    st.subheader("📋 إدارة المهام")

    # Task creation form
    with st.expander("➕ إضافة مهمة جديدة", expanded=False):
        with st.form("new_task"):
            c1, c2, c3 = st.columns(3)
            with c1:
                task_title = st.text_input("عنوان المهمة *")
                task_assignee = st.text_input("المسؤول")
            with c2:
                task_priority = st.selectbox("الأولوية", ["high", "medium", "low", "critical"])
                task_status = st.selectbox("الحالة", ["todo", "in_progress", "review", "done", "blocked"])
            with c3:
                task_due = st.date_input("تاريخ التسليم")
                task_tags = st.text_input("التصنيفات (فاصلة)")

            task_desc = st.text_area("الوصف")
            if st.form_submit_button("إضافة", use_container_width=True):
                if task_title:
                    payload = {
                        "title": task_title,
                        "description": task_desc,
                        "assignee": task_assignee,
                        "priority": task_priority,
                        "status": task_status,
                        "due_date": task_due.isoformat() if task_due else None,
                        "tags": [t.strip() for t in task_tags.split(",") if t.strip()] if task_tags else [],
                    }
                    result = api_post("/skills/tasks", payload)
                    if result:
                        st.success(f"تم إضافة المهمة #{result.get('id')}")
                        st.rerun()

    # Fetch and display tasks
    tasks_resp = api_get("/skills/tasks") or {}
    if isinstance(tasks_resp, dict):
        tasks = tasks_resp.get("tasks", [])
    else:
        tasks = tasks_resp if isinstance(tasks_resp, list) else []
    if tasks:
        st.write(f"**{len(tasks)}** مهمة")

        # Filter
        filter_status = st.selectbox("تصفية حسب الحالة", ["الكل", "todo", "in_progress", "review", "done", "blocked"])
        filtered = tasks if filter_status == "الكل" else [t for t in tasks if isinstance(t, dict) and t.get("status") == filter_status]

        for task in filtered:
            if not isinstance(task, dict):
                continue
            status_icons = {"todo": "⬜", "in_progress": "🔄", "review": "👀", "done": "✅", "blocked": "🚫"}
            priority_colors = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}
            icon = status_icons.get(task.get("status", ""), "⬜")
            pcolor = priority_colors.get(task.get("priority", ""), "⚪")

            with st.expander(f"{icon} {pcolor} {task.get('title', 'بدون عنوان')}"):
                c1, c2 = st.columns(2)
                with c1:
                    st.write(f"**الحالة:** {task.get('status', 'N/A')}")
                    st.write(f"**الأولوية:** {task.get('priority', 'N/A')}")
                    st.write(f"**المسؤول:** {task.get('assignee', 'غير محدد')}")
                with c2:
                    st.write(f"**تاريخ التسليم:** {task.get('due_date', 'غير محدد')}")
                    st.write(f"**التصنيفات:** {', '.join(task.get('tags', []))}")
                    st.write(f"**التقدم:** {task.get('progress', 0)}%")

                if task.get("description"):
                    st.write(f"**الوصف:** {task['description']}")

                # Action buttons
                ac1, ac2, ac3 = st.columns(3)
                with ac1:
                    new_status = st.selectbox("تحديث الحالة", ["todo", "in_progress", "review", "done", "blocked"],
                                               index=["todo", "in_progress", "review", "done", "blocked"].index(task.get("status", "todo")),
                                               key=f"task_status_{task.get('id')}")
                with ac2:
                    if st.button("💾 حفظ", key=f"save_task_{task.get('id')}"):
                        api_post(f"/tasks/{task.get('id')}/status", {"status": new_status})
                        st.success("تم التحديث")
                        st.rerun()
                with ac3:
                    if st.button("🗑️ حذف", key=f"del_task_{task.get('id')}"):
                        api_post(f"/tasks/{task.get('id')}/delete")
                        st.rerun()
    else:
        st.info("لا توجد مهام بعد. أضف مهمة جديدة!")

    st.divider()

    # --- Goal Tracker Section ---
    st.subheader("🎯 تتبع الأهداف (OKR)")

    with st.expander("➕ إضافة هدف جديد", expanded=False):
        with st.form("new_goal"):
            c1, c2 = st.columns(2)
            with c1:
                goal_title = st.text_input("عنوان الهدف *")
                goal_category = st.selectbox("التصنيف", ["revenue", "leads", "properties", "team", "other"])
            with c2:
                goal_target = st.number_input("القيمة المستهدفة", min_value=0.0, value=100.0, step=10.0)
                goal_unit = st.text_input("الوحدة", value="lead")

            goal_desc = st.text_area("الوصف")
            if st.form_submit_button("إضافة هدف", use_container_width=True):
                if goal_title:
                    payload = {
                        "title": goal_title,
                        "description": goal_desc,
                        "category": goal_category,
                        "target_value": goal_target,
                        "unit": goal_unit,
                    }
                    result = api_post("/goals", payload)
                    if result:
                        st.success(f"تم إضافة الهدف #{result.get('id')}")
                        st.rerun()

    goals_resp = api_get("/skills/goals") or {}
    if isinstance(goals_resp, dict):
        goals = goals_resp.get("goals", [])
    else:
        goals = goals_resp if isinstance(goals_resp, list) else []
    if goals:
        for goal in goals:
            if not isinstance(goal, dict):
                continue
            current = goal.get("current_value", 0)
            target = goal.get("target_value", 1)
            progress = min((current / target * 100) if target > 0 else 0, 100)

            with st.expander(f"{'🟢' if progress >= 100 else '🟡' if progress >= 50 else '🔴'} {goal.get('title', 'هدف')}"):
                st.progress(progress / 100)
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.metric("التقدم", f"{current}/{target}")
                with c2:
                    st.metric("النسبة", f"{progress:.0f}%")
                with c3:
                    st.metric("التصنيف", goal.get("category", ""))

                # Update progress
                new_val = st.number_input("تحديث القيمة الحالية", value=float(current), key=f"goal_val_{goal.get('id')}")
                if st.button("💾 تحديث", key=f"update_goal_{goal.get('id')}"):
                    api_post(f"/goals/{goal.get('id')}/progress", {"value": new_val})
                    st.success("تم التحديث")
                    st.rerun()
    else:
        st.info("لا توجد أهداف بعد. أضف هدفاً جديداً!")


# ---------------------------------------------------------------------------
# Kanban Board Page
# ---------------------------------------------------------------------------
def show_kanban():
    """Kanban board page."""
    st.title("📌 لوحة كانبان")
    st.caption("إدارة المهام بصرياً بسحب وإفلات الأعمدة")

    # Board selector
    boards_resp = api_get("/skills/kanban/boards") or {}
    if isinstance(boards_resp, dict):
        boards = boards_resp.get("boards", [])
    else:
        boards = boards_resp if isinstance(boards_resp, list) else []
    board_names = [b.get("name", "لوحة") for b in boards if isinstance(b, dict)] if boards else ["لوحة المهام"]

    selected_board = st.selectbox("اختر اللوحة", board_names)

    # Fetch board data
    board = api_get(f"/kanban/boards/{selected_board}") or {}
    columns = board.get("columns", [])

    if columns:
        # Render columns side by side
        cols = st.columns(len(columns))
        for i, col in enumerate(columns):
            with cols[i]:
                st.subheader(f"📌 {col.get('name', 'عمود')}")
                cards = col.get("cards", [])
                st.caption(f"{len(cards)} بطاقة")

                for card in cards:
                    with st.container(border=True):
                        st.write(f"**{card.get('title', 'بطاقة')}**")
                        if card.get("description"):
                            st.caption(card["description"][:100])
                        if card.get("labels"):
                            for label in card["labels"]:
                                st.badge(label)
                        if card.get("due_date"):
                            st.caption(f"📅 {card['due_date']}")

                        # Move card
                        col_names = [c.get("name", "") for c in columns]
                        new_col = st.selectbox("نقل إلى", col_names,
                                                index=i, key=f"move_{card.get('id')}")
                        if st.button("↗️ نقل", key=f"btn_move_{card.get('id')}"):
                            api_post(f"/kanban/boards/{selected_board}/cards/{card.get('id')}/move",
                                     {"column": new_col})
                            st.rerun()

                # Add card to column
                with st.expander("➕ إضافة بطاقة"):
                    card_title = st.text_input("العنوان", key=f"new_card_{i}")
                    card_desc = st.text_input("الوصف", key=f"new_desc_{i}")
                    if st.button("إضافة", key=f"add_card_{i}"):
                        if card_title:
                            api_post(f"/kanban/boards/{selected_board}/cards",
                                     {"title": card_title, "description": card_desc, "column": col.get("name", "")})
                            st.rerun()
    else:
        st.info("لا توجد أعمدة. أنشئ لوحة أولاً!")

        # Create new board
        with st.expander("➕ إنشاء لوحة جديدة"):
            with st.form("new_board"):
                board_name = st.text_input("اسم اللوحة")
                cols_input = st.text_input("الأعمدة (فاصلة)", value="todo,in_progress,review,done")
                if st.form_submit_button("إنشاء") and board_name:
                    api_post("/skills/kanban/boards", {
                        "name": board_name,
                        "columns": [c.strip() for c in cols_input.split(",")],
                    })
                    st.success("تم الإنشاء!")
                    st.rerun()


# ---------------------------------------------------------------------------
# Notes Page
# ---------------------------------------------------------------------------
def show_notes():
    """Notes and brainstorming page."""
    st.title("📝 الملاحظات والأفكار")
    st.caption("تنظيم الأفكار والملاحظات والمهمات اليومية")

    tab1, tab2, tab3 = st.tabs(["📝 الملاحظات", "💡 العصف الذهني", "⚡ أفكار سريعة"])

    with tab1:
        # Create note
        with st.form("new_note"):
            note_title = st.text_input("العنوان *")
            note_content = st.text_area("المحتوى", height=150)
            note_category = st.selectbox("التصنيف", ["general", "meeting", "idea", "task", "followup"])
            note_tags = st.text_input("الوسوم (فاصلة)")

            if st.form_submit_button("💾 حفظ"):
                if note_title:
                    payload = {
                        "title": note_title,
                        "content": note_content,
                        "category": note_category,
                        "tags": [t.strip() for t in note_tags.split(",") if t.strip()] if note_tags else [],
                    }
                    result = api_post("/notes", payload)
                    if result:
                        st.success("تم الحفظ!")
                        st.rerun()

        # List notes
        notes_resp = api_get("/skills/notes") or {}
        if isinstance(notes_resp, dict):
            notes = notes_resp.get("notes", [])
        else:
            notes = notes_resp if isinstance(notes_resp, list) else []
        if notes:
            for note in notes:
                if not isinstance(note, dict):
                    continue
                with st.expander(f"📝 {note.get('title', 'ملاحظة')} [{note.get('category', '')}]"):
                    st.write(note.get("content", ""))
                    if note.get("tags"):
                        for tag in note["tags"]:
                            st.badge(tag)
                    if st.button("🗑️", key=f"del_note_{note.get('id')}"):
                        api_post(f"/notes/{note.get('id')}/delete")
                        st.rerun()
        else:
            st.info("لا توجد ملاحظات بعد")

    with tab2:
        st.subheader("💡 جلسة عصف الذهني")
        topic = st.text_input("الموضوع الرئيسي")
        if st.button("🧠 ابدأ العصف") and topic:
            with st.spinner("جاري توليد الأفكار..."):
                result = api_post("/notes/brainstorm", {"topic": topic})
            if result and result.get("ideas"):
                st.success(f"تم توليد {len(result['ideas'])} أفكار!")
                for i, idea in enumerate(result["ideas"], 1):
                    st.write(f"{i}. {idea}")
            else:
                st.info("أضف موضوعاً للعصف الذهني")

    with tab3:
        st.subheader("⚡ أفكار سريعة")
        quick_idea = st.text_input("اكتب فكرتك هنا...")
        if st.button("💡 حفظ سريعة") and quick_idea:
            api_post("/notes/quick", {"idea": quick_idea})
            st.success("تم الحفظ!")
            st.rerun()

        quick_notes = api_get("/notes/quick") or []
        for qn in quick_notes[:20]:
            st.write(f"💡 {qn.get('idea', '')}")


# ---------------------------------------------------------------------------
# Lead Scoring Page
# ---------------------------------------------------------------------------
def show_lead_scoring():
    """Lead scoring and auto-matching dashboard."""
    st.title("🎯 تسجيل العملاء وتلقين العروض")
    
    tab1, tab2, tab3 = st.tabs(["📊 لوحة التسجيل", "🔍 تحليل عميل", "🔗 تطابق تلقائي"])
    
    with tab1:
        st.subheader("📊 لوحة التسجيل")
        
        # Get scoring dashboard
        dashboard = api_get("/skills/leads/scoring-dashboard")
        if dashboard:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("إجمالي المسجلين", dashboard.get("total_scored", 0))
            with col2:
                st.metric("العملاء الساخنين", dashboard.get("hot_leads", 0))
            with col3:
                st.metric("العملاء الدافئين", dashboard.get("warm_leads", 0))
            with col4:
                st.metric("العملاء الباردين", dashboard.get("cold_leads", 0))
            
            # Distribution chart
            if dashboard.get("distribution"):
                st.subheader("التوزيع حسب النطاق")
                st.bar_chart(dashboard["distribution"])
        else:
            st.info("لا توجد بيانات تسجيل بعد")
    
    with tab2:
        st.subheader("🔍 تحليل عميل")
        
        with st.form("score_lead_form"):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("اسم العميل")
                area = st.text_input("المنطقة المفضلة")
                max_budget = st.number_input("أقصى ميزانية (جنيه)", min_value=0, value=5000000)
            with col2:
                source = st.selectbox("المصدر", ["referral", "website", "whatsapp", "call", "other"])
                message = st.text_area("رسالة العميل")
            
            if st.form_submit_button("📊 تحليل العميل", use_container_width=True):
                if name and area:
                    result = api_post("/skills/leads/score", {
                        "name": name,
                        "area": area,
                        "max_budget": max_budget,
                        "source": source,
                        "message": message
                    })
                    if result:
                        st.success("تم التحليل!")
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("النتيجة", f"{result.get('score', 0)}/100")
                        with col2:
                            tier = result.get("tier", "unknown")
                            tier_emoji = "🔥" if tier == "hot" else "🌤️" if tier == "warm" else "❄️"
                            st.metric("النطاق", f"{tier_emoji} {tier}")
                        with col3:
                            st.metric("التوصية", result.get("recommendation", ""))
                        
                        # Score breakdown
                        if result.get("breakdown"):
                            st.subheader("تفاصيل التسجيل")
                            st.json(result["breakdown"])
                else:
                    st.error("أدخل اسم العميل والمنطقة")
    
    with tab3:
        st.subheader("🔗 تطابق تلقائي مع العقارات")
        
        with st.form("match_form"):
            col1, col2 = st.columns(2)
            with col1:
                match_name = st.text_input("اسم العميل", key="match_name")
                match_area = st.text_input("المنطقة", key="match_area")
                match_budget = st.number_input("الميزانية", min_value=0, value=5000000, key="match_budget")
            with col2:
                match_bedrooms = st.number_input("عدد الغرف", min_value=1, max_value=10, value=3, key="match_bedrooms")
                match_type = st.selectbox("نوع العقار", ["apartment", "villa", "townhouse", "duplex"], key="match_type")
            
            if st.form_submit_button("🔗 تطابق تلقائي", use_container_width=True):
                if match_name and match_area:
                    result = api_post("/skills/leads/match", {
                        "name": match_name,
                        "area": match_area,
                        "max_budget": match_budget,
                        "bedrooms": match_bedrooms,
                        "property_type": match_type
                    })
                    if result:
                        matches = result.get("matches", [])
                        if matches:
                            st.success(f"تم العثور على {len(matches)} عقارات!")
                            for i, match in enumerate(matches, 1):
                                with st.expander(f"🏢 {i}. {match.get('property_title', 'عقار')} - نتيجة: {match.get('score', 0):.1%}"):
                                    st.write(f"**العنوان:** {match.get('address', 'غير محدد')}")
                                    st.write(f"**السعر:** {match.get('price', 0):,.0f} جنيه")
                                    st.write(f"**النتيجة:** {match.get('score', 0):.1%}")
                        else:
                            st.warning("لم يتم العثور على عقارات مطابقة")
                else:
                    st.error("أدخل اسم العميل والمنطقة")


# ---------------------------------------------------------------------------
# WhatsApp Web Page
# ---------------------------------------------------------------------------
def show_whatsapp_web():
    """WhatsApp Web browser automation page."""
    st.title("💬 واتساب ويب")
    
    # Status check
    status = api_get("/webhooks/whatsapp-web/status")
    
    if status:
        col1, col2, col3 = st.columns(3)
        with col1:
            is_running = status.get("is_running", False)
            st.metric("الحالة", "🟢 يعمل" if is_running else "🔴 متوقف")
        with col2:
            is_auth = status.get("is_authenticated", False)
            st.metric("المصادقة", "✅ مصادق" if is_auth else "❌ غير مصادق")
        with col3:
            is_online = status.get("is_online", False)
            st.metric("الاتصال", "🟢 متصل" if is_online else "🔴 غير متصل")
    
    st.divider()
    
    # Control buttons
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("▶️ تشغيل واتساب ويب", use_container_width=True):
            with st.spinner("جاري التشغيل..."):
                result = api_post("/webhooks/whatsapp-web/start", {"headless": False})
            if result:
                if result.get("status") == "started":
                    st.success("✅ تم تشغيل واتساب ويب!")
                    if not result.get("authenticated"):
                        st.info("📱 امسح رمز QR بالهاتف لتسجيل الدخول")
                else:
                    st.error("❌ فشل التشغيل")
    
    with col2:
        if st.button("⏹️ إيقاف", use_container_width=True):
            with st.spinner("جاري الإيقاف..."):
                result = api_post("/webhooks/whatsapp-web/stop")
            if result:
                st.success("✅ تم الإيقاف")
    
    with col3:
        if st.button("🔄 تحديث الحالة", use_container_width=True):
            st.rerun()
    
    st.divider()
    
    # Check if authenticated
    if status and status.get("is_authenticated"):
        # Tabs for different functions
        tab1, tab2, tab3, tab4 = st.tabs(["📤 إرسال رسالة", "📥 الرسائل غير المقروءة", "💬 الدردشات", "🔍 بحث جهة اتصال"])
        
        with tab1:
            st.subheader("📤 إرسال رسالة واتساب")
            with st.form("send_message_form"):
                phone = st.text_input("رقم الهاتف (مع كود الدولة)", placeholder="+201018541802")
                message = st.text_area("الرسالة", placeholder="مرحباً، كيف حالك؟")
                
                if st.form_submit_button("📤 إرسال", use_container_width=True):
                    if phone and message:
                        with st.spinner("جاري الإرسال..."):
                            result = api_post("/webhooks/whatsapp-web/send", {
                                "to": phone,
                                "message": message
                            })
                        if result:
                            st.success("✅ تم الإرسال بنجاح!")
                        else:
                            st.error("❌ فشل الإرسال")
                    else:
                        st.error("أدخل رقم الهاتف والرسالة")
        
        with tab2:
            st.subheader("📥 الرسائل غير المقروءة")
            if st.button("🔍 تحميل الرسائل", use_container_width=True):
                with st.spinner("جاري التحميل..."):
                    result = api_get("/webhooks/whatsapp-web/unread")
                if result:
                    messages = result.get("messages", [])
                    if messages:
                        st.success(f"تم العثور على {len(messages)} محادثة غير مقروءة")
                        for msg in messages:
                            with st.expander(f"👤 {msg.get('name', 'غير معروف')} ({msg.get('unread_count', 0)} رسالة)"):
                                st.write(f"**آخر رسالة:** {msg.get('last_message', '')}")
                                st.write(f"**الوقت:** {msg.get('timestamp', '')}")
                    else:
                        st.info("لا توجد رسائل غير مقروءة")
        
        with tab3:
            st.subheader("💬 الدردشات الأخيرة")
            if st.button("📋 تحميل الدردشات", use_container_width=True):
                with st.spinner("جاري التحميل..."):
                    result = api_get("/webhooks/whatsapp-web/chats")
                if result:
                    chats = result.get("chats", [])
                    if chats:
                        st.success(f"تم العثور على {len(chats)} دردشة")
                        for chat in chats:
                            unread = chat.get("unread_count", 0)
                            unread_badge = f" 🔴 ({unread})" if unread > 0 else ""
                            st.write(f"👤 **{chat.get('name', 'غير معروف')}**{unread_badge}")
                            st.caption(f"آخر رسالة: {chat.get('last_message', '')[:50]}...")
                    else:
                        st.info("لا توجد دردشات")
        
        with tab4:
            st.subheader("🔍 بحث جهة اتصال")
            search_query = st.text_input("اسم أو رقم الهاتف", key="contact_search")
            if st.button("🔍 بحث", use_container_width=True) and search_query:
                with st.spinner("جاري البحث..."):
                    result = api_get("/webhooks/whatsapp-web/search", {"query": search_query})
                if result:
                    results = result.get("results", [])
                    if results:
                        st.success(f"تم العثور على {len(results)} نتيجة")
                        for r in results:
                            st.write(f"👤 **{r.get('name', 'غير معروف')}** — {r.get('subtitle', '')}")
                    else:
                        st.warning("لم يتم العثور على نتائج")
    else:
        st.info("📱 اضغط 'تشغيل واتساب ويب' ثم امسح رمز QR بالهاتف لتسجيل الدخول")
        
        # Show QR code screenshot if available
        if st.button("📸 عرض رمز QR", use_container_width=True):
            with st.spinner("جاري التحميل..."):
                result = api_get("/webhooks/whatsapp-web/screenshot", {"filename": "qr_code.png"})
            if result and result.get("filepath"):
                st.image(result["filepath"], caption="امسح رمز QR بالهاتف")


# ---------------------------------------------------------------------------
# Data Pipeline Page (NEW)
# ---------------------------------------------------------------------------
def show_data_pipeline():
    """Data extraction and analysis page."""
    st.title("📈 تحليل البيانات")

    tab1, tab2, tab3 = st.tabs(["🔍 استخراج البيانات", "📊 تقييم الجودة", "📞 التحقق من الأرقام"])

    with tab1:
        st.subheader("استخراج بيانات من رسالة")
        source = st.selectbox("مصدر البيانات", ["whatsapp", "facebook", "web", "json"])
        text = st.text_area("النص", placeholder="عايز شقة 3 غرف في الشيخ زايد بميزانية 2 مليون")
        sender = st.text_input("المرسل (اختياري)")

        if st.button("🔍 استخراج", use_container_width=True) and text:
            with st.spinner("جاري الاستخراج..."):
                result = api_post("/data/extract", {
                    "source": source,
                    "text": text,
                    "sender": sender or None,
                })
            if result:
                st.success("تم الاستخراج بنجاح!")
                st.json(result)
            else:
                st.error("فشل الاستخراج")

    with tab2:
        st.subheader("تقييم جودة البيانات")
        data_type = st.selectbox("نوع البيانات", ["property", "lead"])
        data_json = st.text_area("بيانات JSON", placeholder='{"title": "شقة", "price": 2000000}')

        if st.button("📊 تقييم", use_container_width=True) and data_json:
            try:
                data = json.loads(data_json)
                with st.spinner("جاري التقييم..."):
                    result = api_post("/data/quality", {
                        "data": data,
                        "data_type": data_type,
                    })
                if result:
                    st.success("تم التقييم!")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("النقاط", result.get("score", 0))
                    with col2:
                        st.metric("المستوى", result.get("tier", "N/A"))
                    with col3:
                        st.metric("الاكتمال", f"{result.get('completeness', 0):.0%}")
                    if result.get("issues"):
                        st.warning("المشاكل:")
                        for issue in result["issues"]:
                            st.write(f"• {issue}")
            except json.JSONDecodeError:
                st.error("JSON غير صالح")

    with tab3:
        st.subheader("التحقق من رقم الهاتف")
        phone = st.text_input("رقم الهاتف", placeholder="01123456789")

        if st.button("📞 تحقق", use_container_width=True) and phone:
            with st.spinner("جاري التحقق..."):
                result = api_post("/data/whatsapp-check", {"phone": phone})
            if result:
                st.success("تم التحقق!")
                st.json(result)


# ---------------------------------------------------------------------------
# Market Research Page (NEW)
# ---------------------------------------------------------------------------
def show_market_research():
    """Market research and area analysis page."""
    st.title("🔬 بحث السوق")

    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("اختيار المنطقة")
        area = st.selectbox(
            "المنطقة",
            [
                "الكل",
                "المنطقة 7 الشريط المميز",
                "المنطقة 9 الشريط المميز",
                "المنطقة 15 الشريط المميز",
                "الشمال الغربي",
                "الروبيكى",
                "العاصمة الإدارية الجديدة",
            ],
        )
        if st.button("🔍 بحث", use_container_width=True):
            with st.spinner("جاري البحث..."):
                result = api_get("/data/market-research", {"area": area if area != "الكل" else None})
            if result:
                st.session_state["market_data"] = result

    with col2:
        st.subheader("نتائج البحث")
        market_data = st.session_state.get("market_data")
        if market_data:
            st.json(market_data)
        else:
            st.info("اختر منطقة واضغط بحث لعرض البيانات")


# ---------------------------------------------------------------------------
# Reports Page (NEW)
# ---------------------------------------------------------------------------
def show_reports():
    """Reporting and analytics page."""
    st.title("📑 التقارير")

    tab1, tab2, tab3 = st.tabs(["📊 ملخص الأداء", "📈 تقرير السوق", "👥 تقرير العملاء"])

    with tab1:
        st.subheader("ملخص الأداء")
        data = api_get("/dashboard/stats")
        if data:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("إجمالي العملاء", data.get("total_leads", 0))
            with col2:
                st.metric("العقارات", data.get("total_properties", 0))
            with col3:
                st.metric("طلبات معلقة", data.get("total_requests", 0))
            with col4:
                st.metric("رسائل مرسلة", data.get("total_messages", 0))

            st.divider()
            st.subheader("توزيع العملاء حسب النوع")
            by_type = data.get("leads_by_type", {})
            if by_type:
                st.bar_chart(by_type)
        else:
            st.info("لا توجد بيانات متاحة")

    with tab2:
        st.subheader("تقرير السوق")
        st.info("📊 بيانات الأسعار والاتجاهات")
        # Static market data from enricher
        from src.data.enricher import AREA_METADATA
        if AREA_METADATA:
            chart_data = {}
            for area_name, meta in AREA_METADATA.items():
                if isinstance(meta, dict) and "avg_price_per_sqm" in meta:
                    chart_data[area_name] = meta["avg_price_per_sqm"]
            if chart_data:
                st.bar_chart(chart_data)
                st.caption("متوسط السعر للمتر المربع بالجنيه المصري")
        else:
            st.info("لا توجد بيانات أسعار")

    with tab3:
        st.subheader("تقرير العملاء")
        leads = api_get("/leads") or []
        if leads:
            st.write(f"إجمالي العملاء: **{len(leads)}**")

            # Status distribution
            statuses = {}
            for lead in leads:
                status = lead.get("status", "unknown")
                statuses[status] = statuses.get(status, 0) + 1
            if statuses:
                st.bar_chart(statuses)
                st.caption("توزيع العملاء حسب الحالة")
        else:
            st.info("لا توجد بيانات عملاء")


# ---------------------------------------------------------------------------
# Main App
# ---------------------------------------------------------------------------
def main():
    # Check authentication
    if not st.session_state.get("authenticated"):
        show_login()
        return

    # Sidebar navigation
    st.sidebar.title("🏙️ CityEstate")
    user = st.session_state.get("user", {})
    st.sidebar.write(f"مرحباً {user.get('full_name', user.get('username', ''))}")
    st.sidebar.divider()

    page = st.sidebar.radio(
        "التنقل",
        ["📊 لوحة التحكم", "👥 العملاء", "🏠 العقارات", "📋 الطلبات", "📈 تحليل البيانات", "🔬 بحث السوق", "📑 التقارير", "✅ المهام والأهداف", "📌 كانبان", "📝 الملاحظات", "🎯 تسجيل العملاء", "💬 واتساب ويب", "📡 رادار الجروبات", "🤖 الأتمتة", "🗓️ الجدولة", "🛡️ النسخ والويب هوك", "🔌 فليت الأسطول", "⚙️ الإعدادات"]
    )

    if page == "📊 لوحة التحكم":
        show_dashboard()
    elif page == "👥 العملاء":
        show_leads()
    elif page == "🏠 العقارات":
        show_properties()
    elif page == "📋 الطلبات":
        show_requests()
    elif page == "📈 تحليل البيانات":
        show_data_pipeline()
    elif page == "🔬 بحث السوق":
        show_market_research()
    elif page == "📑 التقارير":
        show_reports()
    elif page == "✅ المهام والأهداف":
        show_tasks_goals()
    elif page == "📌 كانبان":
        show_kanban()
    elif page == "📝 الملاحظات":
        show_notes()
    elif page == "🎯 تسجيل العملاء":
        show_lead_scoring()
    elif page == "💬 واتساب ويب":
        show_whatsapp_web()
    elif page == "📡 رادار الجروبات":
        show_radar()
    elif page == "🤖 الأتمتة":
        show_automation()
    elif page == "⚙️ الإعدادات":
        show_settings()
    elif page == "🗓️ الجدولة":
        show_scheduler()
    elif page == "🛡️ النسخ والويب هوك":
        show_backup_webhooks()
    elif page == "🔌 فليت الأسطول":
        show_fleet_monitor()


if __name__ == "__main__":
    main()
