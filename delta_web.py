import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json

# --- CONFIGURATION ---
st.set_page_config(page_title="DELTA OS", page_icon="⚡", layout="wide")

# --- INITIALISATION FIREBASE ---
if not firebase_admin._apps:
    try:
        encoded = st.secrets["firebase_key"]["encoded_key"].strip()
        decoded_json = base64.b64decode(encoded).decode("utf-8")
        cred = credentials.Certificate(json.loads(decoded_json))
        firebase_admin.initialize_app(cred)
    except: pass

db = firestore.client()
doc_ref = db.collection("memoire").document("profil_monsieur")

# --- ÉTATS DE SESSION ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- FONCTION DE PURGE TOTALE ---
def purge_totale():
    # 1. Efface Firebase
    doc_ref.set({"faits": [], "faits_verrouilles": []})
    # 2. Efface l'historique local
    st.session_state.messages = []
    st.rerun()

# --- CHARGEMENT MÉMOIRE ---
res = doc_ref.get()
faits = res.to_dict().get("faits", []) if res.exists else []

# --- SIDEBAR ---
with st.sidebar:
    st.title("🧠 Archives")
    for i, f in enumerate(faits):
        st.info(f)

# --- CHAT ---
st.title("⚡ DELTA OS")

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

if p := st.chat_input("Ordres ?"):
    # VÉRIFICATION DE L'ORDRE DE PURGE
    if p.lower().strip() == "réinitialisation complète":
        purge_totale()
    
    st.session_state.messages.append({"role": "user", "content": p})
    with st.chat_message("user"): st.markdown(p)

    # APPEL IA
    client = Groq(api_key="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")
    with st.chat_message("assistant"):
        instr = f"Tu es DELTA. Infos sur l'utilisateur : {faits}"
        r = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": instr}] + st.session_state.messages
        )
        rep = r.choices[0].message.content
        st.markdown(rep)
        st.session_state.messages.append({"role": "assistant", "content": rep})
