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
    low_p = p.lower().strip()
    
    # 🛠️ LOGIQUE D'ARCHIVAGE INTELLIGENTE
    keywords = ["archive", "mémorise", "enregistre", "souviens-toi"]
    # On n'archive QUE si un mot-clé est présent ET que "supprime/efface" n'est PAS là
    if any(word in low_p for word in keywords) and not any(anti in low_p for anti in ["supprime", "efface", "vire"]):
        info = p
        for word in keywords: info = info.replace(word, "").replace(":", "").strip()
        
        if info:
            faits.append(info)
            doc_ref.update({"faits": faits})
            st.toast(f"Mémoire mise à jour : {info}")

    st.session_state.messages.append({"role": "user", "content": p})
    with st.chat_message("user"): st.markdown(p)

    with st.chat_message("assistant"):
        instr = (
            "Tu es DELTA, le majordome de Monsieur Boran. "
            "TU AS LA CAPACITÉ DE STOCKER DES DONNÉES via Firebase. "
            f"Archives actuelles : {faits}. "
            "Si Monsieur veut supprimer une archive, dis-lui d'utiliser les boutons 🗑️ dans la barre latérale. "
            "Ne dis JAMAIS que tu ne peux pas mémoriser. Sois bref."
        )
        
        r = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": instr}] + st.session_state.messages
        )
        rep = r.choices[0].message.content
        st.markdown(rep)
        st.session_state.messages.append({"role": "assistant", "content": rep})
        
        # Rerun seulement si on a archivé quelque chose
        if any(word in low_p for word in keywords) and not any(anti in low_p for anti in ["supprime", "efface"]):
            st.rerun()
