import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64, json, hashlib
from datetime import datetime, timedelta

# --- INITIALISATION FIREBASE (VERSION CORRIGÉE) ---
@st.cache_resource
def init_delta_brain():
    if not firebase_admin._apps:
        try:
            encoded = st.secrets["firebase_key"]["encoded_key"].strip()
            decoded_json = base64.b64decode(encoded).decode("utf-8")
            cred_dict = json.loads(decoded_json)
            
            # Correction cruciale de la clé privée
            if "private_key" in cred_dict:
                cred_dict["private_key"] = cred_dict["private_key"].replace("\\n", "\n")
                
            cred = credentials.Certificate(cred_dict)
            return firebase_admin.initialize_app(cred)
        except Exception as e:
            st.error(f"Erreur d'initialisation : {e}")
            return None
    return firebase_admin.get_app()

app = init_delta_brain()
db = firestore.client() if app else None
USER_ID = "monsieur_sezer"

# --- INITIALISATION GROQ ---
client = Groq(api_key="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")

# --- UTILITAIRES MÉMOIRE (VOTRE LOGIQUE ULTRA) ---
def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def is_memory_worthy(text: str) -> dict:
    blacklist = ["salut", "ok", "mdr", "lol", "?", "oui", "non"]
    if len(text.strip()) < 15 or any(word in text.lower() for word in blacklist):
        return {"is_worthy": False, "priority": "low", "branch": "Général"}
    try:
        analysis = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Tu es Jarvis. Réponds en JSON : {'is_worthy': bool, 'priority': 'high|medium|low', 'branch':'nom'}"},
                {"role": "user", "content": text}
            ],
            response_format={"type": "json_object"}
        )
        return json.loads(analysis.choices[0].message.content)
    except:
        return {"is_worthy": False, "priority": "low", "branch": "Général"}

def get_memories(limit=20):
    if not db: return []
    try:
        docs = db.collection("users").document(USER_ID).collection("memory") \
                 .order_by("created_at", direction=firestore.Query.DESCENDING) \
                 .limit(limit).stream()
        return [d.to_dict() for d in docs]
    except: return []

def summarize_context(memories, max_chars=500):
    if not memories: return "Aucun souvenir récent."
    lines = [f"[{m.get('priority')}] {m.get('content')}" for m in memories]
    return "\n".join(lines)[:max_chars]

# --- INTERFACE ---
st.set_page_config(page_title="DELTA AGI Ultra", page_icon="🌐", layout="wide")
st.title("🌐 DELTA : Jarvis Ultra-Intelligent")

recent_memories = get_memories()

with st.sidebar:
    st.header("🧠 Mémoire Vive")
    if recent_memories:
        for m in recent_memories[:10]:
            st.caption(f"[{m.get('priority')}] {m.get('content')[:50]}...")
    else:
        st.info("En attente de nouvelles synapses...")
    
    if st.button("🔄 Synchroniser"):
        st.rerun()

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "À vos ordres, Monsieur Sezer. Le système est parfaitement synchronisé."}]

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- PROCESSUS PRINCIPAL ---
if prompt := st.chat_input("Commandez Jarvis..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # 1. Analyse et Écriture
    mem_analysis = is_memory_worthy(prompt)
    if mem_analysis.get("is_worthy") and db:
        m_hash = hash_text(prompt)
        try:
            db.collection("users").document(USER_ID).collection("memory").document(m_hash).set({
                "content": prompt,
                "content_hash": m_hash,
                "priority": mem_analysis.get("priority", "medium"),
                "branch": mem_analysis.get("branch", "Général"),
                "created_at": datetime.utcnow()
            }, merge=True)
            st.toast(f"🧬 Synapse enregistrée : {mem_analysis.get('branch')}")
        except Exception as e:
            st.error(f"Erreur d'écriture : {e}")

    # 2. Réponse Jarvis avec Contexte
    with st.chat_message("assistant"):
        ctx = summarize_context(get_memories(limit=10))
        sys_instr = f"Tu es Jarvis. Créateur: Monsieur Sezer. Contexte: {ctx}. Sois concis et brillant."
        
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
