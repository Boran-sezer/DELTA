import streamlit as st
from groq import Groq

# Configuration de la page
st.set_page_config(page_title="DELTA OS", page_icon="⚡")

# Connexion à l'IA (Groq) - Pas besoin de Firebase ici !
client = Groq(api_key="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")

st.title("⚡ DELTA SYSTEM - TEST DE SURVIE")
st.write("Si vous voyez ce message, le moteur de l'interface fonctionne ! 🚀")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Affichage des messages
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# Entrée utilisateur
if p := st.chat_input("DELTA, m'entends-tu ?"):
    st.session_state.messages.append({"role": "user", "content": p})
    with st.chat_message("user"):
        st.markdown(p)
    
    with st.chat_message("assistant"):
        try:
            r = client.chat.completions.create(
                model="llama-3.3-70b-versatile", 
                messages=st.session_state.messages
            )
            rep = r.choices[0].message.content
            st.markdown(rep)
            st.session_state.messages.append({"role": "assistant", "content": rep})
        except Exception as e:
            st.error(f"Erreur IA : {e}")
