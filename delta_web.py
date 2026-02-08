import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64, json, hashlib
from datetime import datetime, timedelta

# --- INITIALISATION FIREBASE ---
@st.cache_resource
def init_delta_brain():
    if not firebase_admin._apps:
        try:
            encoded = st.secrets["firebase_key"]["encoded_key"].strip()
            decoded_json = base64.b64decode(encoded).decode("utf-8")
            cred_dict = json.loads(decoded_json)
            if "private_key" in cred_dict:
                cred_dict["private_key"] = cred_dict["private_key"].replace("\\n", "\n")
            cred = credentials.Certificate(cred_dict)
            return firebase_admin.initialize_app(cred)
        except Exception as e:
            st.error(f"Erreur Firebase : {e}")
            return None
    return firebase_admin.get_app()

app = init_delta_brain()
db = firestore.client() if app else None
USER_ID = "monsieur_sezer" # Identifiant unique pour vos données

# --- INITIALISATION GROQ ---
client = Groq(api_key="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")

# --- UTILITAIRES ---
def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def get_memories(limit=30):
    """Récupère les souvenirs directement dans la collection de l'utilisateur"""
    if not db: return []
    try:
        # Chemin direct et simplifié pour éviter les erreurs de lecture
        docs = db.collection("users").document(USER_ID).collection("memory") \
                 .order_by("created_at", direction=firestore.Query.DESCENDING) \
                 .limit(limit).stream()
        return [d.to_dict() for d in docs]
    except Exception as e:
        return []

def summarize_context(memories, max_chars=600):
    if not memories: return "Aucun souvenir."
    lines = [f"- {m.get('content')}" for m in memories]
    return "\n".join(lines)[:max_chars]

# --- INTERFACE ---
st.set_page_config(page_title="DELTA AGI", layout="wide", initial_sidebar_state="collapsed")
st.markdown("<style>[data-testid='stSidebar'], header {display: none !important;}</style>", unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "À vos ordres, Monsieur Sezer. Système de mémoire actif."}]

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- PROCESSUS ---
if prompt := st.chat_input("Commandez Jarvis..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # 1. ÉCRITURE DANS FIREBASE (Correction du chemin)
    if db and len(prompt) > 5:
        doc_hash = hash_text(prompt)
        try:
            # On écrit dans : users / monsieur_sezer / memory / [HASH]
            db.collection("users").document(USER_ID).collection("memory").document(doc_hash).set({
                "content": prompt,
                "created_at": datetime.utcnow(),
                "priority": "medium"
            }, merge=True)
        except Exception as e:
            st.error(f"Erreur d'écriture : {e}")

    # 2. RÉPONSE AVEC CONTEXTE
    with st.chat_message("assistant"):
        memories = get_memories()
        ctx = summarize_context(memories)
        
        sys_instr = (
            f"Tu es Jarvis. Ton créateur est Monsieur Sezer. "
            f"Contexte de tes archives : {ctx}. "
            "Réponds de façon concise et intelligente."
        )
        
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": sys_instr}] + st.session_state.messages[-5:]
            ).choices[0].message.content
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
        except:
            st.error("Erreur de connexion Groq.")

    st.rerun()
