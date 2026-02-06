import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json
import time
import re

# --- 1. CONNEXION FIREBASE ---
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

# --- 2. RECUPÉRATION DES DONNÉES ---
res = doc_ref.get()
archives = res.to_dict().get("archives", {}) if res.exists else {}

# --- 3. INTERFACE MINIMALISTE ---
st.set_page_config(page_title="DELTA AI", layout="wide")
st.markdown("<h1 style='color:#00d4ff;'>⚡ SYSTEME DELTA</h1>", unsafe_allow_html=True)
# Suppression de toute barre latérale ou expander d'archives ici

if "messages" not in st.session_state: 
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- 4. ANALYSE ET ARCHIVAGE DISCRET ---
if prompt := st.chat_input("Message pour DELTA..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    sys_analyse = (
        f"Archives : {archives}. "
        "Analyseur DELTA. Archive uniquement les faits cruciaux. "
        "Réponds UNIQUEMENT en JSON : {'action':'add', 'cat':'NOM', 'val':'INFO'} ou {'action':'none'}"
    )
    
    try:
        check = client.chat.completions.create(
            model="llama-3.1-8b-instant", 
            messages=[{"role": "system", "content": "Archiviste invisible."}, {"role": "user", "content": sys_analyse}],
            temperature=0
        )
        match = re.search(r'\{.*\}', check.choices[0].message.content, re.DOTALL)
        if match:
            data = json.loads(match.group(0).replace("'", '"'))
            if data.get('action') == 'add':
                c, v = data.get('cat', 'Général'), data.get('val')
                if v and v not in archives.get(c, []):
                    if c not in archives: archives[c] = []
                    archives[c].append(v)
                    doc_ref.set({"archives": archives})
                    # On ne met qu'un petit toast discret pour confirmer l'action
                    st.toast("💾")
                    time.sleep(0.2)
    except: pass

    # --- 5. RÉPONSE ---
    with st.chat_message("assistant"):
        instruction_delta = (
            f"Tu es DELTA. Créateur : Monsieur Sezer Boran. "
            f"Tu as accès à ces données en mémoire : {archives}. "
            "Sois extrêmement concis et efficace. Pas de blabla inutile."
        )
        try:
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile", 
                messages=[{"role": "system", "content": instruction_delta}] + st.session_state.messages,
                temperature=0.3
            )
            final = resp.choices[0].message.content
        except:
            resp = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "system", "content": instruction_delta}] + st.session_state.messages)
            final = resp.choices[0].message.content
        
        st.markdown(final)
        st.session_state.messages.append({"role": "assistant", "content": final})
