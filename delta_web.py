import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64, json, re

# --- CONFIGURATION ---
GROQ_API_KEY = "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"

# --- CONNEXION ---
if not firebase_admin._apps:
    try:
        encoded = st.secrets["firebase_key"]["encoded_key"].strip()
        decoded_json = base64.b64decode(encoded).decode("utf-8")
        cred = credentials.Certificate(json.loads(decoded_json))
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Erreur : {e}")

db = firestore.client()
doc_ref = db.collection("archives").document("monsieur_sezer")
client = Groq(api_key=GROQ_API_KEY)

# --- ASPIRATION LUX (SÉCURISÉE) ---
res = doc_ref.get()
archives = res.to_dict() if res.exists else {}

# SÉCURITÉ ANTI-CRASH : Si une clé manque, on la rajoute par défaut
if "profil" not in archives: archives["profil"] = {"nom": "Monsieur Sezer", "age": None}
if "projets" not in archives: archives["projets"] = {}
if "preferences" not in archives: archives["preferences"] = {}

# --- INTERFACE ---
st.title("DELTA - Architecture Lux")

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- MOTEUR ---
if prompt := st.chat_input("Ordre..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # 1. LE FILTRE SYNAPTIQUE (Extraction JSON)
    analysis = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": "Tu es l'extracteur de Lux. Réponds uniquement en JSON pur."},
            {"role": "user", "content": f"Extrais les infos de : '{prompt}'. Format: {{'profil': {{'age': 17}}, 'projets': {{'nom': 'ia'}}}}"}
        ],
        response_format={"type": "json_object"}
    ).choices[0].message.content

    try:
        data_to_save = json.loads(analysis)
        if data_to_save and data_to_save != {}:
            doc_ref.set(data_to_save, merge=True)
            st.toast("🧬 Mémoire mise à jour")
            # Mise à jour de la mémoire locale pour la réponse
            for k, v in data_to_save.items():
                if k in archives: archives[k].update(v)
    except: pass

    # 2. RÉPONSE IA
    with st.chat_message("assistant"):
        # Utilisation de .get() pour éviter tout KeyError futur
        nom_user = archives.get("profil", {}).get("nom", "Monsieur Sezer")
        
        sys_instr = (
            f"Tu es DELTA. Créateur : {nom_user}. "
            f"MÉMOIRE : {json.dumps(archives)}. "
            "Ton : Jarvis. Précis, dévoué, concis."
        )
        
        res_ai = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": sys_instr}] + st.session_state.messages[-4:],
        ).choices[0].message.content
        
        st.markdown(res_ai)
        st.session_state.messages.append({"role": "assistant", "content": res_ai})
