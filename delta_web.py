import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64, json, hashlib
from datetime import datetime, timedelta

# --- INITIALISATION FIREBASE (MÉTHODE SÉCURISÉE DELTA) ---
if not firebase_admin._apps:
    try:
        # Récupération et décodage de la clé depuis vos secrets Streamlit
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

# --- UTILITAIRES MÉMOIRE (VOTRE LOGIQUE ULTRA) ---
def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def is_memory_worthy(text: str) -> dict:
    """Décide si une info mérite d'être mémorisée et attribue priorité/branche"""
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
    """Récupère tous les souvenirs pour analyse et contexte"""
    memories = []
    try:
        docs = db.collection("users").document(USER_ID).collection("memory") \
                 .order_by("created_at", direction=firestore.Query.DESCENDING) \
                 .limit(limit).stream()
        memories = [d.to_dict() for d in docs]
    except:
        pass
    return memories

def merge_similar_memories(memories, similarity_threshold=0.8):
    """Fusionne les souvenirs proches pour éviter doublons (basique)"""
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
    """Supprime les souvenirs trop vieux ou peu prioritaires"""
    cutoff = datetime.utcnow() - timedelta(days=days)
    mem_ref = db.collection("users").document(USER_ID).collection("memory")
    try:
        docs = mem_ref.stream()
        for d in docs:
            data = d.to_dict()
            if data.get("priority","low")=="low" and data.get("created_at") < cutoff:
                mem_ref.document(d.id).delete()
    except:
        pass

def summarize_context(memories, max_chars=500):
    """Résumé intelligent des souvenirs récents pour le LLM"""
    memories = sorted(memories, key=lambda x: {"high":3,"medium":2,"low":1}.get(x.get("priority","medium")), reverse=True)
    merged = merge_similar_memories(memories)
    lines = [f"[{m.get('priority')}] {m.get('content')}" for m in merged]
    return "\n".join(lines)[:max_chars]

# --- INTERFACE ---
st.set_page_config(page_title="DELTA AGI Ultra", page_icon="🌐", layout="wide")
st.title("🌐 DELTA : Jarvis Ultra-Intelligent")

# Sidebar : souvenirs récents
cleanup_old_memories()  # nettoyage automatique
recent_memories = get_memories(limit=20)
with st.sidebar:
    st.header("🧠 Mémoire Vive Jarvis")
    if recent_memories:
        for m in recent_memories[:10]:
            st.caption(f"[{m.get('priority')}] {m.get('content')[:50]}...")
    else:
        st.info("Aucun souvenir enregistré.")
    if st.button("🔄 Actualiser"):
        st.rerun()

# Session state pour le chat
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "À vos ordres, Monsieur Sezer. Jarvis est en ligne. Que souhaitez-vous ?"}]

# Affichage du chat
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# --- PROCESSUS PRINCIPAL ---
if prompt := st.chat_input("Parlez à Jarvis..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 1️⃣ Vérification si info utile et mémorisation
    mem_analysis = is_memory_worthy(prompt)
    if mem_analysis.get("is_worthy"):
        branch = mem_analysis.get("branch", "Général")
        priority = mem_analysis.get("priority", "medium")
        m_hash = hash_text(prompt)
        db.collection("users").document(USER_ID).collection("memory").document(m_hash).set({
            "content": prompt,
            "content_hash": m_hash,
            "priority": priority,
            "branch": branch,
            "created_at": datetime.utcnow()
        }, merge=True)
        st.toast(f"🧬 Souvenir mémorisé dans {branch} avec priorité {priority}")

    # 2️⃣ Récupération et résumé du contexte
    recent_memories = get_memories(limit=20)
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
    
    st.rerun()
