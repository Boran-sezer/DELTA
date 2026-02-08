import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64, json, hashlib
from datetime import datetime

# --- INITIALISATION FIREBASE ---
if not firebase_admin._apps:
    try:
        encoded = st.secrets["firebase_key"]["encoded_key"].strip()
        decoded_json = base64.b64decode(encoded).decode("utf-8")
        cred_dict = json.loads(decoded_json)
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Erreur Firebase : {e}")
        st.stop()

db = firestore.client()
USER_ID = "monsieur_sezer"

# --- UTILS MÉMOIRE ---
def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def is_memory_worthy(text: str) -> bool:
    blacklist = ["salut", "ok", "mdr", "lol", "?", "oui", "non"]
    return len(text.strip()) >= 10 and text.lower().strip() not in blacklist

def get_recent_memories(limit=10):
    try:
        mem_ref = db.collection("users").document(USER_ID).collection("memory")
        memories = mem_ref.order_by("created_at", direction=firestore.Query.DESCENDING).limit(limit).stream()
        return [m.to_dict() for m in memories]
    except Exception as e:
        st.error(f"Erreur récupération mémoire : {e}")
        return []

# --- INITIALISATION GROQ ---
client = Groq(api_key="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")

# --- INTERFACE ---
st.set_page_config(page_title="DELTA AGI", page_icon="🌐", layout="wide")
st.title("🌐 DELTA : Système de Mémoire Jarvis")

# Sidebar : souvenirs récents
context_list = get_recent_memories()
with st.sidebar:
    st.header("🧠 Mémoire Vive")
    if context_list:
        for m in context_list:
            st.caption(f"[{m.get('category')}] {m.get('content')}")
    else:
        st.info("Aucun souvenir pour le moment")
    if st.button("🔄 Actualiser"):
        context_list = get_recent_memories()

# Session state pour le chat
if "messages" not in st.session_state:
    st.session_state.messages = []

# Affichage du chat
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# --- PROCESSUS PRINCIPAL ---
if prompt := st.chat_input("Monsieur Sezer, donnez un ordre à Jarvis..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 1. Analyse et stockage mémoire
    if is_memory_worthy(prompt):
        try:
            # Catégorisation automatique
            analysis = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "Tu es Jarvis. Catégorise chaque information en JSON : {'category':'...', 'topic':'...'}"},
                    {"role": "user", "content": f"Analyse cette info : {prompt}"}
                ],
                response_format={"type": "json_object"}
            )
            res = json.loads(analysis.choices[0].message.content)
            cat = res.get("category", "Général")
            topic = res.get("topic", "Divers")

            # Stockage dans Firebase
            m_hash = hash_text(prompt)
            mem_ref = db.collection("users").document(USER_ID).collection("memory").document(m_hash)
            if not mem_ref.get().exists:
                mem_ref.set({
                    "category": cat,
                    "topic": topic,
                    "content": prompt,
                    "created_at": datetime.utcnow()
                })
                st.success("🧬 Souvenir enregistré.")
            else:
                st.info("Souvenir déjà présent.")
        except Exception as e:
            st.error(f"Erreur stockage mémoire : {e}")

    # 2. Récupérer mémoire à jour
    context_list = get_recent_memories()

    # 3. Réponse Jarvis contextualisée
    with st.chat_message("assistant"):
        context_str = "\n".join([f"- {m['content']}" for m in context_list])
        sys_instr = (
            f"Tu es Jarvis, assistant de Monsieur Sezer. "
            f"Voici tes souvenirs récents : {context_str}. "
            "Réponds de façon concise, brillante et directe. Ne mentionne jamais que tu es une IA."
        )
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": sys_instr}] + st.session_state.messages[-5:]
            ).choices[0].message.content

            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
        except Exception as e:
            st.error(f"Erreur Groq : {e}")
