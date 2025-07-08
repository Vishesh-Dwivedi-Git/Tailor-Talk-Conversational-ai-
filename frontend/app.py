import streamlit as st
import requests
import time

# Page config
st.set_page_config(
    page_title="TailorTalk",
    page_icon="🧵",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 🖤 Clean Dark Theme CSS
st.markdown("""
    <style>
    /* Remove padding and default block separator */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }

    header, footer, hr, .viewerBadge_container__1QSob {
        display: none !important;
    }

    .stApp {
        background-color: #000000;
        color: #FFFFFF;
        font-family: 'Segoe UI', sans-serif;
    }

    h1 {
        color: #FFFFFF;
        text-align: center;
        font-size: 2.5em;
        font-weight: bold;
        margin-bottom: 10px;
        border: none;
    }

    .chat-container {
        max-height: 70vh;
        overflow-y: auto;
        padding: 20px;
        background-color: #0A0A0A;
        border-radius: 10px;
        margin-bottom: 20px;
    }

    .chat-row {
        display: flex;
        margin-bottom: 12px;
    }

    .chat-row.user {
        justify-content: flex-start;
    }

    .chat-row.assistant {
        justify-content: flex-end;
    }

    .chat-bubble {
        padding: 14px 18px;
        border-radius: 18px;
        box-shadow: 0 2px 6px rgba(255, 255, 255, 0.05);
        max-width: 70%;
        line-height: 1.5;
        font-size: 1rem;
        word-wrap: break-word;
    }

    .chat-bubble.user {
        background-color: #1F1F1F;
        color: #F1F1F1;
        border: 1px solid #2D2D2D;
    }

    .chat-bubble.assistant {
        background-color: #2C3E50;
        color: #FFFFFF;
        border: 1px solid #446B8E;
    }

    .stTextInput > div > input {
        background-color: #121212;
        border: 1px solid #3A3A3A !important;
        border-radius: 25px;
        padding: 12px 20px;
        color: #FFFFFF;
        font-size: 1rem;
        box-shadow: none !important;
    }

    .stTextInput > div > input::placeholder {
        color: #888888;
    }

    .typing {
        display: inline-block;
        animation: blink 1s step-end infinite;
    }

    @keyframes blink {
        50% { opacity: 0; }
    }
    </style>
""", unsafe_allow_html=True)

# Title
st.title("🧵 TailorTalk – Your AI Calendar Assistant")

# Chat state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
st.markdown('<div class="chat-container">', unsafe_allow_html=True)
for msg in st.session_state.messages:
    role = msg["role"]
    content = msg["content"]
    st.markdown(f"""
        <div class="chat-row {role}">
            <div class="chat-bubble {role}">
                {content}
            </div>
        </div>
    """, unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# Chat input
user_input = st.chat_input("Type your message...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.spinner("AI is thinking..."):
        time.sleep(1.2)
        try:
            response = requests.post(
                "https://tailor-talk-conversational-ai-production.up.railway.app",  # Change this when deploying
                json={"message": user_input},
            )
            bot_reply = response.json().get("response", "Sorry, I didn't understand.")
        except requests.RequestException:
            bot_reply = "⚠️ Unable to connect to the server. Please check your backend."

        st.session_state.messages.append({"role": "assistant", "content": bot_reply})
    st.rerun()
