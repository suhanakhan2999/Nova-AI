import streamlit as st
import requests
import sqlite3
import json
from datetime import datetime
from streamlit_mic_recorder import speech_to_text
import streamlit.components.v1 as components
from pdf_reader import extract_pdf_text

# ==========================================
# VOICE OUTPUT
# ==========================================

def add_voice_output(text, key):
    safe_text = json.dumps(text)

    html = f'''
    <div style="display:flex;gap:10px;align-items:center;">
      <button id="speak-{key}" style="background:#7652c8;color:white;border:0;border-radius:9px;padding:8px 14px;cursor:pointer;">
        🔊 Listen
      </button>
      <button id="stop-{key}" style="background:#302747;color:white;border:0;border-radius:9px;padding:8px 14px;cursor:pointer;">
        ⏹ Stop
      </button>
      <span id="status-{key}" style="color:#cbb9f3;font-size:12px;"></span>
    </div>
    <script>
      const textToRead = {safe_text};
      const speakButton = document.getElementById("speak-{key}");
      const stopButton = document.getElementById("stop-{key}");
      const status = document.getElementById("status-{key}");

      speakButton.addEventListener("click", () => {{
        if (!("speechSynthesis" in window)) {{
          status.textContent = "Speech not supported.";
          return;
        }}

        window.speechSynthesis.cancel();

        const utterance = new SpeechSynthesisUtterance(textToRead);
        utterance.lang = "en-US";
        utterance.rate = 1.0;

        utterance.onstart = () => status.textContent = "Nova is speaking...";
        utterance.onend = () => status.textContent = "";
        utterance.onerror = () => status.textContent = "Speech error.";

        window.speechSynthesis.speak(utterance);
      }});

      stopButton.addEventListener("click", () => {{
        window.speechSynthesis.cancel();
        status.textContent = "Stopped";
      }});
    </script>
    '''

    components.html(html, height=52)


# ==========================================
# 1. CONFIGURATION
# ==========================================

st.set_page_config(
    page_title="Nova AI",
    page_icon="✦",
    layout="wide"
)

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "qwen2.5:3b"
DB_NAME = "nova_chats.db"

MODES = {
    "General Chat": (
        "You are Nova AI, a friendly and helpful AI assistant. "
        "Give clear and accurate answers."
    ),

    "Study Assistant": (
        "You are a patient college tutor. Explain topics step by step "
        "using simple language and examples. Help with engineering "
        "and computer science subjects."
    ),

    "Coding Assistant": (
        "You are an expert programming tutor. Explain code clearly, "
        "find errors and provide complete working examples."
    )
}


# ==========================================
# 2. DATABASE
# ==========================================

def connect_db():
    return sqlite3.connect(DB_NAME)


def initialize_database():
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            mode TEXT,
            created_at TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            role TEXT,
            content TEXT,
            created_at TEXT
        )
    """)

    cursor.execute("PRAGMA table_info(chats)")
    chat_columns = [row[1] for row in cursor.fetchall()]

    if "title" not in chat_columns:
        cursor.execute("ALTER TABLE chats ADD COLUMN title TEXT")

    if "mode" not in chat_columns:
        cursor.execute("ALTER TABLE chats ADD COLUMN mode TEXT")

    if "created_at" not in chat_columns:
        cursor.execute("ALTER TABLE chats ADD COLUMN created_at TEXT")

    cursor.execute("PRAGMA table_info(messages)")
    message_columns = [row[1] for row in cursor.fetchall()]

    if "chat_id" not in message_columns:
        cursor.execute("ALTER TABLE messages ADD COLUMN chat_id INTEGER")

    if "role" not in message_columns:
        cursor.execute("ALTER TABLE messages ADD COLUMN role TEXT")

    if "content" not in message_columns:
        cursor.execute("ALTER TABLE messages ADD COLUMN content TEXT")

    if "created_at" not in message_columns:
        cursor.execute("ALTER TABLE messages ADD COLUMN created_at TEXT")

    conn.commit()
    conn.close()


def create_chat(mode):
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO chats (title, mode, created_at) VALUES (?, ?, ?)",
        ("New Chat", mode, datetime.now().isoformat())
    )

    chat_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return chat_id


def get_chats():
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, title, mode FROM chats ORDER BY id DESC"
    )

    chats = cursor.fetchall()
    conn.close()

    return chats


def get_messages(chat_id):
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT role, content FROM messages WHERE chat_id = ? ORDER BY id",
        (chat_id,)
    )

    messages = cursor.fetchall()
    conn.close()

    return messages


def save_message(chat_id, role, content):
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO messages (chat_id, role, content, created_at)
        VALUES (?, ?, ?, ?)
    """, (
        chat_id,
        role,
        content,
        datetime.now().isoformat()
    ))

    conn.commit()
    conn.close()


def rename_chat(chat_id, title):
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE chats SET title = ? WHERE id = ?",
        (title, chat_id)
    )

    conn.commit()
    conn.close()


def delete_chat(chat_id):
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM messages WHERE chat_id = ?",
        (chat_id,)
    )

    cursor.execute(
        "DELETE FROM chats WHERE id = ?",
        (chat_id,)
    )

    conn.commit()
    conn.close()


initialize_database()


# ==========================================
# 3. SESSION STATE
# ==========================================

if "mode" not in st.session_state:
    st.session_state.mode = "General Chat"

if st.session_state.mode not in MODES:
    st.session_state.mode = "General Chat"

if "chat_id" not in st.session_state:
    st.session_state.chat_id = create_chat(st.session_state.mode)

if "pdf_text" not in st.session_state:
    st.session_state.pdf_text = ""

if "pdf_name" not in st.session_state:
    st.session_state.pdf_name = ""

if "draft" not in st.session_state:
    st.session_state.draft = ""

if "mic_version" not in st.session_state:
    st.session_state.mic_version = 0

if "draft_version" not in st.session_state:
    st.session_state.draft_version = 0

if "last_voice_text" not in st.session_state:
    st.session_state.last_voice_text = ""

valid_chats = get_chats()
valid_chat_ids = [chat[0] for chat in valid_chats]

if st.session_state.chat_id not in valid_chat_ids:
    st.session_state.chat_id = create_chat(st.session_state.mode)


# ==========================================
# 4. DESIGN
# ==========================================

st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #100d20, #19132e);
    color: white;
}

section[data-testid="stSidebar"] {
    background-color: #171126;
}

h1, h2, h3 {
    color: #d7c4ff;
}

.stButton button {
    background-color: #7652c8;
    color: white;
    border-radius: 10px;
    border: none;
}

.stButton button:hover {
    background-color: #9674e5;
    color: white;
}

[data-testid="stChatMessage"] {
    background-color: rgba(255,255,255,0.04);
    border-radius: 12px;
    padding: 12px;
}
</style>
""", unsafe_allow_html=True)


# ==========================================
# 5. SIDEBAR
# ==========================================

with st.sidebar:

    st.title("✦ Nova AI")
    st.caption("Your personal AI assistant")
    st.divider()

    selected_mode = st.radio(
        "Choose assistant mode",
        list(MODES.keys()),
        index=list(MODES.keys()).index(st.session_state.mode),
        key="mode_selector"
    )

    if selected_mode != st.session_state.mode:
        st.session_state.mode = selected_mode
        st.session_state.chat_id = create_chat(selected_mode)
        st.session_state.draft = ""
        st.session_state.draft_version += 1
        st.session_state.mic_version += 1
        st.rerun()

    if st.button("＋ New Chat", use_container_width=True):
        st.session_state.chat_id = create_chat(st.session_state.mode)
        st.session_state.draft = ""
        st.session_state.draft_version += 1
        st.session_state.mic_version += 1
        st.rerun()

    st.divider()
    st.subheader("Chat History")

    chats = get_chats()

    if chats:

        chat_ids = [chat[0] for chat in chats]
        chat_titles = {chat[0]: chat[1] for chat in chats}
        chat_modes = {chat[0]: chat[2] for chat in chats}

        current_index = (
            chat_ids.index(st.session_state.chat_id)
            if st.session_state.chat_id in chat_ids
            else 0
        )

        selected_chat = st.selectbox(
            "Previous conversations",
            options=chat_ids,
            index=current_index,
            format_func=lambda x: chat_titles.get(x, "New Chat"),
            key=f"chat_selector_{len(chat_ids)}"
        )

        if selected_chat != st.session_state.chat_id:
            st.session_state.chat_id = selected_chat

            saved_mode = chat_modes.get(
                selected_chat, "General Chat"
            )

            st.session_state.mode = (
                saved_mode if saved_mode in MODES else "General Chat"
            )

            st.session_state.draft = ""
            st.session_state.draft_version += 1
            st.session_state.mic_version += 1
            st.rerun()

        title_input = st.text_input(
            "Rename conversation",
            value=chat_titles.get(st.session_state.chat_id, ""),
            key=f"title_{st.session_state.chat_id}"
        )

        if st.button("Rename Chat", use_container_width=True):
            if title_input.strip():
                rename_chat(
                    st.session_state.chat_id,
                    title_input.strip()
                )
                st.rerun()

        if st.button("Delete Chat", use_container_width=True):
            delete_chat(st.session_state.chat_id)
            st.session_state.chat_id = create_chat(st.session_state.mode)
            st.session_state.draft = ""
            st.session_state.draft_version += 1
            st.session_state.mic_version += 1
            st.rerun()

    st.divider()

    # ======================================
    # 6. PDF ASSISTANT
    # ======================================

    st.subheader("📄 PDF Assistant")

    uploaded_pdf = st.file_uploader(
        "Upload your college PDF notes",
        type=["pdf"],
        key="pdf_upload"
    )

    if uploaded_pdf is not None:

        if uploaded_pdf.name != st.session_state.pdf_name:

            with st.spinner("Nova is reading your PDF..."):

                result = extract_pdf_text(uploaded_pdf)

                if result.startswith("Error reading PDF:"):
                    st.error(result)

                elif result == "No readable text found in this PDF.":
                    st.warning(result)

                else:
                    st.session_state.pdf_text = result
                    st.session_state.pdf_name = uploaded_pdf.name
                    st.success("PDF successfully loaded!")

    if st.session_state.pdf_text:

        st.caption(f"Loaded: {st.session_state.pdf_name}")

        with st.expander("Preview PDF text"):
            st.text(st.session_state.pdf_text[:4000])

        if st.button("Remove PDF"):
            st.session_state.pdf_text = ""
            st.session_state.pdf_name = ""
            st.rerun()

    st.divider()
    st.caption("Model: Qwen 2.5 — 3B")
    st.caption("Powered by Ollama")


# ==========================================
# 7. MAIN CHAT
# ==========================================

st.title("✦ Nova AI")
st.caption("Your personal AI and study assistant")

if st.session_state.pdf_text:
    st.info(f"📄 PDF mode active: {st.session_state.pdf_name}")

messages = get_messages(st.session_state.chat_id)

for message_index, (role, content) in enumerate(messages):

    with st.chat_message(role):
        st.markdown(content)

        if role == "assistant":
            add_voice_output(
                content,
                f"reply-{st.session_state.chat_id}-{message_index}"
            )


# ==========================================
# 8. ENGLISH VOICE DICTATION
# ==========================================

st.divider()
st.subheader("🎙️ English Voice Dictation")

st.caption(
    "Click Start speaking, speak in English, then click Stop speaking. "
    "Your words will appear in the message box below."
)

try:

    voice_text = speech_to_text(
        language="en",
        start_prompt="🎙️ Start speaking",
        stop_prompt="⏹️ Stop speaking",
        just_once=True,
        use_container_width=True,
        key=f"nova_mic_{st.session_state.mic_version}"
    )

    if voice_text:

        existing_text = st.session_state.draft.strip()

        if existing_text:
            st.session_state.draft = existing_text + " " + voice_text
        else:
            st.session_state.draft = voice_text

        st.session_state.last_voice_text = voice_text

        st.session_state.mic_version += 1
        st.session_state.draft_version += 1

        st.rerun()

except Exception as error:
    st.error(f"Microphone error: {error}")


# ==========================================
# 9. MESSAGE INPUT
# ==========================================

st.subheader("💬 Your Message")

message_text = st.text_area(
    "Type your message or use your microphone above",
    value=st.session_state.draft,
    height=120,
    placeholder="Type your question or dictate it using the microphone...",
    key=f"message_box_{st.session_state.draft_version}"
)

send_col, clear_col = st.columns([3, 1])

with send_col:
    send_clicked = st.button(
        "Send to Nova ➤",
        use_container_width=True
    )

with clear_col:
    clear_clicked = st.button(
        "Clear",
        use_container_width=True
    )

if clear_clicked:
    st.session_state.draft = ""
    st.session_state.draft_version += 1
    st.session_state.last_voice_text = ""
    st.session_state.mic_version += 1
    st.rerun()


# ==========================================
# 10. SEND MESSAGE TO OLLAMA
# ==========================================

if send_clicked:

    user_text = message_text.strip()

    if not user_text:
        st.warning("Please type or dictate a message first.")

    else:

        previous_messages = get_messages(st.session_state.chat_id)

        if len(previous_messages) == 0:
            rename_chat(st.session_state.chat_id, user_text[:35])

        save_message(
            st.session_state.chat_id,
            "user",
            user_text
        )

        system_prompt = MODES[st.session_state.mode]

        if st.session_state.pdf_text:

            pdf_context = st.session_state.pdf_text[:18000]

            system_prompt += (
                "\n\nThe user has uploaded a PDF. "
                "Use this document as the main source for questions "
                "about it. If an answer is not in the document, "
                "say so clearly.\n\nPDF CONTENT:\n"
                + pdf_context
            )

        saved_messages = get_messages(st.session_state.chat_id)

        api_messages = [
            {"role": "system", "content": system_prompt}
        ]

        for role, content in saved_messages[-20:]:

            api_messages.append({
                "role": role,
                "content": content
            })

        with st.chat_message("user"):
            st.markdown(user_text)

        with st.chat_message("assistant"):

            response_placeholder = st.empty()
            full_response = ""

            try:

                response = requests.post(
                    OLLAMA_URL,
                    json={
                        "model": MODEL_NAME,
                        "messages": api_messages,
                        "stream": True
                    },
                    stream=True,
                    timeout=(10, 300)
                )

                response.raise_for_status()

                for line in response.iter_lines():

                    if line:

                        data = json.loads(line.decode("utf-8"))

                        chunk = data.get(
                            "message", {}
                        ).get("content", "")

                        full_response += chunk

                        response_placeholder.markdown(
                            full_response + "▌"
                        )

                response_placeholder.markdown(full_response)

                save_message(
                    st.session_state.chat_id,
                    "assistant",
                    full_response
                )

                st.session_state.draft = ""
                st.session_state.draft_version += 1
                st.session_state.last_voice_text = ""
                st.session_state.mic_version += 1
                st.rerun()

            except requests.exceptions.ConnectionError:
                st.error(
                    "Cannot connect to Ollama. "
                    "Please make sure Ollama is running."
                )

            except requests.exceptions.Timeout:
                st.error(
                    "Nova took too long to respond. Please try again."
                )

            except requests.exceptions.HTTPError as error:
                st.error(f"Ollama returned an error: {error}")

            except Exception as error:
                st.error(f"Something went wrong: {error}")