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
# Votre clé est active ici
client = Groq(api_key="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")

# --- 2. ÉTATS DE SESSION ---
if "messages" not in st.session_state: 
    st.session_state.messages = [{"role": "assistant", "content": "À vos ordres, Monsieur Sezer. ⚡"}]

# --- 3. INTERFACE ---
st.markdown("<h1 style='color:#00d4ff;'>⚡ DELTA IA</h1>", unsafe_allow_html=True)

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# --- 4. TRAITEMENT ET RÉORGANISATION ---
if prompt := st.chat_input("Vos instructions, Monsieur Sezer ?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # A. ANALYSE DE L'INTENTION
    res = doc_ref.get()
    archives = res.to_dict().get("archives", {}) if res.exists else {}

    analyse_prompt = (
        f"Archives actuelles : {archives}. "
        f"L'utilisateur dit : '{prompt}'. "
        "Si l'utilisateur veut RÉORGANISER (déplacer, renommer, supprimer), réponds UNIQUEMENT en JSON : "
        "{'action': 'rename_partie/move_info/delete_partie', 'from': '...', 'to': '...', 'info': '...'}. "
        "Si c'est une NOUVELLE info : {'action': 'add', 'partie': '...', 'info': '...'}. "
        "Sinon réponds 'NON'."
    )
    
    try:
        check = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "user", "content": analyse_prompt}])
        cmd = check.choices[0].message.content.strip()

        # B. LOGIQUE DE RÉORGANISATION
        if "{" in cmd:
            data = json.loads(cmd.replace("'", '"'))
            action = data.get('action')
            modif = False

            if action == 'add':
                p = data['partie']
                if p not in archives: archives[p] = []
                archives[p].append(data['info'])
                modif = True
            elif action == 'rename_partie':
                if data['from'] in archives:
                    archives[data['to']] = archives.pop(data['from'])
                    modif = True
            elif action == 'move_info':
                if data['from'] in archives and data['info'] in archives[data['from']]:
                    archives[data['from']].remove(data['info'])
                    if data['to'] not in archives: archives[data['to']] = []
                    archives[data['to']].append(data['info'])
                    modif = True
            elif action == 'delete_partie':
                if data['from'] in archives:
                    del archives[data['from']]
                    modif = True

            if modif:
                doc_ref.set({"archives": archives})
                st.toast(f"✅ Dossiers mis à jour")
    except: pass

    # C. RÉPONSE DE DELTA
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_raw, displayed = "", ""
        
        # Consignes strictes : Monsieur Sezer / Pas d'accès autorisé / IA décide de montrer ou non
        instr = (
            f"Tu es DELTA, le majordome de Monsieur Sezer. "
            f"Voici tes archives organisées : {archives}. "
            "1. Ne m'appelle JAMAIS 'Créateur', utilise 'Monsieur Sezer'. "
            "2. Ne dis JAMAIS 'Accès autorisé' ou 'Vérification'. "
            "3. Montre les archives ou une info spécifique UNIQUEMENT si Monsieur Sezer le demande ou si la question porte sur un fait archivé. "
            "4. Sois bref, élégant et efficace."
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
