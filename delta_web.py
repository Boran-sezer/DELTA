import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64, json, re

# --- CONFIGURATION (Votre Clé Groq) ---
GROQ_API_KEY = "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"

# --- CONNEXION FIREBASE (Standard Lux) ---
if not firebase_admin._apps:
    try:
        encoded = st.secrets["firebase_key"]["encoded_key"].strip()
        decoded_json = base64.b64decode(encoded).decode("utf-8")
        cred = credentials.Certificate(json.loads(decoded_json))
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Erreur d'initialisation : {e}")

db = firestore.client()
# Lux sépare l'utilisateur par document unique
doc_ref = db.collection("archives").document("monsieur_sezer")
client = Groq(api_key=GROQ_API_KEY)

# --- INITIALISATION DE LA STRUCTURE ---
def get_lux_memory():
    res = doc_ref.get()
    if res.exists:
        return res.to_dict()
    return {
        "profil": {"nom": "Monsieur Sezer", "age": None, "role": "Créateur"},
        "projets": {},
        "preferences": {},
        "historique_synaptique": []
    }

archives = get_lux_memory()

# --- INTERFACE ---
st.title("DELTA (Engine: LUX-Architecture)")

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- CORE LOGIC (L'aspiration de Lux) ---
if prompt := st.chat_input("Ordre direct..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # 1. LE FILTRE (Extraction par le modèle 8B)
    # Lux utilise un 'system prompt' très strict pour transformer le texte en JSON
    instruction_filtre = (
        "Tu es le processeur de données de Lux. Ton rôle est d'extraire des faits. "
        "Analyse le message de l'utilisateur et renvoie UNIQUEMENT un JSON structuré. "
        "Si l'utilisateur donne son âge, son nom ou un projet, remplis les cases correspondantes. "
        "Si rien n'est nouveau, réponds '{}'."
    )
    
    analysis = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": instruction_filtre},
            {"role": "user", "content": f"Message: {prompt} | Archives actuelles: {json.dumps(archives)}"}
        ],
        response_format={"type": "json_object"} # Force le format JSON
    ).choices[0].message.content

    # 2. INJECTION (Sauvegarde Firestore)
    try:
        data_to_save = json.loads(analysis)
        if data_to_save:
            # On fusionne les nouvelles données avec les anciennes sans rien supprimer
            doc_ref.set(data_to_save, merge=True)
            # Mise à jour locale pour que l'IA réponde avec les infos fraîches
            for key in data_to_save:
                if key in archives: archives[key].update(data_to_save[key])
            st.toast("🧬 Synapse synchronisée")
    except:
        pass

    # 3. RÉPONSE IA (Modèle 70B avec la mémoire de Lux)
    with st.chat_message("assistant"):
        sys_instr = (
            f"Tu es DELTA. Ton créateur est {archives['profil']['nom']}. "
            f"MÉMOIRE GLOBALE : {json.dumps(archives)}. "
            "TON : Majordome, distingué, extrêmement concis (Style Jarvis). "
            "Anticipe les besoins en fonction des projets et préférences stockés."
        )
        
        full_res = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": sys_instr}] + st.session_state.messages[-4:],
        ).choices[0].message.content
        
        st.markdown(full_res)
        st.session_state.messages.append({"role": "assistant", "content": full_res})
