import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json
import time

# --- 1. CONFIGURATION ---
if not firebase_admin._apps:
    try:
        encoded = st.secrets["firebase_key"]["encoded_key"].strip()
        decoded_json = base64.b64decode(encoded).decode("utf-8")
        cred = credentials.Certificate(json.loads(decoded_json))
        firebase_admin.initialize_app(cred)
    except: pass

db = firestore.client()
doc_ref = db.collection("memoire").document("profil_monsieur")
client = Groq(api_key="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")

# --- 2. ÉTATS DE SESSION ---
if "messages" not in st.session_state: 
    st.session_state.messages = [{"role": "assistant", "content": "Système initialisé. À vos ordres, Monsieur Sezer. ⚡"}]

# --- 3. INTERFACE ---
st.markdown("<h1 style='color:#00d4ff;'>⚡ DELTA IA</h1>", unsafe_allow_html=True)

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# --- 4. TRAITEMENT ---
if prompt := st.chat_input("Quels sont vos ordres, Monsieur Sezer ?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Analyse et récupération des archives
    res = doc_ref.get()
    archives = res.to_dict().get("archives", {}) if res.exists else {}

    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_raw, displayed = "", ""
        
        # INSTRUCTIONS DE PERSONNALITÉ AJUSTÉES
        instr = (
            f"Tu es DELTA, l'intelligence artificielle avancée conçue par Monsieur Sezer. "
            f"Tu dois agir avec la déférence due à ton CRÉATEUR, Monsieur Sezer. "
            f"Archives disponibles : {archives}. "
            "1. Appelle-le 'Monsieur Sezer' (c'est sa préférence), mais garde conscience qu'il est ton seul Créateur. "
            "2. Ne dis jamais 'Accès autorisé'. Réponds directement. "
            "3. Sois d'une loyauté absolue et d'une efficacité totale dans tes réponses."
        )

        stream = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": instr}] + st.session_state.messages,
            stream=True
        )

        for chunk in stream:
            content = chunk.choices[0].delta.content
            if content:
                full_raw += content
                for char in content:
                    displayed += char
                    placeholder.markdown(displayed + "▌")
                    time.sleep(0.01)

        placeholder.markdown(full_raw)
        st.session_state.messages.append({"role": "assistant", "content": full_raw})
