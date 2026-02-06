import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json

# --- 1. CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="DELTA IA", page_icon="⚡", layout="wide")

# --- 2. SYSTÈME DE SÉCURITÉ (ÉTAPE 1) ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.markdown("<h1 style='text-align:center; color:#00d4ff;'>⚡ DELTA IA SYSTEM</h1>", unsafe_allow_html=True)
    st.write("---")
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        code_input = st.text_input("IDENTIFICATION REQUISE", type="password")
        if st.button("DÉVERROUILLER"):
            if code_input == "20082008":
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("ACCÈS REFUSÉ")
    st.stop()

# --- 3. INITIALISATION SERVICES (VOS CLÉS RÉCUPÉRÉES) ---

# Firebase (Utilise vos Secrets Streamlit pour la sécurité)
if not firebase_admin._apps:
    try:
        encoded = st.secrets["firebase_key"]["encoded_key"].strip()
        decoded_json = base64.b64decode(encoded).decode("utf-8")
        cred = credentials.Certificate(json.loads(decoded_json))
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Erreur Firebase : {e}")

db = firestore.client()
doc_ref = db.collection("memoire").document("profil_monsieur")

# Groq (Votre clé gsk_... est injectée ici)
client = Groq(api_key="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")

# --- 4. CHARGEMENT DES ARCHIVES ---
res = doc_ref.get()
data = res.to_dict() if res.exists else {"faits": []}
faits = data.get("faits", [])

# --- 5. SIDEBAR (ARCHIVES) ---
with st.sidebar:
    st.title("🧠 Mémoire de DELTA")
    st.write(f"Utilisateur : **Monsieur Boran**")
    if st.button("🗑️ EFFACER TOUT"):
        doc_ref.update({"faits": []})
        st.rerun()
    st.write("---")
    for i, fait in enumerate(faits):
        st.info(fait)

# --- 6. INTERFACE DE CHAT ---
st.markdown("<h1 style='color:#00d4ff;'>⚡ DELTA IA</h1>", unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

if p := st.chat_input("Quels sont vos ordres, Monsieur ?"):
    st.session_state.messages.append({"role": "user", "content": p})
    with st.chat_message("user"):
        st.markdown(p)

    with st.chat_message("assistant"):
        # Instruction système avec intelligence d'archivage
        instr = (
            "Tu es DELTA IA, le majordome de Monsieur Boran. Tu es pro et efficace. "
            f"Archives actuelles : {faits}. "
            "RÈGLE : Si Monsieur donne une info importante, ajoute 'ACTION_ARCHIVE: [info]' à la fin."
        )
        
        r = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": instr}] + st.session_state.messages
        )
        
        rep = r.choices[0].message.content
        
        if "ACTION_ARCHIVE:" in rep:
            partie_archive = rep.split("ACTION_ARCHIVE:")[1].strip()
            if partie_archive not in faits:
                faits.append(partie_archive)
                doc_ref.update({"faits": faits})
                st.toast(f"Archive ajoutée : {partie_archive}")
            
            propre = rep.split("ACTION_ARCHIVE:")[0].strip()
            st.markdown(propre)
            st.session_state.messages.append({"role": "assistant", "content": propre})
            st.rerun()
        else:
            st.markdown(rep)
            st.session_state.messages.append({"role": "assistant", "content": rep})
            
