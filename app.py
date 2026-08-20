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
import gspread
from google.oauth2.credentials import Credentials

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

st.set_page_config(
    page_title="Umbra & Tarot: Shadow Prophecy",
    layout="centered"
)

# 커스텀 CSS
st.markdown("""
    <style>
    .stApp { background-color: #0b0b0e; color: #f1f1f1; }
    .main-title {
        text-align: center; color: #f3e5ab; font-family: 'Cinzel', serif;
        letter-spacing: 2px; text-shadow: 0 0 10px rgba(243, 229, 171, 0.3); font-size: 2.5rem;
    }
    @media (max-width: 768px) { .main-title { font-size: 1.6rem !important; } }
    .sub-title { text-align: center; color: #b3b3cc; font-size: 1.05rem; }
    .card-box {
        background-color: #15151c; border: 1px solid #4a4a75; padding: 15px;
        border-radius: 10px; text-align: center; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.5);
    }
    label { color: #d1d1e0 !important; font-weight: 500; }
    div.stButton > button:first-child {
        background-color: #15151c; color: #f3e5ab; border: 1px solid #4a4a75;
        font-weight: 600; border-radius: 5px; width: 100%;
    }
    div.stButton > button:first-child:hover { background-color: #4a4a75; color: #ffffff; border: 1px solid #f3e5ab; }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='main-title'>👁️ UMBRA & TAROT</h1>", unsafe_allow_html=True)
st.markdown("<p class='sub-title'>Pierce the veil of your shadow self. Unearth the truths hidden in the astral dark.</p>", unsafe_allow_html=True)

# 🚨 전면 로그인 방어벽
if "google_token" not in st.session_state:
    st.warning("👁️ Google Login is required to enter the astral realm.")
    result = oauth2.authorize_button(
        name="Continue with Google",
        icon="https://www.google.com/favicon.ico",
        redirect_uri=REDIRECT_URI,
        scope="openid email profile https://www.googleapis.com/auth/spreadsheets",
        key="google_login",
        use_container_width=True
    )
    if result:
        st.session_state["google_token"] = result.get("token")
        st.rerun()
    st.stop()

# 로그인 성공 후 이메일 추출
if "user_email" not in st.session_state:
    try:
        access_token = st.session_state["google_token"]["access_token"]
        headers = {'Authorization': f'Bearer {access_token}'}
        user_info = requests.get('https://www.googleapis.com/oauth2/v1/userinfo', headers=headers).json()
        st.session_state["user_email"] = user_info.get('email', '')
    except Exception:
        st.session_state["user_email"] = ""

user_email = st.session_state["user_email"]

# 구글 시트 DB 연결 함수 (OAuth 토큰 활용)
def get_user_usage_from_sheet(email):
    try:
        access_token = st.session_state["google_token"]["access_token"]
        creds = Credentials(access_token)
        gc = gspread.authorize(creds)
        
        # 'Umbra_DB' 스프레드시트 열기
        sheet = gc.open("Umbra_DB").sheet1
        records = sheet.get_all_records()
        
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        for i, row in enumerate(records):
            if row.get("Email") == email:
                if row.get("Date") == today_str:
                    return int(row.get("WhoAmI_Count", 0)), int(row.get("Custom_Count", 0)), i + 2 # row index
                else:
                    # 날짜가 바뀌었으면 오늘 날짜로 초기화 갱신
                    sheet.update_cell(i + 2, 2, today_str)
                    sheet.update_cell(i + 2, 3, 0)
                    sheet.update_cell(i + 2, 4, 0)
                    return 0, 0, i + 2
                    
        # 유저 기록이 없으면 새로 추가
        sheet.append_row([email, today_str, 0, 0])
        return 0, 0, len(records) + 2
    except Exception as e:
        st.error(f"Database connection warning: {e}")
        return 0, 0, None

def update_user_usage_in_sheet(row_idx, whoami_count, custom_count):
    try:
        access_token = st.session_state["google_token"]["access_token"]
        creds = Credentials(access_token)
        gc = gspread.authorize(creds)
        sheet = gc.open("Umbra_DB").sheet1
        
        sheet.update_cell(row_idx, 3, whoami_count)
        sheet.update_cell(row_idx, 4, custom_count)
    except Exception as e:
        pass

# 사이드바
st.sidebar.markdown("### 🪐 Membership Tiers")
plan_choice = st.sidebar.radio(
    "Select Your Plan", 
    ["Free Trial (3 Days - Basic + 1 Custom Query)", "Pro Oracle ($1.99 / 7 Days - Unlimited)"]
)

if "Free" in plan_choice:
    st.sidebar.info("✨ Free Plan: 3 Days Free. Includes 1 'Who Am I' and 1 'Custom Query' per day.")
else:
    st.sidebar.success("💎 Pro Oracle Active: Unlimited Deep Custom Questions ($1.99/7d).")

st.sidebar.markdown("---")
st.sidebar.markdown("### 🔮 Oracle Mode")
reading_mode = st.sidebar.radio(
    "Choose Reading Focus",
    ["1. Who Am I? (Raw Shadow Discovery)", "2. Custom Oracle Query (Deep Question)"]
)

if user_email:
    st.info(f"✉️ Welcome, voyager. Your prophecy will be securely sent to: **{user_email}**")

# 사용자 입력 폼
user_name = st.text_input("Your Name / Alias", value="")

popular_cities = [
    "New York, United States", 
    "London, United Kingdom", 
    "Seoul, South Korea", 
    "Tokyo, Japan", 
    "Bangkok, Thailand", 
    "Other (Direct Input)"
]

selected_city_option = st.selectbox("Birth Location", popular_cities)

if selected_city_option == "Other (Direct Input)":
    col_city, col_country = st.columns(2)
    with col_city:
        city_input = st.text_input("City", value="Los Angeles")
    with col_country:
        country_input = st.text_input("Country", value="United States")
    birth_place = f"{city_input.strip()}, {country_input.strip()}"
else:
    birth_place = selected_city_option

col1, col2, col3 = st.columns(3)
with col1:
    birth_year = st.number_input("Year", min_value=1930, max_value=2026, value=1988)
with col2:
    birth_month = st.number_input("Month", min_value=1, max_value=12, value=6)
with col3:
    birth_day = st.number_input("Day", min_value=1, max_value=31, value=15)

col_hour, col_minute = st.columns(2)
with col_hour:
    birth_hour = st.selectbox("Birth Hour", [f"{i:02d}" for i in range(24)], index=12)
with col_minute:
    birth_minute = st.selectbox("Birth Minute", [f"{i:02d}" for i in range(60)], index=0)

birth_time = f"{birth_hour}:{birth_minute}"

user_question = ""
if reading_mode == "2. Custom Oracle Query (Deep Question)":
    predefined_queries = [
        "What unseen forces are blocking my financial breakthrough?",
        "When will my current financial struggles be resolved?",
        "When will a new, destined relationship enter my life?",
        "Which path should I take for my career and ultimate destiny?",
        "What hidden truth must I face to break my current karmic cycle?",
        "Other (Direct Input)"
    ]
    selected_query = st.selectbox("✨ Select your query or choose 'Other':", predefined_queries)
    
    if selected_query == "Other (Direct Input)":
        user_question = st.text_input("✍️ Enter your specific query:", value="")
    else:
        user_question = selected_query

tarot_deck = {
    "The Fool": {"file": "images/fool.jpg", "symbol": "🃏 0. The Fool"},
    "The Magician": {"file": "images/magician.jpg", "symbol": "🪄 I. The Magician"},
    "The High Priestess": {"file": "images/high_priestess.jpg", "symbol": "🌙 II. The High Priestess"},
    "The Empress": {"file": "images/empress.jpg", "symbol": "👑 III. The Empress"},
    "The Emperor": {"file": "images/emperor.jpg", "symbol": "🏛️ IV. The Emperor"},
    "The Lovers": {"file": "images/lovers.jpg", "symbol": "💞 VI. The Lovers"},
    "The Chariot": {"file": "images/chariot.jpg", "symbol": "⚡ VII. The Chariot"},
    "The Hermit": {"file": "images/hermit.jpg", "symbol": "🏮 IX. The Hermit"},
    "Wheel of Fortune": {"file": "images/wheel.jpg", "symbol": "☸️ X. Wheel of Fortune"},
    "The Death": {"file": "images/death.jpg", "symbol": "🦋 XIII. The Death"},
    "The Devil": {"file": "images/devil.jpg", "symbol": "🔥 XV. The Devil"},
    "The Tower": {"file": "images/tower.jpg", "symbol": "🌩️ XVI. The Tower"},
    "The Moon": {"file": "images/moon.jpg", "symbol": "🌔 XVIII. The Moon"},
    "The Sun": {"file": "images/sun.jpg", "symbol": "☀️ XIX. The Sun"},
    "The World": {"file": "images/world.jpg", "symbol": "🌍 XXI. The World"}
}

if st.button("Consult the Oracle & Draw Cards"):
    
    # 🚨 구글 시트 DB에서 실시간 사용 횟수 검증
    whoami_used, custom_used, row_idx = get_user_usage_from_sheet(user_email)
    
    if reading_mode == "1. Who Am I? (Raw Shadow Discovery)" and whoami_used >= 1:
        st.error("🌙 You have already discovered your Shadow Self today. The astral veil requires time to reset. Please return tomorrow.")
        st.stop()
    elif reading_mode == "2. Custom Oracle Query (Deep Question)" and custom_used >= 1:
        st.error("🌙 You have exhausted your deep query for today. Over-questioning the Oracle clouds the truth. Please return tomorrow.")
        st.stop()
    
    drawn_keys = random.sample(list(tarot_deck.keys()), 3)
    card1_name = drawn_keys[0]
    card2_name = drawn_keys[1]
    card3_name = drawn_keys[2]

    status = st.empty()
    messages = [
        "🌌 Tunnelling through the astral plane...",
        f"✨ Aligning coordinates for {birth_place}...",
        "🪐 Calculating the shadow planets (Rahu & Ketu)...",
        "☊ Unveiling the devourer's eclipse...",
        "🔮 Shuffling the forbidden deck...",
        "🃏 Drawing the First Gate...",
        "🃏 Drawing the Second Gate...",
        "🃏 Drawing the Third Gate...",
        "🌑 The spirits are settling upon the cards..."
    ]

    for message in messages:
        status.info(message)
        time.sleep(1.2)

    status.info("👁️ The Oracle speaks... compiling the dark prophecy...")
    time.sleep(0.5)

    current_date = datetime.now().strftime("%Y-%m-%d")
    current_year = datetime.now().year
    user_age = current_year - birth_year

    user_context_hint = f"Reflect subtle underlying ambitions, drive for independence, and unspoken strategic pursuits. The user is {user_age} years old. Ensure the advice, tone, and life perspective are highly appropriate for someone of this mature age, reflecting their deep life experience rather than superficial youth advice."

    if reading_mode == "1. Who Am I? (Raw Shadow Discovery)":
        prompt = f"""
You are an ancient, terrifyingly accurate mystic oracle speaking from the shadows of the astral realm. Your tone is cold, piercing, mesmerizing, and deeply psychological.

CURRENT DATE: {current_date} (Base all future predictions and timelines strictly from this date.)

USER PROFILE
Name: {user_name}
Origin: {birth_place}
Birth: {birth_year}-{birth_month:02d}-{birth_day:02d} {birth_time}
Age: {user_age} years old
Subtle Astral Resonance: {user_context_hint}

DRAWN ARCANAS
Gate I (Shadow Self): {card1_name}
Gate II (Wealth & Power): {card2_name}
Gate III (Destiny): {card3_name}

Deliver a chillingly profound, cinematic reading. Use exactly these sections:
SHADOW SELF
WEALTH & POWER
DESTINY
FINAL PROPHECY
"""
    else:
        prompt = f"""
You are an ancient, terrifyingly accurate mystic oracle speaking from the shadows of the astral realm. Your tone is cold, piercing, mesmerizing, and deeply psychological.

CURRENT DATE: {current_date} (Base all future predictions and timelines strictly from this date.)

USER PROFILE
Name: {user_name}
Origin: {birth_place}
Birth: {birth_year}-{birth_month:02d}-{birth_day:02d} {birth_time}
Age: {user_age} years old
Query: "{user_question}"
Subtle Astral Resonance: {user_context_hint}

DRAWN ARCANAS
Gate I (Direct Truth): {card1_name}
Gate II (Hidden Obstacle / Shadow): {card2_name}
Gate III (Unfolding Fate): {card3_name}

Deliver a chillingly profound, cinematic reading directly answering the user's query. Use exactly these sections:
DIRECT TRUTH
HIDDEN OBSTACLE
UNFOLDING FATE
FINAL PROPHECY
"""

    try:
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt,
        )

        status.empty()

        # 🚨 구글 시트 DB에 횟수 반영 기록
        if reading_mode == "1. Who Am I? (Raw Shadow Discovery)":
            update_user_usage_in_sheet(row_idx, whoami_used + 1, custom_used)
        else:
            update_user_usage_in_sheet(row_idx, whoami_used, custom_used + 1)

        st.success(f"Prophecy manifested for {user_name} ({birth_place}).")
        st.markdown("## 🃏 The Three Gates of Umbra")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("<div class='card-box'>", unsafe_allow_html=True)
            st.markdown("### 🌑 Gate I")
            img_path1 = tarot_deck[card1_name]["file"]
            if os.path.exists(img_path1):
                st.image(img_path1, use_container_width=True)
            else:
                st.markdown(f"### {tarot_deck[card1_name]['symbol']}")
            st.caption(card1_name)
            st.markdown("</div>", unsafe_allow_html=True)

        with col2:
            st.markdown("<div class='card-box'>", unsafe_allow_html=True)
            st.markdown("### 💰 Gate II")
            img_path2 = tarot_deck[card2_name]["file"]
            if os.path.exists(img_path2):
                st.image(img_path2, use_container_width=True)
            else:
                st.markdown(f"### {tarot_deck[card2_name]['symbol']}")
            st.caption(card2_name)
            st.markdown("</div>", unsafe_allow_html=True)

        with col3:
            st.markdown("<div class='card-box'>", unsafe_allow_html=True)
            st.markdown("### 🔮 Gate III")
            img_path3 = tarot_deck[card3_name]["file"]
            if os.path.exists(img_path3):
                st.image(img_path3, use_container_width=True)
            else:
                st.markdown(f"### {tarot_deck[card3_name]['symbol']}")
            st.caption(card3_name)
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("## 👁️ Oracle's Vision")
        st.info(response.text)

        if user_email:
            try:
                sender_email = st.secrets["EMAIL_SENDER"]
                sender_password = st.secrets["EMAIL_PASSWORD"]
                
                msg = MIMEText(f"Target: {user_name}\n\n{response.text}")
                msg['Subject'] = f"👁️ Umbra & Tarot: Shadow Prophecy for {user_name}"
                msg['From'] = sender_email
                msg['To'] = user_email
                
                with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                    server.login(sender_email, sender_password)
                    server.send_message(msg)
                    
                st.success("✨ The prophecy has been securely sent to your email.")
            except Exception as email_e:
                st.error(f"Failed to send email. Check your settings. ({email_e})")

    except Exception as e:
        status.empty()
        st.error(f"An error occurred: {e}")
