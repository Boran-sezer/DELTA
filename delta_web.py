import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json
import time
import re
from streamlit_javascript import st_javascript 

# --- 1. CONFIGURATION & FIREBASE ---
st.set_page_config(page_title="DELTA AI", layout="wide")

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

# --- 2. SÉCURITÉ AVANCÉE ---
auth_key = st_javascript("localStorage.getItem('delta_key');")
CODE_ACCES = "20082008"
CODE_MEMOIRE = "B2008a2020@"

if "auth" not in st.session_state:
    st.session_state.auth = False
if "can_view_archives" not in st.session_state:
    st.session_state.can_view_archives = False

# Reconnaissance automatique de l'appareil
if auth_key == "CLE_SPECIALE_SEZER":
    st.session_state.auth = True
    st.session_state.can_view_archives = True

# Écran de verrouillage
if not st.session_state.auth:
    st.markdown("<h2 style='color:#ff4b4b;text-align:center;'>🔒 ACCÈS SYSTÈME DELTA</h2>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        code = st.text_input("Code d'accès", type="password")
        remember = st.checkbox("Se souvenir de moi (Active l'accès aux archives)")
        
        code_confirm = ""
        if remember:
            code_confirm = st.text_input("Code de confirmation 2FA", type="password", key="confirm_code")
            
        if st.button("Lancer DELTA"):
            if code == CODE_ACCES:
                if remember:
                    if code_confirm == CODE_MEMOIRE:
                        st_javascript("localStorage.setItem('delta_key', 'CLE_SPECIALE_SEZER');")
                        st.session_state.can_view_archives = True
                        st.session_state.auth = True
                        st.rerun()
                    else:
                        st.error("Code de confirmation incorrect.")
                else:
                    st.session_state.auth = True
                    st.rerun()
            else:
                st.error("Code d'accès invalide.")
    st.stop()

# --- 3. CHARGEMENT MÉMOIRE & LOGOUT ---
res = doc_ref.get()
archives = res.to_dict().get("archives", {}) if res.exists else {}

# Barre latérale pour la déconnexion
with st.sidebar:
    if st.button("🔴 Verrouiller l'unité"):
        st_javascript("localStorage.removeItem('delta_key');")
        st.session_state.auth = False
        st.session_state.can_view_archives = False
        st.rerun()

# --- 4. INTERFACE ---
st.markdown("<h1 style='color:#00d4ff;'>⚡ SYSTEME DELTA</h1>", unsafe_allow_html=True)

if "messages" not in st.session_state: 
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- 5. LOGIQUE DE TRAITEMENT ---
if prompt := st.chat_input("Commandes..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # Commande Archive
    if "archive" in prompt.lower():
        if st.session_state.can_view_archives:
            with st.chat_message("assistant"):
                st.markdown("### 🗄️ BASE DE DONNÉES")
                for section, items in archives.items():
                    with st.expander(f"📁 {section}"):
                        for item in items: st.write(f"• {item}")
        else:
            with st.chat_message("assistant"):
                st.warning("Accès restreint aux archives.")
        st.stop()

    # Archivage automatique
    sys_analyse = (f"Archives : {archives}. Si Monsieur Sezer donne une info, "
                   "réponds en JSON : {'action':'add', 'cat':'SECTION', 'val':'INFO'}.")
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
        instruction_delta = f"Tu es DELTA. Créateur : Monsieur Sezer Boran. Mémoire : {archives}. Bref."
        placeholder = st.empty()
        full_response = ""
        try:
            stream = client.chat.completions.create(
                model="llama-3.3-70b-versatile", 
                messages=[{"role": "system", "content": instruction_delta}] + st.session_state.messages,
                temperature=0.3, stream=True
            )
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    full_response += chunk.choices[0].delta.content
                    placeholder.markdown(full_response + "▌")
            placeholder.markdown(full_response)
        except:
            placeholder.markdown("Erreur.")
        st.session_state.messages.append({"role": "assistant", "content": full_response})
