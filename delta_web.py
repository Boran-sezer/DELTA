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

# Affichage immédiat des archives
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

# --- 4. LOGIQUE DE COMMANDE (VERSION RAPIDE) ---
if prompt := st.chat_input("Ex: Renomme Vert en Car..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    analyse_prompt = (
        f"Archives : {list(archives.keys())}. "
        f"Ordre : '{prompt}'. "
        "Réponds UNIQUEMENT en JSON : "
        "Si RENOMMER : {'action': 'rename', 'vieux': 'nom', 'nouveau': 'nom'} "
        "Si AJOUTER : {'action': 'add', 'partie': 'nom', 'info': 'texte'} "
        "Si SUPPRIMER : {'action': 'delete', 'cible': 'nom'} "
        "Sinon réponds 'NON'."
    )
    
    try:
        check = client.chat.completions.create(
            model="llama-3.1-8b-instant", 
            messages=[{"role": "system", "content": "Tu es un extracteur JSON."}, {"role": "user", "content": analyse_prompt}],
            temperature=0
        )
        cmd_text = check.choices[0].message.content.strip()
        json_match = re.search(r'(\{.*\})', cmd_text, re.DOTALL)
        
        if json_match:
            data = json.loads(json_match.group(1).replace("'", '"'))
            action = data.get('action')
            modif = False

            if action == 'rename':
                v, n = data.get('vieux'), data.get('nouveau')
                for k in list(archives.keys()):
                    if v.lower() in k.lower() or k.lower() in v.lower():
                        archives[n] = archives.pop(k)
                        modif = True
                        break

            elif action == 'add':
                p = data.get('partie', 'Général')
                if p not in archives: archives[p] = []
                archives[p].append(data.get('info'))
                modif = True

            elif action == 'delete':
                target = data.get('cible', '').lower()
                for k in list(archives.keys()):
                    if target in k.lower():
                        del archives[k]
                        modif = True
                        break

            if modif:
                # Mise à jour Firebase ultra-rapide
                doc_ref.set({"archives": archives})
                # On force le rechargement immédiat AVANT la réponse de l'IA
                st.rerun()
                
    except:
        pass

    # B. RÉPONSE DE DELTA (Après la mise à jour)
    with st.chat_message("assistant"):
        instr = f"Tu es DELTA, créé par Monsieur Sezer. Archives : {archives}. Sois bref."
        try:
            resp = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "system", "content": instr}] + st.session_state.messages)
            full_raw = resp.choices[0].message.content
        except:
            full_raw = "Mise à jour terminée, Monsieur Sezer. ⚡"
        
        st.markdown(full_raw)
        st.session_state.messages.append({"role": "assistant", "content": full_raw})
