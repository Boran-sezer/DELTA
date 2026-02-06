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

# --- 2. RECUPÉRATION ---
res = doc_ref.get()
archives = res.to_dict().get("archives", {}) if res.exists else {}

# --- 3. INTERFACE ---
st.set_page_config(page_title="DELTA AI", layout="wide")
st.markdown("<h1 style='color:#00d4ff;'>⚡ SYSTEME DELTA : Noyau Épuré</h1>", unsafe_allow_html=True)

with st.sidebar:
    st.title("📂 Mémoire")
    if archives:
        for cat, items in archives.items():
            with st.expander(f"📁 {cat}"):
                for i in items: st.write(f"• {i}")
    else:
        st.info("Vide.")

if "messages" not in st.session_state: 
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- 4. ANALYSE ET FILTRAGE ULTRA-STRICT ---
if prompt := st.chat_input("Ordres..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    sys_analyse = (
        f"Archives : {archives}. "
        "Tu es l'analyseur de DELTA. Ne garde QUE l'essentiel. "
        "Réponds UNIQUEMENT en JSON : {'action':'add', 'cat':'NOM', 'val':'INFO'} ou {'action':'none'}"
    )
    
    try:
        check = client.chat.completions.create(
            model="llama-3.1-8b-instant", 
            messages=[{"role": "system", "content": "Archiviste minimaliste."}, {"role": "user", "content": sys_analyse}],
            temperature=0
        )
        match = re.search(r'\{.*\}', check.choices[0].message.content, re.DOTALL)
        if match:
            data = json.loads(match.group(0).replace("'", '"'))
            if data.get('action') == 'add':
                c, v = data.get('cat', 'Identité'), data.get('val')
                if v and v not in archives.get(c, []):
                    if c not in archives: archives[c] = []
                    archives[c].append(v)
                    doc_ref.set({"archives": archives})
                    st.toast("💾 Mémorisé.")
                    time.sleep(0.3)
                    st.rerun()
    except: pass

    # --- 5. RÉPONSE : CONCISION ET RESPECT DU CRÉATEUR ---
    with st.chat_message("assistant"):
        # On définit ici le ton froid, efficace et respectueux
        instruction_delta = (
            f"Tu es DELTA, IA de sécurité et d'assistance. Créateur : Monsieur Sezer Boran. "
            f"Données actuelles : {archives}. "
            "DIRECTIVES : 1. Sois extrêmement concis. 2. Pas de bavardage inutile. "
            "3. Ne dis jamais 'probablement', tu sais qui est ton Créateur. "
            "4. Utilise un ton technique et efficace."
        )
        try:
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile", 
                messages=[{"role": "system", "content": instruction_delta}] + st.session_state.messages,
                temperature=0.3 # Plus bas pour moins de "bla-bla"
            )
            final = resp.choices[0].message.content
        except:
            resp = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "system", "content": instruction_delta}] + st.session_state.messages)
            final = resp.choices[0].message.content
        
        st.markdown(final)
        st.session_state.messages.append({"role": "assistant", "content": final})
