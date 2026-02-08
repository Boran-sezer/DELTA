import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64, json, re
from datetime import datetime

# --- CONFIGURATION (Clé de Monsieur Sezer) ---
GROQ_API_KEY = "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"

# --- CONNEXION FIREBASE (ARCHITECTURE LUX) ---
if not firebase_admin._apps:
    try:
        encoded = st.secrets["firebase_key"]["encoded_key"].strip()
        decoded_json = base64.b64decode(encoded).decode("utf-8")
        cred = credentials.Certificate(json.loads(decoded_json))
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Erreur d'initialisation : {e}")

db = firestore.client()
# Lux utilise la collection 'archives' pour plus de clarté
doc_ref = db.collection("archives").document("monsieur_sezer")
client = Groq(api_key=GROQ_API_KEY)

# --- CHARGEMENT DU SYSTÈME ---
res = doc_ref.get()
# Structure de données aspirée de Lux
archives = res.to_dict() if res.exists else {
    "identite": {"nom": "Monsieur Sezer"},
    "projets": {},
    "preferences": {},
    "logs": []
}

# --- INTERFACE LUX-STYLE ---
st.set_page_config(page_title="DELTA", layout="wide")
st.markdown("<style>button {display:none;} #MainMenu, footer, header {visibility:hidden;}</style>", unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- CORE ENGINE ---
if prompt := st.chat_input("Ordre..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # 1. LE FILTRE SYNAPTIQUE (Extraction & Classement)
    # On force le modèle 8B à se comporter comme un processeur de données
    filtre_prompt = (
        f"CONTEXTE ACTUEL : {json.dumps(archives)}. "
        f"MESSAGE : '{prompt}'. "
        "MISSION : Si le message contient une info capitale (âge, nouveau projet, goût), "
        "mets à jour le JSON ci-dessus. Réponds UNIQUEMENT avec le JSON complet. "
        "Si rien n'est utile, réponds : 'STABLE'."
    )
    
    analysis = client.chat.completions.create(
        model="llama-3.1-8b-instant", 
        messages=[{"role": "system", "content": "Tu es le processeur de données de DELTA. Pas de texte, juste du JSON."},
                  {"role": "user", "content": filtre_prompt}]
    ).choices[0].message.content

    if "STABLE" not in analysis:
        match = re.search(r'\{.*\}', analysis, re.DOTALL)
        if match:
            try:
                # On aspire la nouvelle structure
                archives = json.loads(match.group().replace("'", '"'))
                # On ajoute un log de modification
                archives["logs"].append(f"MàJ: {datetime.now().strftime('%H:%M')}")
                # Sauvegarde forcée
                doc_ref.set(archives, merge=True)
                st.toast("🧬 Synapse mise à jour")
            except: pass

    # 2. GÉNÉRATION DE RÉPONSE (Le Majordome)
    with st.chat_message("assistant"):
        # On injecte toute l'archive aspirée dans le contexte du 70B
        sys_instr = (
            f"Tu es DELTA. Créateur : {archives['identite'].get('nom', 'Monsieur Sezer')}. "
            f"MÉMOIRE : {json.dumps(archives)}. "
            "TON : Jarvis. Précis, dévoué, sans fioritures. Utilise ta mémoire pour anticiper ses besoins."
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
