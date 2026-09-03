import smtplib
import html
import os
import random
import time
import requests

from datetime import datetime
from email.mime.text import MIMEText
from zoneinfo import ZoneInfo

import streamlit as st
from google import genai
from streamlit_oauth import OAuth2Component
from supabase import create_client, Client


# =========================================================
# 기본 설정
# =========================================================

KST = ZoneInfo("Asia/Seoul")


def now_kst():
    return datetime.now(KST)


def today_kst():
    return now_kst().strftime("%Y-%m-%d")


# =========================================================
# Supabase DB
# =========================================================

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_SERVICE_ROLE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# =========================================================
# 사주 라이브러리
# =========================================================

try:
    import sxtwl
    SAJU_AVAILABLE = True
except ImportError:
    SAJU_AVAILABLE = False


GAN_H = ['甲','乙','丙','丁','戊','己','庚','辛','壬','癸']
ZHI_H = ['子','丑','寅','卯','辰','巳','午','未','申','酉','戌','亥']

TIME_TO_ZHI = {
    "모름": 0,
    "00:00": 0, "00:30": 0,
    "01:00": 1, "01:30": 1, "02:00": 1, "02:30": 1,
    "03:00": 2, "03:30": 2, "04:00": 2, "04:30": 2,
    "05:00": 3, "05:30": 3, "06:00": 3, "06:30": 3,
    "07:00": 4, "07:30": 4, "08:00": 4, "08:30": 4,
    "09:00": 5, "09:30": 5, "10:00": 5, "10:30": 5,
    "11:00": 6, "11:30": 6, "12:00": 6, "12:30": 6,
    "13:00": 7, "13:30": 7, "14:00": 7, "14:30": 7,
    "15:00": 8, "15:30": 8, "16:00": 8, "16:30": 8,
    "17:00": 9, "17:30": 9, "18:00": 9, "18:30": 9,
    "19:00": 10, "19:30": 10, "20:00": 10, "20:30": 10,
    "21:00": 11, "21:30": 11, "22:00": 11, "22:30": 11,
    "23:00": 0, "23:30": 0,
}


def get_saju_data(year, month, day, hour_index=0):
    if not SAJU_AVAILABLE:
        return None

    try:
        d = sxtwl.fromSolar(year, month, day)
        yg, mg, dg = d.getYearGZ(), d.getMonthGZ(), d.getDayGZ()

        start_map = {
            0: 0, 5: 0,
            1: 2, 6: 2,
            2: 4, 7: 4,
            3: 6, 8: 6,
            4: 8, 9: 8,
        }

        htg = (start_map[dg.tg] + hour_index) % 10

        return {
            "year": f"{GAN_H[yg.tg]}{ZHI_H[yg.dz]}",
            "month": f"{GAN_H[mg.tg]}{ZHI_H[mg.dz]}",
            "day": f"{GAN_H[dg.tg]}{ZHI_H[dg.dz]}",
            "hour": f"{GAN_H[htg]}{ZHI_H[hour_index]}",
            "day_master": GAN_H[dg.tg],
        }

    except Exception:
        return None


# =========================================================
# 베딕 점성술
# =========================================================

try:
    from jyotishganit import calculate_birth_chart
    VEDIC_AVAILABLE = True
except ImportError:
    VEDIC_AVAILABLE = False


CITY_COORDS = {
    "서울": {"lat": 37.5665, "lon": 126.9780, "tz": 9.0},
    "대전": {"lat": 36.3504, "lon": 127.3845, "tz": 9.0},
    "대구": {"lat": 35.8714, "lon": 128.6014, "tz": 9.0},
    "부산": {"lat": 35.1796, "lon": 129.0756, "tz": 9.0},
    "제주": {"lat": 33.4996, "lon": 126.5312, "tz": 9.0},
    "뉴욕": {"lat": 40.7128, "lon": -74.0060, "tz": -5.0},
    "로스앤젤레스": {"lat": 34.0522, "lon": -118.2437, "tz": -8.0},
    "시카고": {"lat": 41.8781, "lon": -87.6298, "tz": -6.0},
    "시애틀": {"lat": 47.6062, "lon": -122.3321, "tz": -8.0},
    "런던": {"lat": 51.5074, "lon": -0.1278, "tz": 0.0},
    "맨체스터": {"lat": 53.4808, "lon": -2.2426, "tz": 0.0},
    "에든버러": {"lat": 55.9533, "lon": -3.1883, "tz": 0.0},
    "도쿄": {"lat": 35.6762, "lon": 139.6503, "tz": 9.0},
    "오사카": {"lat": 34.6937, "lon": 135.5023, "tz": 9.0},
    "교토": {"lat": 35.0116, "lon": 135.7681, "tz": 9.0},
    "시드니": {"lat": -33.8688, "lon": 151.2093, "tz": 10.0},
    "멜버른": {"lat": -37.8136, "lon": 144.9631, "tz": 10.0},
    "브리즈번": {"lat": -27.4698, "lon": 153.0251, "tz": 10.0},
    "토론토": {"lat": 43.6510, "lon": -79.3470, "tz": -5.0},
    "밴쿠버": {"lat": 49.2827, "lon": -123.1207, "tz": -8.0},
    "몬트리올": {"lat": 45.5017, "lon": -73.5673, "tz": -5.0},
    "기타": {"lat": 37.5665, "lon": 126.9780, "tz": 9.0},
}


def get_vedic_data(year, month, day, hour_str, city_name):
    if not VEDIC_AVAILABLE:
        return "\n[베딕 데이터: 현재 계산 라이브러리를 사용할 수 없습니다.]"

    if city_name not in CITY_COORDS:
        return f"\n[베딕 데이터: '{city_name}'의 좌표가 등록되어 있지 않습니다.]"

    hr, mn = 12, 0

    if hour_str != "모름":
        try:
            hr, mn = map(int, hour_str.split(":"))
        except Exception:
            hr, mn = 12, 0

    coords = CITY_COORDS[city_name]
    birth_dt = datetime(year, month, day, hr, mn, 0)

    try:
        chart = calculate_birth_chart(
            birth_date=birth_dt,
            latitude=coords["lat"],
            longitude=coords["lon"],
            timezone_offset=coords["tz"],
        )

        lines = ["[베딕 점성술 (Jyotisha) 주요 행성 위치]"]

        if hasattr(chart, "d1_chart") and hasattr(chart.d1_chart, "planets"):
            for p in chart.d1_chart.planets:
                p_name = getattr(p, "celestial_body", "")
                p_sign = getattr(p, "sign", "")

                if p_name and p_sign:
                    lines.append(f"- {p_name}: {p_sign}")

        if len(lines) == 1:
            return "[베딕 데이터: 행성 위치를 읽지 못했습니다.]"

        return "\n".join(lines)

    except Exception:
        return "[베딕 데이터: 계산 중 오류가 발생했습니다.]"


# =========================================================
# 수비학
# =========================================================

def reduce_num(n):
    while n > 9 and n not in (11, 22, 33):
        n = sum(int(d) for d in str(n))
    return n


def get_numerology(year, month, day):
    lp = reduce_num(sum(int(c) for c in f"{year}{month:02d}{day:02d}"))

    current = now_kst()
    py = reduce_num(month + reduce_num(day) + reduce_num(current.year))
    pm = reduce_num(py + current.month)
    pd = reduce_num(pm + current.day)

    return {
        "life_path": lp,
        "personal_year": py,
        "personal_month": pm,
        "personal_day": pd,
    }


# =========================================================
# 통합 점술 데이터
# =========================================================

def build_astrology_block(year, month, day, hour_str, birth_city):
    lines = []

    zhi_idx = TIME_TO_ZHI.get(hour_str, 0)
    saju = get_saju_data(year, month, day, zhi_idx)

    if saju:
        lines.append("[만세력(사주) 4주 8자]")
        lines.append(
            f"년주: {saju['year']} / "
            f"월주: {saju['month']} / "
            f"일주: {saju['day']} / "
            f"시주: {saju['hour']} "
            f"(일간: {saju['day_master']})"
        )
    else:
        lines.append("[만세력(사주) 데이터: 계산할 수 없습니다.]")

    num = get_numerology(year, month, day)

    lines.append("\n[수비학(Numerology) 데이터]")
    lines.append(
        f"운명수(Life Path): {num['life_path']} / "
        f"올해의 수: {num['personal_year']} / "
        f"이번 달의 수: {num['personal_month']} / "
        f"오늘의 수: {num['personal_day']}"
    )

    vedic_text = get_vedic_data(
        year, month, day, hour_str, birth_city
    )

    if vedic_text:
        lines.append(vedic_text)

    return "\n".join(lines)


# =========================================================
# Supabase 함수
# =========================================================

def upsert_user(email, name):
    if not email:
        return

    try:
        res = (
            supabase
            .table("users")
            .select("id")
            .eq("email", email)
            .execute()
        )

        if not res.data:
            supabase.table("users").insert({
                "email": email,
                "name": name,
            }).execute()

    except Exception as e:
        print(f"DB Error (upsert_user): {e}")


def has_used_free_today(email, date_str):
    try:
        res = (
            supabase
            .table("free_usage")
            .select("id")
            .eq("email", email)
            .eq("usage_date", date_str)
            .execute()
        )

        return len(res.data) > 0

    except Exception as e:
        print(f"DB Error (has_used_free_today): {e}")
        return True


def save_free_usage(email, date_str):
    try:
        supabase.table("free_usage").insert({
            "email": email,
            "usage_date": date_str,
        }).execute()

    except Exception as e:
        print(f"DB Error (save_free_usage): {e}")


def save_report_to_db(email, product_id, question, result_text):
    try:
        supabase.table("reports").insert({
            "email": email,
            "product_id": product_id,
            "question": question,
            "result": result_text,
        }).execute()

    except Exception as e:
        print(f"DB Error (save_report): {e}")


# =========================================================
# Gemini / Google OAuth
# =========================================================

api_key = st.secrets["GEMINI_API_KEY"]
client = genai.Client(api_key=api_key)

CLIENT_ID = st.secrets["GOOGLE_CLIENT_ID"]
CLIENT_SECRET = st.secrets["GOOGLE_CLIENT_SECRET"]
REDIRECT_URI = st.secrets["REDIRECT_URI"]

AUTHORIZE_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
REVOKE_ENDPOINT = "https://oauth2.googleapis.com/revoke"

oauth2 = OAuth2Component(
    CLIENT_ID,
    CLIENT_SECRET,
    AUTHORIZE_ENDPOINT,
    TOKEN_ENDPOINT,
    TOKEN_ENDPOINT,
    REVOKE_ENDPOINT,
)


# =========================================================
# 페이지 설정 / 디자인
# =========================================================

st.set_page_config(
    page_title="THE RAW TAROT",
    page_icon="🔮",
    layout="centered",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.stApp {
    background-color: #f8f9fa;
    color: #212529;
}

.main-title {
    text-align: center;
    color: #1a1a2e;
    font-family: Georgia, 'Times New Roman', serif;
    letter-spacing: 4px;
    font-size: 2.55rem;
    font-weight: 700;
    margin-bottom: 5px;
}

.sub-title {
    text-align: center;
    color: #6c757d;
    font-size: 1.02rem;
    margin-bottom: 28px;
}

.raw-card {
    background: #ffffff;
    border: 1px solid #dee2e6;
    border-radius: 12px;
    padding: 24px;
    margin: 18px 0;
}

.raw-dark-card {
    background: #1a1a2e;
    color: #ffffff;
    border-radius: 12px;
    padding: 26px 24px;
    margin: 20px 0;
}

.raw-label {
    color: #b7791f;
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: 2px;
    text-transform: uppercase;
}

.raw-heading {
    color: #1a1a2e;
    font-size: 1.35rem;
    font-weight: 700;
    margin-top: 7px;
}

.raw-muted {
    color: #6c757d;
    line-height: 1.7;
}

.deep-price {
    font-size: 1.8rem;
    font-weight: 800;
    color: #1a1a2e;
}

section[data-testid="stSidebar"] {
    background-color: #f1f3f5 !important;
}

section[data-testid="stSidebar"] * {
    color: #212529 !important;
}

div.stButton > button:first-child {
    background-color: #1a1a2e;
    color: #f3e5ab;
    border: 1px solid #1a1a2e;
    font-weight: 700;
    border-radius: 7px;
    width: 100%;
    min-height: 45px;
}

div.stButton > button:first-child:hover {
    background-color: #33334d;
    color: #ffffff;
}
</style>
""", unsafe_allow_html=True)

st.markdown(
    "<h1 class='main-title'>THE RAW TAROT</h1>",
    unsafe_allow_html=True,
)

st.markdown(
    "<p class='sub-title'>당신을 직시하십시오. "
    "당신이 외면해온 진실을 마주할 시간입니다.</p>",
    unsafe_allow_html=True,
)


# =========================================================
# 로그인 전 화면
# =========================================================

if "google_token" not in st.session_state:

    st.markdown("""
    <div class="raw-dark-card">
        <div class="raw-label" style="color:#d4af37;">
            OPEN EVENT · FREE SHADOW READING
        </div>
        <div style="font-size:1.55rem; font-weight:700; margin-top:10px;">
            당신의 돈과 현실을 먼저 읽습니다.
        </div>
        <div style="color:#d9d9df; line-height:1.8; margin-top:12px;">
            타로 한 장의 의미만 설명하지 않습니다.<br>
            생년월일과 출생지에서 계산된 데이터를 바탕으로
            사주 · 수비학 · 베딕 점성술 · 타로를 교차해서 읽습니다.
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="raw-card">
        <div class="raw-label">WHAT YOU WILL SEE</div>
        <div class="raw-heading">무료 SHADOW READING</div>
        <p class="raw-muted">
            지금의 돈과 현실에서 무엇이 막혀 있는지,<br>
            어떤 자원을 활용해야 하는지,<br>
            그리고 다음 선택에서 무엇을 주의해야 하는지를 확인합니다.
        </p>
        <p style="color:#6c757d; font-size:0.88rem;">
            ※ 이 서비스는 미래를 확정하는 예언이 아니라
            자기성찰과 의사결정을 돕는 오라클 리딩입니다.
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(
        "<h4 style='text-align:center; color:#1a1a2e; "
        "margin-top:30px;'>무료 리딩 예시</h4>",
        unsafe_allow_html=True,
    )

    sample_cols = st.columns(3)

    with sample_cols[0]:
        st.image(
            "images/The_Fool.png",
            caption="The Fool",
            use_container_width=True,
        )

    with sample_cols[1]:
        st.image(
            "images/The_Tower.png",
            caption="The Tower",
            use_container_width=True,
        )

    with sample_cols[2]:
        st.image(
            "images/The_Devil.png",
            caption="The Devil",
            use_container_width=True,
        )

    st.markdown("""
    <div class="raw-card"
         style="border-left:4px solid #1a1a2e;">
        <div style="color:#343a40; line-height:1.8;">
            <b>예시</b><br><br>
            돈이 들어오지 않는다고 해서
            반드시 돈의 운이 없는 것은 아닙니다.<br><br>
            <b>The Tower</b>는 지금까지의 방식이
            더 이상 같은 결과를 만들기 어렵다는 신호로 읽힐 수 있습니다.
            무너지는 것이 당신이 아니라,
            당신을 묶고 있던 구조일 수도 있습니다.
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(
        "<p style='text-align:center; color:#6c757d; "
        "font-size:0.9rem;'>하루 1회 무료 SHADOW READING · "
        "Google 로그인 후 시작</p>",
        unsafe_allow_html=True,
    )

    result = oauth2.authorize_button(
        name="Google로 시작하기",
        icon="https://www.google.com/favicon.ico",
        redirect_uri=REDIRECT_URI,
        scope="openid email profile",
        key="google_login",
        use_container_width=True,
    )

    if result:
        st.session_state["google_token"] = result.get("token")
        st.rerun()

    st.stop()


# =========================================================
# 사용자 이메일 확인
# =========================================================

if "user_email" not in st.session_state:
    try:
        headers = {
            "Authorization":
            f"Bearer {st.session_state['google_token']['access_token']}"
        }

        user_info = requests.get(
            "https://www.googleapis.com/oauth2/v1/userinfo",
            headers=headers,
            timeout=10,
        ).json()

        st.session_state["user_email"] = user_info.get("email", "")

    except Exception:
        st.session_state["user_email"] = ""


user_email = st.session_state["user_email"]


# =========================================================
# 사용자 DB 등록
# =========================================================

if user_email:
    upsert_user(user_email, "")


# =========================================================
# 상품
# =========================================================

PRODUCTS = {
    "FREE": {
        "name": "무료 SHADOW READING",
        "price": 0,
        "cards": 3,
        "is_pro": False,
    },
    "RAW_DEEP": {
        "name": "THE RAW DEEP ANALYSIS",
        "price": 990,
        "cards": 5,
        "is_pro": True,
    },
}


selected_product_id = st.session_state.get(
    "checkout_product",
    "FREE",
)

if selected_product_id not in PRODUCTS:
    selected_product_id = "FREE"
    st.session_state["checkout_product"] = "FREE"

current_product = PRODUCTS[selected_product_id]


# =========================================================
# 카드
# =========================================================

MAJOR_ARCANA = [
    "The Fool",
    "The Magician",
    "The High Priestess",
    "The Empress",
    "The Emperor",
    "The Hierophant",
    "The Lovers",
    "The Chariot",
    "Strength",
    "The Hermit",
    "Wheel of Fortune",
    "Justice",
    "The Hanged Man",
    "The Death",
    "Temperance",
    "The Devil",
    "The Tower",
    "The Star",
    "The Moon",
    "The Sun",
    "Judgement",
    "The World",
]

CARD_IMAGE_NAMES = {
    "Wheel of Fortune": "Wheel_of_Fortune",
    "The Death": "The_Death",
}


def get_card_image_path(card_name):
    base_name = CARD_IMAGE_NAMES.get(
        card_name,
        card_name.replace(" ", "_"),
    )

    jpg = f"images/{base_name}.jpg"
    png = f"images/{base_name}.png"

    if os.path.exists(jpg):
        return jpg

    if os.path.exists(png):
        return png

    return None


# =========================================================
# 입력 화면
# =========================================================

st.sidebar.markdown("### 🪐 READING")

if selected_product_id == "FREE":
    st.sidebar.info(
        "오늘은 무료 SHADOW READING을 이용할 수 있습니다."
    )
else:
    st.sidebar.success(
        "THE RAW DEEP ANALYSIS · 990원"
    )

st.sidebar.markdown("---")

reading_mode = st.sidebar.radio(
    "질문 테마",
    [
        "MONEY SHADOW — 돈과 현실",
        "RAW QUESTION — 나만의 심층 질문",
    ],
)

st.sidebar.markdown("---")

st.sidebar.markdown("### 🎧 주파수 동기화")
st.sidebar.caption(
    "원한다면 SynchroVault에서 리딩 후 주파수를 이어갈 수 있습니다."
)
st.sidebar.link_button(
    "SynchroVault 접속하기",
    "https://www.youtube.com/@SynchroVault",
)


if user_email:
    safe_email = html.escape(user_email)

    st.markdown(
        f"""
        <div class="raw-card"
             style="padding:15px 18px; margin-bottom:20px;">
            <span style="color:#6c757d;">현재 계정</span><br>
            <b style="color:#1a1a2e;">{safe_email}</b>
        </div>
        """,
        unsafe_allow_html=True,
    )


country_city_map = {
    "대한민국": ["서울", "대전", "대구", "부산", "제주", "기타"],
    "미국": ["뉴욕", "로스앤젤레스", "시카고", "시애틀", "기타"],
    "영국": ["런던", "맨체스터", "에든버러", "기타"],
    "일본": ["도쿄", "오사카", "교토", "기타"],
    "호주": ["시드니", "멜버른", "브리즈번", "기타"],
    "캐나다": ["토론토", "밴쿠버", "몬트리올", "기타"],
    "기타": ["기타"],
}


ADMIN_EMAIL = "ellykimmain@gmail.com"

if user_email == ADMIN_EMAIL:
    default_name = "Kim Uyoun"
    default_year = 1988
else:
    default_name = ""
    default_year = 1990


user_name = st.text_input(
    "이름 / 닉네임",
    value=default_name,
)

gender = st.radio(
    "성별",
    ["여성", "남성"],
    horizontal=True,
)

col1, col2 = st.columns(2)

with col1:
    birth_country = st.selectbox(
        "출생 국가",
        list(country_city_map.keys()),
        index=0,
    )

with col2:
    birth_city = st.selectbox(
        "출생 도시",
        country_city_map[birth_country],
    )

if birth_city == "기타":
    birth_city = st.text_input(
        "도시를 직접 입력하십시오",
        value="",
    )

birth_place = f"{birth_city}, {birth_country}"


col3, col4, col5 = st.columns(3)

with col3:
    birth_year = st.number_input(
        "태어난 연도",
        min_value=1930,
        max_value=2026,
        value=default_year,
    )

with col4:
    birth_month = st.number_input(
        "월",
        min_value=1,
        max_value=12,
        value=6,
    )

with col5:
    birth_day = st.number_input(
        "일",
        min_value=1,
        max_value=31,
        value=15,
    )


time_options = [
    "모름"
] + [
    f"{h:02d}:{m:02d}"
    for h in range(24)
    for m in (0, 30)
]

birth_time = st.selectbox(
    "태어난 시간",
    time_options,
)


if reading_mode.startswith("MONEY"):
    question_options = [
        "지금 내 돈이 막히는 가장 큰 이유는 무엇인가?",
        "현재 내 수입을 가로막는 가장 중요한 패턴은 무엇인가?",
        "내게 돈이 들어오는 가장 현실적인 경로는 무엇인가?",
        "지금 내가 가진 자원 중 현금화할 수 있는 것은 무엇인가?",
        "사업과 커리어에서 내가 놓치고 있는 수익 기회는 무엇인가?",
        "앞으로 가까운 시기의 금전 흐름에서 무엇을 주의해야 하는가?",
        "지금 돈을 만들기 위해 가장 먼저 바꿔야 할 것은 무엇인가?",
    ]

    selected_query = st.selectbox(
        "무엇을 알고 싶습니까?",
        question_options,
    )

    user_question = selected_query

else:
    user_question = st.text_area(
        "당신의 심층 질문",
        placeholder=(
            "예: 지금 내가 가진 경험으로 "
            "어떤 방식의 수입을 만드는 것이 가장 현실적인가?"
        ),
    )


# =========================================================
# 공통 프롬프트 생성
# =========================================================

def build_prompt(
    user_name,
    gender,
    birth_place,
    birth_year,
    birth_month,
    birth_day,
    birth_time,
    user_question,
    astrology_data,
    drawn_keys,
    product_id,
):
    current_date = today_kst()

    card_lines = "\n".join(
        f"{idx + 1}. {card}"
        for idx, card in enumerate(drawn_keys)
    )

    if product_id == "FREE":
        output_format = """
@INTRO@
현재 상황을 3~4문장으로 뼈아프게 분석하라.
사주 + 수비학 + 베딕 데이터 + 질문을 연결하되, '현재 돈과 현실이 왜 꼬여있는가(문제점)'에만 집중하라.

@CARD_1@
첫 번째 카드가 보여주는 뼈를 때리는 현실 진단.
내담자의 기질적(사주/수비학) 단점이 현실에서 어떻게 최악으로 발현되고 있는지 폭로하라. (4문장 내외)

@CARD_2@
두 번째 카드가 보여주는, 돈과 성과를 가로막는 숨겨진 그림자(가장 치명적인 문제/회피하는 진실)를 분석하라. (4문장 내외)

@CARD_3@
세 번째 카드가 보여주는 돌파구를 위한 아주 작은 실마리(힌트) 및 숨겨진 자원. 구체적인 전체 전략은 주지 마라. (4문장 내외)

@CONCLUSION@
전체를 종합하여 4~5문장으로 작성하라.
반드시 다음을 포함하라.
1. 지금 당장 멈춰야 할 치명적인 행동 1가지
2. 문제를 직시하라는 단호한 경고 메시지
3. [핵심] 마지막 문장은 반드시 내담자의 사주(방위, 오행), 타로 상징, 또는 수비학 숫자를 활용해 '구체적이고 찝찝한 질문'으로 끝낼 것. 
   (예시: "카드는 당신의 과거 인연 중 '문서'를 쥐고 있는 자가 아직 영향을 미치고 있다고 말합니다. 혹시 짐작 가는 서류나 인물이 있습니까?", "명식에 꼬여있는 불(火)의 기운을 볼 때, 최근 남쪽 방향에서 들어온 제안이나 붉은색 상징이 화근이 되고 있습니다. 짚이는 것이 있습니까?")

[절대 금지 규칙]
절대로 "THE RAW DEEP ANALYSIS", "결제", "유료", "더 깊은 분석에서 다루어야 합니다" 등의 상품 안내나 마케팅 문구를 작성하지 마라. 영업은 시스템이 알아서 하므로 당신은 순수하게 질문만 던지고 여운을 남긴 채 리딩을 종료하라.
"""

    else:
        output_format = """
@INTRO@
전체 데이터를 기반으로 질문에 대한 핵심 결론을 먼저 제시하라.
5~6문장.

@MONEY@
돈, 수입, 현금화, 사업/커리어의 관점에서 현재 구조를 깊게 분석하라.
돈을 막는 핵심 패턴 3가지, 버려야 할 수익 방식과 당장 활용해야 할 수익 방식을 명확히 구분하라.
6~8문장.

@CROSSCHECK@
사주, 수비학, 베딕, 타로가 서로 일치하는 부분과 충돌하는 신호를 분석하여 진짜 문제의 본질을 찾아라.
6~8문장.

@CARDS@
5장의 카드가 각각 어떤 역할을 하는지 설명하되,
카드 의미를 단순 복사하지 말고 돈을 만드는 흐름과 연결하라.
각 카드당 2~3문장.

@ACTION@
현실에서 즉각 실행할 수 있는 전략을 제시하라.
지금 당장 돈을 만들기 위해 무엇부터 해야 하는지 향후 30일/7일 단위의 구체적 실행 지침을 주어라.
6~8문장.

@TIMING@
제공된 데이터 범위 안에서만 시기적 흐름을 해석하라.
존재하지 않는 대운, 월운, 다샤 등을 만들어내지 마라.
4~6문장.

@CONCLUSION@
전체 분석을 8~10문장으로 정리하고,
가장 강력하고 현실적인 행동 지침으로 마무리하라.
"""

    return f"""
당신은 THE RAW TAROT의 핵심 분석가다.

당신의 역할은 단순히 타로 카드의 의미를 설명하는 것이 아니다.
내담자가 실제로 제공한 생년월일, 출생지, 계산된 사주 데이터, 수비학 데이터,
베딕 점성술 데이터, 타로 카드와 질문을 교차 분석하여
현재의 핵심 문제와 현실적인 돌파구를 찾는 것이다.

==================================================================
[가장 중요한 원칙]
==================================================================
1. 입력 데이터에 없는 사실을 절대로 만들어내지 마라.
2. 점술에서 도출되는 내용은 가능성이 높은 패턴으로 표현하라. 미래를 확정하지 마라.
3. 근거 없는 공포를 만들지 마라.
4. 내담자를 조롱하거나 모욕하지 마라.
5. 주식, 코인, 특정 투자상품의 매수·매도를 확정적으로 권유하지 마라.
6. 실제 금융정보가 없으면 금액을 만들어내지 마라.
7. [중요] 당신의 입으로 무료/유료 상품을 홍보하거나 결제를 유도하는 멘트를 절대 하지 마라.

==================================================================
[분석 우선순위]
==================================================================
1순위: 내담자의 질문
2순위: 돈 / 수입 / 사업 / 커리어 / 현실적인 성과
3순위: 사주
4순위: 수비학
5순위: 베딕 점성술
6순위: 타로

==================================================================
[문체]
==================================================================
한국어로 작성하라.
문장은 짧고 선명하게 작성하라. 차갑고 직접적이되 품위를 유지하라.
불필요한 미사여구를 사용하지 마라.
'당신은 무조건 성공한다' 같은 근거 없는 확언을 하지 마라.

==================================================================
[현재 날짜]
==================================================================
{current_date}

==================================================================
[내담자 프로필]
==================================================================
이름: {user_name}
성별: {gender}
출생지: {birth_place}
생년월일시: {birth_year}년 {birth_month:02d}월 {birth_day:02d}일 {birth_time}
내담자의 질문: {user_question}

==================================================================
[실제로 계산된 점술 데이터]
==================================================================
{astrology_data}

==================================================================
[뽑힌 그림자 아르카나]
==================================================================
{card_lines}

==================================================================
[출력 형식]
==================================================================
반드시 아래 구분자를 정확하게 사용하라.

{output_format}
"""
# =========================================================
# 결과 표시
# =========================================================

def extract_section(text, tag, next_tag=None):
    if tag not in text:
        return ""

    try:
        content = text.split(tag, 1)[1]

        if next_tag and next_tag in content:
            content = content.split(next_tag, 1)[0]

        return content.strip()

    except Exception:
        return ""


def display_card(card_name, title=None):
    if title:
        st.markdown(
            f"<h4 style='text-align:center; color:#1a1a2e;'>"
            f"{title}</h4>",
            unsafe_allow_html=True,
        )

    image_path = get_card_image_path(card_name)

    if image_path:
        st.image(
            image_path,
            caption=card_name,
            use_container_width=True,
        )
    else:
        st.warning(f"카드 이미지가 없습니다: {card_name}")


def safe_html_text(text):
    return html.escape(text or "").replace("\n", "<br>")


def display_free_result(result_text, drawn_keys):
    intro = extract_section(
        result_text,
        "@INTRO@",
        "@CARD_1@",
    )

    card1 = extract_section(
        result_text,
        "@CARD_1@",
        "@CARD_2@",
    )

    card2 = extract_section(
        result_text,
        "@CARD_2@",
        "@CARD_3@",
    )

    card3 = extract_section(
        result_text,
        "@CARD_3@",
        "@CONCLUSION@",
    )

    conclusion = extract_section(
        result_text,
        "@CONCLUSION@",
        None,
    )

    if intro:
        st.markdown(
            f"""
            <div class="raw-card">
                <div class="raw-label">RAW SNAPSHOT</div>
                <div style="color:#343a40; line-height:1.85;">
                    {safe_html_text(intro)}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    sections = [
        ("1 · 현재의 현실", drawn_keys[0], card1),
        ("2 · 돈을 막는 그림자", drawn_keys[1], card2),
        ("3 · 숨겨진 자원", drawn_keys[2], card3),
    ]

    for title, card_name, text in sections:
        st.markdown(
            f"<h4 style='color:#1a1a2e; margin-top:28px;'>"
            f"{title}</h4>",
            unsafe_allow_html=True,
        )

        col1, col2, col3 = st.columns([1, 1.5, 1])

        with col2:
            display_card(card_name)

        if text:
            st.markdown(
                f"""
                <div class="raw-card"
                     style="line-height:1.85;">
                    {safe_html_text(text)}
                </div>
                """,
                unsafe_allow_html=True,
            )

    if conclusion:
        st.markdown(
            f"""
            <div class="raw-dark-card">
                <div class="raw-label" style="color:#d4af37;">
                    THE RAW CONCLUSION
                </div>
                <div style="line-height:1.85; margin-top:12px;">
                    {safe_html_text(conclusion)}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def display_deep_result(result_text, drawn_keys):
    sections = [
        ("@INTRO@", "@MONEY@", "THE RAW · 핵심 진단"),
        ("@MONEY@", "@CROSSCHECK@", "MONEY · 돈의 구조"),
        ("@CROSSCHECK@", "@CARDS@", "CROSSCHECK · 교차 검증"),
        ("@CARDS@", "@ACTION@", "CARDS · 카드 분석"),
        ("@ACTION@", "@TIMING@", "ACTION · 현실 전략"),
        ("@TIMING@", "@CONCLUSION@", "TIMING · 흐름"),
        ("@CONCLUSION@", None, "CONCLUSION · 최종 판단"),
    ]

    for tag, next_tag, title in sections:
        content = extract_section(
            result_text,
            tag,
            next_tag,
        )

        if not content:
            continue

        st.markdown(
            f"""
            <div class="raw-card">
                <div class="raw-label">{title}</div>
                <div style="color:#343a40; line-height:1.9; margin-top:10px;">
                    {safe_html_text(content)}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        "<h4 style='color:#1a1a2e; margin-top:30px;'>"
        "🎴 이번 분석에 사용된 카드</h4>",
        unsafe_allow_html=True,
    )

    cols = st.columns(len(drawn_keys))

    for idx, card_name in enumerate(drawn_keys):
        with cols[idx]:
            display_card(card_name)


# =========================================================
# 이메일
# =========================================================

def send_result_email(user_email, user_name, result_text, product_name):
    if not user_email:
        return False

    try:
        safe_name = html.escape(user_name or "여행자")
        safe_result = safe_html_text(result_text)

        html_body = f"""
        <html>
        <body style="
            background:#050505;
            color:#d4d4d4;
            font-family:Arial,Helvetica,sans-serif;
            padding:20px;
            line-height:1.7;
        ">
            <div style="
                max-width:600px;
                margin:0 auto;
                border:1px solid #222;
                padding:35px;
                background:#0a0a0a;
            ">
                <h2 style="
                    text-align:center;
                    color:#ffffff;
                    letter-spacing:4px;
                    font-weight:normal;
                ">
                    THE RAW TAROT
                </h2>

                <p style="color:#999;">
                    {safe_name}님을 위한 {html.escape(product_name)}
                </p>

                <div style="
                    margin-top:30px;
                    color:#cccccc;
                    font-size:15px;
                ">
                    {safe_result}
                </div>

                <hr style="
                    border:0;
                    border-top:1px solid #222;
                    margin:40px 0;
                ">

                <p style="
                    color:#888;
                    font-size:13px;
                    text-align:center;
                ">
                    THE RAW TAROT · 현실을 직시하고 다음 행동을 선택하십시오.
                </p>
            </div>
        </body>
        </html>
        """

        msg = MIMEText(html_body, "html")
        msg["Subject"] = f"THE RAW TAROT · {product_name}"
        msg["From"] = st.secrets["EMAIL_SENDER"]
        msg["To"] = user_email

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(
                st.secrets["EMAIL_SENDER"],
                st.secrets["EMAIL_PASSWORD"],
            )
            server.send_message(msg)

        return True

    except Exception as e:
        print(f"Email Error: {e}")
        return False


# =========================================================
# FREE SHADOW READING
# =========================================================

if selected_product_id == "FREE":

    if st.button("오늘의 SHADOW READING 시작하기"):

        current_date = today_kst()

        if not user_name.strip():
            st.warning("이름 또는 닉네임을 입력하십시오.")
            st.stop()

        upsert_user(user_email, user_name)

        if user_email != ADMIN_EMAIL:
            if has_used_free_today(
                user_email,
                current_date,
            ):
                st.error(
                    "오늘의 무료 SHADOW READING은 이미 사용했습니다. "
                    "내일 다시 새로운 리딩을 시작할 수 있습니다."
                )
                st.stop()

        ph = st.empty()

        loading_messages = [
            "🌌 당신의 데이터를 불러오고 있습니다...",
            "🪐 사주와 수비학의 구조를 교차 확인하고 있습니다...",
            "☽ 베딕 데이터를 현재 질문과 대조하고 있습니다...",
            "🃏 당신의 그림자 카드 3장을 추출하고 있습니다...",
            "⚡ 서로 다른 신호가 어디에서 겹치는지 확인하고 있습니다...",
        ]

        for message in loading_messages:
            ph.info(message)
            time.sleep(0.8)

        # ★ 기존 NameError 수정:
        # prompt에서 사용하기 전에 astrology_data를 먼저 계산한다.
        astrology_data = build_astrology_block(
            int(birth_year),
            int(birth_month),
            int(birth_day),
            birth_time,
            birth_city,
        )

        drawn_keys = random.sample(
            MAJOR_ARCANA,
            PRODUCTS["FREE"]["cards"],
        )

        prompt = build_prompt(
            user_name=user_name,
            gender=gender,
            birth_place=birth_place,
            birth_year=int(birth_year),
            birth_month=int(birth_month),
            birth_day=int(birth_day),
            birth_time=birth_time,
            user_question=user_question,
            astrology_data=astrology_data,
            drawn_keys=drawn_keys,
            product_id="FREE",
        )

        try:
            response = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=prompt,
            )

            result_text = response.text or ""

            ph.empty()

            st.success("오늘의 SHADOW READING이 완성되었습니다.")

            display_free_result(
                result_text,
                drawn_keys,
            )

            save_free_usage(
                user_email,
                current_date,
            )

            save_report_to_db(
                user_email,
                "FREE",
                user_question,
                result_text,
            )

            email_sent = send_result_email(
                user_email,
                user_name,
                result_text,
                "무료 SHADOW READING",
            )

            if email_sent:
                st.caption("리딩 결과를 이메일로도 보내드렸습니다.")

            st.markdown("---")

            st.markdown("""
<div class="raw-dark-card" style="text-align:center;">
    <div class="raw-label" style="color:#d4af37;">
        GO DEEPER
    </div>
    <div style="font-size:1.45rem; font-weight:700; margin-top:8px;">
        여기서부터 THE RAW입니다.
    </div>
    <p style="color:#d9d9df; line-height:1.8; margin-top:12px;">
        무료 리딩은 지금의 핵심 그림자를 보여줍니다.<br>
        DEEP ANALYSIS에서는 돈의 구조, 교차검증, 현실 전략과 흐름을 더 깊게 분석합니다.
    </p>
    <div class="deep-price" style="color:#f3e5ab; margin-top:15px;">
        990원
    </div>
    <div style="color:#aaa; font-size:0.85rem; margin-top:5px;">
        1회성 · 결제 연동 전 테스트 모드
    </div>
</div>
""", unsafe_allow_html=True)

            if st.button(
                "🔓 THE RAW DEEP ANALYSIS · 990원",
                key="go_deep",
            ):
                st.session_state["checkout_product"] = "RAW_DEEP"
                st.rerun()

        except Exception as e:
            ph.empty()
            st.error(
                f"리딩 생성 중 오류가 발생했습니다: {str(e)}"
            )


# =========================================================
# RAW DEEP ANALYSIS
# =========================================================

elif selected_product_id == "RAW_DEEP":

    st.markdown(
        "<h2 style='text-align:center; color:#1a1a2e;'>"
        "THE RAW DEEP ANALYSIS</h2>",
        unsafe_allow_html=True,
    )

    st.markdown("""
    <div class="raw-card">
        <div class="raw-label">ONE QUESTION · FULL ANALYSIS</div>

        <div class="raw-heading">
            당신의 질문 하나를 깊게 파고듭니다.
        </div>

        <p class="raw-muted">
            사주 · 수비학 · 베딕 점성술 · 타로를 함께 놓고
            서로 일치하는 부분과 충돌하는 부분을 구분합니다.
        </p>

        <hr>

        <p>
            <b>제공 내용</b><br>
            · 5장 타로 스프레드<br>
            · 돈과 현실적인 성과 분석<br>
            · 점술 체계 간 교차 검증<br>
            · 현실적인 행동 전략<br>
            · 결과 이메일 발송
        </p>

        <div class="deep-price">
            990원
        </div>

        <p style="color:#868e96; font-size:0.85rem;">
            현재는 결제 연동 전 테스트 모드입니다.
            사업자 및 결제 설정이 완료되면 이 버튼을
            토스페이먼츠 결제로 교체합니다.
        </p>
    </div>
    """, unsafe_allow_html=True)

    if st.button(
        "990원 결제 및 DEEP 리포트 생성 · 테스트",
        key="deep_test",
    ):

        if not user_name.strip():
            st.warning("이름 또는 닉네임을 입력하십시오.")
            st.stop()

        ph = st.empty()
        ph.info(
            "🌌 당신의 데이터를 심층 분석하고 있습니다..."
        )

        time.sleep(0.8)

        astrology_data = build_astrology_block(
            int(birth_year),
            int(birth_month),
            int(birth_day),
            birth_time,
            birth_city,
        )

        drawn_keys = random.sample(
            MAJOR_ARCANA,
            PRODUCTS["RAW_DEEP"]["cards"],
        )

        prompt = build_prompt(
            user_name=user_name,
            gender=gender,
            birth_place=birth_place,
            birth_year=int(birth_year),
            birth_month=int(birth_month),
            birth_day=int(birth_day),
            birth_time=birth_time,
            user_question=user_question,
            astrology_data=astrology_data,
            drawn_keys=drawn_keys,
            product_id="RAW_DEEP",
        )

        try:
            response = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=prompt,
            )

            result_text = response.text or ""

            ph.empty()

            st.success(
                "THE RAW DEEP ANALYSIS가 완성되었습니다."
            )

            display_deep_result(
                result_text,
                drawn_keys,
            )

            save_report_to_db(
                user_email,
                "RAW_DEEP",
                user_question,
                result_text,
            )

            email_sent = send_result_email(
                user_email,
                user_name,
                result_text,
                "THE RAW DEEP ANALYSIS",
            )

            if email_sent:
                st.success(
                    "심층 리포트를 이메일로도 발송했습니다."
                )

        except Exception as e:
            ph.empty()
            st.error(
                f"DEEP 분석 중 오류가 발생했습니다: {str(e)}"
            )

    st.markdown("---")

    if st.button(
        "← 무료 SHADOW READING으로 돌아가기",
        key="back_free",
    ):
        st.session_state["checkout_product"] = "FREE"
        st.rerun()
