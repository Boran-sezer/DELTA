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

# --- FONCTIONS MÉMOIRE ---
def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()

def is_memory_worthy(text: str) -> bool:
    # Blacklist simple pour filtrer le bruit
    blacklist = ["salut", "ok", "mdr", "lol", "?", "oui", "non"]
    return len(text.strip()) >= 10 and text.lower().strip() not in blacklist

def get_recent_branches(limit=10):
    """Récupère les derniers éléments de toutes les branches"""
    archives = {}
    try:
        collections = db.collection("archives").document(USER_ID).collections()
        for col in collections:
            docs = col.order_by("created_at", direction=firestore.Query.DESCENDING).limit(limit).stream()
            archives[col.id] = [d.to_dict() for d in docs]
    except:
        pass
    return archives

def summarize_context(archives, max_chars=500):
    """Condense les souvenirs pour le contexte LLM"""
    lines = []
    for branch, items in archives.items():
        for item in items:
            lines.append(f"[{branch}] {item.get('content')}")
    summary = "\n".join(lines)
    return summary[:max_chars]

# --- INTERFACE ---
st.set_page_config(page_title="DELTA AGI", page_icon="🌐", layout="wide")
st.title("🌐 DELTA : Système Jarvis Opérationnel")

archives = get_recent_branches()

with st.sidebar:
    st.header("🗂️ Branches Archives")
    if not archives:
        st.info("Aucune archive pour le moment...")
    for branch, items in archives.items():
        with st.expander(f"📁 {branch}"):
            for item in items:
                st.caption(f"• {item.get('content')[:50]}...")

# --- SESSION STATE CHAT ---
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "À vos ordres, Monsieur Sezer. Le système est en ligne. Que souhaitez-vous structurer aujourd'hui ?"}]

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# --- PROCESSUS PRINCIPAL ---
if prompt := st.chat_input("Répondez à Jarvis..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 1. ANALYSE SI MÉMOIRE UTILE ET CATÉGORISATION
    if is_memory_worthy(prompt):
        try:
            analysis = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "Tu es Jarvis, l'architecte de données. "
                                                  "Décide si une info mérite d'être mémorisée. "
                                                  "Réponds en JSON : {'branch':'NOM_BRANCHE', 'is_worthy': bool}"},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            res = json.loads(analysis.choices[0].message.content)
            if res.get("is_worthy"):
                branch_name = res.get("branch", "Général")
                m_hash = hash_text(prompt)
                db.collection("archives").document(USER_ID).collection(branch_name).document(m_hash).set({
                    "content": prompt,
                    "created_at": datetime.utcnow()
                }, merge=True)
                st.toast(f"🧬 Donnée mémorisée dans la branche {branch_name}")
        except Exception as e:
            st.warning(f"Note : Analyse de branche ignorée ({e})")

    # 2. RÉCUPÉRATION CONTEXTE POUR JARVIS
    archives = get_recent_branches()
    context_summary = summarize_context(archives)

    # 3. RÉPONSE JARVIS CONTEXTUALISÉE
    with st.chat_message("assistant"):
        sys_instr = (
            f"Tu es Jarvis. Ton créateur est Monsieur Sezer. "
            f"Voici le contexte récent des branches : {context_summary}. "
            "Réponds de manière concise, intelligente et directe, toujours prêt à servir."
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
