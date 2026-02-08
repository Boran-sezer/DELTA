import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64, json, hashlib
from datetime import datetime, timedelta

# --- INITIALISATION FIREBASE ---
if not firebase_admin._apps:
    try:
        encoded = st.secrets["firebase_key"]["encoded_key"].strip()
        decoded_json = base64.b64decode(encoded).decode("utf-8")
        cred_dict = json.loads(decoded_json)
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Erreur d'initialisation Firebase : {e}")
        st.stop()

db = firestore.client()
USER_ID = "monsieur_sezer"

# --- INITIALISATION GROQ ---
client = Groq(api_key="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")

# --- UTILITAIRES ---
def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def write_memory(content: str, priority="medium", branch="Général"):
    """Écrit un souvenir dans Firestore avec validation immédiate"""
    if not content.strip():
        return False
    try:
        m_hash = hash_text(content)
        # Chemin conforme à votre structure : users -> monsieur_sezer -> memory
        doc_ref = db.collection("users").document(USER_ID).collection("memory").document(m_hash)
        
        data = {
            "content": content,
            "content_hash": m_hash,
            "priority": priority,
            "branch": branch,
            "created_at": datetime.utcnow()
        }
        doc_ref.set(data, merge=True)
        st.toast(f"🧬 Branche {branch} mise à jour.")
        return True
    except Exception as e:
        st.error(f"Erreur d'écriture Firebase : {e}")
        return False

def is_memory_worthy(text: str) -> dict:
    """Analyse de pertinence via LLM"""
    blacklist = ["salut", "ok", "mdr", "lol", "?", "oui", "non"]
    if len(text.strip()) < 10 or any(word == text.lower().strip() for word in blacklist):
        return {"is_worthy": False, "priority": "low", "branch": "Général"}

    try:
        analysis = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Tu es Jarvis. Analyse si l'info mérite d'être sauvée. JSON: {'is_worthy': bool, 'priority': 'high|medium|low', 'branch':'nom'}"},
                {"role": "user", "content": text}
            ],
            response_format={"type": "json_object"}
        )
        return json.loads(analysis.choices[0].message.content)
    except:
        return {"is_worthy": False, "priority": "low", "branch": "Général"}

def get_memories(limit=50):
    """Récupère et nettoie les données pour Streamlit"""
    memories = []
    try:
        # On force la lecture sur la sous-collection memory
        docs = db.collection("users").document(USER_ID).collection("memory") \
                 .order_by("created_at", direction=firestore.Query.DESCENDING) \
                 .limit(limit).stream()
        for d in docs:
            m = d.to_dict()
            # Sécurité pour l'affichage Streamlit (les dates Firestore causent parfois des erreurs)
            if 'created_at' in m and hasattr(m['created_at'], 'isoformat'):
                m['created_at'] = m['created_at'].isoformat()
            memories.append(m)
    except Exception as e:
        st.sidebar.error(f"Erreur de lecture : {e}")
    return memories

def summarize_context(memories, max_chars=600):
    """Prépare le résumé pour Jarvis"""
    if not memories: return "Aucun souvenir."
    # Tri par priorité
    prio_map = {"high": 3, "medium": 2, "low": 1}
    sorted_mem = sorted(memories, key=lambda x: prio_map.get(x.get("priority", "low"), 0), reverse=True)
    
    lines = [f"[{m.get('branch', 'Info')}] {m.get('content')}" for m in sorted_mem[:10]]
    return "\n".join(lines)[:max_chars]

# --- INTERFACE ---
st.set_page_config(page_title="DELTA AGI Ultra", page_icon="🌐", layout="wide")
st.title("🌐 DELTA : Jarvis Ultra-Intelligent")

# Sidebar
recent_memories = get_memories(limit=20)
with st.sidebar:
    st.header("🧠 Mémoire Vive")
    if recent_memories:
        for m in recent_memories:
            with st.expander(f"📁 {m.get('branch', 'Général')}"):
                st.write(m.get('content'))
                st.caption(f"Priorité: {m.get('priority')}")
    else:
        st.info("Base de données en attente d'initialisation.")
    
    if st.button("🔄 Synchroniser"):
        st.rerun()

# Session state chat
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Système opérationnel. À vos ordres, Monsieur Sezer."}]

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- ACTION ---
if prompt := st.chat_input("Commandez Jarvis..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # 1. Analyse & Écriture
    analysis = is_memory_worthy(prompt)
    if analysis.get("is_worthy"):
        write_memory(prompt, priority=analysis.get("priority"), branch=analysis.get("branch"))

    # 2. Contexte & Réponse
    current_memories = get_memories(limit=15)
    ctx = summarize_context(current_memories)
    
    with st.chat_message("assistant"):
        sys_instr = f"Tu es Jarvis. Créateur: Monsieur Sezer. Contexte récent: {ctx}. Sois brillant et concis."
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": sys_instr}] + st.session_state.messages[-5:]
            ).choices[0].message.content
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
        except Exception as e:
            st.error(f"Erreur Brain : {e}")

    st.rerun()
