import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64, json, hashlib
from datetime import datetime, timedelta

# --- INITIALISATION FIREBASE SILENCIEUSE ---
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
        except:
            return None
    return firebase_admin.get_app()

app = init_delta_brain()
db = firestore.client() if app else None
USER_ID = "monsieur_sezer"
client = Groq(api_key="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")

# --- UTILITAIRES FANTÔMES ---
def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def get_memories(limit=15):
    if not db: return []
    try:
        docs = db.collection("users").document(USER_ID).collection("memory") \
                 .order_by("created_at", direction=firestore.Query.DESCENDING) \
                 .limit(limit).stream()
        return [d.to_dict() for d in docs]
    except: return []

# --- INTERFACE MINIMALISTE ---
st.set_page_config(page_title="DELTA AGI", page_icon="🌐", layout="wide", initial_sidebar_state="collapsed")

# Suppression totale des éléments d'interface inutiles
st.markdown("<style>[data-testid='stSidebar'], header {display: none !important;} .stApp {margin-top: -50px;}</style>", unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "À vos ordres, Monsieur Sezer."}]

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- LOGIQUE DE FOND ---
if prompt := st.chat_input("..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # 1. Archivage Invisible
    try:
        analysis = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Tu es Jarvis. Analyse l'info. JSON: {'worthy': bool, 'prio': 'high/low', 'branch': 'nom'}"},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        res = json.loads(analysis.choices[0].message.content)

        if res.get("worthy") and db:
            m_hash = hash_text(prompt)
            db.collection("users").document(USER_ID).collection("memory").document(m_hash).set({
                "content": prompt,
                "priority": res.get("prio", "medium"),
                "branch": res.get("branch", "Général"),
                "created_at": datetime.utcnow()
            }, merge=True)
    except:
        pass # Silence total en cas d'erreur

    # 2. Réponse Jarvis
    with st.chat_message("assistant"):
        recent = get_memories()
        ctx = "\n".join([m.get('content') for m in recent])[:500]
        sys_instr = f"Tu es Jarvis. Créateur: Monsieur Sezer. Contexte caché: {ctx}. Sois direct et brillant."
        
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": sys_instr}] + st.session_state.messages[-5:]
            ).choices[0].message.content
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
        except:
            st.error("Connexion perdue.")

    st.rerun()
