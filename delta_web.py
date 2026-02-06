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

# --- 2. ÉTATS DE SESSION ---
if "messages" not in st.session_state: 
    st.session_state.messages = [{"role": "assistant", "content": "Système DELTA paré, Monsieur Sezer. ⚡"}]

# --- 3. INTERFACE & SIDEBAR ---
st.set_page_config(page_title="DELTA", layout="wide")
st.markdown("<h1 style='color:#00d4ff;'>⚡ DELTA</h1>", unsafe_allow_html=True)

res = doc_ref.get()
archives = res.to_dict().get("archives", {}) if res.exists else {}

with st.sidebar:
    st.title("📂 Archives de Monsieur Sezer")
    if archives:
        for partie, infos in archives.items():
            with st.expander(f"📁 {partie}"):
                for i in infos:
                    st.write(f"• {i}")
    else:
        st.info("Archives vides.")

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# --- 4. LOGIQUE MULTI-ACTION (VERSION CORRIGÉE) ---
if prompt := st.chat_input("Ordres pour vos archives..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    analyse_prompt = (
        f"Archives actuelles : {archives}. "
        f"Ordre : '{prompt}'. "
        "Tu es un terminal de données. Réponds UNIQUEMENT par un objet JSON. "
        "1. Ajouter info: {'action': 'add', 'partie': 'nom', 'info': 'texte'} "
        "2. Renommer catégorie: {'action': 'rename_cat', 'old': 'nom', 'new': 'nom'} "
        "3. Supprimer catégorie: {'action': 'delete_partie', 'target': 'nom'} "
        "4. Supprimer ligne: {'action': 'delete_info', 'partie': 'nom', 'info': 'texte'} "
        "5. Modifier ligne: {'action': 'update', 'partie': 'nom', 'old': 'vieux', 'new': 'neuf'} "
        "Sinon, réponds 'NON'."
    )
    
    try:
        check = client.chat.completions.create(
            model="llama-3.1-8b-instant", 
            messages=[{"role": "system", "content": "Tu es un extracteur JSON pur."}, {"role": "user", "content": analyse_prompt}],
            temperature=0
        )
        cmd_text = check.choices[0].message.content.strip()
        json_match = re.search(r'(\{.*\})', cmd_text, re.DOTALL)
        
        if json_match:
            data = json.loads(json_match.group(1).replace("'", '"'))
            action = data.get('action')
            modif = False

            # AJOUT
            if action == 'add':
                p = data.get('partie', 'Général')
                if p not in archives: archives[p] = []
                archives[p].append(data.get('info'))
                modif = True
            
            # RENOMMER CATÉGORIE
            elif action == 'rename_cat':
                old_n, new_n = data.get('old'), data.get('new')
                if old_n in archives:
                    archives[new_n] = archives.pop(old_n)
                    modif = True

            # SUPPRIMER PARTIE
            elif action == 'delete_partie':
                target = data.get('target', '').lower()
                for k in list(archives.keys()):
                    if target in k.lower():
                        del archives[k]
                        modif = True
            
            # SUPPRIMER INFO
            elif action == 'delete_info':
                p, info = data.get('partie'), data.get('info')
                if p in archives and info in archives[p]:
                    archives[p].remove(info)
                    modif = True
            
            # MODIFIER INFO
            elif action == 'update':
                p, old, new = data.get('partie'), data.get('old'), data.get('new')
                if p in archives and old in archives[p]:
                    idx = archives[p].index(old)
                    archives[p][idx] = new
                    modif = True

            if modif:
                doc_ref.set({"archives": archives})
                st.toast("✅ Mise à jour effectuée.")
                time.sleep(0.4)
                st.rerun()
    except Exception as e:
        st.error(f"Erreur : {e}")

    # B. RÉPONSE DE DELTA
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_raw = ""
        instr = f"Tu es DELTA, l'IA de Monsieur Sezer. Archives : {archives}. Ne dis jamais 'accès autorisé'."
        
        try:
            stream = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "system", "content": instr}] + st.session_state.messages, stream=True)
            for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    full_raw += content
                    placeholder.markdown(full_raw + "▌")
        except:
            # Secours si le gros modèle bloque
            resp = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "system", "content": instr}] + st.session_state.messages)
            full_raw = resp.choices[0].message.content
        
        placeholder.markdown(full_raw)
        st.session_state.messages.append({"role": "assistant", "content": full_raw})
