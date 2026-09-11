import os
import sys
import streamlit as st

# Force UTF-8 encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdin.reconfigure(encoding="utf-8")

# src folder ko path me add karein
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from chatbot import TrustLinkChatbot

# Page configuration
st.set_page_config(
    page_title="TrustLink - Police AI Legal Assistant",
    page_icon="🛡️",
    layout="centered"
)

# Model aur Retriever ko cache karein taaki har click par reload na ho
@st.cache_resource
def load_trustlink_bot():
    return TrustLinkChatbot()

# Sidebar: Legal Disclaimer and Helplines
with st.sidebar:
    st.header("🚨 Emergency Helplines")
    st.markdown("""
    - **Police Emergency:** `112`
    - **Women Helpline:** `1091`
    - **Cyber Crime Portal:** `1930`
    - **Child Helpline:** `1098`
    """)
    st.divider()
    st.warning(
        "⚠️ **Disclaimer:** This AI terminal is for informational assistance and statutory cross-referencing (BNS/IPC). "
        "It does not constitute formal legal counsel. For FIR or emergencies, visit your nearest police station."
    )

# Main Title & Subtitle
st.title("🛡️ TrustLink AI Assistant")
st.caption("Statutory Police & Legal Information System (BNS, BNSS & IPC Mapped)")

# Chat history state initialize karein
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Namaste. Main TrustLink AI Assistant hoon. Aap naye Bharatiya Nyaya Sanhita (BNS) aur purane IPC kanoon se sambandhit sawal pooch sakte hain."
        }
    ]

# Chat history display karein
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# User Input handle karein
if prompt := st.chat_input("Apna sawal likhein (e.g. murder par kaun sa section lagega?)..."):
    # User message display aur save karein
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Bot response generate karein
    with st.chat_message("assistant"):
        with st.spinner("Statutory provisions verify ho rahe hain..."):
            bot = load_trustlink_bot()
            response = bot.generate_response(prompt)
            st.markdown(response)

    st.session_state.messages.append({"role": "assistant", "content": response})