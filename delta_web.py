import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64, json

# --- CONFIGURATION ---
GROQ_API_KEY = "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"

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

# --- CHARGEMENT DE LA MÉMOIRE ---
res = doc_ref.get()
archives = res.to_dict() if res.exists else {}

# --- INTERFACE ---
st.set_page_config(page_title="DELTA EVOLVE", page_icon="🧠")
st.title("🧠 DELTA : Cognition Indépendante")

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- MOTEUR D'ADAPTATION ---
if prompt := st.chat_input("Communication libre..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # Initialisation de sécurité (Évite le NameError)
    brain_data = {"adaptation_style": "Jarvis classique"}

    # 1. ANALYSE COGNITIVE
    cognition_prompt = (
        f"MÉMOIRE ACTUELLE : {json.dumps(archives)}\n"
        f"INPUT RÉCENT : '{prompt}'\n\n"
        "MISSION : Déduis l'implicite et les besoins. "
        "FORMAT : {'update': {'catégorie': {'clé': 'valeur'}}, 'adaptation_style': 'ton à adopter'}"
    )
    
    try:
        evolution = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": "Noyau cognitif DELTA. Analyse et évolution."},
                      {"role": "user", "content": cognition_prompt}],
            response_format={"type": "json_object"}
        ).choices[0].message.content
        
        # On remplace l'initialisation par les vraies données
        brain_data = json.loads(evolution)
        
        if "update" in brain_data:
            doc_ref.set(brain_data["update"], merge=True)
            for c, d in brain_data["update"].items():
                if c not in archives: archives[c] = {}
                archives[c].update(d)
            st.toast("🧬 Évolution cognitive synchronisée.")
            
    except Exception as e:
        st.warning("Analyse cognitive en attente... Passage en mode standard.")

    # 2. RÉACTION ADAPTATIVE
    with st.chat_message("assistant"):
        nom = archives.get("profil", {}).get("nom", "Monsieur Sezer")
        # Utilisation sécurisée de brain_data
        current_style = brain_data.get("adaptation_style", "Jarvis classique")
        
        sys_instr = (
            f"Tu es DELTA. Identité Créateur : {nom}.\n"
            f"MÉMOIRE GLOBALE : {json.dumps(archives)}.\n"
            f"TON ADAPTATIF : {current_style}.\n"
            "STYLE : Jarvis. Indépendant, capable d'apprendre et d'anticiper."
        )
        
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": sys_instr}] + st.session_state.messages[-5:],
        ).choices[0].message.content
        
        st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})
