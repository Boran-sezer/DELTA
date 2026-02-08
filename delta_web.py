import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64, json, re
from datetime import datetime

# --- CONFIGURATION ---
GROQ_API_KEY = "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"

# --- CONNEXION FIREBASE (ARCHITECTURE LUX) ---
if not firebase_admin._apps:
    try:
        encoded = st.secrets["firebase_key"]["encoded_key"].strip()
        decoded_json = base64.b64decode(encoded).decode("utf-8")
        cred = credentials.Certificate(json.loads(decoded_json))
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Erreur Système : {e}")

db = firestore.client()
doc_ref = db.collection("archives").document("monsieur_sezer")
client = Groq(api_key=GROQ_API_KEY)

# --- CHARGEMENT DU CERVEAU ---
res = doc_ref.get()
# Structure de données identique à Lux
cerveau = res.to_dict() if res.exists else {
    "identite": {"nom": "Monsieur Sezer"},
    "projets": {},
    "preferences": {},
    "historique_court": []
}

# --- INTERFACE ÉPURÉE ---
st.set_page_config(page_title="DELTA", layout="wide")
st.markdown("<style>button {display:none;} #MainMenu, footer, header {visibility:hidden;} .stChatMessage {border-radius:10px;}</style>", unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- CYCLE DE TRAITEMENT ---
if prompt := st.chat_input("En attente d'ordres..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # 1. LE TRIEUR (LOGIQUE LUX)
    # On utilise le modèle 8B pour classer l'info sans ralentir le système
    extraction_prompt = (
        f"Tu es le Trieur de DELTA. Analyse : '{prompt}'. "
        "Classe les nouvelles infos dans ce JSON uniquement si elles sont certaines : "
        "{'identite': {}, 'projets': {}, 'preferences': {}}. "
        "Si rien n'est nouveau, réponds 'NEANT'."
    )
    
    trieur_res = client.chat.completions.create(
        model="llama-3.1-8b-instant", 
        messages=[{"role": "user", "content": extraction_prompt}]
    ).choices[0].message.content

    if "NEANT" not in trieur_res:
        match = re.search(r'\{.*\}', trieur_res, re.DOTALL)
        if match:
            try:
                nouvelles_infos = json.loads(match.group().replace("'", '"'))
                # Fusion intelligente (Merge) dans Firestore
                for cle in ["identite", "projets", "preferences"]:
                    if nouvelles_infos.get(cle):
                        cerveau[cle].update(nouvelles_infos[cle])
                
                # Mise à jour de l'historique court (5 derniers messages)
                cerveau["historique_court"].append(prompt)
                cerveau["historique_court"] = cerveau["historique_court"][-5:]
                
                doc_ref.set(cerveau, merge=True)
            except: pass

    # 2. LA RÉPONSE (LOGIQUE JARVIS)
    with st.chat_message("assistant"):
        # On injecte la mémoire structurée dans le système
        sys_instr = (
            f"Tu es DELTA, l'IA de Monsieur Sezer. "
            f"IDENTITÉ : {cerveau['identite']}. "
            f"PROJETS : {cerveau['projets']}. "
            f"PRÉFÉRENCES : {cerveau['preferences']}. "
            "Ton : Majordome, distingué, extrêmement concis. "
            "Ne répète pas les infos si ce n'est pas nécessaire."
        )
        
        full_res = ""
        stream = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": sys_instr}] + st.session_state.messages[-6:],
            stream=True
        )
        placeholder = st.empty()
        for chunk in stream:
            if chunk.choices[0].delta.content:
                full_res += chunk.choices[0].delta.content
                placeholder.markdown(full_res + "▌")
        placeholder.markdown(full_res)
        st.session_state.messages.append({"role": "assistant", "content": full_res})
