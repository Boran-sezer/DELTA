import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64

# --- INITIALISATION FIREBASE ---
if not firebase_admin._apps:
    try:
        # 1. On récupère les infos de base
        creds_dict = dict(st.secrets["firebase"])
        
        # 2. On décode la clé protégée
        encoded = st.secrets["firebase_key"]["encoded_key"]
        decoded_key = base64.b64decode(encoded).decode("utf-8")
        
        # 3. On injecte la clé propre dans la config
        creds_dict["private_key"] = decoded_key
        
        cred = credentials.Certificate(creds_dict)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Erreur Mémoire (Firebase) : {e}")
        # On ne stoppe pas l'app, pour que l'IA puisse quand même répondre sans mémoire
        st.warning("DELTA fonctionne en mode 'Mémoire Courte' uniquement.")

# Connexion Groq
client = Groq(api_key="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")

st.title("⚡ DELTA SYSTEM - ONLINE")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Affichage des messages
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# Entrée utilisateur
if p := st.chat_input("Ordres ?"):
    st.session_state.messages.append({"role": "user", "content": p})
    with st.chat_message("user"):
        st.markdown(p)
    
    with st.chat_message("assistant"):
        r = client.chat.completions.create(
            model="llama-3.3-70b-versatile", 
            messages=st.session_state.messages
        )
        rep = r.choices[0].message.content
        st.markdown(rep)
        st.session_state.messages.append({"role": "assistant", "content": rep})
