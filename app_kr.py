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
    "Wheel of Fortune", "Justice", "The Hanged Man", "Death", "Temperance",
    "The Devil", "The Tower", "The Star", "The Moon", "The Sun",
    "Judgement", "The World"
]

# ── 오라클 버튼 실행 및 결제 대기(Checkout) 분기 ────────────────────────────────
if selected_product_id == "FREE":
    if st.button("무료 체험 시작하기"):
        current_date = datetime.now().strftime("%Y-%m-%d")
        upsert_user(user_email, user_name)
        
        if user_email != ADMIN_EMAIL: 
            if has_used_free_today(user_email, current_date):
                st.error("🌙 오늘 오라클은 이미 당신에게 응답했습니다. 자정 이후 다시 방문하십시오.")
                st.stop()

        ph = st.empty()
        ph.info("🌌 무료 체험 우주적 데이터를 동기화합니다...")

        gender_str = "Male" if gender == "남성" else "Female"
        astrology_data = build_astrology_block(int(birth_year), int(birth_month), int(birth_day), birth_time, birth_city)
        drawn_keys = random.sample(MAJOR_ARCANA, current_product["cards"])
        question_ctx = f"\n[내담자 질문]: {user_question}" if user_question else ""

        prompt = f"""당신은 냉철한 운명 전략가입니다.
        아래 데이터와 {current_product["cards"]}장의 타로 카드를 바탕으로 '무료 체험용' 짧은 핵심 메시지를 작성하십시오. 상세 예측은 금지합니다.
        
        [데이터]
        {astrology_data}
        {question_ctx}
        뽑힌 카드: {', '.join(drawn_keys)}
        
        반드시 다음 구조로 작성:
        1. 짧고 강렬한 현재 상황 진단
        2. 핵심 경고 메시지
        """

        try:
            res = client.models.generate_content(model="gemini-3.6-flash", contents=prompt)
            ph.empty()
            st.success("무료 체험 렌더링 완료.")
            st.info(res.text)
            
            save_free_usage(user_email, current_date)
            save_report_to_db(user_email, "FREE", user_question, res.text)

            st.markdown("---")
            st.markdown("""
            <div style='background-color:#e9ecef; padding:20px; text-align:center;'>
                <h3 style='color:#1a1a2e;'>여기서부터가 RAW입니다</h3>
                <p style='color:#212529;'>단 하나의 질문을 4개의 시스템으로 교차분석한 전체 리포트를 확인하세요.</p>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("RAW ONE 심층 리포트 보기 — 990원"):
                st.session_state["checkout_product"] = "RAW_ONE"
                st.rerun()
        except Exception as e:
            ph.empty()
            st.error(f"아스트랄 연결 오류: {str(e)}")

elif selected_product_id == "RAW_ONE":
    st.markdown("---")
    st.markdown("## 💳 RAW ONE 결제 데스크")
    st.markdown("""
    당신의 단 하나의 질문을 **타로(5장) × 사주 × 수비학 × 베딕 점성술**로 교차 검증합니다.
    - **결제 금액:** 990원
    - **제공 내용:** 현재 상황, 충돌 신호 분석, 숨겨진 장애물, 단호한 행동 전략
    """)
    
    # [TO-DO] 이 버튼을 누르면 실제 토스페이먼츠 결제창으로 넘어가도록 다음 단계에서 구현합니다.
    # 현재는 결제가 완료되었다고 가정하고 심층 프롬프트를 즉시 실행하는 테스트용입니다.
    if st.button("990원 결제하기 (현재는 클릭 시 즉시 생성)"):
        ph = st.empty()
        ph.info("🌌 RAW ONE 심층 우주적 데이터를 동기화합니다...")
        
        gender_str = "Male" if gender == "남성" else "Female"
        astrology_data = build_astrology_block(int(birth_year), int(birth_month), int(birth_day), birth_time, birth_city)
        drawn_keys = random.sample(MAJOR_ARCANA, current_product["cards"])
        question_ctx = f"\n[내담자 질문]: {user_question}" if user_question else ""

        prompt = f"""당신은 냉철하고 분석적인 운명 전략가입니다.
        아래 데이터와 {current_product["cards"]}장의 타로 카드를 '교차 검증'하여 심층 리포트를 작성하십시오.
        
        [데이터]
        {astrology_data}
        {question_ctx}
        뽑힌 카드: {', '.join(drawn_keys)}
        
        반드시 다음 구조로 작성:
        1. 질문의 본질과 현재 상황 (팩트 폭행)
        2. 점술 시스템 간 일치하는 신호와 충돌하는 신호 분석
        3. 당신을 가로막는 숨겨진 장애물
        4. 즉각적으로 실행해야 할 단호한 행동 전략
        """
        try:
            res = client.models.generate_content(model="gemini-3.6-flash", contents=prompt)
            ph.empty()
            st.success("RAW ONE 심층 리포트 렌더링 완료.")
            st.info(res.text)
            save_report_to_db(user_email, "RAW_ONE", user_question, res.text)
            
            if st.button("돌아가기"):
                st.session_state["checkout_product"] = "FREE"
                st.rerun()
        except Exception as e:
            ph.empty()
            st.error(f"오류: {str(e)}")
