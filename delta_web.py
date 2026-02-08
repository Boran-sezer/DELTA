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
        cred = credentials.Certificate(json.loads(decoded_json))
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Erreur Firebase : {e}")
        st.stop()

db = firestore.client()

# --- INITIALISATION GROQ (BLINDÉE) ---
def get_groq_client():
    # Test format 1: GROQ_API_KEY = "..."
    if "GROQ_API_KEY" in st.secrets:
        return Groq(api_key=st.secrets["GROQ_API_KEY"])
    # Test format 2: [groq] \n api_key = "..."
    if "groq" in st.secrets and "api_key" in st.secrets["groq"]:
        return Groq(api_key=st.secrets["groq"]["api_key"])
    return None

client = get_groq_client()

if not client:
    st.error("❌ Clé Groq introuvable dans les Secrets.")
    st.info("Vérifiez que vous avez bien écrit : GROQ_API_KEY = 'votre_cle' dans Settings > Secrets")
    st.stop()

USER_ID = "monsieur_sezer"

# --- UTILS MÉMOIRE ---
def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def is_memory_worthy(text: str) -> bool:
    blacklist = ["salut", "ok", "mdr", "lol", "?", "oui", "non"]
    return len(text.strip()) >= 10 and text.lower().strip() not in blacklist

# --- INTERFACE ---
st.set_page_config(page_title="DELTA AGI", page_icon="🌐", layout="wide")
st.title("🌐 DELTA : Système AGI")

# --- RÉCUPÉRATION DU CONTEXTE ---
mem_ref = db.collection("users").document(USER_ID).collection("memory")
try:
    memories = mem_ref.order_by("created_at", direction=firestore.Query.DESCENDING).limit(10).stream()
    context_list = [m.to_dict() for m in memories]
except Exception:
    context_list = []

with st.sidebar:
    st.header("🧠 Mémoire Vive")
    for m in context_list:
        st.caption(f"[{m.get('category')}] {m.get('content')}")
    if st.button("🔄 Actualiser"):
        st.rerun()

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- PROCESSUS ---
if prompt := st.chat_input("Ordre direct..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # 1. MÉMOIRE HASH
    if is_memory_worthy(prompt):
        m_hash = hash_text(prompt)
        try:
            analysis = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "Tu es une IA forte. Catégorise en JSON: {'category': '...'} "},
                    {"role": "user", "content": f"Catégorie pour : {prompt}"}
                ],
                response_format={"type": "json_object"}
            )
            cat = json.loads(analysis.choices[0].message.content).get("category", "info")
            
            ref = mem_ref.document(m_hash)
            if not ref.get().exists:
                ref.set({
                    "category": cat,
                    "content": prompt,
                    "created_at": datetime.utcnow()
                })
                st.toast("🧬 Synapse enregistrée.")
        except Exception as e:
            st.warning(f"Note : Mémoire non mise à jour ({e})")

    # 2. RÉPONSE JARVIS
    with st.chat_message("assistant"):
        context_str = "\n".join([f"- {m['content']}" for m in context_list])
        sys_instr = f"Tu es Jarvis. Créateur: Monsieur Sezer. Contexte: {context_str}. Sois concis."
        
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": sys_instr}] + st.session_state.messages[-5:]
            ).choices[0].message.content
            
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
        except Exception as e:
            st.error(f"Erreur Groq : {e}")
            
    st.rerun()
