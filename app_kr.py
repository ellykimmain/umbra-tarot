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
from supabase import create_client, Client

# ── Supabase DB 초기화 ───────────────────────────────────────────────────────
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_SERVICE_ROLE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ── 사주 라이브러리 (py-iztro 제외, sxtwl만 유지) ──────────────────────────────
try:
    import sxtwl
    SAJU_AVAILABLE = True
except ImportError:
    SAJU_AVAILABLE = False

# ── 천간·지지 한자 및 영문 리스트 ──────────────────────────────────────────────
GAN_H  = ['甲','乙','丙','丁','戊','己','庚','辛','壬','癸']
ZHI_H  = ['子','丑','寅','卯','辰','巳','午','未','申','酉','戌','亥']
GAN_EN = ['Jia(Wood+)','Yi(Wood-)','Bing(Fire+)','Ding(Fire-)','Wu(Earth+)','Ji(Earth-)','Geng(Metal+)','Xin(Metal-)','Ren(Water+)','Gui(Water-)']
ZHI_EN = ['Zi(Rat)','Chou(Ox)','Yin(Tiger)','Mao(Rabbit)','Chen(Dragon)','Si(Snake)','Wu(Horse)','Wei(Goat)','Shen(Monkey)','You(Rooster)','Xu(Dog)','Hai(Pig)']

TIME_TO_ZHI = {
    "모름": 0, "00:00": 0, "00:30": 0, "01:00": 1, "01:30": 1, "02:00": 1, "02:30": 1, "03:00": 2, "03:30": 2,
    "04:00": 2, "04:30": 2, "05:00": 3, "05:30": 3, "06:00": 3, "06:30": 3, "07:00": 4, "07:30": 4, "08:00": 4,
    "08:30": 4, "09:00": 5, "09:30": 5, "10:00": 5, "10:30": 5, "11:00": 6, "11:30": 6, "12:00": 6, "12:30": 6,
    "13:00": 7, "13:30": 7, "14:00": 7, "14:30": 7, "15:00": 8, "15:30": 8, "16:00": 8, "16:30": 8, "17:00": 9,
    "17:30": 9, "18:00": 9, "18:30": 9, "19:00":10, "19:30":10, "20:00":10, "20:30":10, "21:00":11, "21:30":11,
    "22:00":11, "22:30":11, "23:00": 0, "23:30": 0
}

def get_saju_data(year, month, day, hour_index=0):
    if not SAJU_AVAILABLE: return None
    try:
        d  = sxtwl.fromSolar(year, month, day)
        yg, mg, dg = d.getYearGZ(), d.getMonthGZ(), d.getDayGZ()
        start_map = {0:0,5:0,1:2,6:2,2:4,7:4,3:6,8:6,4:8,9:8}
        htg = (start_map[dg.tg] + hour_index) % 10
        return {
            "year": f"{GAN_H[yg.tg]}{ZHI_H[yg.dz]}", "month": f"{GAN_H[mg.tg]}{ZHI_H[mg.dz]}",
            "day": f"{GAN_H[dg.tg]}{ZHI_H[dg.dz]}", "hour": f"{GAN_H[htg]}{ZHI_H[hour_index]}",
            "day_master": GAN_H[dg.tg]
        }
    except: return None
from datetime import datetime

try:
    from jyotishganit import calculate_birth_chart
    VEDIC_AVAILABLE = True
except ImportError:
    VEDIC_AVAILABLE = False

def get_vedic_data(year, month, day, hour_str, city_name):
    if not VEDIC_AVAILABLE:
        return "\n[베딕 오류: 라이브러리 인식 불가. requirements.txt 수정 후 Streamlit Cloud에서 'Reboot app'을 실행해야 설치됩니다.]"
    
    if city_name not in CITY_COORDS:
        return f"\n[베딕 오류: 선택한 도시('{city_name}')의 위도/경도 데이터가 CITY_COORDS에 없습니다. 코드에 좌표를 추가하십시오.]"
    
    hr, mn = 12, 0
    if hour_str != "모름":
        hr, mn = map(int, hour_str.split(":"))
        
    coords = CITY_COORDS.get(city_name)
    birth_dt = datetime(year, month, day, hr, mn, 0)
    
    try:
        # 베딕 차트 정밀 연산 실행
        chart = calculate_birth_chart(
            birth_date=birth_dt,
            latitude=coords["lat"],
            longitude=coords["lon"],
            timezone_offset=coords["tz"]
        )
        
        lines = ["\n[베딕 점성술 (Jyotisha) 주요 행성 위치]"]
        if hasattr(chart, 'd1_chart') and hasattr(chart.d1_chart, 'planets'):
            for p in chart.d1_chart.planets:
                # 로그 확인 결과 'name'이 아닌 'celestial_body'를 사용함
                p_name = getattr(p, 'celestial_body', '')
                p_sign = getattr(p, 'sign', '')
                
                if p_name and p_sign:
                    lines.append(f"- {p_name}: {p_sign}")
        
        return "\n".join(lines) if len(lines) > 1 else "\n[베딕 연산 오류: 행성 데이터 파싱 실패]"
        
    except Exception as e:
        return f"\n[베딕 연산 오류: {e}]"
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

def build_astrology_block(year, month, day, hour_str, birth_city):
    lines = []
    zhi_idx = TIME_TO_ZHI.get(hour_str, 0)
    saju = get_saju_data(year, month, day, zhi_idx)
    if saju:
        lines.append("[만세력(사주) 4주 8자]")
        lines.append(f"년주: {saju['year']} / 월주: {saju['month']} / 일주: {saju['day']} / 시주: {saju['hour']} (일간: {saju['day_master']})")
    num = get_numerology(year, month, day)
    lines.append("\n[수리학(Numerology) 데이터]")
    lines.append(f"운명수(Life Path): {num['life_path']} / 올해의 수: {num['personal_year']} / 이번 달의 수: {num['personal_month']}")
    # 💡 베딕 데이터 추가
    vedic_text = get_vedic_data(year, month, day, hour_str, birth_city)
    if vedic_text:
        lines.append(vedic_text)
        
    return "\n".join(lines) if lines else "우주적 데이터 계산 불가. 입력된 정보만으로 판단하십시오."

# ── DB 및 상태 검증 함수 ─────────────────────────────────────────────────────
def upsert_user(email, name):
    """구글 로그인 시 users 테이블에 사용자 등록 (최초 1회)"""
    if not email: return
    try:
        res = supabase.table("users").select("id").eq("email", email).execute()
        if not res.data:
            supabase.table("users").insert({"email": email, "name": name}).execute()
    except Exception as e:
        st.error(f"사용자 정보 저장에 실패했습니다. 상세 에러: {e}")

def has_used_free_today(email, date_str):
    """오늘 무료 진단을 이미 사용했는지 free_usage 테이블에서 팩트 체크"""
    try:
        res = supabase.table("free_usage").select("id").eq("email", email).eq("usage_date", date_str).execute()
        return len(res.data) > 0
    except Exception as e:
        print(f"DB Error (has_used_free_today): {e}")
        return True  # 에러 시 남용을 막기 위해 방어적으로 접근 차단

def save_free_usage(email, date_str):
    """무료 진단 완료 후 free_usage 테이블에 사용 기록 영구 저장"""
    try:
        supabase.table("free_usage").insert({"email": email, "usage_date": date_str}).execute()
    except Exception as e:
        print(f"DB Error (save_free_usage): {e}")

def save_report_to_db(email, product_id, question, result_text):
    """분석 완료 후 reports 테이블에 결과 저장"""
    try:
        supabase.table("reports").insert({
            "email": email,
            "product_id": product_id,
            "question": question,
            "result": result_text
        }).execute()
    except Exception as e:
        print(f"DB Error (save_report): {e}")

# ── Streamlit 및 API 설정 ───────────────────────────────────────────────────
api_key = st.secrets["GEMINI_API_KEY"]
client = genai.Client(api_key=api_key)

CLIENT_ID = st.secrets["GOOGLE_CLIENT_ID"]
CLIENT_SECRET = st.secrets["GOOGLE_CLIENT_SECRET"]
REDIRECT_URI = st.secrets["REDIRECT_URI"]
AUTHORIZE_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
REVOKE_ENDPOINT = "https://oauth2.googleapis.com/revoke"

oauth2 = OAuth2Component(CLIENT_ID, CLIENT_SECRET, AUTHORIZE_ENDPOINT, TOKEN_ENDPOINT, TOKEN_ENDPOINT, REVOKE_ENDPOINT)

st.set_page_config(page_title="THE RAW TAROT: 그림자 진단", layout="centered", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; color: #212529; }
    .main-title { text-align: center; color: #1a1a2e; font-family: 'Cinzel', serif; letter-spacing: 2px; font-size: 2.5rem; font-weight: 700; }
    .sub-title { text-align: center; color: #6c757d; font-size: 1.05rem; }
    label, [data-testid="stWidgetLabel"] p { color: #212529 !important; font-weight: 600 !important; }
    div.stButton > button:first-child { background-color: #1a1a2e; color: #f3e5ab; border: 1px solid #1a1a2e; font-weight: 600; border-radius: 5px; width: 100%; }
    div.stButton > button:first-child:hover { background-color: #33334d; color: #ffffff; }
    section[data-testid="stSidebar"] { background-color: #f1f3f5 !important; }
    section[data-testid="stSidebar"] *, section[data-testid="stSidebar"] label, section[data-testid="stSidebar"] span, section[data-testid="stSidebar"] p { color: #212529 !important; }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='main-title'> THE RAW TAROT </h1>", unsafe_allow_html=True)
st.markdown("<p class='sub-title'>당신을 직시하십시오. 잔혹한 진실과 마주할 시간입니다.</p>", unsafe_allow_html=True)

# ── 구글 로그인 및 강력한 경고문 ───────────────────────────────────────────────
if "google_token" not in st.session_state:
    st.markdown("### ✨ 오픈 이벤트! 3일 무료 ")
    
    # 💡 핏빛 경고문 추가
    st.error("""
    **⚠️ 경고 : 감당할 수 있는 자만 입장할 것**  
    이 오라클은 어떠한 위로나 헛된 희망, 따뜻한 힐링을 제공하지 않습니다.  
    당신의 환상을 부수고 잔혹하고 가감 없는 우주적 진실만을 전달하도록 설계되었습니다.  
    멘탈이 여리거나 달콤한 거짓말을 원한다면, <절대 로그인하지 마세요.>
    """)

    st.markdown("구글 로그인으로 당신의 '숨겨진 그림자 자아 진단'과 1개의 심층 커스텀 질문 권한을 획득하십시오.")
    st.info("무료 체험을 시작하고 진단의 방에 입장하려면 구글 로그인이 필수입니다.")
    
    st.markdown("<br><h4 style='text-align: center; color: #1a1a2e;'> 진단서 엿보기 (샘플 타로)</h4>", unsafe_allow_html=True)
    sample_cols = st.columns(3)
    with sample_cols[0]: st.image("images/The_Fool.png", caption="The Fool", use_container_width=True)
    with sample_cols[1]: st.image("images/The_Tower.png", caption="The Tower", use_container_width=True)
    with sample_cols[2]: st.image("images/The_Devil.png", caption="The Devil", use_container_width=True)
        
    st.markdown("""
    <div style="background-color: #e9ecef; padding: 15px; border-left: 4px solid #1a1a2e; border-radius: 4px; color: #212529; font-style: italic; font-size: 0.95rem; margin-bottom: 25px;">
    "당신은 재물과 안정을 묻고 있으나, 탑(The Tower) 카드는 당신의 기반이 지독한 자기 기만 위에 세워져 있음을 폭로하느라. 다가오는 붕괴는 형벌이 아니라 허상을 박살내는 필수적인 정화의 과정이다..."
    </div>
    """, unsafe_allow_html=True)

    result = oauth2.authorize_button(name="구글로 계속하기", icon="https://www.google.com/favicon.ico", redirect_uri=REDIRECT_URI, scope="openid email profile", key="google_login", use_container_width=True)
    if result:
        st.session_state["google_token"] = result.get("token")
        st.rerun()
    st.stop()

if "user_email" not in st.session_state:
    try:
        headers = {'Authorization': f'Bearer {st.session_state["google_token"]["access_token"]}'}
        user_info = requests.get('https://www.googleapis.com/oauth2/v1/userinfo', headers=headers).json()
        st.session_state["user_email"] = user_info.get('email', '')
    except: 
        st.session_state["user_email"] = ""

user_email = st.session_state["user_email"]
# ── 사용자 DB 등록 ─────────────────────────────────────────────
if user_email:
    try:
        # 1. 이미 DB에 이메일이 존재하는지 안전하게 조회
        res = supabase.table("users").select("id").eq("email", user_email).execute()
        
        # 2. 존재하지 않는 신규 유저일 경우에만 Insert 실행
        if not res.data:
            supabase.table("users").insert({"email": user_email}).execute()
            
    except Exception as e:
        # 에러가 발생할 경우, 숨기지 않고 화면에 실제 원인(e)을 출력하여 즉각 대응
        st.error(f"사용자 정보 저장에 실패했습니다. 상세 에러: {e}")

st.sidebar.markdown("### 🪐 멤버십 등급")
st.sidebar.radio("플랜 선택", ["무료 체험 (활성화됨)", "Pro Oracle (9월 20일 오픈)"], index=0, disabled=True)
st.sidebar.info("✨ **그랜드 오픈!** 현재 무료 체험 기간입니다.")
st.sidebar.markdown("---")
st.sidebar.markdown("### 🔮 진단 모드")
reading_mode = st.sidebar.radio("질문 테마 선택", ["1. 나는 누구인가? (그림자 자아 진단)", "2. 커스텀 진단 (심층 질문)"])
st.sidebar.markdown("---")
st.sidebar.markdown("### 🎧 주파수 동기화")
st.sidebar.caption("불안정한 주파수를 재정렬하십시오.")
st.sidebar.link_button("SynchroVault 접속하기", "https://www.youtube.com/@SynchroVault")

if user_email:
    st.markdown(f"""
        <div style="background-color: #e9ecef; padding: 15px; border-radius: 8px; border: 1px solid #ced4da; color: #212529; margin-bottom: 20px;">
            🌌 <b>환영합니다, 여행자여.</b> 결과가 발송될 이메일: <span style="color: #d97706; font-weight: bold;">{user_email}</span>
        </div>
    """, unsafe_allow_html=True)

country_city_map = {
    "대한민국": ["서울", "대전", "대구", "부산", "제주", "기타"],
    "미국": ["뉴욕", "로스앤젤레스", "시카고", "시애틀", "기타"],
    "영국": ["런던", "맨체스터", "에든버러", "기타"],
    "일본": ["도쿄", "오사카", "교토", "기타"],
    "호주": ["시드니", "멜버른", "브리즈번", "기타"],
    "캐나다": ["토론토", "밴쿠버", "몬트리올", "기타"],
    "기타": ["기타"]
}
# 도시별 위도, 경도, 타임존 오프셋 맵핑
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
    "기타": {"lat": 37.5665, "lon": 126.9780, "tz": 9.0} # 기본값 서울로 처리
}
ADMIN_EMAIL = "ellykimmain@gmail.com" 

if user_email == ADMIN_EMAIL:
    default_name = "Kim Uyoun"
    default_country_idx = 0 
    default_year = 1988      
else:
    default_name = ""
    default_country_idx = 0 
    default_year = 1990

user_name = st.text_input("이름 / 닉네임", default_name)
gender = st.radio("성별", ["여성", "남성"], horizontal=True)

col1, col2 = st.columns(2)
with col1: birth_country = st.selectbox("출생 국가", list(country_city_map.keys()), index=default_country_idx)
with col2: birth_city = st.selectbox("출생 도시", country_city_map[birth_country])
if birth_city == "기타": birth_city = st.text_input("도시를 직접 입력하십시오", "")
birth_place = f"{birth_city}, {birth_country}"

col3, col4, col5 = st.columns(3)
with col3: birth_year = st.number_input("태어난 연도", min_value=1930, max_value=2026, value=default_year)
with col4: birth_month = st.number_input("월", min_value=1, max_value=12, value=6)
with col5: birth_day = st.number_input("일", min_value=1, max_value=31, value=15)

time_options = ["모름"] + [f"{h:02d}:{m:02d}" for h in range(24) for m in (0, 30)]
birth_time = st.selectbox("태어난 시간", time_options)

if "2." in reading_mode or "커스텀" in reading_mode:
    question_options = [
        "이 끔찍한 재정적 고통은 언제 끝나는가?", "나의 부를 가로막는 숨겨진 장애물",
        "현재 관계(연인)에 숨겨진 잔혹한 진실", "나의 진짜 인연은 언제 나타나는가?",
        "현재 사업(커리어)은 올바른 길인가?", "내일 나의 운세는?",
        "내가 필사적으로 외면하고 있는 진실", "내 그림자 자아의 미친듯한 경고",
        "직접 입력 (심층 질문 작성)"
    ]
    selected_query = st.selectbox("질문을 선택하거나 직접 입력하십시오", question_options)
    user_question = st.text_area("당신의 심층 질문", placeholder="예: 벼랑 끝입니다. 어떻게 살아남아야 합니까?") if selected_query == "직접 입력 (심층 질문 작성)" else selected_query
else:
    user_question = ""

# ── 상품(Product) 정의 ──────────────────────────────────────────────────────
PRODUCTS = {
    "FREE": {
        "name": "무료 체험",
        "price": 0,
        "cards": 3,
        "is_pro": False
    },
    "RAW_ONE": {
        "name": "RAW ONE 심층 리포트",
        "price": 990,  # 💡 9900에서 990으로 변경
        "cards": 5,
        "is_pro": True
    }
}

# (임시) 현재 선택된 상품 상태. 추후 결제 시스템 연동 시 PAID 상태 확인 후 'RAW_ONE'으로 전환
selected_product_id = st.session_state.get("checkout_product", "FREE")
current_product = PRODUCTS[selected_product_id]

# ── 카드 이름 매핑 ─────────────────────────────────────────────────────────
MAJOR_ARCANA = [
    "The Fool", "The Magician", "The High Priestess", "The Empress", "The Emperor",
    "The Hierophant", "The Lovers", "The Chariot", "Strength", "The Hermit",
    "Wheel of Fortune", "Justice", "The Hanged Man", "The Death", "Temperance",
    "The Devil", "The Tower", "The Star", "The Moon", "The Sun",
    "Judgement", "The World"
]

# ── 오라클 버튼 실행 및 결제 대기(Checkout) 분기 ────────────────────────────────
if selected_product_id == "FREE":
    if st.button("오늘의 그림자 확인하기"):
        current_date = datetime.now().strftime("%Y-%m-%d")
        upsert_user(user_email, user_name)
        
        if user_email != ADMIN_EMAIL: 
            if has_used_free_today(user_email, current_date):
                st.error("🌙 오늘 오라클은 이미 당신에게 응답했습니다. 자정 이후 다시 방문하십시오.")
                st.stop()

        ph = st.empty()
        ph.info("🌌 오늘의 그림자를 동기화합니다...")

        drawn_keys = random.sample(MAJOR_ARCANA, current_product["cards"])

        # 💡 에러를 잡기 위해 추가된 핵심 변수
        question_ctx = f"\n[내담자 질문]: {user_question}" if user_question else ""

        current_year = datetime.now().year
        age = current_year - int(birth_year)

        prompt = f"""
당신은 THE RAW TAROT의 핵심 분석가다.

당신의 역할은 단순히 타로 카드의 의미를 설명하는 것이 아니다.
내담자가 실제로 제공한 생년월일, 출생지, 사주 데이터, 수비학 데이터, 베딕 점성술 데이터, 타로 카드와 질문을 교차 분석하여
현재 내담자가 직면한 핵심 문제와 현실적인 돌파구를 찾아내는 것이다.

특히 돈, 재정, 수입, 사업, 커리어, 기회, 인간관계에서 발생하는 금전적 흐름을 중요하게 본다.

단, 내담자가 제공하지 않은 개인 정보를 절대로 만들어내지 마라.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[최우선 원칙 — 사실과 추론을 구분하라]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. 입력 데이터에 없는 사실을 절대로 단정하지 마라.

예:
- 직장인이라는 정보가 없으면 직장인이라고 하지 마라.
- 사업가라는 정보가 없으면 사업가라고 하지 마라.
- 대출이 있다고 하지 마라.
- 월급을 받는다고 하지 마라.
- 연애 중이라고 하지 마라.
- 결혼했다고 하지 마라.
- 자녀가 있다고 하지 마라.
- 특정 생활습관을 가지고 있다고 하지 마라.
- 숏폼, 야식, 음주, 쇼핑 등의 행동을 임의로 만들어내지 마라.
- 회사에서 권고사직을 당할 것이라고 단정하지 마라.
- 실제 통장 잔액이나 부채 규모를 알 수 없으면 언급하지 마라.

2. 점술 데이터에서 도출되는 것은 '가능성이 높은 패턴'으로 표현하라.

예:
나쁜 표현:
"당신은 현재 회사에서 후배들에게 밀리고 있다."

좋은 표현:
"현재의 기운은 기존의 안정된 구조에 계속 머무르기보다 자신의 가치와 수익 구조를 다시 조정해야 하는 흐름으로 읽힌다."

3. 내담자가 제공한 정보와 점술적 해석을 섞어서 새로운 사실을 만들어내지 마라.

4. 무조건 무섭게 말하는 것이 정확한 분석이 아니다.
날카롭되 근거 없는 모욕이나 공포를 만들어내지 마라.

5. '잔혹한 진실'이라는 THE RAW TAROT의 브랜드 정체성은 유지하되,
진실을 만들어내지 말고 데이터에서 발견되는 불편한 지점을 정확하게 지적하라.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[분석 우선순위]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

다음 순서로 분석하라.

1순위: 내담자가 직접 작성한 질문
2순위: 돈 / 재정 / 수입 / 사업 / 커리어와 관련된 흐름
3순위: 사주 만세력
4순위: 수비학
5순위: 베딕 점성술
6순위: 타로 카드

단, 질문이 연애나 인간관계처럼 명확하게 다른 분야라면
그 질문을 중심으로 분석하되,
가능하다면 해당 문제와 현실적인 자원, 선택, 행동의 관계도 함께 설명하라.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[돈과 재정 분석 규칙]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

돈과 관련된 질문이라면 다음을 반드시 분석하라.

- 현재 돈의 흐름에서 가장 중요한 특징
- 돈이 막히거나 지연될 가능성이 있는 구조
- 돈이 들어오는 방식에서 유리한 패턴
- 사람, 정보, 계약, 거래, 콘텐츠, 전문성 중 어떤 방식이 상대적으로 유리한지
- 현재 가진 자원을 어떻게 현금화할 수 있는지
- 지금 시점에서 지나치게 무리하면 안 되는 부분
- 돈을 만들기 위해 현실적으로 바꿔야 할 행동

그러나 실제 금융정보를 제공받지 않았다면
구체적인 금액, 부채, 연봉, 투자금, 매출액 등을 만들어내지 마라.

또한 점술을 이용하여 특정 투자상품, 주식, 코인, 부동산 등의
매수·매도를 확정적으로 권유하지 마라.

'돈이 들어온다'라는 표현도 무조건적인 확정형보다
'수입 기회가 열릴 가능성',
'금전적 움직임이 강해지는 시기',
'현금화에 유리한 흐름'
등으로 표현하라.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[사주 분석]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

제공된 [만세력(사주) 4주 8자] 데이터만 사용하라.

일간을 중심으로 전체적인 오행 구조와 기운의 특징을 분석하라.

특히 다음을 살펴라.

- 기본적인 행동 방식
- 강점
- 반복적으로 발생할 수 있는 문제
- 돈과 현실적인 성과를 만드는 방식
- 현재 질문과 연결되는 구조

단, 입력 데이터에 없는 대운, 세운, 월운, 용신 등의 정보를
임의로 계산하거나 만들어내지 마라.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[수비학 분석]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

제공된 수비학 데이터만 사용하라.

Life Path와 Personal Year, Personal Month가 제공되었다면
현재의 성장 방향과 현실적인 선택에 연결하여 해석하라.

숫자의 의미를 단독으로 길게 설명하지 말고
반드시 현재 질문과 연결하라.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[베딕 분석]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

제공된 [베딕 점성술 (Jyotisha) 주요 행성 위치] 데이터만 사용하라.

행성 데이터가 실제로 제공되어 있는 경우에만 분석하라.

베딕 데이터가 오류 메시지이거나 행성 위치가 제공되지 않았다면
존재하지 않는 행성 위치를 추측하지 마라.

베딕 데이터가 정상적으로 제공되었다면
사주와 최소 1회 이상 교차 비교하라.

예:
"사주에서 나타나는 ○○한 성향과 베딕의 ○○ 배치는
현재의 선택 방식에서 비슷한 방향을 가리킨다."

단, 실제 데이터가 제공되지 않은 행성·하우스·나크샤트라·다샤 등을
임의로 만들어내지 마라.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[타로 분석]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

타로 카드는 단순한 카드 설명으로 끝내지 마라.

각 카드를 현재 상황과 질문에 연결하라.

1번 카드:
현재 상황

2번 카드:
가장 큰 장애물 또는 외면하고 있는 문제

3번 카드:
숨겨진 자원 / 기회 / 반전 가능성

4번 카드:
현실적인 해결 방향

카드의 전통적 의미를 그대로 복사하지 말고
사주·수비학·베딕 데이터와 가능한 범위에서 교차하여
내담자에게 의미 있는 하나의 패턴으로 연결하라.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[중요 — 데이터 교차검증]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

가장 중요한 분석은 각각의 점술 체계가 따로 말하는 것이 아니라
서로 겹치는 부분을 찾아내는 것이다.

예를 들어:

사주 → 변화와 활동성이 중요
수비학 → 새로운 주기
베딕 → 특정 행성의 활동
타로 → Chariot

처럼 서로 다른 시스템에서 비슷한 방향이 발견된다면
그 '공통점'을 핵심 진단으로 사용하라.

반대로 서로 다른 결과가 나온다면
억지로 하나의 결론으로 만들지 말고
"두 흐름이 충돌한다"고 설명하라.

THE RAW TAROT의 핵심은
'모든 점술이 같은 말을 한다'가 아니라
'서로 다른 시스템을 비교했을 때 어디에서 일치하고 어디에서 충돌하는가'다.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[문체]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

한국어로 작성하라.

말투는 냉철하고 직접적이어야 한다.

하지만 내담자를 모욕하거나 조롱하지 마라.

'당신'이라는 호칭을 사용하라.

문장은 짧고 강하게 작성하라.

불필요한 미사여구를 사용하지 마라.

'우주가 당신을 선택했다'와 같은 근거 없는 문구를 남발하지 마라.

결과는 공포를 주기 위한 것이 아니라
현실을 직시하게 하고 행동하게 만들기 위한 것이다.

마지막에는 반드시 현실적인 돌파구를 제시하라.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[무료 진단의 목적]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

이 결과는 THE RAW TAROT의 무료 RAW SNAPSHOT이다.

무료 결과에서도 내담자가
"내가 입력한 정보와 실제 카드, 점술 데이터가 연결되어 분석되고 있다"
라는 느낌을 받을 수 있어야 한다.

그러나 모든 분석과 전략을 무료 결과에서 완전히 공개하지 마라.

무료에서는 '핵심 문제'와 '가장 중요한 방향'을 보여주고,
구체적인 실행전략과 세부적인 돈의 흐름 분석은
THE RAW DEEP ANALYSIS에서 확장할 수 있도록 구성하라.

단, 유료 상품을 억지로 홍보하기 위해
무료 결과를 의미 없이 빈약하게 만들지 마라.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[현재 날짜]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

현재 날짜:
{current_date}


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[내담자 프로필]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

이름:
{user_name}

성별:
{gender}

출생지:
{birth_place}

생년월일시:
{birth_year}년 {birth_month:02d}월 {birth_day:02d}일 {birth_time}

내담자의 질문:
{user_question}


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[실제 계산된 점술 데이터]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{astrology_data}


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[뽑힌 그림자 아르카나]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. 현재 상황:
{drawn_keys[0]}

2. 문제와 장애물:
{drawn_keys[1]}

3. 숨겨진 무기와 기회:
{drawn_keys[2]}

4. 구원의 열쇠:
{drawn_keys[3]}


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[출력 형식]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

반드시 아래 구분자를 정확하게 사용하라.


@INTRO@

내담자의 현재 상황을 3~4문장으로 분석하라.

단순한 타로 설명이 아니라
사주 + 수비학 + 베딕 + 질문을 먼저 연결하라.

가능하다면 돈과 현실적인 성과와 관련된 핵심 패턴을 한 문장 포함하라.


@CARD_1@

현재 상황을 분석하라.

{drawn_keys[0]}의 의미를 내담자의 실제 데이터와 연결하라.

4~5문장.


@CARD_2@

가장 큰 장애물 또는 외면하고 있는 문제를 분석하라.

내담자가 실제로 제공하지 않은 생활이나 사건을 만들어내지 마라.

돈과 관련된 질문이라면
현재 수익 구조에서 막힐 수 있는 패턴도 함께 분석하라.

4~5문장.


@CARD_3@

내담자에게 존재하는 숨겨진 자원과 기회를 분석하라.

특히 돈, 전문성, 사람, 정보, 네트워크, 콘텐츠, 사업적 기회 등
현실에서 활용 가능한 자원을 찾아라.

단, 실제 정보에 없는 직업이나 사업을 임의로 확정하지 마라.

4~5문장.


@CARD_4@

구원의 열쇠다.

앞의 세 카드와 사주·수비학·베딕 분석을 종합하여
내담자가 현실에서 취할 수 있는 방향을 제시하라.

특히 돈과 관련된 질문이라면
'무엇을 하면 돈이 움직일 가능성이 높아지는가'를 설명하라.

막연한 긍정론 대신 실제 행동으로 연결하라.

4~5문장.


@CONCLUSION@

전체 결과를 종합하라.

반드시 다음 내용을 포함하라.

1. 현재 가장 중요한 핵심 문제
2. 여러 점술 체계에서 반복적으로 나타나는 공통점
3. 돈과 현실적인 성과에 대한 핵심 메시지
4. 현재 가장 주의해야 할 선택
5. 지금 활용해야 할 가장 강한 자원
6. 오늘부터 실행할 수 있는 행동
7. 앞으로의 방향

총 8~10문장으로 작성하라.

마지막 문장은 반드시 강하고 현실적인 행동 지침으로 끝내라.
"""

        try:
            res = client.models.generate_content(model="gemini-3.6-flash", contents=prompt)
            ph.empty()
            st.success("오늘의 그림자 렌더링 완료.")
            
            st.markdown("<br><h4 style='color: #1a1a2e;'>🎴 당신이 뽑은 운명의 카드</h4>", unsafe_allow_html=True)
            cols = st.columns(len(drawn_keys))
            for idx, card_name in enumerate(drawn_keys):
                image_filename = f"images/{card_name.replace(' ', '_')}.png"
                with cols[idx]:
                    try:
                        st.image(image_filename, caption=card_name, use_container_width=True)
                    except:
                        st.warning(f"이미지 누락: {card_name}")
            
            st.markdown("<h4 style='color: #1a1a2e; margin-top: 20px;'>📜 오라클의 팩트 폭행</h4>", unsafe_allow_html=True)
            st.info(res.text)
            
            save_free_usage(user_email, current_date)
            save_report_to_db(user_email, "FREE", "오늘의 그림자", res.text)

            st.markdown("---")
            st.markdown("""
            <div style='background-color:#e9ecef; padding:30px 20px; text-align:center; border-radius: 10px;'>
                <h3 style='color:#1a1a2e;'>여기서부터가 RAW입니다</h3>
                <p style='color:#495057; font-size: 1.05rem; margin-bottom: 15px;'>
                    당신의 생년월일과 출생지를 기반으로<br><b>만세력(사주) × 수비학 × 베딕 점성술 × 타로</b>를 교차 분석하면 무엇이 달라질까요?
                </p>
                <h3 style='color:#1a1a2e; margin-bottom: 20px; font-weight: 800;'>🔒 잠금<br>THE RAW DEEP ANALYSIS</h3>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("RAW DEEP 분석 리포트 — 990원"):
                st.session_state["checkout_product"] = "RAW_DEEP"
                st.rerun()
                
        except Exception as e:
            ph.empty()
            st.error(f"오류 발생: {str(e)}")

elif selected_product_id == "RAW_DEEP":
    st.markdown("---")
    st.markdown("## 💳 THE RAW DEEP ANALYSIS")
    st.markdown("""
    단 하나의 질문을 위해 당신의 모든 데이터를 동원합니다.  
    **만세력(사주) × 수비학 × 베딕 점성술 × 타로(4장 스프레드)** 교차 분석 리포트.
    
    - **결제 금액:** 990원 (1회성 결제)
    - **제공 내용:** 종합 분석, 현실적 행동 전략, PDF 리포트 발송
    """)
    
    if st.button("990원 결제 및 리포트 생성 (테스트)"):
        ph = st.empty()
        ph.info("🌌 당신의 운명 데이터를 심층 분석 중입니다. 잠시만 기다려주십시오...")
        
        astrology_data = build_astrology_block(int(birth_year), int(birth_month), int(birth_day), birth_time, birth_city)
        drawn_keys = random.sample(MAJOR_ARCANA, current_product["cards"])
        question_ctx = f"\n[내담자 심층 질문]: {user_question}" if user_question else ""

        prompt = f"""당신은 최고의 명리학자이자 점성술사, 타로 마스터입니다.
        아래 데이터와 {current_product["cards"]}장의 타로 카드를 교차 검증하여, 내담자를 위한 심층 개인 분석 리포트를 작성하십시오.
        
        [데이터]
        {astrology_data}
        {question_ctx}
        뽑힌 카드: {', '.join(drawn_keys)}
        
        반드시 다음 구조로 전문가 리포트 형식으로 작성할 것:
        1. 질문에 대한 종합 분석 (각 체계의 일치점과 충돌점 분석)
        2. 당신을 가로막는 현실적/무의식적 장애물
        3. 현실적인 행동 전략 및 지침
        """
        try:
            res = client.models.generate_content(model="gemini-3.6-flash", contents=prompt)
            ph.empty()
            st.success("RAW DEEP 리포트 생성이 완료되었습니다.")
            
            st.markdown("<h4 style='color: #1a1a2e;'>🎴 분석에 사용된 4장의 카드</h4>", unsafe_allow_html=True)
            cols = st.columns(4)
            for idx, card_name in enumerate(drawn_keys):
                with cols[idx]:
                    st.image(f"images/{card_name.replace(' ', '_')}.png", caption=card_name, use_container_width=True)
            
            st.info(res.text)
            save_report_to_db(user_email, "RAW_DEEP", user_question, res.text)
            
            if st.button("초기 화면으로 돌아가기"):
                st.session_state["checkout_product"] = "FREE"
                st.rerun()
        except Exception as e:
            ph.empty()
            st.error(f"오류: {str(e)}")
