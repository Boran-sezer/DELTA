import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import os

# Connexion directe via le fichier JSON
if not firebase_admin._apps:
    try:
        # On pointe directement vers le fichier que vous venez de créer
        path = os.path.join(os.getcwd(), "service_account.json")
        cred = credentials.Certificate(path)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Erreur d'accès au fichier : {e}")
        st.stop()

db = firestore.client()
client = Groq(api_key="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")

st.title("⚡ DELTA SYSTEM V3")

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

if p := st.chat_input("Ordres ?"):
    st.session_state.messages.append({"role": "user", "content": p})
    with st.chat_message("user"): st.markdown(p)
    with st.chat_message("assistant"):
        r = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=st.session_state.messages)
        rep = r.choices[0].message.content
        st.markdown(rep)
        st.session_state.messages.append({"role": "assistant", "content": rep})
