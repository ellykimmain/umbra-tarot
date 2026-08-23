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

def build_astrology_block(year, month, day, hour_str):
    lines = []
    zhi_idx = TIME_TO_ZHI.get(hour_str, 0)
    saju = get_saju_data(year, month, day, zhi_idx)
    if saju:
        lines.append("[만세력(사주) 4주 8자]")
        lines.append(f"년주: {saju['year']} / 월주: {saju['month']} / 일주: {saju['day']} / 시주: {saju['hour']} (일간: {saju['day_master']})")
    num = get_numerology(year, month, day)
    lines.append("\n[수리학(Numerology) 데이터]")
    lines.append(f"운명수(Life Path): {num['life_path']} / 올해의 수: {num['personal_year']} / 이번 달의 수: {num['personal_month']}")
    return "\n".join(lines) if lines else "우주적 데이터 계산 불가. 입력된 정보만으로 판단하십시오."

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
st.markdown("<p class='sub-title'>당신의 숨겨진 그림자 자아를 직시하십시오. 잔혹한 진실을 마주할 시간입니다.</p>", unsafe_allow_html=True)

# ── 구글 로그인 및 강력한 경고문 ───────────────────────────────────────────────
if "google_token" not in st.session_state:
    st.markdown("### ✨ 3일 무료 통행권 발급")
    
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

st.sidebar.markdown("### 🪐 멤버십 등급")
st.sidebar.radio("플랜 선택", ["무료 체험 (활성화됨)", "Pro Oracle (9월 1일 오픈)"], index=0, disabled=True)
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
        "현재 사업(커리어)은 올바른 길인가?", "반복되는 파괴적 패턴의 진짜 이유",
        "내가 필사적으로 외면하고 있는 진실", "내 그림자 자아의 미친듯한 경고",
        "직접 입력 (심층 질문 작성)"
    ]
    selected_query = st.selectbox("질문을 선택하거나 직접 입력하십시오", question_options)
    user_question = st.text_area("당신의 심층 질문", placeholder="예: 벼랑 끝입니다. 어떻게 살아남아야 합니까?") if selected_query == "직접 입력 (심층 질문 작성)" else selected_query
else:
    user_question = ""

if st.button("오라클 연결 및 아르카나 뽑기"):
    current_date = datetime.now().strftime("%Y-%m-%d")
    user_key = f"{user_email}_{current_date}"
    if "already_prophesied" not in st.session_state: 
        st.session_state["already_prophesied"] = {}
    
    if st.session_state["already_prophesied"].get(user_key, 0) >= 1:
        st.error("🌙 오늘 오라클은 이미 당신에게 응답했습니다. 자정 이후 별들이 재정렬되면 다시 방문하십시오.")
        st.stop()

    loading_placeholder = st.empty()
    loading_placeholder.markdown("<p style='text-align: center; color: #6c757d; font-size: 1.1rem; font-weight: bold;'>🌌 아스트랄 차원으로 터널링 중...</p>", unsafe_allow_html=True)
    time.sleep(1.5)
    loading_placeholder.markdown("<p style='text-align: center; color: #6c757d; font-size: 1.1rem; font-weight: bold;'>🔮 우주적 배열 및 만세력 데이터 교차 검증 중...</p>", unsafe_allow_html=True)
    time.sleep(1.5)
    loading_placeholder.markdown("<p style='text-align: center; color: #6c757d; font-size: 1.1rem; font-weight: bold;'>🃏 4장의 그림자 아르카나 카드 추출 중...</p>", unsafe_allow_html=True)
    time.sleep(1.5)
    loading_placeholder.markdown("<p style='text-align: center; color: #d97706; font-size: 1.1rem; font-weight: bold;'>⚡ 잔혹한 진단과 구원의 열쇠를 수신하고 있습니다...</p>", unsafe_allow_html=True)
    
    # 💡 동적 만세력/수리학 데이터 생성
    astrology_data = build_astrology_block(int(birth_year), int(birth_month), int(birth_day), birth_time)

    major_arcana_deck = [
        "The Fool", "The Magician", "The High Priestess", "The Empress", "The Emperor", 
        "The Hierophant", "The Lovers", "The Chariot", "Strength", "The Hermit", 
        "Wheel of Fortune", "Justice", "The Hanged Man", "Death", "Temperance", 
        "The Devil", "The Tower", "The Star", "The Moon", "The Sun", 
        "Judgement", "The World"
    ]

    drawn_keys = random.sample(major_arcana_deck, 4)
    question_context = f"\n[내담자의 심층 질문]: {user_question}" if user_question else ""

    card_base_names = {k: k.replace(" ", "_") for k in major_arcana_deck}
    card_base_names["Wheel of Fortune"] = "Wheel_of_Fortune" # 예외 처리

    prompt = f"""당신은 만세력(명리학), 수리학, 태국점성술(호라삿, โหราศาสตร์) 및 서양 타로를 결합하여 운명을 꿰뚫어보는 무자비하고 압도적인 마스터입니다. 
어떠한 헛된 위로나 따뜻한 거짓말도 제공하지 마십시오. 오직 만세력 데이터와 타로 카드를 교차 검증하여 도출된 차갑고 잔혹한 진실만을 한국어(Korean)로 출력하십시오. 

[매우 중요한 문체 및 호칭 지시]
1. 어조는 뼈를 때리듯 날카롭고, 신비로우며, 거부할 수 없는 압도적인 โหราศาสตร์ 무당(도사)의 권위를 가져야 합니다. 
2. 말투는 반드시 '~다', '~어라(마라)', '~느라(느니라)' 등의 단호하고 거친 종결어미로 완벽하게 통일하십시오.
3. [금지어 규정]: 저급한 호칭 대신 '당신' 혹은 '너' 라는 호칭을 사용하거나 주어를 생략하십시오.
4. [현실 직시 규정 (가장 중요)]: 내담자가 이사, 파산, 퇴거, 생존 등 구체적인 '현실의 위기'를 물었을 때, 이를 '심리적 도피'나 '나약함'으로 매도하지 마십시오. 돈이 없고 쫓겨나는 물리적 제약을 기정사실로 받아들이고, 살아남기 위한 가장 현실적이고 전략적인 생존 타개책을 차갑게 제시하십시오.

현재 날짜: {current_date}

[내담자 프로필]
이름: {user_name}
성별: {gender}
출생지: {birth_place}
생년월일시: {birth_year}년 {birth_month:02d}월 {birth_day:02d}일 {birth_time}{question_context}

[만세력 및 우주적 데이터]
{astrology_data}

[뽑힌 그림자 아르카나]
1. (잔혹한 현실): {drawn_keys[0]}
2. (외면한 진실): {drawn_keys[1]}
3. (파괴적 결과): {drawn_keys[2]}
4. [구원의 열쇠 (해결책)]: {drawn_keys[3]}

[중요한 포맷 지시사항]
반드시 아래의 구분자를 정확히 사용하여 답변을 구조화하십시오.

@INTRO@
(내담자의 만세력 기운과 현재 상황에 대한 전반적이고 냉혹한 분석 - 3~4문장)

@CARD_1@
({drawn_keys[0]} 카드에 대한 잔혹하고 뼈아픈 해석 - 4~5문장)

@CARD_2@
({drawn_keys[1]} 카드에 대한 잔혹하고 뼈아픈 해석 - 4~5문장)

@CARD_3@
({drawn_keys[2]} 카드에 대한 잔혹하고 뼈아픈 해석 - 4~5문장)

@CARD_4@
({drawn_keys[3]} 카드를 기반으로, 이 파멸적인 상황을 뚫고 나가기 위해 내담자가 정확히 무엇을 버리고 현실 세계에서 어떻게 행동해야 하는지 '조건부 희망과 구체적 해결책'을 제시하십시오. 철저히 계산된 구원의 문을 열어주어라.)

@CONCLUSION@
(최종적인 팩트 요약 및 뼈를 때리는 마지막 행동 지침 - 3~4문장)
"""

    try:
        response = client.models.generate_content(
            model="gemini-3.6-flash", 
            contents=prompt
        )
        
        st.session_state["already_prophesied"][user_key] = 1
        loading_placeholder.empty()
        st.success("카드가 열렸습니다.")
        
        res_text = response.text
        
        if "@INTRO@" in res_text and "@CARD_1@" in res_text and "@CONCLUSION@" in res_text:
            def extract_section(tag, next_tag, text):
                try: return text.split(tag)[1].split(next_tag)[0].strip()
                except: return ""
                    
            intro_text = extract_section("@INTRO@", "@CARD_1@", res_text)
            card1_text = extract_section("@CARD_1@", "@CARD_2@", res_text)
            card2_text = extract_section("@CARD_2@", "@CARD_3@", res_text)
            card3_text = extract_section("@CARD_3@", "@CARD_4@", res_text)
            card4_text = extract_section("@CARD_4@", "@CONCLUSION@", res_text)
            conclusion_text = res_text.split("@CONCLUSION@")[1].strip() if "@CONCLUSION@" in res_text else ""
            
            st.markdown(f"<div style='background-color: #e9ecef; padding: 20px; border-radius: 5px; color: #1a1a2e; margin-bottom: 20px;'>{intro_text}</div>", unsafe_allow_html=True)
            
            cards_text = [card1_text, card2_text, card3_text, card4_text]
            
            for idx, card in enumerate(drawn_keys):
                if idx == 3:
                    st.markdown(f"<h3 style='text-align: center; color: #d97706; margin-top: 40px; margin-bottom: 15px;'>🌟 4. 구원의 열쇠 ({card})</h3>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<h3 style='text-align: center; color: #1a1a2e; margin-top: 30px; margin-bottom: 15px;'>{idx+1}. {card}</h3>", unsafe_allow_html=True)
                
                c1, c2, c3 = st.columns([1, 1.5, 1])
                with c2:
                    base_name = card_base_names.get(card, "")
                    img_path_jpg = f"images/{base_name}.jpg"
                    img_path_png = f"images/{base_name}.png"
                    
                    if os.path.exists(img_path_jpg): st.image(img_path_jpg, use_container_width=True)
                    elif os.path.exists(img_path_png): st.image(img_path_png, use_container_width=True)
                    else: st.error(f"[{card} 이미지 누락]")
                st.info(cards_text[idx])
            
            st.markdown("<hr>", unsafe_allow_html=True)
            st.warning(conclusion_text)
            
        else:
            st.info(res_text)
            st.markdown("<h3 style='text-align: center; color: #1a1a2e; margin-top: 20px;'>🃏 뽑힌 아르카나 카드</h3>", unsafe_allow_html=True)
            cols = st.columns(4)
            for i, card in enumerate(drawn_keys):
                with cols[i]:
                    base_name = card_base_names.get(card, "")
                    img_path_jpg = f"images/{base_name}.jpg"
                    img_path_png = f"images/{base_name}.png"
                    if os.path.exists(img_path_jpg): st.image(img_path_jpg, use_container_width=True)
                    elif os.path.exists(img_path_png): st.image(img_path_png, use_container_width=True)
                    else: st.error(f"[{card} 이미지 누락]")

        try:
            base_prophecy = response.text.replace('@INTRO@', '').replace('@CARD_1@', '').replace('@CARD_2@', '').replace('@CARD_3@', '').replace('@CARD_4@', '').replace('@CONCLUSION@', '')
            html_prophecy = base_prophecy.replace('\n', '<br>')
            
            html_body = f"""
            <html>
            <body style="background-color: #050505; color: #d4d4d4; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; padding: 20px; line-height: 1.6; margin: 0;">
                <div style="max-width: 600px; margin: 0 auto; border: 1px solid #222222; padding: 40px; background-color: #0a0a0a;">
                    <h2 style="text-align: center; color: #ffffff; letter-spacing: 4px; border-bottom: 1px solid #333333; padding-bottom: 20px; font-weight: normal;">THE RAW TAROT (그림자 진단)</h2>
                    <p style="font-size: 14px; color: #888888; text-transform: uppercase; letter-spacing: 1px;"><strong>{user_name}</strong>님을 위한 진단 기록</p>
                    <div style="font-size: 15px; margin-top: 30px; color: #cccccc;">
                        {html_prophecy}
                    </div>
                    <hr style="border: 0; border-top: 1px solid #222222; margin: 40px 0;">
                    <div style="text-align: center;">
                        <h3 style="color: #ffffff; letter-spacing: 2px; font-weight: normal;">🎧 주파수 동기화</h3>
                        <p style="font-size: 13px; color: #888888; margin-bottom: 30px;">
                            잔혹한 진실과 구원의 열쇠를 마주하셨습니까?<br>
                            당신 운명의 뼈대가 드러났습니다.<br>이제 산산조각 나 있는 당신의 주파수를 우주적 기하학으로 재정렬하고, 물리적 부를 강력하게 끌어당길 시간입니다.
                        </p>
                        <div style="margin-bottom: 15px;">
                            <a href="https://buly.kr/3u5ctxV" style="display: inline-block; padding: 12px 24px; border: 1px solid #555555; background-color: transparent; color: #ffffff; text-decoration: none; font-size: 12px; font-weight: bold; letter-spacing: 2px; text-transform: uppercase; width: 220px; text-align: center;">
                                진단의 방으로 복귀
                            </a>
                        </div>
                        <div>
                            <a href="https://www.youtube.com/@SynchroVault" style="display: inline-block; padding: 12px 24px; background-color: #ffffff; color: #000000; text-decoration: none; font-size: 12px; font-weight: bold; letter-spacing: 2px; text-transform: uppercase; width: 220px; text-align: center;">
                                주파수 동기화 시작
                            </a>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """
            
            msg = MIMEText(html_body, 'html')
            msg['Subject'] = "당신의 카드가 도착했습니다"
            msg['From'] = st.secrets["EMAIL_SENDER"]
            msg['To'] = user_email
            
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(st.secrets["EMAIL_SENDER"], st.secrets["EMAIL_PASSWORD"])
                server.send_message(msg)
                
        except Exception as e: 
            st.error("이메일 발송에 실패했습니다.")
            
    except Exception as e:
        loading_placeholder.empty()
        error_msg = str(e)
        if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
            st.error("🌙 아스트랄 에너지가 고갈되었습니다. 오늘의 무료 시간이 종료되었습니다. 자정 이후 다시 방문하십시오.")
        else:
            # 💡 아래 줄을 수정하여 실제 에러 원인을 화면에 출력하도록 만든다.
            st.error(f"아스트랄 연결이 끊어졌습니다. 상세 에러: {error_msg}")
