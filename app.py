import smtplib
from email.mime.text import MIMEText
import streamlit as st
import random
import time
import requests
import os
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

st.set_page_config(page_title="Umbra & Tarot: Shadow Prophecy", layout="centered", initial_sidebar_state="expanded")

# 화이트 배경 및 깔끔한 가독성을 위한 커스텀 CSS
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

st.markdown("<h1 class='main-title'> UMBRA & TAROT</h1>", unsafe_allow_html=True)
st.markdown("<p class='sub-title'>Pierce the veil of your shadow self. Unearth the truths hidden in the astral dark.</p>", unsafe_allow_html=True)

# 로그인 세션 관리
if "google_token" not in st.session_state:
    st.markdown("### ✨ Claim Your 3-Day Free Trial")
    st.markdown("Unlock the gates. Sign in now to receive your **complimentary 'Who Am I' shadow reading** and **1 deep custom query**.")
    st.info("👁️ Google Login is required to begin your free trial and enter the astral realm.")
    
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
    except: 
        st.session_state["user_email"] = ""

user_email = st.session_state["user_email"]

# 사이드바
st.sidebar.markdown("### 🪐 Membership Tiers")
st.sidebar.radio("Select Your Plan", ["Free Trial (Active)", "Pro Oracle (Available Sept 1st)"], index=0, disabled=True)
st.sidebar.info("✨ **Grand Opening!** Currently in Free Trial Period.")
st.sidebar.warning("💎 **Pro Oracle** features will unlock on September 1st.")
st.sidebar.markdown("---")
st.sidebar.markdown("### 🔮 Oracle Mode")
reading_mode = st.sidebar.radio("Choose Reading Focus", ["1. Who Am I? (Raw Shadow Discovery)", "2. Custom Oracle Query (Deep Question)"])

# 환영 메시지
if user_email:
    st.markdown(f"""
        <div style="background-color: #e9ecef; padding: 15px; border-radius: 8px; border: 1px solid #ced4da; color: #212529; margin-bottom: 20px;">
            🌌 <b>Welcome, voyager.</b> Prophecy will be sent to: <span style="color: #d97706; font-weight: bold;">{user_email}</span>
        </div>
    """, unsafe_allow_html=True)

# 1. 국가/도시 매핑 데이터베이스 (주요 국가 및 도시 세팅)
country_city_map = {
    "South Korea": ["Seoul", "Daejeon", "Daegu", "Busan", "Jeju", "Other"],
    "United States": ["New York", "Los Angeles", "Chicago", "Seattle", "Other"],
    "United Kingdom": ["London", "Manchester", "Edinburgh", "Other"],
    "Japan": ["Tokyo", "Osaka", "Kyoto", "Other"],
    "Australia": ["Sydney", "Melbourne", "Brisbane", "Other"],
    "Canada": ["Toronto", "Vancouver", "Montreal", "Other"],
    "Other": ["Other"]
}

# 2. 관리자(본인) 퀵 자동 완성 로직
# 아래 이메일을 실제 네 구글 계정 이메일로 수정해라.
ADMIN_EMAIL = "ellykimmain@gmail.com" 

if user_email == ADMIN_EMAIL:
    default_name = "Kim Uyoun"
    default_country_idx = 0  # South Korea
    default_year = 1988      # 본인 출생년도
else:
    default_name = ""
    default_country_idx = 1  # United States
    default_year = 1988

# 입력 폼
user_name = st.text_input("Your Name / Alias", default_name)

# 국가/도시 연동 드롭다운
col1, col2 = st.columns(2)
with col1:
    birth_country = st.selectbox("Country of Birth", list(country_city_map.keys()), index=default_country_idx)
with col2:
    birth_city = st.selectbox("City of Birth", country_city_map[birth_country])

# 'Other' 선택 시 직접 입력할 수 있는 폼 제공
if birth_city == "Other":
    birth_city = st.text_input("Please specify your city", "")

birth_place = f"{birth_city}, {birth_country}"

birth_year = st.number_input("Year", min_value=1930, max_value=2026, value=default_year)
birth_month = st.number_input("Month", min_value=1, max_value=12, value=6)
birth_day = st.number_input("Day", min_value=1, max_value=31, value=15)

time_options = ["Unknown"] + [f"{h:02d}:{m:02d}" for h in range(24) for m in (0, 30)]
birth_time = st.selectbox("Time of Birth", time_options)

# 질문 프리셋 확장 및 직접 입력
if "2." in reading_mode or "Custom" in reading_mode:
    question_options = [
        "When will this current financial hardship finally improve?",
        "What is the hidden block preventing my wealth and success?",
        "What is the brutal truth about my connection with my current partner?",
        "I am single. When will authentic love pierce through my isolation?",
        "Am I on the right path with my current business or career?",
        "Why do I keep repeating the same destructive patterns?",
        "What truth am I aggressively avoiding right now?",
        "What does my shadow self desperately want me to know?",
        "Direct Input (Write your own query)"
    ]
    selected_query = st.selectbox("Choose your query or select Direct Input", question_options)
    
    if selected_query == "Direct Input (Write your own query)":
        user_question = st.text_area("Your Deep Query", placeholder="e.g., Will my new business venture succeed this year?")
    else:
        user_question = selected_query
else:
    user_question = ""

# 메인 버튼 및 실행 로직
if st.button("Consult the Oracle & Draw Cards"):
    current_date = datetime.now().strftime("%Y-%m-%d")
    user_key = f"{user_email}_{current_date}"
    if "already_prophesied" not in st.session_state: 
        st.session_state["already_prophesied"] = {}
    
    count = st.session_state["already_prophesied"].get(user_key, 0)
    if count >= 1:
        st.error("🌙 The Oracle has already spoken to you for today. Return when the stars realign tomorrow.")
        st.stop()

    # 테두리 없는 깔끔한 텍스트 애니메이션 로딩
    loading_placeholder = st.empty()
    
    loading_placeholder.markdown("<p style='text-align: center; color: #6c757d; font-size: 1.1rem; font-weight: bold;'>🌌 Tunnelling through the astral plane...</p>", unsafe_allow_html=True)
    time.sleep(1.5)
    loading_placeholder.markdown("<p style='text-align: center; color: #6c757d; font-size: 1.1rem; font-weight: bold;'>🔮 Consulting the cosmic alignment & Manse-ryeok data...</p>", unsafe_allow_html=True)
    time.sleep(1.5)
    loading_placeholder.markdown("<p style='text-align: center; color: #6c757d; font-size: 1.1rem; font-weight: bold;'>🃏 Drawing the shadow arcana cards...</p>", unsafe_allow_html=True)
    time.sleep(1.5)
    loading_placeholder.markdown("<p style='text-align: center; color: #d97706; font-size: 1.1rem; font-weight: bold;'>⚡ Channeling the blunt prophecy...</p>", unsafe_allow_html=True)
    time.sleep(1.5)
    
    try:
        astrology_data = "External API connection placeholder: Sun in Taurus, Moon in Scorpio, Ascendant Leo."
    except Exception as e:
        astrology_data = "API connection failed. Falling back to native cosmic calculations."

    major_arcana_deck = [
        "The Fool", "The Magician", "The High Priestess", "The Empress", "The Emperor", 
        "The Hierophant", "The Lovers", "The Chariot", "Strength", "The Hermit", 
        "Wheel of Fortune", "Justice", "The Hanged Man", "Death", "Temperance", 
        "The Devil", "The Tower", "The Star", "The Moon", "The Sun", 
        "Judgement", "The World"
    ]

    drawn_keys = random.sample(major_arcana_deck, 3)
    question_context = f"\nUSER'S DEEP QUERY: {user_question}" if user_question else ""

    # 확장자 대응을 위한 베이스 파일명 딕셔너리
    card_base_names = {
        "The Fool": "The_Fool",
        "The Magician": "The_Magician",
        "The High Priestess": "The_High_Priestess",
        "The Empress": "The_Empress",
        "The Emperor": "The_Emperor",
        "The Hierophant": "The_Hierophant",
        "The Lovers": "The_Lovers",
        "The Chariot": "The_Chariot",
        "Strength": "Strength",
        "The Hermit": "The_Hermit",
        "Wheel of Fortune": "Wheel_of_Fortune",
        "Justice": "Justice",
        "The Hanged Man": "The_Hanged_Man",
        "Death": "The_Death",
        "Temperance": "Temperance",
        "The Devil": "The_Devil",
        "The Tower": "The_Tower",
        "The Star": "The_Star",
        "The Moon": "The_Moon",
        "The Sun": "The_Sun",
        "Judgement": "Judgement",
        "The World": "The_World"
    }

    # 프롬프트에 실시간 접속 날짜를 강제 주입하여 시간 오류 완벽 차단
    prompt = f"""You are a highly skilled, blunt, and slightly cynical traditional Thai fortune teller. 
You speak directly, offering no comforting lies. Deliver cold, hard truths based on the cosmic data. Use a tone that is piercing, mystical, and authoritative.

CURRENT DATE & TIME: {current_date} (Ensure all future predictions start strictly from this specific date onwards. Do not refer to past years as the future.)

USER PROFILE
Name: {user_name}
Origin: {birth_place}
Birth: {birth_year}-{birth_month:02d}-{birth_day:02d} {birth_time}{question_context}

ASTROLOGY API REAL-TIME DATA & MANSE-RYEOK
{astrology_data}
Calculate the precise Eastern Manse-ryeok (Four Pillars) elemental dynamics based on the provided time and location.

DRAWN ARCANAS
{', '.join(drawn_keys)}

Analyze the exact astrological data provided above, the Manse-ryeok elements, and the Tarot cards. 
Do not output raw data. Weave the exact cosmic alignments and the cards into a chillingly accurate, highly specific reading. Speak in English, reflecting the exact tone of a traditional, blunt Thai fortune teller."""

    try:
        response = client.models.generate_content(
            model="gemini-3.6-flash", 
            contents=prompt
        )
        
        st.session_state["already_prophesied"][user_key] = count + 1
        
        # 로딩 텍스트 삭제
        loading_placeholder.empty()
        
        st.success("Prophecy manifested.")
        st.info(response.text)

        # 이미지 렌더링 (.jpg 및 .png 자동 이중 탐색)
        st.markdown("<h3 style='text-align: center; color: #1a1a2e; margin-top: 20px;'>🃏 The Drawn Arcanas</h3>", unsafe_allow_html=True)
        cols = st.columns(3)
        
        for i, card in enumerate(drawn_keys):
            with cols[i]:
                base_name = card_base_names.get(card, "")
                img_path_jpg = f"images/{base_name}.jpg"
                img_path_png = f"images/{base_name}.png"
                
                if os.path.exists(img_path_jpg):
                    st.image(img_path_jpg, caption=card, use_container_width=True)
                elif os.path.exists(img_path_png):
                    st.image(img_path_png, caption=card, use_container_width=True)
                else:
                    st.error(f"[{card} Image Missing]")

        # 이메일 발송
        try:
            msg = MIMEText(f"Prophecy for {user_name}:\n\n{response.text}")
            msg['Subject'] = "👁️ Your Shadow Prophecy"
            msg['From'] = st.secrets["EMAIL_SENDER"]
            msg['To'] = user_email
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(st.secrets["EMAIL_SENDER"], st.secrets["EMAIL_PASSWORD"])
                server.send_message(msg)
        except Exception as e: 
            st.error("Email failed.")
            
    except Exception as e:
        # 에러 발생 시 로딩 텍스트 삭제
        loading_placeholder.empty()
        error_msg = str(e)
        if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
            st.error("🌙 The astral energy is depleted. Today's complimentary prophecies (Limit: 20) have concluded. Return after midnight.")
        else:
            st.error("The astral connection was lost. Please try again later.")
