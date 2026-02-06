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
client = Groq(api_key="VOTRE_CLE_GROQ")

# --- 2. ÉTATS DE SESSION ---
if "messages" not in st.session_state: 
    st.session_state.messages = [{"role": "assistant", "content": "À vos ordres, Monsieur Sezer. ⚡"}]

# --- 3. INTERFACE ---
st.markdown("<h1 style='color:#00d4ff;'>⚡ DELTA IA</h1>", unsafe_allow_html=True)

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# --- 4. TRAITEMENT ---
if prompt := st.chat_input("Vos instructions, Monsieur Sezer ?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # A. TRI AUTOMATIQUE (Discret)
    res = doc_ref.get()
    archives = res.to_dict().get("archives", {}) if res.exists else {}

    # B. RÉPONSE DE DELTA (Plus sobre)
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_raw, displayed = "", ""
        
        instr = (
            f"Tu es DELTA, le majordome de Monsieur Sezer. "
            f"Archives : {archives}. "
            "IMPORTANT : Ne m'appelle JAMAIS 'Créateur', utilise uniquement 'Monsieur Sezer'. "
            "Si on te demande de montrer les archives, fais-le directement sans dire 'accès autorisé' ou 'vérification terminée'. "
            "Sois efficace, élégant et concis."
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
