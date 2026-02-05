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
client = Groq(api_key="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")

# --- ÉTATS DE SESSION ---
if "messages" not in st.session_state: st.session_state.messages = []

# --- CHARGEMENT DES ARCHIVES ---
res = doc_ref.get()
data = res.to_dict() if res.exists else {"faits": []}
faits = data.get("faits", [])

# --- SIDEBAR (ARCHIVES) ---
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
    st.session_state.messages.append({"role": "user", "content": p})
    with st.chat_message("user"): st.markdown(p)

    with st.chat_message("assistant"):
        # 🛡️ INSTRUCTION SYSTÈME ÉVOLUÉE
        # On explique à l'IA comment répondre si elle doit archiver quelque chose
        instr = (
            "Tu es DELTA, le majordome de Monsieur Boran. "
            f"Archives actuelles : {faits}. "
            "IMPORTANT : Si Monsieur te demande CLAIREMENT d'archiver ou de mémoriser une information, "
            "réponds EXCLUSIVEMENT en commençant ta réponse par le mot-clé : 'ACTION_ARCHIVE: ' suivi de l'info à retenir. "
            "Si Monsieur parle juste de ses archives ou demande une suppression, réponds normalement sans le mot-clé."
        )
        
        r = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": instr}] + st.session_state.messages
        )
        
        rep = r.choices[0].message.content
        
        # --- TRAITEMENT DE L'ACTION D'ARCHIVAGE ---
        if "ACTION_ARCHIVE:" in rep:
            # On sépare le mot-clé de la réponse pour l'utilisateur
            partie_archive = rep.split("ACTION_ARCHIVE:")[1].split("\n")[0].strip()
            faits.append(partie_archive)
            doc_ref.update({"faits": faits})
            
            # Nettoyage de la réponse pour ne pas afficher le code technique à Monsieur
            propre = rep.replace(f"ACTION_ARCHIVE: {partie_archive}", "").strip()
            if not propre: propre = f"C'est fait Monsieur, j'ai archivé : {partie_archive} 🗄️"
            
            st.markdown(propre)
            st.session_state.messages.append({"role": "assistant", "content": propre})
            st.rerun()
        else:
            st.markdown(rep)
            st.session_state.messages.append({"role": "assistant", "content": rep})
