import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json

# --- CONFIGURATION (DÉFINITIVE) ---
st.set_page_config(page_title="DELTA OS", page_icon="⚡", layout="wide")

# --- ÉTATS DE SESSION ---
if "messages" not in st.session_state: st.session_state.messages = []
if "locked" not in st.session_state: st.session_state.locked = False

# --- 🔒 LOGIQUE DE VÉRROUILLAGE PRIORITAIRE ---
if st.session_state.locked:
    # On vide l'écran visuellement
    st.empty() 
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    st.title("🔒 SYSTÈME VERROUILLÉ")
    st.subheader("Protocole de sécurité DELTA activé.")
    
    code_input = st.text_input("Veuillez entrer le code Maître :", type="password")
    
    if st.button("DÉVERROUILLER"):
        if code_input == "20082008":
            st.session_state.locked = False
            st.success("✅ Code correct. Restauration du système...")
            st.rerun()
        else:
            st.error("❌ Accès refusé.")
    
    # On utilise st.stop() pour être SÛR que rien d'autre ne s'affiche en dessous
    st.stop() 

# --- INITIALISATION FIREBASE & GROQ (Seulement si déverrouillé) ---
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

# --- GESTION DES ARCHIVES ---
res = doc_ref.get()
faits = res.to_dict().get("faits", []) if res.exists else []

with st.sidebar:
    st.title("🧠 Archives")
    if st.button("🗑️ TOUT EFFACER"):
        doc_ref.update({"faits": []})
        st.rerun()
    st.write("---")
    for i, fait in enumerate(faits):
        col1, col2 = st.columns([4, 1])
        col1.info(fait)
        if col2.button("🗑️", key=f"del_{i}"):
            faits.pop(i)
            doc_ref.update({"faits": faits})
            st.rerun()

# --- INTERFACE DE CHAT ---
st.title("⚡ DELTA OS")

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

if p := st.chat_input("Vos ordres, Monsieur ?"):
    low_p = p.lower().strip()
    
    # Commande de verrouillage
    if "verrouille-toi" in low_p or "lock" in low_p:
        st.session_state.locked = True
        st.rerun()

    st.session_state.messages.append({"role": "user", "content": p})
    with st.chat_message("user"): st.markdown(p)

    with st.chat_message("assistant"):
        instr = f"Tu es DELTA. Archives : {faits}"
        r = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": instr}] + st.session_state.messages
        )
        rep = r.choices[0].message.content
        st.markdown(rep)
        st.session_state.messages.append({"role": "assistant", "content": rep})
