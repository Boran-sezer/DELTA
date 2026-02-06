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

# --- 2. SYSTEME DE VERROUILLAGE ---
def check_password():
    def password_entered():
        if st.session_state["password"] == "VOTRE_CODE_ICI": # Remplacez par votre code
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.markdown("<h2 style='color:#00d4ff;text-align:center;'>ACCÈS RESTREINT - UNITÉ DELTA</h2>", unsafe_allow_html=True)
        st.text_input("Code d'accès requis", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.error("Code erroné.")
        st.text_input("Code d'accès requis", type="password", on_change=password_entered, key="password")
        return False
    return True

if not check_password():
    st.stop()

# --- 3. RÉCUPÉRATION DES DONNÉES ---
res = doc_ref.get()
archives = res.to_dict().get("archives", {}) if res.exists else {}

# --- 4. INTERFACE ---
st.set_page_config(page_title="DELTA AI", layout="wide")
st.markdown("<h1 style='color:#00d4ff;'>⚡ SYSTEME DELTA ACTIVE</h1>", unsafe_allow_html=True)

if "messages" not in st.session_state: 
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- 5. LOGIQUE AUTONOME ---
if prompt := st.chat_input("Commandes..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # Analyse d'archivage discrète
    sys_analyse = (f"Archives : {archives}. "
                   "Garde l'essentiel. JSON : {'action':'add', 'cat':'NOM', 'val':'INFO'} ou {'action':'none'}")
    
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

    # Réponse de DELTA
    with st.chat_message("assistant"):
        instr = (f"Tu es DELTA. Créateur : Monsieur Sezer Boran. "
                 f"Mémoire : {archives}. Sois bref et technique.")
        try:
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile", 
                messages=[{"role": "system", "content": instr}] + st.session_state.messages,
                temperature=0.3
            )
            final = resp.choices[0].message.content
        except:
            final = "Erreur de flux. Réessayez."
        
        st.markdown(final)
        st.session_state.messages.append({"role": "assistant", "content": final})
