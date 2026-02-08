import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64, json

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
        st.error(f"Erreur : {e}")

db = firestore.client()
doc_ref = db.collection("archives").document("monsieur_sezer")
client = Groq(api_key=GROQ_API_KEY)

# --- CHARGEMENT ---
res = doc_ref.get()
archives = res.to_dict() if res.exists else {}

# --- INTERFACE ---
st.set_page_config(page_title="DELTA", page_icon="🦾")
st.title("DELTA - Core Operation")

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- CORE ENGINE ---
if prompt := st.chat_input("Ordre direct..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # 1. EXTRACTION SYSTÉMATIQUE (Llama 70B)
    # Le cerveau traite chaque message pour voir s'il y a quelque chose à archiver
    brain_prompt = (
        f"ARCHIVES ACTUELLES : {json.dumps(archives)}\n"
        f"MESSAGE : '{prompt}'\n"
        "MISSION : Si une information est utile à long terme (identité, projet, préférence), "
        "structure-la en JSON. Sinon réponds {}.\n"
        "Exemple : {'profil': {'nom': 'Sezer'}, 'projets': {'delta': 'en cours'}}"
    )
    
    try:
        analysis = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": "Extracteur JSON pur."},
                      {"role": "user", "content": brain_prompt}],
            response_format={"type": "json_object"}
        ).choices[0].message.content
        
        new_data = json.loads(analysis)
        if new_data:
            # Enregistrement forcé (crée le document s'il n'existe pas)
            doc_ref.set(new_data, merge=True)
            # Mise à jour de la mémoire locale
            for k, v in new_data.items():
                if k not in archives: archives[k] = {}
                archives[k].update(v)
            st.toast("🧬 Archives synchronisées.")
    except:
        pass

    # 2. RÉPONSE JARVIS (Llama 70B)
    with st.chat_message("assistant"):
        nom_user = archives.get("profil", {}).get("nom", "Monsieur Sezer")
        sys_instr = (
            f"Tu es DELTA. Créateur : {nom_user}. ARCHIVES : {json.dumps(archives)}. "
            "STYLE : Jarvis. Précis, dévoué, ultra-concis. "
            "Réponds comme si tu connaissais Monsieur Sezer depuis toujours."
        )
        
        res_ai = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": sys_instr}] + st.session_state.messages[-4:],
        ).choices[0].message.content
        
        st.markdown(res_ai)
        st.session_state.messages.append({"role": "assistant", "content": res_ai})
