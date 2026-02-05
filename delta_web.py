import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json

# --- CONFIGURATION ---
st.set_page_config(page_title="DELTA OS", page_icon="⚡")

# --- ÉTATS DE SESSION ---
if "messages" not in st.session_state: st.session_state.messages = []
if "sec_mode" not in st.session_state: st.session_state.sec_mode = "OFF"
if "essais" not in st.session_state: st.session_state.essais = 0

# --- FIREBASE ---
if not firebase_admin._apps:
    try:
        encoded = st.secrets["firebase_key"]["encoded_key"].strip()
        decoded_json = base64.b64decode(encoded).decode("utf-8")
        cred = credentials.Certificate(json.loads(decoded_json))
        firebase_admin.initialize_app(cred)
    except: st.error("Erreur Firebase")

db = firestore.client()
doc = db.collection("memoire").document("profil_monsieur")

# --- GROQ ---
client = Groq(api_key="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")

# --- INTERFACE ---
st.title("⚡ DELTA SYSTEM")
st.sidebar.write(f"SÉCURITÉ : {st.session_state.sec_mode}")
st.sidebar.write(f"ESSAIS : {st.session_state.essais}")

# Affichage chat
for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- LOGIQUE ---
if p := st.chat_input("Ordres ?"):
    st.session_state.messages.append({"role": "user", "content": p})
    with st.chat_message("user"): st.markdown(p)
    
    rep = ""

    # 1. SI LE VERROU EST ACTIVÉ
    if st.session_state.sec_mode == "ON":
        if st.session_state.essais < 3:
            if p == "20082008":
                doc.set({"faits": [], "faits_verrouilles": []})
                rep = "✅ CODE CORRECT. MÉMOIRE PURGÉE."
                st.session_state.sec_mode = "OFF"
                st.session_state.essais = 0
            else:
                st.session_state.essais += 1
                rep = f"❌ MAUVAIS CODE ({st.session_state.essais}/3)."
        else:
            if p == "B2008a2020@":
                doc.set({"faits": [], "faits_verrouilles": []})
                rep = "✅ CODE DE SECOURS ACCEPTÉ. PURGE EFFECTUÉE."
                st.session_state.sec_mode = "OFF"
                st.session_state.essais = 0
            else:
                rep = "🚨 ÉCHEC TOTAL. ANNULATION."
                st.session_state.sec_mode = "OFF"
                st.session_state.essais = 0

    # 2. DÉTECTION DE L'ORDRE
    elif "réinitialisation complète" in p.lower():
        st.session_state.sec_mode = "ON"
        st.session_state.essais = 0
        rep = "🔒 CONFIRMATION REQUISE. Entrez le code."

    # 3. RÉPONSE IA
    else:
        with st.chat_message("assistant"):
            r = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": "Tu es DELTA."}] + st.session_state.messages
            )
            rep = r.choices[0].message.content

    with st.chat_message("assistant"):
        st.markdown(rep)
        st.session_state.messages.append({"role": "assistant", "content": rep})
