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

# --- 2. LOGIQUE DE SÉCURITÉ (PRIORITÉ ABSOLUE) ---
if "verrou" not in st.session_state:
    st.session_state.verrou = False

# Fonction pour déverrouiller
def deverrouiller():
    if st.session_state.entree_code == "B2008a2020@":
        st.session_state.verrou = False
        st.toast("Accès autorisé, Monsieur Sezer.")
    else:
        st.error("Code incorrect.")

# SI VERROUILLÉ : On affiche UNIQUEMENT le cadenas et le mot de passe
if st.session_state.verrou:
    st.markdown("<h1 style='text-align:center;margin-top:100px;'>🔒</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align:center;color:#ff4b4b;'>SYSTÈME DELTA SÉCURISÉ</h3>", unsafe_allow_html=True)
    st.text_input("Code de sécurité", type="password", key="entree_code", on_change=deverrouiller)
    st.stop() # Bloque tout le reste de l'application

# --- 3. INTERFACE NORMALE ---
st.set_page_config(page_title="DELTA AI", layout="wide")

# Bouton de verrouillage rapide
c1, c2 = st.columns([0.9, 0.1])
with c1:
    st.markdown("<h1 style='color:#00d4ff;'>⚡ DELTA</h1>", unsafe_allow_html=True)
with c2:
    if st.button("LOCK"):
        st.session_state.verrou = True
        st.rerun()

# Récupération archives
res = doc_ref.get()
archives = res.to_dict().get("archives", {}) if res.exists else {}

if "messages" not in st.session_state: 
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- 4. TRAITEMENT ---
if prompt := st.chat_input("Message..."):
    # Détection immédiate du verrouillage
    if "lock" in prompt.lower() or "verrou" in prompt.lower():
        st.session_state.verrou = True
        st.rerun()

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # Analyse archivage (invisible)
    sys_analyse = f"Archives : {archives}. JSON : {{'action':'add', 'cat':'NOM', 'val':'INFO'}} ou {{'action':'none'}}"
    try:
        check = client.chat.completions.create(
            model="llama-3.1-8b-instant", 
            messages=[{"role": "system", "content": "Archiviste."}, {"role": "user", "content": sys_analyse}],
            temperature=0
        )
        match = re.search(r'\{.*\}', check.choices[0].message.content, re.DOTALL)
        if match:
            data = json.loads(match.group(0).replace("'", '"'))
            if data.get('action') == 'add':
                c, v = data.get('cat', 'Mémoire'), data.get('val')
                if v and v not in archives.get(c, []):
                    if c not in archives: archives[c] = []
                    archives[c].append(v)
                    doc_ref.set({"archives": archives})
                    st.toast("💾")
    except: pass

    # Réponse DELTA
    with st.chat_message("assistant"):
        instr = f"Tu es DELTA. Créateur : Monsieur Sezer Boran. Mémoire : {archives}. Concis."
        try:
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile", 
                messages=[{"role": "system", "content": instr}] + st.session_state.messages,
                temperature=0.3
            )
            final = resp.choices[0].message.content
        except:
            final = "Système opérationnel."
        
        st.markdown(final)
        st.session_state.messages.append({"role": "assistant", "content": final})
