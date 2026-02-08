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

# --- INITIALISATION GROQ ---
client = Groq(api_key="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")

# --- UTILITAIRES MÉMOIRE ---
def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def is_memory_worthy(text: str) -> dict:
    """Détermine si l'info mérite d'être mémorisée"""
    blacklist = ["salut", "ok", "mdr", "lol", "?", "oui", "non"]
    if len(text.strip()) < 15 or any(word in text.lower() for word in blacklist):
        return {"is_worthy": False, "priority": "low", "branch": "Memory"}
    try:
        analysis = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Tu es Jarvis. Réponds en JSON : {'is_worthy': bool, 'priority': 'high|medium|low', 'branch':'nom'}"},
                {"role": "user", "content": text}
            ],
            response_format={"type": "json_object"}
        )
        res = json.loads(analysis.choices[0].message.content)
        # Si LLM propose une branche trop vague ou inutile, mettre "Memory"
        if not res.get("branch") or res.get("branch").lower() in ["général", "default"]:
            res["branch"] = "Memory"
        return res
    except:
        return {"is_worthy": False, "priority": "low", "branch": "Memory"}

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
    memory_ref = db.collection("memory")
    for branch_doc in memory_ref.stream():  # pour chaque branche/personne
        souvenirs_ref = branch_doc.reference.collection("souvenirs")
        for doc in souvenirs_ref.stream():
            data = doc.to_dict()
            created_at = data.get("created_at")
            if created_at and hasattr(created_at, "timestamp"):
                created_at = created_at.to_datetime()
            elif not created_at:
                continue
            if data.get("priority","low")=="low" and created_at < cutoff:
                souvenirs_ref.document(doc.id).delete()

def get_memories(branch_name, limit=50):
    if not db: return []
    try:
        docs = db.collection("memory").document(branch_name).collection("souvenirs") \
                 .order_by("created_at", direction=firestore.Query.DESCENDING) \
                 .limit(limit).stream()
        return [d.to_dict() for d in docs]
    except:
        return []

def summarize_context(branch_name, max_chars=500):
    memories = get_memories(branch_name, limit=50)
    if not memories: return "Aucun souvenir récent."
    memories = sorted(memories, key=lambda x: {"high":3,"medium":2,"low":1}.get(x.get("priority","medium")), reverse=True)
    merged = merge_similar_memories(memories)
    lines = [f"[{m.get('priority')}] {m.get('content')}" for m in merged]
    return "\n".join(lines)[:max_chars]

# --- INTERFACE ---
st.set_page_config(page_title="DELTA AGI Ultra", page_icon="🌐", layout="wide")
st.title("🌐 DELTA : Jarvis Ultra-Intelligent")

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "À vos ordres. Le système est parfaitement synchronisé."}]

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# --- PROCESSUS PRINCIPAL ---
if prompt := st.chat_input("Commandez Jarvis..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Analyse mémoire
    mem_analysis = is_memory_worthy(prompt)
    branch_name = mem_analysis.get("branch", "Memory")  # Branche par défaut = Memory
    doc_hash = hash_text(prompt)

    # Écriture silencieuse uniquement si info utile
    if db and mem_analysis.get("is_worthy"):
        try:
            db.collection("memory").document(branch_name).collection("souvenirs").document(doc_hash).set({
                "content": prompt,
                "content_hash": doc_hash,
                "priority": mem_analysis.get("priority","medium"),
                "branch": branch_name,
                "created_at": datetime.utcnow()
            }, merge=True)
        except:
            pass

    cleanup_old_memories()  # Nettoyage automatique

    # Réponse Jarvis
    with st.chat_message("assistant"):
        ctx = summarize_context(branch_name)
        sys_instr = f"Tu es Jarvis. Contexte: {ctx}. Sois concis, intelligent et bluffant."
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": sys_instr}] + st.session_state.messages[-5:]
            ).choices[0].message.content
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
        except:
            st.session_state.messages.append({"role": "assistant", "content": "Erreur interne."})
