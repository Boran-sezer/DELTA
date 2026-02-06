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

# --- 2. RECUPÉRATION DES ARCHIVES ---
res = doc_ref.get()
archives = res.to_dict().get("archives", {}) if res.exists else {}

# --- 3. INTERFACE ---
st.set_page_config(page_title="DELTA ZERO", layout="wide")
st.markdown("<h1 style='color:#00d4ff;'>⚡ DELTA ZERO</h1>", unsafe_allow_html=True)

with st.sidebar:
    st.title("📂 Archives")
    if archives:
        for cat, items in archives.items():
            with st.expander(f"📁 {cat}"):
                for i in items: st.write(f"• {i}")
    else:
        st.info("Archives vides.")

if "messages" not in st.session_state: 
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- 4. MOTEUR DE TRAITEMENT ---
if prompt := st.chat_input("Ordre..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    sys_prompt = (
        f"Archives : {archives}. "
        "Réponds UNIQUEMENT en JSON : "
        "{'action':'add', 'cat':'nom', 'val':'texte'} "
        "{'action':'rename', 'old':'nom', 'new':'nom'} "
        "{'action':'delete_cat', 'cat':'nom'} "
        "{'action':'delete_val', 'cat':'nom', 'val':'texte'} "
        "Sinon {'action':'none'}"
    )
    
    try:
        check = client.chat.completions.create(
            model="llama-3.1-8b-instant", 
            messages=[{"role": "system", "content": sys_prompt}, {"role": "user", "content": prompt}],
            temperature=0
        )
        
        match = re.search(r'\{.*\}', check.choices[0].message.content, re.DOTALL)
        if match:
            data = json.loads(match.group(0).replace("'", '"'))
            action = data.get('action')
            modif = False

            if action == 'add':
                c, v = data.get('cat', 'Général'), data.get('val')
                if v:
                    if c not in archives: archives[c] = []
                    archives[c].append(v)
                    modif = True
            elif action == 'rename':
                o, n = data.get('old'), data.get('new')
                if o in archives:
                    archives[n] = archives.pop(o)
                    modif = True
            elif action == 'delete_cat':
                c = data.get('cat')
                if c in archives:
                    del archives[c]
                    modif = True
            elif action == 'delete_val':
                c, v = data.get('cat'), data.get('val')
                if c in archives and v in archives[c]:
                    archives[c].remove(v)
                    modif = True

            if modif:
                doc_ref.set({"archives": archives})
                st.toast("🗑️ Mise à jour effectuée")
                time.sleep(0.5)
                st.rerun()
    except: pass

    # --- 5. RÉPONSE DE DELTA (AVEC ANTI-CRASH) ---
    with st.chat_message("assistant"):
        instr = f"Tu es DELTA. Archives : {archives}. Réponds brièvement à Monsieur Sezer. Ne dis jamais 'Accès autorisé'."
        
        try:
            # On essaye le gros modèle
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile", 
                messages=[{"role": "system", "content": instr}] + st.session_state.messages
            )
            final = resp.choices[0].message.content
        except Exception:
            # SI RATE LIMIT (OU AUTRE) : On bascule sur le modèle rapide sans crash
            resp = client.chat.completions.create(
                model="llama-3.1-8b-instant", 
                messages=[{"role": "system", "content": instr}] + st.session_state.messages
            )
            final = resp.choices[0].message.content
        
        st.markdown(final)
        st.session_state.messages.append({"role": "assistant", "content": final})
