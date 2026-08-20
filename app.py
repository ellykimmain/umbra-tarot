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

if user_email: st.info(f"✉️ Welcome, voyager. Prophecy will be sent to: **{user_email}**")

# 입력 폼
user_name = st.text_input("Your Name / Alias", "")
birth_place = st.text_input("Origin / Place of Birth (City, Country)", "") # 이 줄을 추가하십시오.

# (이 아래에 기존의 Year, Month, Day 입력 코드는 그대로 둡니다)
birth_year = st.number_input("Year", min_value=1930, max_value=2026, value=1988)
# (중략: Birth date/time inputs 동일)
birth_month = st.number_input("Month", min_value=1, max_value=12, value=6)
birth_day = st.number_input("Day", min_value=1, max_value=31, value=15)
birth_time = "12:00"

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
    
    prompt = f"Perform a mystic tarot reading for {user_name}."
    response = client.models.generate_content(model="gemini-3.6-flash", contents=prompt)
    
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
