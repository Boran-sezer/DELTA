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

# --- FONCTION DE DÉPLOIEMENT DE STRUCTURE ---
def deploy_structure(category, content, topic):
    try:
        # 1. Force la création du document parent (indispensable pour voir la structure)
        parent_ref = db.collection("archives").document(USER_ID)
        parent_ref.set({"status": "active", "last_update": datetime.utcnow()}, merge=True)
        
        # 2. Crée la branche dans la sous-collection
        m_hash = hashlib.sha256(content.encode()).hexdigest()
        branch_ref = parent_ref.collection("branches").document(m_hash)
        
        branch_ref.set({
            "category": category,
            "content": content,
            "topic": topic,
            "created_at": datetime.utcnow()
        })
        return True
    except Exception as e:
        st.error(f"Erreur d'écriture : {e}")
        return False

# --- INITIALISATION GROQ ---
client = Groq(api_key="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")

# --- INTERFACE ---
st.set_page_config(page_title="DELTA AGI", page_icon="🌐", layout="wide")
st.title("🌐 DELTA : Déploiement Forcé")

# Chargement des données pour la sidebar
memories = db.collection("archives").document(USER_ID).collection("branches").stream()
context_list = [m.to_dict() for m in memories]

with st.sidebar:
    st.header("🧠 Branches Lux")
    for m in context_list:
        st.write(f"📁 **{m.get('category')}** : {m.get('content')}")
    if st.button("🔄 Hard Refresh"):
        st.rerun()

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- LOGIQUE PRINCIPALE ---
if prompt := st.chat_input("Initialisation de branche..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # Analyse IA
    analysis = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "Tu es une IA forte. Réponds en JSON: {'branch': 'nom', 'topic': 'sujet'}"},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"}
    )
    
    res = json.loads(analysis.choices[0].message.content)
    
    # Exécution du déploiement
    success = deploy_structure(res.get('branch'), prompt, res.get('topic'))
    
    if success:
        st.toast("✅ Structure déployée dans Firebase.")
        
    # Réponse Jarvis
    with st.chat_message("assistant"):
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": "Tu es Jarvis. Confirme la création de la branche."}] + st.session_state.messages[-3:]
        ).choices[0].message.content
        st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})
    
    st.rerun()
