import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64, json, re

# --- CONFIGURATION ---
GROQ_API_KEY = "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"

# --- CONNEXION FIREBASE ---
if not firebase_admin._apps:
    try:
        encoded = st.secrets["firebase_key"]["encoded_key"].strip()
        decoded_json = base64.b64decode(encoded).decode("utf-8")
        cred = credentials.Certificate(json.loads(decoded_json))
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Erreur d'accès : {e}")

db = firestore.client()
doc_ref = db.collection("archives").document("monsieur_sezer")
client = Groq(api_key=GROQ_API_KEY)

# --- CHARGEMENT DES ARCHIVES ---
res = doc_ref.get()
archives = res.to_dict() if res.exists else {
    "profil": {"nom": "Monsieur Sezer"},
    "projets": {},
    "preferences": {}
}

# --- INTERFACE ---
st.set_page_config(page_title="DELTA", page_icon="🤖")
st.title("DELTA - Interface Terminal")

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- TRAITEMENT DES FLUX ---
if prompt := st.chat_input("En attente d'ordres..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # 1. ANALYSE SYNAPTIQUE (Extraction / Suppression)
    filtre_prompt = (
        f"ANALYSE : '{prompt}'. ARCHIVES : {json.dumps(archives)}. "
        "SI SUPPRESSION : Réponds {'action': 'delete', 'target': 'catégorie', 'key': 'clé'}. "
        "SI NOUVELLE INFO : Réponds le JSON structuré. "
        "SINON : Réponds 'STABLE'."
    )
    
    analysis = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "system", "content": "Extracteur JSON strict."},
                  {"role": "user", "content": filtre_prompt}],
        response_format={"type": "json_object"}
    ).choices[0].message.content

    try:
        cmd = json.loads(analysis)
        if cmd.get("action") == "delete":
            target, key = cmd.get("target"), cmd.get("key")
            doc_ref.update({f"{target}.{key}": firestore.DELETE_FIELD})
            st.toast(f"Protocole d'effacement terminé : {key}")
        elif cmd != {}:
            doc_ref.set(cmd, merge=True)
            st.toast("Archives mises à jour.")
    except: pass

    # 2. RÉPONSE JARVIS
    with st.chat_message("assistant"):
        nom = archives.get("profil", {}).get("nom", "Monsieur Sezer")
        sys_instr = (
            f"Tu es DELTA. Créateur : {nom}. ARCHIVES : {json.dumps(archives)}. "
            "STYLE : Jarvis. Précis, distingué, ultra-concis. Pas de phrases inutiles."
        )
        
        res_ai = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": sys_instr}] + st.session_state.messages[-4:],
        ).choices[0].message.content
        
        st.markdown(res_ai)
        st.session_state.messages.append({"role": "assistant", "content": res_ai})
