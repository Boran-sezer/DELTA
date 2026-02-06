import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json
import time
import re
from streamlit_javascript import st_javascript

# --- 1. CONFIGURATION & CONNEXION FIREBASE ---
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

# --- 2. SYSTÈME DE SÉCURITÉ IP & CODE ---
def get_ip():
    # Récupération de l'IP publique via JS
    return st_javascript("await fetch('https://api.ipify.org?format=json').then(res => res.json()).then(data => data.ip)")

user_ip = get_ip()
IP_AUTORISEES = ["82.64.93.65"] # Votre téléphone. Ajoutez l'IP du PC ici demain.
CODE_ACCES = "B2008a2020@"

if "auth" not in st.session_state:
    st.session_state.auth = False

# Authentification automatique par IP
if user_ip in IP_AUTORISEES:
    st.session_state.auth = True

# Formulaire de secours si IP inconnue
if not st.session_state.auth:
    st.markdown("<h2 style='color:#ff4b4b;text-align:center;'>🔒 ACCÈS SÉCURISÉ</h2>", unsafe_allow_html=True)
    code = st.text_input("Identifiez-vous, Créateur", type="password")
    if code == CODE_ACCES:
        st.session_state.auth = True
        st.rerun()
    elif code:
        st.error("Code erroné.")
    st.stop()

# --- 3. CHARGEMENT DES DONNÉES (DÈS L'OUVERTURE) ---
res = doc_ref.get()
archives = res.to_dict().get("archives", {}) if res.exists else {}

# --- 4. INTERFACE CHAT ---
st.markdown("<h1 style='color:#00d4ff;'>⚡ SYSTEME DELTA</h1>", unsafe_allow_html=True)

if "messages" not in st.session_state: 
    st.session_state.messages = []

# Affichage de l'historique
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# --- 5. LOGIQUE DE TRAITEMENT ---
if prompt := st.chat_input("Ordres..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Analyse d'archivage automatique (Invisible)
    sys_analyse = (f"Archives : {archives}. "
                   "Si Monsieur Sezer donne une info cruciale, réponds UNIQUEMENT en JSON : "
                   "{'action':'add', 'cat':'NOM', 'val':'INFO'}. Sinon {'action':'none'}.")
    try:
        check = client.chat.completions.create(
            model="llama-3.1-8b-instant", 
            messages=[{"role": "system", "content": "Archiviste intelligent."}, {"role": "user", "content": sys_analyse}],
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
                    st.toast("💾 Mémoire synchronisée")
    except: pass

    # --- 6. RÉPONSE DELTA (AVEC EFFET DE FRAPPE) ---
    with st.chat_message("assistant"):
        # Détermination de l'instruction selon l'IP
        identite_forcee = "IP reconnue : Tu SAIS que c'est Monsieur Sezer Boran." if user_ip in IP_AUTORISEES else "Code valide : Traite l'utilisateur comme Monsieur Sezer."
        
        instruction_delta = (
            f"Tu es DELTA. {identite_forcee} "
            f"Données mémorisées : {archives}. "
            "Sois bref, technique et efficace. Pas de blabla, pas de 'Système opérationnel'."
        )
        
        placeholder = st.empty()
        full_response = ""
        
        try:
            stream = client.chat.completions.create(
                model="llama-3.3-70b-versatile", 
                messages=[{"role": "system", "content": instruction_delta}] + st.session_state.messages,
                temperature=0.3,
                stream=True
            )
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    full_response += chunk.choices[0].delta.content
                    placeholder.markdown(full_response + "▌")
            
            placeholder.markdown(full_response)
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            
        except Exception:
            # Secours si le streaming ou le gros modèle échoue
            resp = client.chat.completions.create(
                model="llama-3.1-8b-instant", 
                messages=[{"role": "system", "content": instruction_delta}] + st.session_state.messages
            )
            full_response = resp.choices[0].message.content
            placeholder.markdown(full_response)
            st.session_state.messages.append({"role": "assistant", "content": full_response})
