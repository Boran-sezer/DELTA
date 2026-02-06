import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json
import time
import re

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

# --- 2. RÉCUPÉRATION ---
res = doc_ref.get()
archives = res.to_dict().get("archives", {}) if res.exists else {}

# --- 3. INTERFACE ---
st.set_page_config(page_title="DELTA", layout="wide")
st.markdown("<h1 style='color:#00d4ff;'>⚡ DELTA</h1>", unsafe_allow_html=True)

with st.sidebar:
    st.title("📂 Archives")
    if archives:
        for cat, items in archives.items():
            with st.expander(f"📁 {cat}"):
                for i in items: st.write(f"• {i}")
    else:
        st.info("Vide.")

if "messages" not in st.session_state: 
    st.session_state.messages = [{"role": "assistant", "content": "Système DELTA paré, Monsieur Sezer. ⚡"}]

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- 4. LOGIQUE DIRECTE ---
if prompt := st.chat_input("Ordre..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # Analyse simplifiée à l'extrême
    sys_prompt = (
        "Tu es un robot JSON. Archives actuelles: " + str(list(archives.keys())) + ". "
        "Si l'user veut AJOUTER: {'action': 'add', 'cat': 'nom', 'val': 'texte'}. "
        "Si l'user veut RENOMMER dossier: {'action': 'rename', 'old': 'nom', 'new': 'nom'}. "
        "Sinon: {'action': 'none'}."
    )
    
    try:
        check = client.chat.completions.create(
            model="llama-3.1-8b-instant", 
            messages=[{"role": "system", "content": sys_prompt}, {"role": "user", "content": prompt}],
            temperature=0
        )
        # Extraction chirurgicale
        txt_res = check.choices[0].message.content
        match = re.search(r'\{.*\}', txt_res, re.DOTALL)
        
        if match:
            data = json.loads(match.group(0).replace("'", '"'))
            action = data.get('action')
            m = False

            if action == 'add':
                c, v = data.get('cat', 'Général'), data.get('val')
                if v:
                    if c not in archives: archives[c] = []
                    archives[c].append(v)
                    m = True
            elif action == 'rename':
                o, n = data.get('old'), data.get('new')
                if o in archives:
                    archives[n] = archives.pop(o)
                    m = True

            if m:
                doc_ref.set({"archives": archives})
                st.rerun() # Rafraîchissement immédiat de la barre latérale
    except: pass

    # B. RÉPONSE
    with st.chat_message("assistant"):
        instr = f"Tu es DELTA. Voici tes archives : {str(archives)}. Réponds brièvement à Monsieur Sezer."
        try:
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile", 
                messages=[{"role": "system", "content": instr}] + st.session_state.messages
            )
            final = resp.choices[0].message.content
        except: final = "Mise à jour effectuée. ⚡"
        
        st.markdown(final)
        st.session_state.messages.append({"role": "assistant", "content": final})
