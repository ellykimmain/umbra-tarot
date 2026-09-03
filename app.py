import smtplib
import re
from email.mime.text import MIMEText
import streamlit as st
import random
import time
import requests
import os
from google import genai
from streamlit_oauth import OAuth2Component
from datetime import datetime

# ── 사주 / 자미두수 라이브러리 ──────────────────────────────────────────────
try:
    import sxtwl
    from py_iztro import Astro
    SAJU_AVAILABLE = True
except ImportError:
    SAJU_AVAILABLE = False

# ── 천간·지지 한자 리스트 ───────────────────────────────────────────────────
GAN_H  = ['甲','乙','丙','丁','戊','己','庚','辛','壬','癸']
ZHI_H  = ['子','丑','寅','卯','辰','巳','午','未','申','酉','戌','亥']
GAN_EN = ['Jia(Wood+)','Yi(Wood-)','Bing(Fire+)','Ding(Fire-)',
          'Wu(Earth+)','Ji(Earth-)','Geng(Metal+)','Xin(Metal-)',
          'Ren(Water+)','Gui(Water-)']
ZHI_EN = ['Zi(Rat)','Chou(Ox)','Yin(Tiger)','Mao(Rabbit)',
          'Chen(Dragon)','Si(Snake)','Wu(Horse)','Wei(Goat)',
          'Shen(Monkey)','You(Rooster)','Xu(Dog)','Hai(Pig)']

# ── 출생 시간 → 지지 인덱스 매핑 ───────────────────────────────────────────
TIME_TO_ZHI = {
    "Unknown":  0,
    "00:00": 0, "00:30": 0,  # 자시
    "01:00": 1, "01:30": 1,  # 축시
    "02:00": 1, "02:30": 1,
    "03:00": 2, "03:30": 2,  # 인시
    "04:00": 2, "04:30": 2,
    "05:00": 3, "05:30": 3,  # 묘시
    "06:00": 3, "06:30": 3,
    "07:00": 4, "07:30": 4,  # 진시
    "08:00": 4, "08:30": 4,
    "09:00": 5, "09:30": 5,  # 사시
    "10:00": 5, "10:30": 5,
    "11:00": 6, "11:30": 6,  # 오시
    "12:00": 6, "12:30": 6,
    "13:00": 7, "13:30": 7,  # 미시
    "14:00": 7, "14:30": 7,
    "15:00": 8, "15:30": 8,  # 신시
    "16:00": 8, "16:30": 8,
    "17:00": 9, "17:30": 9,  # 유시
    "18:00": 9, "18:30": 9,
    "19:00":10, "19:30":10,  # 술시
    "20:00":10, "20:30":10,
    "21:00":11, "21:30":11,  # 해시
    "22:00":11, "22:30":11,
    "23:00": 0, "23:30": 0,  # 자시(야자시)
}

# ── 사주 계산 함수 ──────────────────────────────────────────────────────────
def get_saju_data(year, month, day, hour_index=0):
    """BaZi(사주) 4주 반환. hour_index: 지지 인덱스(0=子,1=丑,…)"""
    if not SAJU_AVAILABLE:
        return None
    try:
        d  = sxtwl.fromSolar(year, month, day)
        yg = d.getYearGZ()
        mg = d.getMonthGZ()
        dg = d.getDayGZ()

        start_map = {0:0,5:0,1:2,6:2,2:4,7:4,3:6,8:6,4:8,9:8}
        htg = (start_map[dg.tg] + hour_index) % 10

        return {
            "year":  f"{GAN_EN[yg.tg]} / {ZHI_EN[yg.dz]}",
            "month": f"{GAN_EN[mg.tg]} / {ZHI_EN[mg.dz]}",
            "day":   f"{GAN_EN[dg.tg]} / {ZHI_EN[dg.dz]}",
            "hour":  f"{GAN_EN[htg]} / {ZHI_EN[hour_index]}",
            "day_master": GAN_EN[dg.tg],
            "raw": {
                "year":  f"{GAN_H[yg.tg]}{ZHI_H[yg.dz]}",
                "month": f"{GAN_H[mg.tg]}{ZHI_H[mg.dz]}",
                "day":   f"{GAN_H[dg.tg]}{ZHI_H[dg.dz]}",
                "hour":  f"{GAN_H[htg]}{ZHI_H[hour_index]}",
            }
        }
    except Exception:
        return None

# ── 자미두수 계산 함수 ──────────────────────────────────────────────────────
def get_ziwei_data(year, month, day, hour_index, gender_str='Female'):
    """자미두수 명반 핵심 정보 반환"""
    if not SAJU_AVAILABLE:
        return None
    try:
        a = Astro()
        astrolabe = a.by_solar(f'{year}-{month}-{day}', hour_index, gender_str, True, 'ko-KR')
        palaces = {}
        for p in astrolabe.palaces:
            stars = [s.name for s in p.major_stars]
            palaces[p.name] = stars if stars else ["Empty Palace"]
        return {
            "soul_star":  astrolabe.soul,
            "body_star":  astrolabe.body,
            "five_elem":  astrolabe.five_elements_class,
            "wealth_palace": palaces.get("재백", ["N/A"]),
            "career_palace": palaces.get("관록", ["N/A"]),
            "life_palace":   palaces.get("명궁", ["N/A"]),
        }
    except Exception:
        return None
        
# ── 베딕 점성술(Jyotisha) 계산 함수 ──────────────────────────────────────────
try:
    from jyotishganit import calculate_birth_chart
    VEDIC_AVAILABLE = True
except ImportError:
    VEDIC_AVAILABLE = False

CITY_COORDS = {
    "Seoul": {"lat": 37.5665, "lon": 126.9780, "tz": 9.0},
    "Busan": {"lat": 35.1796, "lon": 129.0756, "tz": 9.0},
    "Daejeon": {"lat": 36.3504, "lon": 127.3845, "tz": 9.0},
    "Daegu": {"lat": 35.8714, "lon": 128.6014, "tz": 9.0},
    "Incheon": {"lat": 37.4563, "lon": 126.7052, "tz": 9.0},
    "Jeju": {"lat": 33.4996, "lon": 126.5312, "tz": 9.0},
    "New York": {"lat": 40.7128, "lon": -74.0060, "tz": -5.0},
    "Los Angeles": {"lat": 34.0522, "lon": -118.2437, "tz": -8.0},
    "Chicago": {"lat": 41.8781, "lon": -87.6298, "tz": -6.0},
    "Seattle": {"lat": 47.6062, "lon": -122.3321, "tz": -8.0},
    "Houston": {"lat": 29.7604, "lon": -95.3698, "tz": -6.0},
    "London": {"lat": 51.5074, "lon": -0.1278, "tz": 0.0},
    "Manchester": {"lat": 53.4808, "lon": -2.2426, "tz": 0.0},
    "Edinburgh": {"lat": 55.9533, "lon": -3.1883, "tz": 0.0},
    "Birmingham": {"lat": 52.4862, "lon": -1.8904, "tz": 0.0},
    "Tokyo": {"lat": 35.6762, "lon": 139.6503, "tz": 9.0},
    "Osaka": {"lat": 34.6937, "lon": 135.5023, "tz": 9.0},
    "Kyoto": {"lat": 35.0116, "lon": 135.7681, "tz": 9.0},
    "Fukuoka": {"lat": 33.5902, "lon": 130.4017, "tz": 9.0},
    "Sydney": {"lat": -33.8688, "lon": 151.2093, "tz": 10.0},
    "Melbourne": {"lat": -37.8136, "lon": 144.9631, "tz": 10.0},
    "Brisbane": {"lat": -27.4698, "lon": 153.0251, "tz": 10.0},
    "Perth": {"lat": -31.9505, "lon": 115.8605, "tz": 8.0},
    "Toronto": {"lat": 43.6510, "lon": -79.3470, "tz": -5.0},
    "Vancouver": {"lat": 49.2827, "lon": -123.1207, "tz": -8.0},
    "Montreal": {"lat": 45.5017, "lon": -73.5673, "tz": -5.0},
    "Calgary": {"lat": 51.0447, "lon": -114.0719, "tz": -7.0},
    "Bangkok": {"lat": 13.7563, "lon": 100.5018, "tz": 7.0},
    "Chiang Mai": {"lat": 18.7883, "lon": 98.9853, "tz": 7.0},
    "Phuket": {"lat": 7.8804, "lon": 98.3922, "tz": 7.0},
    "Singapore": {"lat": 1.3521, "lon": 103.8198, "tz": 8.0},
    "Other": {"lat": 37.5665, "lon": 126.9780, "tz": 9.0}
}

def get_vedic_data(year, month, day, hour_str, city_name):
    if not VEDIC_AVAILABLE:
        return "\n[Vedic Error: Library not found. Reboot app.]"
    
    if city_name not in CITY_COORDS:
        return f"\n[Vedic Error: Coordinates for '{city_name}' not found.]"
    
    hr, mn = 12, 0
    if ":" in hour_str:
        hr, mn = map(int, hour_str.split(":"))
        
    coords = CITY_COORDS.get(city_name)
    birth_dt = datetime(year, month, day, hr, mn, 0)
    
    try:
        chart = calculate_birth_chart(
            birth_date=birth_dt,
            latitude=coords["lat"],
            longitude=coords["lon"],
            timezone_offset=coords["tz"]
        )
        
        lines = ["\n=== Vedic Astrology (Jyotisha) ==="]
        if hasattr(chart, 'd1_chart') and hasattr(chart.d1_chart, 'planets'):
            for p in chart.d1_chart.planets:
                p_name = p.get('celestial_body', '') if isinstance(p, dict) else getattr(p, 'celestial_body', '')
                p_sign = p.get('sign', '') if isinstance(p, dict) else getattr(p, 'sign', '')
                if p_name and p_sign:
                    lines.append(f"- {p_name}: {p_sign}")
        
        return "\n".join(lines) if len(lines) > 1 else "\n[Vedic Error: Planet data parsing failed]"
    except Exception as e:
        return f"\n[Vedic Calculation Error: {e}]"

# ── 수리학(Numerology) 계산 ─────────────────────────────────────────────────
def reduce_num(n):
    while n > 9 and n not in (11, 22, 33):
        n = sum(int(d) for d in str(n))
    return n

def get_numerology(year, month, day):
    lp = reduce_num(sum(int(c) for c in f"{year}{month:02d}{day:02d}"))
    now = datetime.now()
    py = reduce_num(month + reduce_num(day) + reduce_num(now.year))
    pm = reduce_num(py + now.month)
    pd = reduce_num(pm + now.day)
    return {"life_path": lp, "personal_year": py, "personal_month": pm, "personal_day": pd}

# ── 점성술 요약 구성 ─────────────────────────────────────────────────────────
def build_astrology_block(year, month, day, hour_str, birth_place, gender):
    lines = []

    # BaZi
    zhi_idx = TIME_TO_ZHI.get(hour_str, 0)
    saju = get_saju_data(year, month, day, zhi_idx)
    if saju:
        lines.append("=== BaZi (Four Pillars) ===")
        lines.append(f"Year Pillar : {saju['year']}")
        lines.append(f"Month Pillar: {saju['month']}")
        lines.append(f"Day Pillar  : {saju['day']}")
        lines.append(f"Hour Pillar : {saju['hour']}")
        lines.append(f"Day Master  : {saju['day_master']}")

    # 자미두수
    gender_str = 'Male' if gender == 'M' else 'Female'
    ziwei = get_ziwei_data(year, month, day, zhi_idx, gender_str)
    if ziwei:
        lines.append("\n=== Purple Star Astrology (Zi Wei Dou Shu) ===")
        lines.append(f"Soul Star (Ming Gong) : {ziwei['soul_star']}")
        lines.append(f"Body Star             : {ziwei['body_star']}")
        lines.append(f"Five Elements Class   : {ziwei['five_elem']}")
        lines.append(f"Wealth Palace Stars   : {', '.join(ziwei['wealth_palace'])}")
        lines.append(f"Career Palace Stars   : {', '.join(ziwei['career_palace'])}")

    # 수리학
    num = get_numerology(year, month, day)
    lines.append("\n=== Numerology ===")
    lines.append(f"Life Path Number  : {num['life_path']}")
    lines.append(f"Personal Year     : {num['personal_year']}")
    lines.append(f"Personal Month    : {num['personal_month']}")
    lines.append(f"Personal Day      : {num['personal_day']}")

    # 베딕 점성술 추가 (birth_place에서 도시 이름만 추출하여 넘김)
    city = birth_place.split(",")[0].strip()
    vedic_text = get_vedic_data(year, month, day, hour_str, city)
    lines.append(vedic_text)

    if not lines:
        lines.append("Cosmic calculation unavailable — reading based on birth data only.")

    return "\n".join(lines)

# ── Streamlit 시크릿 로드 ───────────────────────────────────────────────────
api_key       = st.secrets["GEMINI_API_KEY"]
client        = genai.Client(api_key=api_key)
CLIENT_ID     = st.secrets["GOOGLE_CLIENT_ID"]
CLIENT_SECRET = st.secrets["GOOGLE_CLIENT_SECRET"]
REDIRECT_URI  = st.secrets["REDIRECT_URI"]
ADMIN_EMAIL   = st.secrets.get("ADMIN_EMAIL", "")   # secrets에 넣어서 코드에 노출 방지

AUTHORIZE_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT     = "https://oauth2.googleapis.com/token"
REVOKE_ENDPOINT    = "https://oauth2.googleapis.com/revoke"

oauth2 = OAuth2Component(
    CLIENT_ID, CLIENT_SECRET,
    AUTHORIZE_ENDPOINT, TOKEN_ENDPOINT, TOKEN_ENDPOINT, REVOKE_ENDPOINT
)

# ── 페이지 설정 & CSS ───────────────────────────────────────────────────────
st.set_page_config(
    page_title="THE RAW TAROT: Shadow Prophecy",
    layout="centered",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; color: #212529; }
    .main-title { text-align: center; color: #1a1a2e; font-family: 'Cinzel', serif;
                  letter-spacing: 2px; font-size: 2.5rem; font-weight: 700; }
    .sub-title  { text-align: center; color: #6c757d; font-size: 1.05rem; }
    label, [data-testid="stWidgetLabel"] p { color: #212529 !important; font-weight: 600 !important; }
    div.stButton > button:first-child {
        background-color: #1a1a2e; color: #f3e5ab;
        border: 1px solid #1a1a2e; font-weight: 600;
        border-radius: 5px; width: 100%; }
    div.stButton > button:first-child:hover { background-color: #33334d; color: #ffffff; }
    section[data-testid="stSidebar"] { background-color: #f1f3f5 !important; }
    section[data-testid="stSidebar"] *,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] p { color: #212529 !important; }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='main-title'>THE RAW TAROT</h1>", unsafe_allow_html=True)
st.markdown("<p class='sub-title'>Pierce the veil of your shadow self. Unearth the truths hidden in the astral dark.</p>", unsafe_allow_html=True)

# ── Google 로그인 ───────────────────────────────────────────────────────────
if "google_token" not in st.session_state:
    st.markdown("### ✨ Claim Your 3-Day Free Trial")

    # 💡 [경고 문구 추가]
    st.error("""
    **⚠️ WARNING : ENTER AT YOUR OWN RISK**  
    This oracle does not provide comfort, false hope, or gentle healing.  
    It is designed to tear down your illusions and deliver brutal, unvarnished cosmic truths.  
    If you are emotionally fragile or seeking sweet lies, **DO NOT PROCEED**.
    """)
    
    st.markdown("Unlock the gates. Sign in now to receive your **complimentary 'Who Am I' shadow reading** and **1 deep custom query**.")
    st.info("Google Login is required to begin your free trial and enter the astral realm.")

    st.markdown("<br><h4 style='text-align:center;color:#1a1a2e;'>Glimpse the Shadows (Sample Reading)</h4>", unsafe_allow_html=True)
    cols = st.columns(3)
    for col, img in zip(cols, ["The_Fool", "The_Tower", "The_Devil"]):
        with col:
            for ext in [".png", ".jpg"]:
                p = f"images/{img}{ext}"
                if os.path.exists(p):
                    st.image(p, caption=img.replace("_"," "), use_container_width=True)
                    break

    st.markdown("""
    <div style="background-color:#e9ecef;padding:15px;border-left:4px solid #1a1a2e;
                border-radius:4px;color:#212529;font-style:italic;font-size:0.95rem;margin-bottom:25px;">
    "You ask about wealth, yet The Tower reveals your foundation is built on self-deception.
    The collapse is not a punishment, but a necessary clearing of your illusions…"
    </div>""", unsafe_allow_html=True)

    result = oauth2.authorize_button(
        name="Continue with Google",
        icon="https://www.google.com/favicon.ico",
        redirect_uri=REDIRECT_URI,
        scope="openid email profile",
        key="google_login",
        use_container_width=True
    )
    if result:
        st.session_state["google_token"] = result.get("token")
        st.rerun()
    st.stop()

# ── 유저 이메일 추출 ────────────────────────────────────────────────────────
if "user_email" not in st.session_state:
    try:
        headers   = {"Authorization": f"Bearer {st.session_state['google_token']['access_token']}"}
        user_info = requests.get("https://www.googleapis.com/oauth2/v1/userinfo", headers=headers).json()
        st.session_state["user_email"] = user_info.get("email", "")
    except Exception:
        st.session_state["user_email"] = ""

user_email = st.session_state["user_email"]

# ── 사이드바 ────────────────────────────────────────────────────────────────
st.sidebar.markdown("### 🪐 Membership Tiers")
st.sidebar.radio("Select Your Plan", ["Free Trial (Active)", "Pro Oracle (Available Sept 20th)"], index=0, disabled=True)
st.sidebar.info("✨ **Grand Opening!** Currently in Free Trial Period.")
st.sidebar.warning("💎 **Pro Oracle** features will unlock on September 20st.")
st.sidebar.markdown("---")
st.sidebar.markdown("### 🔮 Oracle Mode")
reading_mode = st.sidebar.radio(
    "Choose Reading Focus",
    ["1. Who Am I? (Raw Shadow Discovery)", "2. Custom Oracle Query (Deep Question)"]
)
st.sidebar.markdown("---")
st.sidebar.markdown("### 🎧 Frequency Alignment")
st.sidebar.caption("Realign your shattered frequencies after the reading.")
st.sidebar.link_button("Tune in at SynchroVault", "https://www.youtube.com/@SynchroVault")

# ── 환영 메시지 ─────────────────────────────────────────────────────────────
if user_email:
    st.markdown(f"""
        <div style="background-color:#e9ecef;padding:15px;border-radius:8px;
                    border:1px solid #ced4da;color:#212529;margin-bottom:20px;">
        🌌 <b>Welcome, voyager.</b> Prophecy will be sent to:
        <span style="color:#d97706;font-weight:bold;">{user_email}</span>
        </div>""", unsafe_allow_html=True)

# ── 국가-도시 매핑 ──────────────────────────────────────────────────────────
COUNTRY_CITY = {
    "South Korea": ["Seoul","Busan","Daejeon","Daegu","Incheon","Jeju","Other"],
    "United States": ["New York","Los Angeles","Chicago","Seattle","Houston","Other"],
    "United Kingdom": ["London","Manchester","Edinburgh","Birmingham","Other"],
    "Japan": ["Tokyo","Osaka","Kyoto","Fukuoka","Other"],
    "Australia": ["Sydney","Melbourne","Brisbane","Perth","Other"],
    "Canada": ["Toronto","Vancouver","Montreal","Calgary","Other"],
    "Thailand": ["Bangkok","Chiang Mai","Phuket","Other"],
    "Singapore": ["Singapore"],
    "Other": ["Other"],
}

# ── 입력 폼 ─────────────────────────────────────────────────────────────────
is_admin = (user_email == ADMIN_EMAIL)

user_name   = st.text_input("Your Name / Alias", "Kim Uyoun" if is_admin else "")
gender      = st.radio("Gender", ["Female", "Male"], horizontal=True)

col1, col2  = st.columns(2)
with col1:
    birth_country = st.selectbox("Country of Birth", list(COUNTRY_CITY.keys()), index=0 if is_admin else 0)
with col2:
    birth_city    = st.selectbox("City of Birth", COUNTRY_CITY[birth_country])

if birth_city == "Other":
    birth_city = st.text_input("Please specify your city", "")

birth_place = f"{birth_city}, {birth_country}"

birth_year  = st.number_input("Year",  min_value=1930, max_value=2026, value=1984 if is_admin else 1988, step=1)
birth_month = st.number_input("Month", min_value=1,    max_value=12,   value=9    if is_admin else 6,    step=1)
birth_day   = st.number_input("Day",   min_value=1,    max_value=31,   value=20   if is_admin else 15,   step=1)

time_options = ["Unknown"] + [f"{h:02d}:{m:02d}" for h in range(24) for m in (0, 30)]
birth_time   = st.selectbox("Time of Birth", time_options)
if birth_time == "Unknown":
    st.caption("⚠️ For deeper cosmic accuracy, adding your birth time is recommended.")

# ── 질문 모드 ───────────────────────────────────────────────────────────────
if "2." in reading_mode or "Custom" in reading_mode:
    QUESTION_OPTIONS = [
        "When will this current financial hardship finally improve?",
        "What is the hidden block preventing my wealth and success?",
        "What is the brutal truth about my connection with my current partner?",
        "I am single. When will authentic love pierce through my isolation?",
        "Am I on the right path with my current business or career?",
        "Why do I keep repeating the same destructive patterns?",
        "What truth am I aggressively avoiding right now?",
        "What does my shadow self desperately want me to know?",
        "Direct Input (Write your own query)",
    ]
    selected_query = st.selectbox("Choose your query or select Direct Input", QUESTION_OPTIONS)
    user_question  = st.text_area("Your Deep Query", placeholder="e.g., Will my new venture succeed?") \
                     if selected_query == "Direct Input (Write your own query)" else selected_query
else:
    user_question = ""

# ── 카드 이름 → 파일명 매핑 ─────────────────────────────────────────────────
CARD_FILES = {
    "The Fool":"The_Fool","The Magician":"The_Magician","The High Priestess":"The_High_Priestess",
    "The Empress":"The_Empress","The Emperor":"The_Emperor","The Hierophant":"The_Hierophant",
    "The Lovers":"The_Lovers","The Chariot":"The_Chariot","Strength":"Strength",
    "The Hermit":"The_Hermit","Wheel of Fortune":"Wheel_of_Fortune","Justice":"Justice",
    "The Hanged Man":"The_Hanged_Man","Death":"The_Death","Temperance":"Temperance",
    "The Devil":"The_Devil","The Tower":"The_Tower","The Star":"The_Star",
    "The Moon":"The_Moon","The Sun":"The_Sun","Judgement":"Judgement","The World":"The_World",
}

MAJOR_ARCANA = list(CARD_FILES.keys())

# ── 오라클 버튼 ─────────────────────────────────────────────────────────────
if st.button("Consult the Oracle & Draw Cards"):

    # 하루 1회 제한 (세션 기반 — 업그레이드 시 DB 연동 권장)
    today_key = f"{user_email}_{datetime.now().strftime('%Y-%m-%d')}"
    if "prophesied" not in st.session_state:
        st.session_state["prophesied"] = {}
    if st.session_state["prophesied"].get(today_key, 0) >= 1:
        st.error("🌙 The Oracle has already spoken to you today. Return when the stars realign tomorrow.")
        st.stop()

    # 로딩 메시지
    ph = st.empty()
    for msg in [
        "🌌 Tunnelling through the astral plane...",
        "🔮 Consulting BaZi & Purple Star alignment...",
        "🃏 Drawing the shadow arcana cards...",
        "⚡ Channeling the blunt prophecy...",
    ]:
        ph.markdown(f"<p style='text-align:center;color:#6c757d;font-size:1.1rem;font-weight:bold;'>{msg}</p>",
                    unsafe_allow_html=True)
        time.sleep(1.5)

    # ── 실제 사주/자미두수 데이터 구성 ──────────────────────────────────────
    gender_str    = "Male" if gender == "Male" else "Female"
    astrology_data = build_astrology_block(
        int(birth_year), int(birth_month), int(birth_day),
        birth_time, birth_place, "M" if gender == "Male" else "F"
    )

    # 카드 드로우
    drawn_keys    = random.sample(MAJOR_ARCANA, 4)
    current_date  = datetime.now().strftime("%Y-%m-%d")
    question_ctx  = f"\nUSER'S DEEP QUERY: {user_question}" if user_question else ""

    prompt = f"""You are a highly skilled, blunt, and slightly cynical traditional Thai fortune teller.
You speak directly, offering no comforting lies, yet you NEVER end in despair. Deliver cold, hard truths based on the cosmic data, but ALWAYS provide a calculated, positive breakthrough and concrete survival strategies.
Use a tone that is piercing, mystical, and authoritative, acting as a stern but deeply empowering mentor.

[CRITICAL INSTRUCTION]
You MUST read the provided [Vedic Astrology (Jyotisha)] data. Cross-reference the client's karmic traits and planetary positions with their BaZi/Ziwei data, and include this analysis in at least one sentence in your response.

CURRENT DATE: {current_date} (All future predictions must start strictly from this date onwards.)

USER PROFILE
Name       : {user_name}
Gender     : {gender_str}
Birth Place: {birth_place}
Birth Date : {int(birth_year)}-{int(birth_month):02d}-{int(birth_day):02d}
Birth Time : {birth_time}{question_ctx}

COSMIC CALCULATIONS (BaZi · Purple Star Astrology · Vedic · Numerology)
{astrology_data}

DRAWN ARCANAS
1. (Current Situation): {drawn_keys[0]}
2. (Obstacle/Harsh Truth): {drawn_keys[1]}
3. (Hidden Strength/Opportunity): {drawn_keys[2]}
4. (The Key/Solution): {drawn_keys[3]}

CRITICAL FORMATTING INSTRUCTION:
Structure your response EXACTLY using the delimiters below. No text outside these blocks.

@INTRO@
(Analyze the current situation and face the harsh reality using BaZi, Ziwei, and Vedic data. Brutally honest but objective — 3-4 sentences)

@CARD_1@
(Objective analysis of the current problem and crisis reflected in {drawn_keys[0]} — 4-5 sentences)

@CARD_2@
(Point out the obstacles or the painful truth the client is avoiding, based on {drawn_keys[1]} — 4-5 sentences)

@CARD_3@
(MANDATORY POSITIVITY: Find and highlight the client's unique hidden strengths, positive cosmic energy, and opportunity for a turnaround based on {drawn_keys[2]}. Do not just criticize; show them their hidden weapon — 4-5 sentences)

@CARD_4@
(Based on {drawn_keys[3]}, use the positive energy identified in Card 3 as a lever to provide a realistic, concrete, and highly actionable solution they can execute TODAY. Open the door to a calculated hope and salvation — 4-5 sentences)

@CONCLUSION@
(Summarize the combined cosmic data and cards, leaving them with powerful, firm, and positively empowering behavioral guidelines to take immediate action — 10-11 sentences)
"""

    try:
        response = client.models.generate_content(
            model="gemini-3.6-flash",   # ✅ 수정된 모델명
            contents=prompt
        )
        st.session_state["prophesied"][today_key] = 1
        ph.empty()
        st.success("Prophecy manifested.")

        res_text = response.text

        def extract(tag, next_tag, text):
            try:
                return text.split(tag)[1].split(next_tag)[0].strip()
            except Exception:
                return ""

        # 💡 [핵심 수정] 4번째 카드(CARD_4) 파싱 및 렌더링 추가
        if "@INTRO@" in res_text and "@CARD_1@" in res_text and "@CONCLUSION@" in res_text:
            intro_text      = extract("@INTRO@",      "@CARD_1@",      res_text)
            card1_text      = extract("@CARD_1@",     "@CARD_2@",      res_text)
            card2_text      = extract("@CARD_2@",     "@CARD_3@",      res_text)
            card3_text      = extract("@CARD_3@",     "@CARD_4@",      res_text)
            card4_text      = extract("@CARD_4@",     "@CONCLUSION@",  res_text)
            conclusion_text = res_text.split("@CONCLUSION@")[1].strip() if "@CONCLUSION@" in res_text else ""

            st.markdown(f"""<div style='background-color:#e9ecef;padding:20px;
                            border-radius:5px;color:#1a1a2e;margin-bottom:20px;'>
                            {intro_text}</div>""", unsafe_allow_html=True)

            cards_text = [card1_text, card2_text, card3_text, card4_text]

            for idx, (card, card_text) in enumerate(zip(drawn_keys, cards_text)):
                # 4번째 카드는 구원의 열쇠로 오렌지색 렌더링
                if idx == 3:
                    st.markdown(f"<h3 style='text-align:center;color:#d97706;margin-top:40px;'>🌟 4. The Key ({card})</h3>",
                                unsafe_allow_html=True)
                else:
                    st.markdown(f"<h3 style='text-align:center;color:#1a1a2e;margin-top:30px;'>{idx+1}. {card}</h3>",
                                unsafe_allow_html=True)
                
                c1, c2, c3 = st.columns([1, 1.5, 1])
                with c2:
                    base = CARD_FILES.get(card, "")
                    shown = False
                    for ext in [".jpg", ".png"]:
                        p = f"images/{base}{ext}"
                        if os.path.exists(p):
                            st.image(p, use_container_width=True)
                            shown = True
                            break
                    if not shown:
                        st.error(f"[{card} image missing]")
                st.info(card_text)

            st.markdown("<hr>", unsafe_allow_html=True)
            st.warning(conclusion_text)
        else:
            st.info(res_text)
            cols = st.columns(4)
            for i, card in enumerate(drawn_keys):
                with cols[i]:
                    base = CARD_FILES.get(card, "")
                    for ext in [".jpg", ".png"]:
                        p = f"images/{base}{ext}"
                        if os.path.exists(p):
                            st.image(p, use_container_width=True)
                            break

        # ── 이메일 발송 ──────────────────────────────────────────────────────
        try:
            # 마크다운 → HTML 변환
            clean = res_text
            for tag in ["@INTRO@","@CARD_1@","@CARD_2@","@CARD_3@","@CONCLUSION@"]:
                clean = clean.replace(tag, "")
            clean = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', clean)
            clean = re.sub(r'\*(.*?)\*',     r'<em>\1</em>',         clean)
            html_body_content = clean.replace('\n', '<br>')

            html_body = f"""
<html>
<body style="background-color:#050505;color:#d4d4d4;font-family:'Helvetica Neue',Arial,sans-serif;
             padding:20px;line-height:1.6;margin:0;">
  <div style="max-width:600px;margin:0 auto;border:1px solid #222;padding:40px;background:#0a0a0a;">
    <h2 style="text-align:center;color:#fff;letter-spacing:4px;
               border-bottom:1px solid #333;padding-bottom:20px;font-weight:normal;">
      THE RAW TAROT
    </h2>
    <p style="font-size:14px;color:#888;text-transform:uppercase;letter-spacing:1px;">
      Prophecy for <strong>{user_name}</strong>
    </p>
    <div style="font-size:15px;margin-top:30px;color:#ccc;">
      {html_body_content}
    </div>
    <hr style="border:0;border-top:1px solid #222;margin:40px 0;">
    <div style="text-align:center;">
      <h3 style="color:#fff;letter-spacing:2px;font-weight:normal;">🎧 FREQUENCY ALIGNMENT</h3>
      <p style="font-size:13px;color:#888;margin-bottom:30px;">
        Have you faced the brutal truth?<br>
        It is time to realign your shattered frequencies and attract physical wealth.
      </p>
      <div style="margin-bottom:15px;">
        <a href="https://buly.kr/3u5ctxV"
           style="display:inline-block;padding:12px 24px;border:1px solid #555;
                  background:transparent;color:#fff;text-decoration:none;
                  font-size:12px;font-weight:bold;letter-spacing:2px;
                  text-transform:uppercase;width:220px;text-align:center;">
          Return to Prophecy
        </a>
      </div>
      <div>
        <a href="https://www.youtube.com/@SynchroVault"
           style="display:inline-block;padding:12px 24px;background:#fff;color:#000;
                  text-decoration:none;font-size:12px;font-weight:bold;
                  letter-spacing:2px;text-transform:uppercase;
                  width:220px;text-align:center;">
          Synchronize Vibration
        </a>
      </div>
    </div>
  </div>
</body>
</html>"""

            msg = MIMEText(html_body, "html")
            msg["Subject"] = "👁️ Your Shadow Prophecy"
            msg["From"]    = st.secrets["EMAIL_SENDER"]
            msg["To"]      = user_email

            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(st.secrets["EMAIL_SENDER"], st.secrets["EMAIL_PASSWORD"])
                server.send_message(msg)

        except Exception as e:
            st.error(f"Email dispatch failed: {e}")

    except Exception as e:
        ph.empty()
        err = str(e)
        if "429" in err or "RESOURCE_EXHAUSTED" in err:
            st.error("🌙 The astral energy is depleted. Today's complimentary prophecies have concluded. Return after midnight.")
        else:
            st.error(f"The astral connection was lost. Please try again. ({err})")
