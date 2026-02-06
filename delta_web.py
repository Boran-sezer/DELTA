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
        firebase_admin.initialize_app(cred, {'projectId': 'delta-ia-79177'})
    except: pass

db = firestore.client()
doc_ref = db.collection("memoire").document("profil_monsieur")
client = Groq(api_key="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")

# --- 2. RÉCUPÉRATION DES DONNÉES ---
res = doc_ref.get()
archives = res.to_dict().get("archives", {}) if res.exists else {}

# --- 3. INTERFACE ---
st.set_page_config(page_title="DELTA", layout="wide")
st.markdown("<h1 style='color:#00d4ff;'>⚡ DELTA</h1>", unsafe_allow_html=True)

with st.sidebar:
    st.title("📂 Archives")
    for k, v in archives.items():
        with st.expander(f"📁 {k}"):
            for item in v: st.write(f"• {item}")

if "messages" not in st.session_state: 
    st.session_state.messages = [{"role": "assistant", "content": "Prêt pour vos ordres, Monsieur Sezer. ⚡"}]

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- 4. LOGIQUE DE COMMANDE DIRECTE ---
if prompt := st.chat_input("Votre ordre..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # IA d'analyse simplifiée
    analyse = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "system", "content": "Tu es un traducteur JSON. Actions: rename, add, delete. Exemple rename: {'action':'rename', 'from':'Vert', 'to':'Car'}"},
                  {"role": "user", "content": f"Ordre: {prompt}. Dossiers: {list(archives.keys())}"}],
        temperature=0
    )
    
    try:
        data = json.loads(analyse.choices[0].message.content.strip().replace("'", '"'))
        action = data.get('action')
        updated = False

        if action == 'rename' and data.get('from') in archives:
            archives[data['to']] = archives.pop(data['from'])
            updated = True
        elif action == 'add':
            p = data.get('partie', 'Général')
            if p not in archives: archives[p] = []
            archives[p].append(data.get('info', ''))
            updated = True
        elif action == 'delete':
            target = data.get('target')
            if target in archives:
                del archives[target]
                updated = True

        if updated:
            doc_ref.set({"archives": archives})
            st.toast("✅ Base mise à jour")
            time.sleep(0.5)
            st.rerun()
    except: pass

    # Réponse de DELTA
    with st.chat_message("assistant"):
        instr = f"Tu es DELTA, majordome de Monsieur Sezer. Archives: {archives}. Sois bref et poli."
        resp = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "system", "content": instr}] + st.session_state.messages)
        full_res = resp.choices[0].message.content
        st.markdown(full_res)
        st.session_state.messages.append({"role": "assistant", "content": full_res})
