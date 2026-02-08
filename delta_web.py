import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64, json, hashlib, re
from datetime import datetime

# ---------------- FIREBASE ----------------
@st.cache_resource
def init_firebase():
    if not firebase_admin._apps:
        encoded = st.secrets["firebase_key"]["encoded_key"]
        decoded = base64.b64decode(encoded).decode("utf-8")
        cred_dict = json.loads(decoded)
        cred_dict["private_key"] = cred_dict["private_key"].replace("\\n", "\n")
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
    return firestore.client()

db = init_firebase()

# ---------------- CONFIG ----------------
USER_ID = "monsieur_sezer"

client = Groq(api_key="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")

# ---------------- UTILS ----------------
def hash_text(text):
    return hashlib.sha256(text.encode()).hexdigest()

def is_useless(text):
    blacklist = ["salut", "ok", "mdr", "lol", "?", "oui", "non", "hello"]
    if len(text.strip()) < 8:
        return True
    return text.lower().strip() in blacklist

def classify_memory(text):
    t = text.lower()

    # Infos personnelles (toi)
    if re.search(r"\b(j'ai|je suis|mon|ma|mes|moi)\b", t):
        return ("profiles", USER_ID)

    # Autre personne détectée (ex: "mon pote Jules a 18 ans")
    match = re.search(r"(jules|paul|alex|luc)", t)
    if match:
        return ("profiles", match.group(1))

    # Projets / idées
    if any(word in t for word in ["projet", "idée", "application", "site", "jeu"]):
        return ("projects", "general")

    # Faits généraux
    if any(word in t for word in ["est", "sont", "fonctionne", "permet"]):
        return ("facts", "general")

    return (None, None)

def save_memory(text):
    if is_useless(text):
        return

    category, sub = classify_memory(text)
    if not category:
        return

    doc_id = hash_text(text)

    db.collection("memory") \
      .document(category) \
      .collection(sub) \
      .document(doc_id) \
      .set({
          "content": text,
          "created_at": datetime.utcnow()
      }, merge=True)

def load_context(limit=20):
    memories = []
    collections = [
        ("profiles", USER_ID),
        ("facts", "general"),
        ("projects", "general")
    ]

    for cat, sub in collections:
        docs = db.collection("memory").document(cat).collection(sub) \
            .order_by("created_at", direction=firestore.Query.DESCENDING) \
            .limit(limit).stream()
        for d in docs:
            memories.append(d.to_dict()["content"])

    return "\n".join(memories[:limit])

# ---------------- UI ----------------
st.set_page_config(layout="wide")
st.markdown("<style>header,[data-testid=stSidebar]{display:none}</style>", unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "🧠 Jarvis en ligne. Mémoire structurée activée."}
    ]

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# ---------------- CHAT ----------------
if prompt := st.chat_input("Parle…"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    save_memory(prompt)

    context = load_context()

    system = (
        "Tu es Jarvis, une IA avec une mémoire structurée. "
        "Voici les informations importantes connues :\n"
        f"{context}\n"
        "Utilise-les intelligemment sans les répéter inutilement."
    )

    with st.chat_message("assistant"):
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": system}] + st.session_state.messages[-6:]
        ).choices[0].message.content

        st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})

    st.rerun()
