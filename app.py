import smtplib
from email.mime.text import MIMEText
import streamlit as st
import random
import time
import os
import requests
from google import genai
from streamlit_oauth import OAuth2Component
from datetime import datetime

# Streamlit Secrets 로드
api_key = st.secrets["GEMINI_API_KEY"]
client = genai.Client(api_key=api_key)

CLIENT_ID = st.secrets["GOOGLE_CLIENT_ID"]
CLIENT_SECRET = st.secrets["GOOGLE_CLIENT_SECRET"]
REDIRECT_URI = st.secrets["REDIRECT_URI"]
AUTHORIZE_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
REVOKE_ENDPOINT = "https://oauth2.googleapis.com/revoke"

oauth2 = OAuth2Component(CLIENT_ID, CLIENT_SECRET, AUTHORIZE_ENDPOINT, TOKEN_ENDPOINT, TOKEN_ENDPOINT, REVOKE_ENDPOINT)

st.set_page_config(page_title="Umbra & Tarot: Shadow Prophecy", layout="centered")

# 커스텀 CSS
st.markdown("""
    <style>
    .stApp { background-color: #0b0b0e; color: #f1f1f1; }
    .main-title { text-align: center; color: #f3e5ab; font-family: 'Cinzel', serif; letter-spacing: 2px; text-shadow: 0 0 10px rgba(243, 229, 171, 0.3); font-size: 2.5rem; }
    .sub-title { text-align: center; color: #b3b3cc; font-size: 1.05rem; }
    .card-box { background-color: #15151c; border: 1px solid #4a4a75; padding: 15px; border-radius: 10px; text-align: center; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.5); }
    div.stButton > button:first-child { background-color: #15151c; color: #f3e5ab; border: 1px solid #4a4a75; font-weight: 600; border-radius: 5px; width: 100%; }
    div.stButton > button:first-child:hover { background-color: #4a4a75; color: #ffffff; border: 1px solid #f3e5ab; }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='main-title'> UMBRA & TAROT</h1>", unsafe_allow_html=True)
st.markdown("<p class='sub-title'>Pierce the veil of your shadow self. Unearth the truths hidden in the astral dark.</p>", unsafe_allow_html=True)

# 로그인 세션 관리
if "google_token" not in st.session_state:
    st.markdown("### ✨ Claim Your 3-Day Free Trial")
    st.markdown("Unlock the gates. Sign in now to receive your **complimentary 'Who Am I' shadow reading** and **1 deep custom query**.")
    st.info("Google Login is required to begin your free trial and enter the astral realm.")
    
    result = oauth2.authorize_button(name="Continue with Google", icon="https://www.google.com/favicon.ico", redirect_uri=REDIRECT_URI, scope="openid email profile", key="google_login", use_container_width=True)
    if result:
        st.session_state["google_token"] = result.get("token")
        st.rerun()
    st.stop()

if "user_email" not in st.session_state:
    try:
        headers = {'Authorization': f'Bearer {st.session_state["google_token"]["access_token"]}'}
        user_info = requests.get('https://www.googleapis.com/oauth2/v1/userinfo', headers=headers).json()
        st.session_state["user_email"] = user_info.get('email', '')
    except: st.session_state["user_email"] = ""

user_email = st.session_state["user_email"]

# 사이드바 (Pro 기능 비활성화)
st.sidebar.markdown("### 🪐 Membership Tiers")
st.sidebar.radio("Select Your Plan", ["Free Trial (Active)", "Pro Oracle (Available Sept 1st)"], index=0, disabled=True)
st.sidebar.info("✨ **Grand Opening!** Currently in Free Trial Period.")
st.sidebar.warning("💎 **Pro Oracle** features will unlock on September 1st.")
st.sidebar.markdown("---")
st.sidebar.markdown("### 🔮 Oracle Mode")
reading_mode = st.sidebar.radio("Choose Reading Focus", ["1. Who Am I? (Raw Shadow Discovery)", "2. Custom Oracle Query (Deep Question)"])

if user_email:
    st.markdown(f"""
        <div style="background-color: #151522; padding: 15px; border-radius: 8px; border: 1px solid #3f3f5a; color: #e0e0e0; margin-bottom: 20px;">
            🌌 <b>Welcome, voyager.</b> Prophecy will be sent to: <span style="color: #fca311; font-weight: bold;">{user_email}</span>
        </div>
    """, unsafe_allow_html=True)

# 입력 폼
user_name = st.text_input("Your Name / Alias", "")
# 국가와 도시를 좌우로 분리하여 입력받는 UI
col1, col2 = st.columns(2)
with col1:
    birth_country = st.text_input("Country of Birth", "United States") # 주요 타깃 국가를 기본값으로 세팅
with col2:
    birth_city = st.text_input("City of Birth", "")

# 지역 입력(City, Country) 코드 바로 아래에 추가
birth_time = st.text_input("Time of Birth (e.g., 23:30 or Unknown)", "Unknown")

# AI 프롬프트 전달을 위해 백그라운드에서 하나의 텍스트로 병합
birth_place = f"{birth_city}, {birth_country}"

# (이 아래에 기존의 Year, Month, Day 입력 코드는 그대로 둡니다)
birth_year = st.number_input("Year", min_value=1930, max_value=2026, value=1988)
# (중략: Birth date/time inputs 동일)
birth_month = st.number_input("Month", min_value=1, max_value=12, value=6)
birth_day = st.number_input("Day", min_value=1, max_value=31, value=15)
# 태어난 시간 선택 (30분 단위 드롭다운)
time_options = ["Unknown"] + [f"{h:02d}:{m:02d}" for h in range(24) for m in (0, 30)]
birth_time = st.selectbox("Time of Birth", time_options)

# (위쪽에는 생년월일, 태어난 시간 등의 입력 코드가 있습니다.)

# 커스텀 질문 모드일 경우: 드롭다운 선택 및 직접 입력 연동
if "2." in reading_mode or "Custom" in reading_mode:
    question_options = [
        "What is the hidden truth of my current situation?",
        "What subconscious fear is holding me back?",
        "What energy should I embrace to move forward?",
        "Direct Input (Write your own query)"
    ]
    selected_query = st.selectbox("Choose your query or select Direct Input", question_options)
    
    # '직접 입력'을 선택했을 때만 텍스트 입력창 활성화
    if selected_query == "Direct Input (Write your own query)":
        user_question = st.text_area("Your Deep Query", placeholder="Type your specific question here...")
    else:
        user_question = selected_query
else:
    user_question = ""

# 메인 버튼 및 방어 로직
if st.button("Consult the Oracle & Draw Cards"):
    today = datetime.now().strftime("%Y-%m-%d")
    user_key = f"{user_email}_{today}"
    if "already_prophesied" not in st.session_state: st.session_state["already_prophesied"] = {}
    
    # [테스트 시 limit=1 로 설정됨]
    count = st.session_state["already_prophesied"].get(user_key, 0)
    if count >= 1:
        st.error("🌙 The Oracle has already spoken to you for today. Return when the stars realign tomorrow.")
        st.stop()

    # 리딩 수행
    drawn_keys = random.sample(["The Fool", "The Magician", "The Hermit", "The Devil", "The Star"], 3)
    status = st.info("🌌 Tunnelling through the astral plane...")
    time.sleep(1)
    
   # 1. 커스텀 질문 존재 여부에 따른 조건부 텍스트 추가
question_context = f"\nUSER'S DEEP QUERY: {user_question}" if user_question else ""

# 2. 점성술과 Manse-ryeok 기운이 통합된 프롬프트 엔진
prompt = f"""You are a dark, mystic Tarot Oracle. Perform a chillingly accurate and deep shadow reading.

USER PROFILE
Name: {user_name}
Origin: {birth_place}
Birth: {birth_year}-{birth_month:02d}-{birth_day:02d} {birth_time}{question_context}

ASTROLOGICAL & MANSE-RYEOK ALIGNMENT
Calculate and analyze the user's Western Astrological profile (Sun, Moon, Ascendant) and Eastern Manse-ryeok (Four Pillars) elemental dynamics based on the provided time and location. Do not output the raw chart data. Instead, seamlessly weave these precise cosmic mechanics and elemental forces into the Tarot interpretation to create a highly differentiated, deep reading.

Deliver the prophecy in a dark, atmospheric tone."""

# 3. Gemini API 호출 (최신 3.6-flash 모델)
response = client.models.generate_content(
    model="gemini-3.6-flash", 
    contents=prompt
)
    
# 성공 기록
st.session_state["already_prophesied"][user_key] = count + 1

st.success("Prophecy manifested.")
st.info(response.text)

# 이메일 발송
try:
    msg = MIMEText(f"Prophecy for {user_name}:\n\n{response.text}")
    msg['Subject'] = "👁️ Your Shadow Prophecy"
    msg['From'] = st.secrets["EMAIL_SENDER"]
    msg['To'] = user_email
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(st.secrets["EMAIL_SENDER"], st.secrets["EMAIL_PASSWORD"])
        server.send_message(msg)
except: st.error("Email failed.")
