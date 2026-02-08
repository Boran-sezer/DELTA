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
        st.success("✅ Firebase initialisé avec succès !")
    except Exception as e:
        st.error(f"Erreur Firebase : {e}")
        st.stop()

db = firestore.client()
USER_ID = "monsieur_sezer"

# --- INITIALISATION GROQ ---
client = Groq(api_key="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")

# --- UTILITAIRES ---
def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def write_memory(content: str, priority="medium", branch="Général"):
    """Écrit un souvenir dans Firestore avec debug"""
    if not content.strip():
        st.warning("Le contenu est vide, rien à écrire.")
        return False
    m_hash = hash_text(content)
    doc_ref = db.collection("users").document(USER_ID).collection("memory").document(m_hash)
    try:
        doc_ref.set({
            "content": content,
            "content_hash": m_hash,
            "priority": priority,
            "branch": branch,
            "created_at": datetime.utcnow()
        })
        st.success(f"🧬 Souvenir mémorisé : {branch} [{priority}]")
        return True
    except Exception as e:
        st.error(f"Erreur lors de l’écriture dans Firebase : {e}")
        return False

def is_memory_worthy(text: str) -> dict:
    """Décide si une info mérite d'être mémorisée"""
    blacklist = ["salut", "ok", "mdr", "lol", "?", "oui", "non"]
    if len(text.strip()) < 15 or any(word in text.lower() for word in blacklist):
        return {"is_worthy": False, "priority": "low", "branch": "Général"}

    try:
        analysis = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": (
                    "Tu es Jarvis, assistant intelligent de Tony Stark. "
                    "Décide si cette info mérite d'être mémorisée. "
                    "Réponds strictement en JSON : "
                    "{'is_worthy': bool, 'priority': 'high|medium|low', 'branch':'nom_de_branche'}"
                )},
                {"role": "user", "content": text}
            ],
            response_format={"type": "json_object"}
        )
        return json.loads(analysis.choices[0].message.content)
    except:
        return {"is_worthy": False, "priority": "low", "branch": "Général"}

def get_memories(limit=50):
    """Récupère tous les souvenirs"""
    memories = []
    try:
        docs = db.collection("users").document(USER_ID).collection("memory") \
                 .order_by("created_at", direction=firestore.Query.DESCENDING) \
                 .limit(limit).stream()
        memories = [d.to_dict() for d in docs]
    except Exception as e:
        st.error(f"Erreur récupération mémoires : {e}")
    return memories

def merge_similar_memories(memories):
    """Fusionne souvenirs proches (basique)"""
    merged = []
    seen_hashes = set()
    for m in memories:
        h = m.get("content_hash")
        if h in seen_hashes:
            continue
        merged.append(m)
        seen_hashes.add(h)
    return merged

def cleanup_old_memories(days=30):
    """Supprime les souvenirs peu prioritaires et vieux"""
    cutoff = datetime.utcnow() - timedelta(days=days)
    mem_ref = db.collection("users").document(USER_ID).collection("memory")
    docs = mem_ref.stream()
    for d in docs:
        data = d.to_dict()
        if data.get("priority","low")=="low" and data.get("created_at") < cutoff:
            mem_ref.document(d.id).delete()

def summarize_context(memories, max_chars=500):
    """Résumé intelligent pour LLM"""
    memories = sorted(memories, key=lambda x: {"high":3,"medium":2,"low":1}.get(x.get("priority","medium")), reverse=True)
    merged = merge_similar_memories(memories)
    lines = [f"[{m.get('priority')}] {m.get('content')}" for m in merged]
    return "\n".join(lines)[:max_chars]

# --- INTERFACE ---
st.set_page_config(page_title="DELTA AGI Ultra", page_icon="🌐", layout="wide")
st.title("🌐 DELTA : Jarvis Ultra-Intelligent")

# Sidebar
cleanup_old_memories()
recent_memories = get_memories(limit=20)
with st.sidebar:
    st.header("🧠 Mémoire Vive Jarvis")
    if recent_memories:
        for m in recent_memories[:10]:
            st.caption(f"[{m.get('priority')}] {m.get('content')[:50]}...")
    else:
        st.info("Aucun souvenir enregistré.")
    if st.button("🔄 Actualiser"):
        recent_memories = get_memories(limit=20)

# Session state
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "À vos ordres, Monsieur Sezer. Jarvis est en ligne. Que souhaitez-vous ?"}]

# Affichage chat
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# --- PROCESSUS PRINCIPAL ---
if prompt := st.chat_input("Parlez à Jarvis..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Vérification si info utile
    mem_analysis = is_memory_worthy(prompt)
    if mem_analysis.get("is_worthy"):
        write_memory(prompt, priority=mem_analysis.get("priority","medium"), branch=mem_analysis.get("branch","Général"))

    # Contexte
    recent_memories = get_memories(limit=20)
    context_summary = summarize_context(recent_memories)

    # Réponse Jarvis
    with st.chat_message("assistant"):
        sys_instr = (
            f"Tu es Jarvis, assistant intelligent de Monsieur Sezer. "
            f"Voici les souvenirs récents : {context_summary}. "
            "Réponds de façon concise, intelligente, directe et pertinente. "
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
