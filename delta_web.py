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
            st.error(f"Erreur d'initialisation : {e}")
            return None
    return firebase_admin.get_app()

app = init_delta_brain()
db = firestore.client() if app else None
USER_ID = "monsieur_sezer"

# --- INITIALISATION GROQ ---
client = Groq(api_key="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")

# --- UTILITAIRES MÉMOIRE ---
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

def get_memories(limit=50):
    if not db: return []
    try:
        docs = db.collection("users").document(USER_ID).collection("memory") \
                 .order_by("created_at", direction=firestore.Query.DESCENDING) \
                 .limit(limit).stream()
        return [d.to_dict() for d in docs]
    except:
        return []

def merge_similar_memories(memories):
    merged = []
    seen_hashes = set()
    for m in memories:
        h = m.get("content_hash")
        if h in seen_hashes: continue
        merged.append(m)
        seen_hashes.add(h)
    return merged

def cleanup_old_memories(days=30):
    if not db: return
    cutoff = datetime.utcnow() - timedelta(days=days)
    mem_ref = db.collection("users").document(USER_ID).collection("memory")
    for d in mem_ref.stream():
        data = d.to_dict()
        if data.get("priority","low")=="low" and data.get("created_at") < cutoff:
            mem_ref.document(d.id).delete()

def summarize_context(memories, max_chars=500):
    if not memories: return "Aucun souvenir récent."
    memories = sorted(memories, key=lambda x: {"high":3,"medium":2,"low":1}.get(x.get("priority","medium")), reverse=True)
    merged = merge_similar_memories(memories)
    lines = [f"[{m.get('priority')}] {m.get('content')}" for m in merged]
    return "\n".join(lines)[:max_chars]

# --- INTERFACE SILENCIEUSE ---
st.set_page_config(page_title="DELTA AGI Ultra", page_icon="🌐", layout="wide")
st.title("🌐 DELTA : Jarvis Ultra-Intelligent")

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "À vos ordres, Monsieur Sezer."}]

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# --- PROCESSUS PRINCIPAL ---
if prompt := st.chat_input("Commandez Jarvis..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Analyse et écriture automatique silencieuse
    mem_analysis = is_memory_worthy(prompt)
    if db:
        m_hash = hash_text(prompt)
        try:
            db.collection("users").document(USER_ID).collection("memory").document(m_hash).set({
                "content": prompt,
                "content_hash": m_hash,
                "priority": mem_analysis.get("priority","medium"),
                "branch": mem_analysis.get("branch","Général"),
                "created_at": datetime.utcnow()
            }, merge=True)
        except:
            pass  # Rien à afficher, tout est silencieux

    cleanup_old_memories()  # Nettoyage automatique

    # Réponse Jarvis avec contexte
    with st.chat_message("assistant"):
        ctx = summarize_context(get_memories(limit=10))
        sys_instr = f"Tu es Jarvis. Créateur: Monsieur Sezer. Contexte: {ctx}. Sois concis, intelligent et pertinent."
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": sys_instr}] + st.session_state.messages[-5:]
            ).choices[0].message.content
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
        except:
            st.session_state.messages.append({"role": "assistant", "content": "Erreur interne."})
