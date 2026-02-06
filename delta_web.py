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

# --- 2. ÉTATS DE SESSION ---
if "messages" not in st.session_state: 
    st.session_state.messages = [{"role": "assistant", "content": "DELTA opérationnel. ⚡"}]
if "locked" not in st.session_state: st.session_state.locked = False
if "pending_auth" not in st.session_state: st.session_state.pending_auth = False
if "essais" not in st.session_state: st.session_state.essais = 0

# --- 3. SÉCURITÉ LOCKDOWN (En haut car c'est un blocage total) ---
if st.session_state.locked:
    st.markdown("<h1 style='color:red;'>🚨 SYSTÈME BLOQUÉ</h1>", unsafe_allow_html=True)
    m_input = st.text_input("CODE MAÎTRE :", type="password", key="m_field")
    if st.button("🔓 RÉACTIVER"):
        if m_input == CODE_MASTER:
            st.session_state.locked = False
            st.session_state.essais = 0
            st.rerun()
    st.stop()

# --- 4. RÉCUPÉRATION MÉMOIRE ---
res = doc_ref.get()
faits = res.to_dict().get("faits", []) if res.exists else []

# --- 5. INTERFACE ---
st.markdown("<h1 style='color:#00d4ff;'>⚡ DELTA IA</h1>", unsafe_allow_html=True)

# Affichage de l'historique
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# --- 6. GESTION DE L'AUTHENTIFICATION (Placée ici pour rester en bas) ---
if st.session_state.pending_auth:
    with st.chat_message("assistant"):
        st.warning(f"🔒 Identification requise ({3 - st.session_state.essais}/3)")
        c = st.text_input("Entrez votre code :", type="password", key="auth_input")
        if st.button("VALIDER"):
            if c == CODE_ACT:
                st.session_state.pending_auth = False
                st.session_state.essais = 0
                txt = "Accès autorisé. Archives : \n\n" + "\n".join([f"- {i}" for i in faits])
                st.session_state.messages.append({"role": "assistant", "content": txt})
                st.rerun()
            else:
                st.session_state.essais += 1
                if st.session_state.essais >= 3:
                    st.session_state.locked = True
                st.rerun()
    st.stop() # Bloque l'input de chat pendant qu'on demande le code

# --- 7. TRAITEMENT DES MESSAGES ---
if prompt := st.chat_input("Vos ordres ?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    if "verrouille" in prompt.lower():
        st.session_state.locked = True
        st.rerun()

    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_raw, displayed = "", ""
        
        instr = (
            f"Tu es DELTA. Ne cite JAMAIS ces faits sans code : {faits}. "
            "Si on te demande qui tu es, ce que tu sais, ou des infos personnelles : réponds REQUIS_CODE."
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
                if "REQUIS_CODE" in full_raw:
                    st.session_state.pending_auth = True
                    break
                for char in content:
                    displayed += char
                    placeholder.markdown(displayed + "▌")
                    time.sleep(0.01)

        if st.session_state.pending_auth:
            st.rerun()
        else:
            placeholder.markdown(full_raw)
            st.session_state.messages.append({"role": "assistant", "content": full_raw})
