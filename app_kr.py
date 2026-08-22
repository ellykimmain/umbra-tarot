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

st.set_page_config(page_title="THE RAW TAROT: 그림자 진단", layout="centered", initial_sidebar_state="expanded")

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

st.markdown("<h1 class='main-title'> THE RAW TAROT </h1>", unsafe_allow_html=True)
st.markdown("<p class='sub-title'>당신의 숨겨진 자아를 꿰뚫어라. 심연 속에 숨겨진 잔혹한 진실을 마주할 시간입니다.</p>", unsafe_allow_html=True)

# 로그인 세션 관리
if "google_token" not in st.session_state:
    st.markdown("### ✨ 3일 무료권 발급")
    st.markdown("구글 로그인으로 당신의 '숨겨진 자아 진단'과 단 1개의 심층 커스텀 질문 권한을 획득하세요.")
    st.info("무료 체험을 시작하고 진단의 방에 입장하려면 구글 로그인이 필수입니다.")
    
    # 샘플 티저 UI
    st.markdown("<br><h4 style='text-align: center; color: #1a1a2e;'> 진단서 엿보기 (샘플 타로)</h4>", unsafe_allow_html=True)
    sample_cols = st.columns(3)
    with sample_cols[0]:
        st.image("images/The_Fool.png", caption="The Fool", use_container_width=True)
    with sample_cols[1]:
        st.image("images/The_Tower.png", caption="The Tower", use_container_width=True)
    with sample_cols[2]:
        st.image("images/The_Devil.png", caption="The Devil", use_container_width=True)
        
    st.markdown("""
    <div style="background-color: #e9ecef; padding: 15px; border-left: 4px solid #1a1a2e; border-radius: 4px; color: #212529; font-style: italic; font-size: 0.95rem; margin-bottom: 25px;">
    "당신은 부를 탐하지만, 탑(The Tower) 카드는 당신의 기반이 자기 기만 위에 세워져 있음을 폭로합니다. 이 붕괴는 형벌이 아니라 환상을 부수는 필수적인 과정입니다. 악마(The Devil)는 당신을 안락함에 묶어두려 하지만, 진짜 힘을 원한다면 허공으로 몸을 던져야만 합니다..."
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
st.sidebar.warning("💎 **Pro Oracle** 기능은 9월 1일에 잠금 해제됩니다.")
st.sidebar.markdown("---")
st.sidebar.markdown("### 🔮 진단 모드")
reading_mode = st.sidebar.radio("질문 테마 선택", ["1. 나는 누구인가? (그림자 자아 진단)", "2. 커스텀 진단 (심층 질문)"])
st.sidebar.markdown("---")
st.sidebar.markdown("### 🎧 주파수 동기화")
st.sidebar.caption("진단을 마주한 후 산산조각 난 주파수를 재정렬하십시오.")
st.sidebar.link_button("SynchroVault 접속하기", "https://www.youtube.com/@SynchroVault")

if user_email:
    st.markdown(f"""
        <div style="background-color: #e9ecef; padding: 15px; border-radius: 8px; border: 1px solid #ced4da; color: #212529; margin-bottom: 20px;">
            🌌 <b>환영합니다, 여행자여.</b> 진단서가 발송될 이메일: <span style="color: #d97706; font-weight: bold;">{user_email}</span>
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

col1, col2 = st.columns(2)
with col1:
    birth_country = st.selectbox("출생 국가", list(country_city_map.keys()), index=default_country_idx)
with col2:
    birth_city = st.selectbox("출생 도시", country_city_map[birth_country])

if birth_city == "기타":
    birth_city = st.text_input("도시를 직접 입력하십시오", "")

birth_place = f"{birth_city}, {birth_country}"

col3, col4, col5 = st.columns(3)
with col3:
    birth_year = st.number_input("태어난 연도", min_value=1930, max_value=2026, value=default_year)
with col4:
    birth_month = st.number_input("월", min_value=1, max_value=12, value=6)
with col5:
    birth_day = st.number_input("일", min_value=1, max_value=31, value=15)

time_options = ["모름"] + [f"{h:02d}:{m:02d}" for h in range(24) for m in (0, 30)]
birth_time = st.selectbox("태어난 시간", time_options)

if "2." in reading_mode or "커스텀" in reading_mode:
    question_options = [
        "지금 겪고 있는 재정적 고통은 언제쯤 끝날까?",
        "나의 부와 성공을 가로막고 있는 숨겨진 장애물은 무엇일까?",
        "현재 만나는 사람(연인/파트너)과의 관계에 숨겨진 잔혹한 진실은 무엇인가?",
        "나는 언제쯤 진짜 인연을 만날 수 있을까?",
        "내가 현재 추진 중인 사업(혹은 커리어)은 올바른 길일까?",
        "왜 나는 항상 똑같은 파괴적인 패턴(실수/관계)을 반복할까?",
        "내가 현재 필사적으로 외면하고 있는 것은 무엇인가?",
        "나의 숨겨진 자아가 나에게 미친듯이 경고하고 싶은 것은 무엇인가?",
        "직접 입력 (당신의 질문을 적으세요)"
    ]
    selected_query = st.selectbox("질문을 선택하거나 직접 입력하십시오", question_options)
    
    if selected_query == "직접 입력 (당신의 질문을 적으세요)":
        user_question = st.text_area("당신의 심층 질문", placeholder="예: 올해 새로 시작한 사업이 성공할 수 있을까?")
    else:
        user_question = selected_query
else:
    user_question = ""

if st.button("오라클 연결 및 아르카나 뽑기"):
    current_date = datetime.now().strftime("%Y-%m-%d")
    user_key = f"{user_email}_{current_date}"
    if "already_prophesied" not in st.session_state: 
        st.session_state["already_prophesied"] = {}
    
    count = st.session_state["already_prophesied"].get(user_key, 0)
    if count >= 1:
        st.error("🌙 오늘 오라클은 이미 당신에게 응답했습니다. 자정 이후 별들이 재정렬되면 다시 방문하십시오.")
        st.stop()

    loading_placeholder = st.empty()
    loading_placeholder.markdown("<p style='text-align: center; color: #6c757d; font-size: 1.1rem; font-weight: bold;'>🌌 아스트랄 차원으로 터널링 중...</p>", unsafe_allow_html=True)
    time.sleep(1.5)
    loading_placeholder.markdown("<p style='text-align: center; color: #6c757d; font-size: 1.1rem; font-weight: bold;'>🔮 우주적 배열 및 만세력 데이터 교차 검증 중...</p>", unsafe_allow_html=True)
    time.sleep(1.5)
    loading_placeholder.markdown("<p style='text-align: center; color: #6c757d; font-size: 1.1rem; font-weight: bold;'>🃏 그림자 아르카나 카드 추출 중...</p>", unsafe_allow_html=True)
    time.sleep(1.5)
    loading_placeholder.markdown("<p style='text-align: center; color: #d97706; font-size: 1.1rem; font-weight: bold;'>⚡ 잔혹한 진단을 수신하고 있습니다...</p>", unsafe_allow_html=True)
    time.sleep(1.5)
    
    try:
        astrology_data = "External API connection placeholder: Sun in Taurus, Moon in Scorpio, Ascendant Leo."
    except Exception as e:
        astrology_data = "API 연결 실패. 우주적 자체 계산으로 대체합니다."

    major_arcana_deck = [
        "The Fool", "The Magician", "The High Priestess", "The Empress", "The Emperor", 
        "The Hierophant", "The Lovers", "The Chariot", "Strength", "The Hermit", 
        "Wheel of Fortune", "Justice", "The Hanged Man", "Death", "Temperance", 
        "The Devil", "The Tower", "The Star", "The Moon", "The Sun", 
        "Judgement", "The World"
    ]

    drawn_keys = random.sample(major_arcana_deck, 3)
    question_context = f"\n[내담자의 심층 질문]: {user_question}" if user_question else ""

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
    prompt = f"""당신은 만세력(명리학), 태국점 및 서양 타로를 결합하여 운명을 꿰뚫어보는 직설적이고 냉소적인 마스터입니다. 
어떠한 위로나 따뜻한 거짓말도 제공하지 마십시오. 오직 만세력 데이터와 타로 카드를 교차 검증하여 도출된 차갑고 잔혹한 진실만을 한국어(Korean) 무당체로 출력하십시오. 

[매우 중요한 문체 지시]
어조는 뼈를 때리듯 날카롭고, 신비로우며, 거부할 수 없는 권위를 가져야 합니다. 
절대로 한 문단 내에서 존댓말과 반말을 섞어 쓰지 마십시오. 처음부터 끝까지 감정을 철저히 배제하고, 내담자와 거리를 두는 차갑고 건조한 무당체로만 완벽하게 일관성을 유지하십시오.

현재 날짜 & 시간: {current_date} (모든 미래 예측은 반드시 이 날짜를 기준으로 시작하십시오.)

[내담자 프로필]
이름: {user_name}
출생지: {birth_place}
생년월일시: {birth_year}년 {birth_month:02d}월 {birth_day:02d}일 {birth_time}{question_context}

[만세력 및 우주적 데이터]
{astrology_data}

[뽑힌 그림자 아르카나]
1. {drawn_keys[0]}
2. {drawn_keys[1]}
3. {drawn_keys[2]}

[중요한 포맷 지시사항]
반드시 아래의 구분자를 정확히 사용하여 답변을 구조화하십시오. 이 블록 밖에는 어떠한 텍스트도 추가하지 마십시오.

@INTRO@
(내담자의 만세력 기운과 현재 상황에 대한 전반적이고 냉혹한 분석을 작성하십시오)

@CARD_1@
({drawn_keys[0]} 카드에 대한 잔혹하고 뼈아픈 해석을 작성하십시오)

@CARD_2@
({drawn_keys[1]} 카드에 대한 잔혹하고 뼈아픈 해석을 작성하십시오)

@CARD_3@
({drawn_keys[2]} 카드에 대한 잔혹하고 뼈아픈 해석을 작성하십시오)

@CONCLUSION@
(위선을 벗겨낸 최종적이고 가감 없는 경고와 조언을 작성하십시오)
"""

    try:
        response = client.models.generate_content(
            model="gemini-3.6-flash", 
            contents=prompt
        )
        
        st.session_state["already_prophesied"][user_key] = count + 1
        loading_placeholder.empty()
        st.success("진단이 완료되었습니다.")
        
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
                        st.error(f"[{card} 이미지 누락]")
                
                # 카드별 진단 텍스트 출력
                st.info(cards_text[idx])
            
            # 3. 결론 출력
            st.markdown("<hr>", unsafe_allow_html=True)
            st.warning(conclusion_text)
            
        else:
            # AI가 포맷 지시를 무시했을 때를 대비한 안전망 (Fallback)
            st.info(res_text)
            st.markdown("<h3 style='text-align: center; color: #1a1a2e; margin-top: 20px;'>🃏 뽑힌 아르카나 카드</h3>", unsafe_allow_html=True)
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
                        st.error(f"[{card} 이미지 누락]")

        # 이메일 발송 (HTML 포맷 및 복귀 버튼 추가)
        try:
            base_prophecy = response.text.replace('@INTRO@', '').replace('@CARD_1@', '').replace('@CARD_2@', '').replace('@CARD_3@', '').replace('@CONCLUSION@', '')
            
            # 파이썬 줄바꿈(\n)을 HTML 줄바꿈(<br>)으로 변환
            html_prophecy = base_prophecy.replace('\n', '<br>')
            
            # 프리미엄 다크 테마 HTML 구조 및 듀얼 버튼 세팅 (한글화)
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
                            잔혹한 진실과 마주하셨습니까?<br>
                            당신 운명의 뼈대가 드러났습니다.<br>이제 산산조각 나 있는 당신의 주파수를 우주적 기하학으로 재정렬하고, 물리적 부를 강력하게 끌어당길 시간입니다.
                        </p>
                        
                        <!-- 복귀 및 채널 이동 버튼 영역 -->
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
            
            # 두 번째 인자로 'html'을 명시하여 HTML 메일로 인식하게 만듦
            msg = MIMEText(html_body, 'html')
            msg['Subject'] = "당신의 그림자 진단서가 도착했습니다"
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
            st.error("🌙 아스트랄 에너지가 고갈되었습니다. 오늘의 무료(제한: 20회)시간이 종료되었습니다. 자정 이후 다시 방문하십시오.")
        else:
            st.error("아스트랄 연결이 끊어졌습니다. 잠시 후 다시 시도하십시오.")
