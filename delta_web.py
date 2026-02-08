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

# --- LOGIQUE DE STRUCTURE ---
def get_recent_memories(limit=15):
    try:
        # On cible la collection 'archives' pour créer le premier dossier
        memories = db.collection("archives").document(USER_ID).collection("branches") \
                     .order_by("created_at", direction=firestore.Query.DESCENDING) \
                     .limit(limit).stream()
        return [m.to_dict() for m in memories]
    except Exception:
        return []

# --- INITIALISATION GROQ ---
client = Groq(api_key="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")

# --- INTERFACE ---
st.set_page_config(page_title="DELTA AGI", page_icon="🌐", layout="wide")
st.title("🌐 DELTA : Déploiement de Structure")

context_list = get_recent_memories()

with st.sidebar:
    st.header("🧠 Branches Lux")
    if context_list:
        for m in context_list:
            st.write(f"📁 **{m.get('category')}** : {m.get('content')}")
    else:
        st.info("Base de données vierge. En attente d'initialisation...")

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- PROCESSUS DE CRÉATION DE BRANCHES ---
if prompt := st.chat_input("Monsieur Sezer, donnez un ordre pour initialiser les dossiers..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    try:
        # L'IA définit l'architecture de la branche
        analysis = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Tu es une IA forte. Crée une structure de dossier. Réponds en JSON: {'branch': 'nom_du_dossier', 'topic': 'sujet'}"},
                {"role": "user", "content": f"Organise cette info : {prompt}"}
            ],
            response_format={"type": "json_object"}
        )
        
        res = json.loads(analysis.choices[0].message.content)
        m_hash = hashlib.sha256(prompt.encode()).hexdigest()
        
        # CRÉATION PHYSIQUE DANS FIREBASE
        # Chemin : archives (Collection) -> monsieur_sezer (Document) -> branches (Sous-collection)
        doc_ref = db.collection("archives").document(USER_ID).collection("branches").document(m_hash)
        
        doc_ref.set({
            "category": res.get("branch", "Général"),
            "content": prompt,
            "topic": res.get("topic", "Divers"),
            "created_at": datetime.utcnow()
        })
        
        st.toast("📁 Dossier et branche créés dans Firebase.")
        
    except Exception as e:
        st.error(f"Erreur de déploiement : {e}")

    # RÉPONSE JARVIS
    with st.chat_message("assistant"):
        sys_instr = f"Tu es Jarvis. Tu viens de structurer une nouvelle branche dans Firebase pour Monsieur Sezer."
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": sys_instr}] + st.session_state.messages[-3:]
        ).choices[0].message.content
        st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})
    
    st.rerun()
