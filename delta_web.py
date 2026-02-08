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

# --- INITIALISATION GROQ ---
client = Groq(api_key="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")

# --- UTILITAIRES MÉMOIRE ---
def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def is_memory_worthy(text: str) -> bool:
    """Décide si une information mérite d'être mémorisée, façon Jarvis."""
    # blacklist simple pour éviter les trivialités
    blacklist = ["salut", "ok", "mdr", "lol", "?", "oui", "non"]
    if len(text.strip()) < 15 or any(word in text.lower() for word in blacklist):
        return False

    # Vérification via Groq (LLM) pour décider si info est utile
    try:
        analysis = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Tu es Jarvis, assistant de Tony Stark. "
                                              "Décide si cette info mérite d'être mémorisée. "
                                              "Réponds strictement en JSON : {'is_worthy': bool, 'priority': 'high|medium|low', 'branch':'nom_de_branche'}"},
                {"role": "user", "content": text}
            ],
            response_format={"type": "json_object"}
        )
        res = json.loads(analysis.choices[0].message.content)
        return res
    except:
        return {"is_worthy": False, "priority": "low", "branch": "Général"}

def get_recent_memories(limit=10):
    """Récupère les souvenirs récents pour contextualiser Jarvis"""
    memories = []
    try:
        mem_ref = db.collection("users").document(USER_ID).collection("memory")
        docs = mem_ref.order_by("created_at", direction=firestore.Query.DESCENDING).limit(limit).stream()
        memories = [d.to_dict() for d in docs]
    except:
        pass
    return memories

def summarize_context(memories, max_chars=500):
    """Résume les souvenirs récents pour fournir un contexte LLM"""
    lines = []
    for m in memories:
        lines.append(f"[{m.get('priority','medium')}] {m.get('content')}")
    return "\n".join(lines)[:max_chars]

# --- INTERFACE ---
st.set_page_config(page_title="DELTA AGI", page_icon="🌐", layout="wide")
st.title("🌐 DELTA : Système Jarvis Intelligence Artificielle")

# Sidebar : souvenirs récents
recent_memories = get_recent_memories()
with st.sidebar:
    st.header("🧠 Mémoire Vive Jarvis")
    if recent_memories:
        for m in recent_memories:
            st.caption(f"[{m.get('priority','medium')}] {m.get('content')[:50]}...")
    else:
        st.info("Aucun souvenir enregistré pour le moment.")
    if st.button("🔄 Actualiser"):
        recent_memories = get_recent_memories()

# Session state pour le chat
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "À vos ordres, Monsieur Sezer. Jarvis est en ligne. Que souhaitez-vous ?" }]

# Affichage du chat
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# --- PROCESSUS PRINCIPAL ---
if prompt := st.chat_input("Parlez à Jarvis..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 1️⃣ Vérification si info utile et catégorisation
    mem_analysis = is_memory_worthy(prompt)
    if mem_analysis.get("is_worthy"):
        branch = mem_analysis.get("branch", "Général")
        priority = mem_analysis.get("priority", "medium")
        m_hash = hash_text(prompt)
        db.collection("users").document(USER_ID).collection("memory").document(m_hash).set({
            "content": prompt,
            "priority": priority,
            "branch": branch,
            "created_at": datetime.utcnow()
        }, merge=True)
        st.toast(f"🧬 Souvenir mémorisé dans {branch} avec priorité {priority}")

    # 2️⃣ Récupération contexte pour Jarvis
    recent_memories = get_recent_memories()
    context_summary = summarize_context(recent_memories)

    # 3️⃣ Réponse Jarvis
    with st.chat_message("assistant"):
        sys_instr = (
            f"Tu es Jarvis, assistant intelligent de Monsieur Sezer. "
            f"Voici les souvenirs récents : {context_summary}. "
            "Réponds de façon concise, intelligente, directe, et toujours pertinente. "
            "Ne mentionne jamais que tu es une IA."
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
