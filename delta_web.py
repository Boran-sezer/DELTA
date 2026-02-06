import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json
import time

# --- 1. CONFIGURATION ---
CODE_ACT = "20082008"
CODE_MASTER = "B2008a2020@"

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

# --- 2. ÉTATS ---
if "messages" not in st.session_state: 
    st.session_state.messages = [{"role": "assistant", "content": "DELTA prêt. ⚡"}]
if "locked" not in st.session_state: st.session_state.locked = False
if "ask_auth" not in st.session_state: st.session_state.ask_auth = False

# --- 3. MÉMOIRE ---
res = doc_ref.get()
data = res.to_dict() if res.exists else {"faits": []}
faits = data.get("faits", [])

# --- 4. SÉCURITÉ ---
if st.session_state.locked:
    st.error("🚨 SYSTÈME VERROUILLÉ")
    if st.text_input("CODE MAÎTRE :", type="password") == CODE_MASTER:
        st.session_state.locked = False
        st.rerun()
    st.stop()

# --- 5. FONCTION DE RÉPONSE ---
def reponse_delta(prompt, special_instr=None):
    instr = special_instr if special_instr else f"Tu es DELTA, majordome de Monsieur SEZER. Ultra-concis. Archives : {faits}. Si info apprise: ACTION_ARCHIVE: [info]"
    
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_raw, displayed = "", ""
        
        stream = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": instr}] + st.session_state.messages,
            stream=True
        )
        
        for chunk in stream:
            content = chunk.choices[0].delta.content
            if content:
                full_raw += content
                if "ACTION_ARCHIVE" in full_raw: break
                for char in content:
                    displayed += char
                    placeholder.markdown(displayed + "▌")
                    time.sleep(0.01)
        
        clean = full_raw.split("ACTION_ARCHIVE")[0].strip()
        placeholder.markdown(clean)
        st.session_state.messages.append({"role": "assistant", "content": clean})
        
        # Archivage silencieux
        if "ACTION_ARCHIVE:" in full_raw:
            info = full_raw.split("ACTION_ARCHIVE:")[1].strip()
            if info not in faits:
                faits.append(info)
                doc_ref.set({"faits": faits}, merge=True)

# --- 6. INTERFACE ---
st.markdown("<h1 style='color:#00d4ff;'>⚡ DELTA</h1>", unsafe_allow_html=True)

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# Si une authentification est en cours
if st.session_state.ask_auth:
    with st.chat_message("assistant"):
        st.warning("🔒 Identification requise.")
        code_input = st.text_input("CODE :", type="password")
        if st.button("CONFIRMER"):
            if code_input == CODE_ACT:
                st.session_state.ask_auth = False
                # On déclenche l'affichage immédiatement
                reponse_delta("Affiche les archives", special_instr=f"Tu es DELTA. Liste les archives suivantes sans blabla : {faits}")
                st.rerun()
            else:
                st.error("Code erroné.")
    st.stop()

# Saisie standard
if prompt := st.chat_input("Ordres ?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.rerun()

# Logique de traitement après envoi du message
if st.session_state.messages[-1]["role"] == "user":
    last_prompt = st.session_state.messages[-1]["content"].lower()
    
    if "verrouille" in last_prompt:
        st.session_state.locked = True
        st.rerun()
    
    if any(w in last_prompt for w in ["archive", "mémoire"]):
        st.session_state.ask_auth = True
        st.rerun()
    else:
        reponse_delta(last_prompt)
        st.rerun()
