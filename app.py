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

st.set_page_config(page_title="THE RAW TAROT: Shadow Prophecy", layout="centered", initial_sidebar_state="expanded")

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

st.markdown("<h1 class='main-title'> THE RAW TAROT</h1>", unsafe_allow_html=True)
st.markdown("<p class='sub-title'>Pierce the veil of your shadow self. Unearth the truths hidden in the astral dark.</p>", unsafe_allow_html=True)

# 로그인 세션 관리
if "google_token" not in st.session_state:
    st.markdown("### ✨ Claim Your 3-Day Free Trial")
    st.markdown("Unlock the gates. Sign in now to receive your **complimentary 'Who Am I' shadow reading** and **1 deep custom query**.")
    st.info("Google Login is required to begin your free trial and enter the astral realm.")
    
    # 샘플 티저 UI
    st.markdown("<br><h4 style='text-align: center; color: #1a1a2e;'> Glimpse the Shadows (Sample Reading)</h4>", unsafe_allow_html=True)
    sample_cols = st.columns(3)
    with sample_cols[0]:
        st.image("images/The_Fool.png", caption="The Fool", use_container_width=True)
    with sample_cols[1]:
        st.image("images/The_Tower.png", caption="The Tower", use_container_width=True)
    with sample_cols[2]:
        st.image("images/The_Devil.png", caption="The Devil", use_container_width=True)
        
    st.markdown("""
    <div style="background-color: #e9ecef; padding: 15px; border-left: 4px solid #1a1a2e; border-radius: 4px; color: #212529; font-style: italic; font-size: 0.95rem; margin-bottom: 25px;">
    "You ask about wealth, yet The Tower reveals your foundation is built on self-deception. The collapse is not a punishment, but a necessary clearing of your illusions. The Devil binds you to comfort, but true power requires you to step into the void..."
    </div>
    """, unsafe_allow_html=True)

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

st.sidebar.markdown("### 🪐 Membership Tiers")
st.sidebar.radio("Select Your Plan", ["Free Trial (Active)", "Pro Oracle (Available Sept 1st)"], index=0, disabled=True)
st.sidebar.info("✨ **Grand Opening!** Currently in Free Trial Period.")
st.sidebar.warning("💎 **Pro Oracle** features will unlock on September 1st.")
st.sidebar.markdown("---")
st.sidebar.markdown("### 🔮 Oracle Mode")
reading_mode = st.sidebar.radio("Choose Reading Focus", ["1. Who Am I? (Raw Shadow Discovery)", "2. Custom Oracle Query (Deep Question)"])
# 기존 사이드바 코드 바로 아래에 이 줄들을 추가해라
st.sidebar.markdown("---")
st.sidebar.markdown("### 🎧 Frequency Alignment")
st.sidebar.caption("Realign your shattered frequencies after the reading.")
# 아래 주소는 네 채널의 실제 링크로 반드시 수정해라
st.sidebar.link_button("Tune in at SynchroVault", "https://www.youtube.com/@SynchroVault")

if user_email:
    st.markdown(f"""
        <div style="background-color: #e9ecef; padding: 15px; border-radius: 8px; border: 1px solid #ced4da; color: #212529; margin-bottom: 20px;">
            🌌 <b>Welcome, voyager.</b> Prophecy will be sent to: <span style="color: #d97706; font-weight: bold;">{user_email}</span>
        </div>
    """, unsafe_allow_html=True)

country_city_map = {
    "South Korea": ["Seoul", "Daejeon", "Daegu", "Busan", "Jeju", "Other"],
    "United States": ["New York", "Los Angeles", "Chicago", "Seattle", "Other"],
    "United Kingdom": ["London", "Manchester", "Edinburgh", "Other"],
    "Japan": ["Tokyo", "Osaka", "Kyoto", "Other"],
    "Australia": ["Sydney", "Melbourne", "Brisbane", "Other"],
    "Canada": ["Toronto", "Vancouver", "Montreal", "Other"],
    "Other": ["Other"]
}

# 네 계정 자동완성 (이메일 팩트 체크 후 수정할 것)
ADMIN_EMAIL = "ellykimmain@gmail.com" 

if user_email == ADMIN_EMAIL:
    default_name = "Kim Uyoun"
    default_country_idx = 0 
    default_year = 1988      
else:
    default_name = ""
    default_country_idx = 1 
    default_year = 1988

user_name = st.text_input("Your Name / Alias", default_name)

col1, col2 = st.columns(2)
with col1:
    birth_country = st.selectbox("Country of Birth", list(country_city_map.keys()), index=default_country_idx)
with col2:
    birth_city = st.selectbox("City of Birth", country_city_map[birth_country])

if birth_city == "Other":
    birth_city = st.text_input("Please specify your city", "")

birth_place = f"{birth_city}, {birth_country}"

birth_year = st.number_input("Year", min_value=1930, max_value=2026, value=default_year)
birth_month = st.number_input("Month", min_value=1, max_value=12, value=6)
birth_day = st.number_input("Day", min_value=1, max_value=31, value=15)

time_options = ["Unknown"] + [f"{h:02d}:{m:02d}" for h in range(24) for m in (0, 30)]
birth_time = st.selectbox("Time of Birth", time_options)

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

if st.button("Consult the Oracle & Draw Cards"):
    current_date = datetime.now().strftime("%Y-%m-%d")
    user_key = f"{user_email}_{current_date}"
    if "already_prophesied" not in st.session_state: 
        st.session_state["already_prophesied"] = {}
    
    count = st.session_state["already_prophesied"].get(user_key, 0)
    if count >= 1:
        st.error("🌙 The Oracle has already spoken to you for today. Return when the stars realign tomorrow.")
        st.stop()

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

    card_base_names = {
        "The Fool": "The_Fool", "The Magician": "The_Magician", "The High Priestess": "The_High_Priestess",
        "The Empress": "The_Empress", "The Emperor": "The_Emperor", "The Hierophant": "The_Hierophant",
        "The Lovers": "The_Lovers", "The Chariot": "The_Chariot", "Strength": "Strength",
        "The Hermit": "The_Hermit", "Wheel of Fortune": "Wheel_of_Fortune", "Justice": "Justice",
        "The Hanged Man": "The_Hanged_Man", "Death": "The_Death", "Temperance": "Temperance",
        "The Devil": "The_Devil", "The Tower": "The_Tower", "The Star": "The_Star",
        "The Moon": "The_Moon", "The Sun": "The_Sun", "Judgement": "Judgement", "The World": "The_World"
    }

    # 파싱을 위한 강제 구분자(@) 프롬프트 삽입
    prompt = f"""You are a highly skilled, blunt, and slightly cynical traditional Thai fortune teller. 
You speak directly, offering no comforting lies. Deliver cold, hard truths based on the cosmic data. Use a tone that is piercing, mystical, and authoritative.

CURRENT DATE & TIME: {current_date} (Ensure all future predictions start strictly from this specific date onwards.)

USER PROFILE
Name: {user_name}
Origin: {birth_place}
Birth: {birth_year}-{birth_month:02d}-{birth_day:02d} {birth_time}{question_context}

ASTROLOGY & MANSE-RYEOK
{astrology_data}

DRAWN ARCANAS
1. {drawn_keys[0]}
2. {drawn_keys[1]}
3. {drawn_keys[2]}

CRITICAL FORMATTING INSTRUCTION:
You MUST structure your response EXACTLY using the following delimiters. Do not add any text outside of these blocks.

@INTRO@
(Write the overall astrological and Manse-ryeok analysis here)

@CARD_1@
(Write the brutal interpretation for {drawn_keys[0]} here)

@CARD_2@
(Write the brutal interpretation for {drawn_keys[1]} here)

@CARD_3@
(Write the brutal interpretation for {drawn_keys[2]} here)

@CONCLUSION@
(Write the final, unvarnished advice here)
"""

    try:
        response = client.models.generate_content(
            model="gemini-3.6-flash", 
            contents=prompt
        )
        
        st.session_state["already_prophesied"][user_key] = count + 1
        loading_placeholder.empty()
        st.success("Prophecy manifested.")
        
        res_text = response.text
        
        # 구분자를 활용한 텍스트 파싱 및 렌더링
        if "@INTRO@" in res_text and "@CARD_1@" in res_text and "@CONCLUSION@" in res_text:
            def extract_section(tag, next_tag, text):
                try:
                    return text.split(tag)[1].split(next_tag)[0].strip()
                except:
                    return ""
                    
            intro_text = extract_section("@INTRO@", "@CARD_1@", res_text)
            card1_text = extract_section("@CARD_1@", "@CARD_2@", res_text)
            card2_text = extract_section("@CARD_2@", "@CARD_3@", res_text)
            card3_text = extract_section("@CARD_3@", "@CONCLUSION@", res_text)
            conclusion_text = res_text.split("@CONCLUSION@")[1].strip() if "@CONCLUSION@" in res_text else ""
            
            # 1. 인트로 출력
            st.markdown(f"<div style='background-color: #e9ecef; padding: 20px; border-radius: 5px; color: #1a1a2e; margin-bottom: 20px;'>{intro_text}</div>", unsafe_allow_html=True)
            
            cards_text = [card1_text, card2_text, card3_text]
            
            # 2. 카드 이미지와 해석 텍스트를 순차적으로 렌더링
            for idx, card in enumerate(drawn_keys):
                st.markdown(f"<h3 style='text-align: center; color: #1a1a2e; margin-top: 30px; margin-bottom: 15px;'>{idx+1}. {card}</h3>", unsafe_allow_html=True)
                
                # 이미지가 화면을 다 덮지 않도록 중앙 정렬 컬럼 활용
                c1, c2, c3 = st.columns([1, 1.5, 1])
                with c2:
                    base_name = card_base_names.get(card, "")
                    img_path_jpg = f"images/{base_name}.jpg"
                    img_path_png = f"images/{base_name}.png"
                    
                    if os.path.exists(img_path_jpg):
                        st.image(img_path_jpg, use_container_width=True)
                    elif os.path.exists(img_path_png):
                        st.image(img_path_png, use_container_width=True)
                    else:
                        st.error(f"[{card} Image Missing]")
                
                # 카드별 예언 텍스트 출력
                st.info(cards_text[idx])
            
            # 3. 결론 출력
            st.markdown("<hr>", unsafe_allow_html=True)
            st.warning(conclusion_text)
            
        else:
            # AI가 포맷 지시를 무시했을 때를 대비한 안전망 (Fallback)
            st.info(res_text)
            st.markdown("<h3 style='text-align: center; color: #1a1a2e; margin-top: 20px;'>🃏 The Drawn Arcanas</h3>", unsafe_allow_html=True)
            cols = st.columns(3)
            for i, card in enumerate(drawn_keys):
                with cols[i]:
                    base_name = card_base_names.get(card, "")
                    img_path_jpg = f"images/{base_name}.jpg"
                    img_path_png = f"images/{base_name}.png"
                    if os.path.exists(img_path_jpg):
                        st.image(img_path_jpg, use_container_width=True)
                    elif os.path.exists(img_path_png):
                        st.image(img_path_png, use_container_width=True)
                    else:
                        st.error(f"[{card} Image Missing]")

      # 이메일 발송
        try:
            base_prophecy = response.text.replace('@INTRO@', '').replace('@CARD_1@', '').replace('@CARD_2@', '').replace('@CARD_3@', '').replace('@CONCLUSION@', '')
            
            email_body = f"""Prophecy for {user_name}:

{base_prophecy}

---
🎧 FREQUENCY ALIGNMENT

Have you faced the brutal truth? 
The framework of your fate is now exposed. It is time to realign your shattered frequencies through cosmic geometry and forcefully attract physical wealth.

Synchronize your vibration at SynchroVault.
▶ https://www.youtube.com/@SynchroVault
"""
            msg = MIMEText(email_body)
            msg['Subject'] = "Your Shadow Prophecy"
            msg['From'] = st.secrets["EMAIL_SENDER"]
            msg['To'] = user_email
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(st.secrets["EMAIL_SENDER"], st.secrets["EMAIL_PASSWORD"])
                server.send_message(msg)
        except Exception as e: 
            st.error("Email failed.")
            
    except Exception as e:
        loading_placeholder.empty()
        error_msg = str(e)
        if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
            st.error("🌙 The astral energy is depleted. Today's complimentary prophecies (Limit: 20) have concluded. Return after midnight.")
        else:
            st.error("The astral connection was lost. Please try again later.")
