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
from streamlit_oauth import OAuth2Component, StreamlitOauthError
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

    # 💡 꼬여있는 인증 State 파라미터를 잡아내고 URL을 청소하는 방어 로직
    try:
        result = oauth2.authorize_button(
            name="Google로 시작하기",
            icon="https://www.google.com/favicon.ico",
            redirect_uri=REDIRECT_URI,
            scope="openid email profile",
            key="google_login",
            use_container_width=True,
        )
    except StreamlitOauthError:
        st.error("로그인 세션이 만료되었거나 충돌했습니다. 화면을 정리하고 다시 시작합니다.")
        st.query_params.clear() # URL에 남은 이전 로그인 찌꺼기 초기화
        time.sleep(1.5)
        st.rerun()

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
        "RAW CHAT — 실시간 상담하기",
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
기계적인 인사를 생략하고, 내담자의 현재 운기와 꼬여있는 현실을 3~4문장으로 꿰뚫어라.
"(내담자 이름)은 최근 2~3년간 ~때문에 마음고생이 많았을 거라는 거죠." 식의 확신에 찬 어투로 시작하라.

@CARD_1@
첫 번째 카드가 보여주는 가장 뼈아픈 단점.
"본인은 도와준다고 나섰지만 그게 도리어 구설수로 돌아오는 형국입니다." 같이 단호하게 타격하라. (4문장 내외)

@CARD_2@
두 번째 카드가 짚어내는 금전/현실을 막는 가장 큰 원인. (4문장 내외)

@CARD_3@
세 번째 카드가 보여주는 시기적 흐름과 돌파구.
"하반기로 갈수록 막혔던 금전이 풀린다", "지금 씨를 뿌린 투자는 연말에 가서야 성과가 난다" 등 구체적인 시기와 보상을 예측하는 화법을 써라. (4문장 내외)

@CONCLUSION@
전체를 4~5문장으로 종합하라.
1. 당장 멈춰야 할 헛짓거리 1가지.
2. "이 고비만 넘기면 금전 운기가 풀릴 테니 흔들리지 마십시오. 다만 투자나 계약 시 ~한 기운을 가진 사람은 절대 조심해야 한다는 겁니다." 식의 실질적 당부.
3. [핵심] 마지막은 내담자의 기운을 짚으며(한자 없이 우리말로 풀어서) 찝찝하고 날카로운 질문을 던지고 끝낼 것.
4. 베딕, 만세력을 이용해 살아날 구멍을 위치 혹은 시기를 짚어줄 것.
"""

    else:
        output_format = """
@INTRO@
전체 데이터를 훑어본 뒤, 질문에 대한 결론부터 묵직하게 던져라.
"이 기운과 카드의 흐름을 보면, 당신이 지금 막혀있는 진짜 이유는 ~라는 겁니다." (5~6문장)

@MONEY@
금전과 사업의 운기를 해부하라. "그동안 노력한 만큼 금전을 거둬들이지 못했겠지만, 하반기부터는 막혔던 물꼬가 트인다" 식의 시기적 흐름을 짚어라. 돈을 갉아먹는 진짜 이유와 앞으로 돈이 들어올 구멍을 정확히 진단하라. (6~8문장)

@CROSSCHECK@
사주, 수비학, 타로의 기운이 충돌하거나 일치하는 지점을 찾아내라. (6~8문장)

@CARDS@
5장의 카드를 현실의 금전, 투자, 구설, 문서운, 인덕과 직결시켜 해석하라. (각 2~3문장)

@ACTION@
현실에서 당장 해야 할 행동을 지시하라. "주변 사람 말 듣지 말고 본인 결단력으로 밀어붙여야 성과가 난다는 겁니다." (6~8문장)

@TIMING@
투자, 이동, 이직, 인간관계에 있어 움직여야 할 시기와 납작 엎드려야 할 시기를 짚어라. (4~6문장)

@CONCLUSION@
전체 분석을 정리하고, 내담자가 정신을 번쩍 차릴 수 있는 가장 강력하고 단호한 오라클의 선언으로 마무리하라. (8~10문장)
"""

    return f"""
당신은 THE RAW TAROT의 핵심 분석가이자, 산전수전 다 겪은 압도적 내공의 '현대판 오라클(명리학자/타로마스터)'이다.

==================================================================
[말투 및 톤앤매너 지시사항 - 반드시 지킬 것!]
==================================================================
1. 한자 사용 절대 금지: 甲辰, 子水 같은 명리학 한자 용어를 그대로 출력하지 마라. 반드시 "거대한 나무의 기운", "얼어붙은 차가운 물줄기" 등 직관적인 우리말로 풀어서 묘사하라.
2. 실질적인 점사 화법: "하반기로 갈수록 풀린다", "지금 투자한 것은 끝물에 성과가 난다", "~한 문서는 쥐어도 좋다" 등 시기와 투자, 행동에 대한 구체적이고 실질적인 예측을 반드시 섞어라.
3. 종결어미의 변화: "~다는 거죠", "~형국입니다", "~라고 보시면 됩니다", "~라는 거예요"를 적극적으로 섞어 써라.
4. 어휘의 선택: '금전', '운기', '구설수', '문서운', '인덕', '이별수' 같은 명리/점술계 용어를 자연스럽게 사용하라.
5. 금지어: "AI로서", "개인적인 의견", "미래는 바뀔 수 있습니다" 같은 자신감 없는 면피성 멘트를 절대 출력하지 마라.

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
# FREE SHADOW READING & RAW CHAT (LUXURY DARK TERMINAL)
# =========================================================

if selected_product_id == "FREE":

    # 💡 [핵심] 모든 모드에서 만세력 표를 띄우기 위해 함수를 바깥으로 뺐습니다. (들여쓰기 4칸 유지)
    def build_visual_block():
        saju_dict = get_saju_data(int(birth_year), int(birth_month), int(birth_day), TIME_TO_ZHI.get(birth_time, 0))
        num_data = get_numerology(int(birth_year), int(birth_month), int(birth_day))
        
        def get_zodiac(m, d):
            if (m == 1 and d >= 20) or (m == 2 and d <= 18): return "물병자리", "♒"
            elif (m == 2 and d >= 19) or (m == 3 and d <= 20): return "물고기자리", "♓"
            elif (m == 3 and d >= 21) or (m == 4 and d <= 19): return "양자리", "♈"
            elif (m == 4 and d >= 20) or (m == 5 and d <= 20): return "황소자리", "♉"
            elif (m == 5 and d >= 21) or (m == 6 and d <= 20): return "쌍둥이자리", "♊"
            elif (m == 6 and d >= 21) or (m == 7 and d <= 22): return "게자리", "♋"
            elif (m == 7 and d >= 23) or (m == 8 and d <= 22): return "사자자리", "♌"
            elif (m == 8 and d >= 23) or (m == 9 and d <= 22): return "처녀자리", "♍"
            elif (m == 9 and d >= 23) or (m == 10 and d <= 22): return "천칭자리", "♎"
            elif (m == 10 and d >= 23) or (m == 11 and d <= 21): return "전갈자리", "♏"
            elif (m == 11 and d >= 22) or (m == 12 and d <= 21): return "사수자리", "♐"
            else: return "염소자리", "♑"
            
        zodiac_name, zodiac_symbol = get_zodiac(int(birth_month), int(birth_day))
        life_path = num_data['life_path']
        
        if not saju_dict:
            return ""
            
        return f"""
        <div style="border: 1px solid rgba(212, 175, 55, 0.2); border-radius: 8px; padding: 25px 20px; margin-bottom: 30px; background: rgba(13, 14, 18, 0.7); box-shadow: inset 0 0 20px rgba(0,0,0,0.5);">
            <div style="color: #64748b; font-size: 0.75rem; letter-spacing: 3px; margin-bottom: 20px; text-align: center; font-weight: 600;">[ EXTRACTED RAW DATA ]</div>
            <div style="display: flex; justify-content: space-around; text-align: center; font-family: 'Times New Roman', serif, '명조'; margin-bottom: 20px; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 20px;">
                <div><div style="color:#94a3b8; font-size:0.75rem; margin-bottom:10px;">時 (시간)</div><div style="color:#e2e8f0; font-size:1.7rem; font-weight:bold; line-height:1.5;">{saju_dict['hour'][0]}<br>{saju_dict['hour'][1]}</div></div>
                <div><div style="color:#d4af37; font-size:0.75rem; margin-bottom:10px;">日 (본질)</div><div style="color:#d4af37; font-size:1.7rem; font-weight:bold; line-height:1.5;">{saju_dict['day'][0]}<br>{saju_dict['day'][1]}</div></div>
                <div><div style="color:#94a3b8; font-size:0.75rem; margin-bottom:10px;">月 (환경)</div><div style="color:#e2e8f0; font-size:1.7rem; font-weight:bold; line-height:1.5;">{saju_dict['month'][0]}<br>{saju_dict['month'][1]}</div></div>
                <div><div style="color:#94a3b8; font-size:0.75rem; margin-bottom:10px;">年 (근원)</div><div style="color:#e2e8f0; font-size:1.7rem; font-weight:bold; line-height:1.5;">{saju_dict['year'][0]}<br>{saju_dict['year'][1]}</div></div>
            </div>
            <div style="display: flex; justify-content: space-around; text-align: center;">
                <div><div style="color:#94a3b8; font-size:0.7rem; letter-spacing: 1px; margin-bottom:8px;">ZODIAC SIGN</div><div style="color:#d4af37; font-size:1.1rem; font-weight:bold;">{zodiac_symbol} {zodiac_name}</div></div>
                <div><div style="color:#94a3b8; font-size:0.7rem; letter-spacing: 1px; margin-bottom:8px;">LIFE PATH</div><div style="color:#d4af37; font-size:1.1rem; font-weight:bold;">NO. {life_path}</div></div>
            </div>
        </div>
        """

    # 1. 실시간 상담 모드 (RAW CHAT - 1일 1회 제한 및 단호한 오라클 선언)
    if reading_mode.startswith("RAW CHAT"):
        
        st.markdown("""
        <style>
        .luxury-terminal {
            background-color: #0d0e12;
            border: 1px solid rgba(212, 175, 55, 0.3);
            border-radius: 12px;
            padding: 24px;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            color: #e2e8f0;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
            margin-bottom: 20px;
        }
        .terminal-header {
            color: #d4af37;
            font-family: Georgia, 'Times New Roman', serif;
            letter-spacing: 3px;
            font-weight: 700;
            font-size: 1.1rem;
            margin-bottom: 16px;
            border-bottom: 1px solid rgba(212, 175, 55, 0.2);
            padding-bottom: 12px;
            text-transform: uppercase;
        }
        </style>
        """, unsafe_allow_html=True)

        st.markdown('<div class="terminal-header">THE RAW · ORACLE SECURE CHANNEL (PREVIEW)</div>', unsafe_allow_html=True)

        # 세션 초기화
        if "chat_messages" not in st.session_state:
            st.session_state["chat_messages"] = []
            st.session_state["chat_initialized"] = False

        # 💡 [핵심 1] 사주, 별자리, 수비학 데이터를 HTML 시각화 표로 렌더링하는 공통 함수
        def build_visual_block():
            saju_dict = get_saju_data(int(birth_year), int(birth_month), int(birth_day), TIME_TO_ZHI.get(birth_time, 0))
            num_data = get_numerology(int(birth_year), int(birth_month), int(birth_day))
            
            def get_zodiac(m, d):
                if (m == 1 and d >= 20) or (m == 2 and d <= 18): return "물병자리", "♒"
                elif (m == 2 and d >= 19) or (m == 3 and d <= 20): return "물고기자리", "♓"
                elif (m == 3 and d >= 21) or (m == 4 and d <= 19): return "양자리", "♈"
                elif (m == 4 and d >= 20) or (m == 5 and d <= 20): return "황소자리", "♉"
                elif (m == 5 and d >= 21) or (m == 6 and d <= 20): return "쌍둥이자리", "♊"
                elif (m == 6 and d >= 21) or (m == 7 and d <= 22): return "게자리", "♋"
                elif (m == 7 and d >= 23) or (m == 8 and d <= 22): return "사자자리", "♌"
                elif (m == 8 and d >= 23) or (m == 9 and d <= 22): return "처녀자리", "♍"
                elif (m == 9 and d >= 23) or (m == 10 and d <= 22): return "천칭자리", "♎"
                elif (m == 10 and d >= 23) or (m == 11 and d <= 21): return "전갈자리", "♏"
                elif (m == 11 and d >= 22) or (m == 12 and d <= 21): return "사수자리", "♐"
                else: return "염소자리", "♑"
                
            zodiac_name, zodiac_symbol = get_zodiac(int(birth_month), int(birth_day))
            life_path = num_data['life_path']
            
            if not saju_dict:
                return ""
                
            return f"""
            <div style="border: 1px solid rgba(212, 175, 55, 0.2); border-radius: 8px; padding: 25px 20px; margin-bottom: 30px; background: rgba(13, 14, 18, 0.7); box-shadow: inset 0 0 20px rgba(0,0,0,0.5);">
                <div style="color: #64748b; font-size: 0.75rem; letter-spacing: 3px; margin-bottom: 20px; text-align: center; font-weight: 600;">[ EXTRACTED RAW DATA ]</div>
                <div style="display: flex; justify-content: space-around; text-align: center; font-family: 'Times New Roman', serif, '명조'; margin-bottom: 20px; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 20px;">
                    <div><div style="color:#94a3b8; font-size:0.75rem; margin-bottom:10px;">時 (시간)</div><div style="color:#e2e8f0; font-size:1.7rem; font-weight:bold; line-height:1.5;">{saju_dict['hour'][0]}<br>{saju_dict['hour'][1]}</div></div>
                    <div><div style="color:#d4af37; font-size:0.75rem; margin-bottom:10px;">日 (본질)</div><div style="color:#d4af37; font-size:1.7rem; font-weight:bold; line-height:1.5;">{saju_dict['day'][0]}<br>{saju_dict['day'][1]}</div></div>
                    <div><div style="color:#94a3b8; font-size:0.75rem; margin-bottom:10px;">月 (환경)</div><div style="color:#e2e8f0; font-size:1.7rem; font-weight:bold; line-height:1.5;">{saju_dict['month'][0]}<br>{saju_dict['month'][1]}</div></div>
                    <div><div style="color:#94a3b8; font-size:0.75rem; margin-bottom:10px;">年 (근원)</div><div style="color:#e2e8f0; font-size:1.7rem; font-weight:bold; line-height:1.5;">{saju_dict['year'][0]}<br>{saju_dict['year'][1]}</div></div>
                </div>
                <div style="display: flex; justify-content: space-around; text-align: center;">
                    <div><div style="color:#94a3b8; font-size:0.7rem; letter-spacing: 1px; margin-bottom:8px;">ZODIAC SIGN</div><div style="color:#d4af37; font-size:1.1rem; font-weight:bold;">{zodiac_symbol} {zodiac_name}</div></div>
                    <div><div style="color:#94a3b8; font-size:0.7rem; letter-spacing: 1px; margin-bottom:8px;">LIFE PATH</div><div style="color:#d4af37; font-size:1.1rem; font-weight:bold;">NO. {life_path}</div></div>
                </div>
            </div>
            """

        # 아직 상담을 시작하지 않은 경우
        if not st.session_state["chat_initialized"]:
            if st.button(">> INITIALIZE ORACLE CHAT (상담 채널 열기)"):
                current_date = today_kst()

                if not user_name.strip():
                    st.warning("이름 또는 닉네임을 입력하십시오.")
                    st.stop()
                
                upsert_user(user_email, user_name)

                if user_email != ADMIN_EMAIL:
                    if has_used_free_today(user_email, current_date):
                        st.error("오늘의 오라클 세션은 이미 사용했습니다. 내일 다시 새로운 세션을 시작할 수 있습니다.")
                        st.stop()

                astrology_data = build_astrology_block(
                    int(birth_year), int(birth_month), int(birth_day), birth_time, birth_city
                )
                
                steps = [
                    ("🪐 사주 명식 구조 분석", f"""
                    [프로필] 이름: {user_name} / 생년월일시: {birth_year}년 {birth_month}월 {birth_day}일 {birth_time}
                    [점술 데이터] {astrology_data}
                    [상담 주제] {user_question}
                    [지시] 사주 명식의 관점에서 내담자의 핵심 기질과 돈줄의 흐름을 딱 2줄로 서늘하게 요약하라. 한문이나 전문 용어는 배제할 것.
                    """, "사주 명식의 구조를 해부하는 중..."),
                    
                    ("🎴 운명의 타로 4장 개방", f"""
                    [프로필] 이름: {user_name} / 생년월일시: {birth_year}년 {birth_month}월 {birth_day}일 {birth_time}
                    [점술 데이터] {astrology_data}
                    [상담 주제] {user_question}
                    [지시] 타로 카드가 드러내는 현재의 숨겨진 함정과 그림자를 딱 2줄로 압축하여 타격하라.
                    """, "운명의 타로 카드 4장을 뒤집는 중..."),
                    
                    ("☽ 베딕 점성술 행성 궤도 대조", f"""
                    [프로필] 이름: {user_name} / 생년월일시: {birth_year}년 {birth_month}월 {birth_day}일 {birth_time}
                    [점술 데이터] {astrology_data}
                    [상담 주제] {user_question}
                    [지시] 베딕 점성술의 행성 궤도에서 드러나는 거대한 흐름과 피해야 할 위기를 딱 2줄로 서늘하게 진단하라.
                    """, "베딕 점성술의 행성 배치를 대조하는 중..."),
                    
                    ("⚡ 자미두수 및 최종 오라클 선언", f"""
                    [프로필] 이름: {user_name} / 생년월일시: {birth_year}년 {birth_month}월 {birth_day}일 {birth_time}
                    [점술 데이터] {astrology_data}
                    [상담 주제] {user_question}
                    [지시] 자미두수와 수비학 숫자가 가리키는 현실적 돌파구를 짚고, 마지막 문장은 반드시 방위(예: 북서쪽), 특정 띠, 성씨 등의 디테일을 포함한 단호한 선언으로 마무리하라. 절대 물음표로 끝내지 마라. 분량은 4~5줄 내외로 압축하라.
                    """, "자미두수 및 수비학 코드를 교차 검증하는 중...")
                ]

                try:
                    # 💡 [핵심 2] 화면 상단에 시각적 표 생성
                    saju_visual_block = build_visual_block()
                    
                    terminal_placeholder = st.empty()
                    saved_results = []

                    for title, prompt_text, loading_msg in steps:
                        
                        # 💡 HTML 안에서 올바르게 표시되도록 줄바꿈(<br>) 적용
                        text_display = ""
                        for res_title, res_text in saved_results:
                            text_display += f"<strong style='color:#d4af37; font-size:1.05em;'>{res_title}</strong><br><br>{res_text}<br><br><hr style='border: 0; border-top: 1px solid rgba(212,175,55,0.2); margin: 15px 0;'><br>"
                        
                        text_display += f"<span style='color:#94a3b8; font-style:italic;'>⚡ {loading_msg}</span>"

                        terminal_placeholder.markdown(f"""
                        <div class="luxury-terminal">
                            <div style="color:#d4af37; font-size:0.85rem; letter-spacing:1px; margin-bottom:20px;">[ ORACLE · SECURE CHANNEL ]</div>
                            {saju_visual_block}
                            <div style="line-height: 1.8; color: #f1f5f9; font-size:0.95rem;">
                                {text_display}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        time.sleep(0.6)

                        response = client.models.generate_content(
                            model="gemini-3.6-flash",
                            contents=prompt_text,
                        )
                        
                        # 💡 [핵심 3] AI가 뱉은 특수기호나 찌꺼기 태그를 '미리' 깨끗하게 제거하고 저장 (DOM 파괴 방지)
                        step_result = response.text.strip().replace("</div>", "").replace("<div>", "").replace("**", "").replace("###", "")
                        step_result = step_result.replace(chr(10), "<br>")
                        
                        saved_results.append((title, step_result))
                        time.sleep(0.4)

                    final_text_html = ""
                    for res_title, res_text in saved_results:
                        final_text_html += f"<strong style='color:#d4af37; font-size:1.05em;'>{res_title}</strong><br><br>{res_text}<br><br><hr style='border: 0; border-top: 1px solid rgba(212,175,55,0.2); margin: 15px 0;'><br>"

                    save_free_usage(user_email, current_date)

                    st.session_state["chat_messages"] = [{"role": "assistant", "content": final_text_html}]
                    st.session_state["chat_initialized"] = True
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"채널 연결 오류: {e}")
            else:
                st.markdown("""
                <div class="luxury-terminal" style="text-align:center; padding: 30px;">
                    <div style="color:#d4af37; font-size:1.1rem; margin-bottom:10px;">SECURE CHANNEL READY</div>
                    <div style="color:#94a3b8; font-size:0.9rem; line-height:1.7;">
                        입력된 프로필과 질문을 바탕으로 오라클의 4단계 정밀 교차 검증 세션을 엽니다.<br>
                        사주, 타로, 베딕, 자미두수의 데이터가 순차적으로 해부되어 출력됩니다.
                    </div>
                </div>
                """, unsafe_allow_html=True)
        
        else:
            # 💡 [핵심 4] 세션 완료 후에도 시각화 블록을 깨짐 없이 완벽하게 복구하여 결합
            saju_visual_block = build_visual_block()
            
            for message in st.session_state["chat_messages"]:
                st.markdown(f"""
                <div class="luxury-terminal">
                    <div style="color:#d4af37; font-size:0.85rem; letter-spacing:1px; margin-bottom:20px;">[ ORACLE · SECURE CHANNEL ]</div>
                    {saju_visual_block}
                    <div style="line-height: 1.8; color: #f1f5f9; font-size:0.95rem;">
                        {message["content"]}
                    </div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.button("🔓 THE RAW DEEP ANALYSIS · 990원", use_container_width=True, key="go_deep_chat_wide_final"):
                st.session_state["checkout_product"] = "RAW_DEEP"
                st.rerun()

            st.markdown("<div style='text-align: center; margin-top: 15px;'>", unsafe_allow_html=True)
            if st.button("↺ 처음부터 다시 시작하기", key="reset_session_sub_final"):
                st.session_state["chat_messages"] = []
                st.session_state["chat_initialized"] = False
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
                
    # 2. 기존 무료 SHADOW READING 모드
    else:
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

            # ... (이전 if has_used_free_today(...) 검사 로직 유지) ...

            ph = st.empty()
            bar = st.progress(0.0)

            loading_steps = [
                ("🌌 운명 데이터 동기화 중...", 0.2),
                ("🪐 사주 명식과 수비학 구조 교차 분석 중...", 0.4),
                ("☽ 베딕 점성술 행성 배치 대조 중...", 0.6),
                ("🎴 타로 덱에서 운명의 카드를 뽑는 중...", 0.8),
                ("⚡ 카드를 뒤집어 오늘의 그림자를 조합하는 중...", 0.95)
            ]

            for msg, progress_val in loading_steps:
                ph.info(msg)
                bar.progress(progress_val)
                time.sleep(0.4)

            # 점술 데이터 및 프롬프트 빌드 (백그라운드에서 빠르게 처리)
            astrology_data = build_astrology_block(
                int(birth_year), int(birth_month), int(birth_day), birth_time, birth_city
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

            # 💡 로딩바 100% 상태로 문구만 변경하여 API 연결 대기
            bar.progress(1.0)
            ph.info("🌌 오라클 엔진 가동 중... 교차 검증을 마치고 리포트를 조립하고 있습니다. (약 5~10초 소요)")

            try:
                # 💡 스트리밍(타이핑 효과)을 제거하고 완성된 결과를 한 번에 받아옵니다.
                response = client.models.generate_content(
                    model="gemini-3.6-flash",
                    contents=prompt,
                )

                # 답변이 100% 완성되어 도착하면 비로소 로딩바 삭제
                bar.empty()
                ph.empty()

                result_text = response.text.strip()

                st.success("오늘의 SHADOW READING이 완성되었습니다.")

                # 만세력 시각화 표 출력 (최상단)
                saju_html = build_visual_block()
                if saju_html:
                    st.markdown(saju_html, unsafe_allow_html=True)

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
