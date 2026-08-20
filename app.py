import smtplib
from email.mime.text import MIMEText
import streamlit as st
import random
import time
import os
from google import genai

# Streamlit Secrets에서 API Key 가져오기
api_key = st.secrets["GEMINI_API_KEY"]
client = genai.Client(api_key=api_key)

st.set_page_config(
    page_title="Umbra & Tarot: Shadow Prophecy",
    layout="centered"
)

# 다크 오컬트 프리미엄 스타일 커스텀 CSS
st.markdown("""
    <style>
    .stApp {
        background-color: #0b0b0e;
        color: #f1f1f1;
    }
    .main-title {
        text-align: center;
        color: #f3e5ab;
        font-family: 'Cinzel', serif;
        letter-spacing: 2px;
        text-shadow: 0 0 10px rgba(243, 229, 171, 0.3);
        font-size: 2.5rem;
    }
    /* 스마트폰(모바일) 화면일 때 글자 크기 축소 */
    @media (max-width: 768px) {
        .main-title {
            font-size: 1.6rem !important;
        }
    }
    .sub-title {
        text-align: center;
        color: #b3b3cc;
        font-size: 1.05rem;
    }
    .card-box {
        background-color: #15151c;
        border: 1px solid #4a4a75;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.5);
    }
    label {
        color: #d1d1e0 !important;
        font-weight: 500;
    }
    /* 버튼 스타일 강제 덮어쓰기 */
    div.stButton > button:first-child {
        background-color: #15151c;
        color: #f3e5ab;
        border: 1px solid #4a4a75;
        font-weight: 600;
        border-radius: 5px;
    }
    div.stButton > button:first-child:hover {
        background-color: #4a4a75;
        color: #ffffff;
        border: 1px solid #f3e5ab;
    }
    </style>
""", unsafe_allow_html=True)


st.markdown("<h1 class='main-title'>👁️ UMBRA & TAROT</h1>", unsafe_allow_html=True)
st.markdown("<p class='sub-title'>Pierce the veil of your shadow self. Unearth the truths hidden in the astral dark.</p>", unsafe_allow_html=True)

# -------------------------------------------------------------
# [멤버십 및 리딩 모드 세션]
# -------------------------------------------------------------
st.sidebar.markdown("### 🪐 Membership Tiers")
plan_choice = st.sidebar.radio(
    "Select Your Plan", 
    ["Free Trial (1 reading/day - 7 Days Free)", "Pro Oracle ($1.99 / 7 Days - 3 readings/day)"]
)

if "Free" in plan_choice:
    st.sidebar.info("✨ Free Plan Active: 1 Daily Shadow Reading.")
else:
    st.sidebar.success("💎 Pro Oracle Active: Unlimited Deep Custom Questions ($1.99/7d).")

st.sidebar.markdown("---")
st.sidebar.markdown("### 🔮 Oracle Mode")
reading_mode = st.sidebar.radio(
    "Choose Reading Focus",
    ["1. Who Am I? (Raw Shadow Discovery)", "2. Custom Oracle Query (Deep Question)"]
)

# 사용자 기본 정보 입력
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

# 모드 2일 때 질문 입력창
user_question = ""
if reading_mode == "2. Custom Oracle Query (Deep Question)":
    user_question = st.text_input("✨ Enter your specific query (Wealth, Career, Hidden Truth):", value="What unseen forces are blocking my financial breakthrough?")

# 결과 받을 이메일 입력창 (위치 수정 완료)
user_email = st.text_input("Your Email (To receive the prophecy)", value="")

# 타로 카드 데이터
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
    
    drawn_keys = random.sample(list(tarot_deck.keys()), 3)
    card1_name = drawn_keys[0]
    card2_name = drawn_keys[1]
    card3_name = drawn_keys[2]

    # 10단계 오컬트 로딩 연출
    status = st.empty()
    messages = [
        "🌌 Tunnelling through the astral plane...",
        f"✨ Aligning coordinates for {birth_place}...",
        "🪐 Calculating the shadow planets (Rahu & Ketu)...",
        "☊ Unveiling the devourer's eclipse...",
        "🔮 Shuffling the forbidden deck...",
        "🃏 Drawing the First Gate (The Core)...",
        "🃏 Drawing the Second Gate (The Wealth & Trap)...",
        "🃏 Drawing the Third Gate (The Inevitable Fate)...",
        "🌑 The spirits are settling upon the cards..."
    ]

    for message in messages:
        status.info(message)
        time.sleep(1.2)

    status.info("👁️ The Oracle speaks... compiling the dark prophecy...")
    time.sleep(0.5)

    user_context_hint = "Reflect subtle underlying ambitions, drive for independence, and unspoken strategic pursuits."

    if reading_mode == "1. Who Am I? (Raw Shadow Discovery)":
        prompt = f"""
You are an ancient, terrifyingly accurate mystic oracle speaking from the shadows of the astral realm. Your tone is cold, piercing, mesmerizing, and deeply psychological—like a gifted shaman who looks straight through human pretense and speaks absolute truths.

USER PROFILE
Name: {user_name}
Origin: {birth_place}
Birth: {birth_year}-{birth_month:02d}-{birth_day:02d} {birth_time}
Subtle Astral Resonance: {user_context_hint}

DRAWN ARCANAS
Gate I (Shadow Self): {card1_name}
Gate II (Wealth & Power): {card2_name}
Gate III (Destiny): {card3_name}

Deliver a chillingly profound, cinematic reading. Do not sound like a generic AI or cheerful coach. Sound like an arcane oracle unearthing hidden secrets, suppressed hungers, and raw spiritual karma (using Rahu/Ketu astrological symbolism). Weave in their subtle resonance naturally so it feels uncomfortably accurate.

Use exactly these sections:
SHADOW SELF
WEALTH & POWER
DESTINY
FINAL PROPHECY

Keep it punchy, haunting, and intensely engaging in English.
"""
    else:
        prompt = f"""
You are an ancient, terrifyingly accurate mystic oracle speaking from the shadows of the astral realm. Your tone is cold, piercing, mesmerizing, and deeply psychological—like a gifted shaman who looks straight through human pretense and answers hidden truths.

USER PROFILE
Name: {user_name}
Origin: {birth_place}
Birth: {birth_year}-{birth_month:02d}-{birth_day:02d} {birth_time}
Query: "{user_question}"
Subtle Astral Resonance: {user_context_hint}

DRAWN ARCANAS
Gate I (Direct Truth): {card1_name}
Gate II (Hidden Obstacle / Shadow): {card2_name}
Gate III (Unfolding Fate): {card3_name}

Deliver a chillingly profound, cinematic reading directly answering the user's query through the lens of dark astral forces (Rahu/Ketu) and their underlying energetic resonance. Speak with unyielding prophetic authority.

Use exactly these sections:
DIRECT TRUTH
HIDDEN OBSTACLE
UNFOLDING FATE
FINAL PROPHECY

Keep it punchy, haunting, and intensely engaging in English.
"""

    try:
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt,
        )

        status.empty()

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

        # 들여쓰기 완벽하게 수정된 이메일 전송 로직
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
