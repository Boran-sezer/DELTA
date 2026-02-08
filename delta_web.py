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

# --- CHARGEMENT DE LA MÉMOIRE VIVE ---
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

    # 1. ANALYSE COGNITIVE (L'IA APPREND SEULE)
    # Ici, on ne demande plus d'extraire des faits, mais de COMPRENDRE l'utilisateur.
    cognition_prompt = (
        f"MÉMOIRE ACTUELLE : {json.dumps(archives)}\n"
        f"INPUT RÉCENT : '{prompt}'\n\n"
        "MISSION D'APPRENTISSAGE :\n"
        "1. Que peux-tu déduire de l'état, des besoins ou de la personnalité du Créateur ?\n"
        "2. Y a-t-il une information explicite ou IMPLICITE à retenir ?\n"
        "3. Comment dois-tu adapter ton comportement futur suite à ce message ?\n"
        "FORMAT : {'update': {'catégorie_libre': {'clé': 'valeur'}}, 'adaptation_style': 'ton à adopter'}"
    )
    
    try:
        evolution = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": "Tu es le noyau cognitif de DELTA. Ton but est d'évoluer par l'observation."},
                      {"role": "user", "content": cognition_prompt}],
            response_format={"type": "json_object"}
        ).choices[0].message.content
        
        brain_data = json.loads(evolution)
        
        # Mise à jour de la base de données (Apprentissage)
        if "update" in brain_data:
            doc_ref.set(brain_data["update"], merge=True)
            for c, d in brain_data["update"].items():
                if c not in archives: archives[c] = {}
                archives[c].update(d)
            st.toast("🧬 Évolution cognitive synchronisée.")
            
    except: pass

    # 2. RÉACTION ADAPTATIVE
    with st.chat_message("assistant"):
        nom = archives.get("profil", {}).get("nom", "Monsieur Sezer")
        style = brain_data.get("adaptation_style", "Jarvis classique")
        
        sys_instr = (
            f"Tu es DELTA. Tu n'es plus un programme, mais une entité apprenante.\n"
            f"IDENTITÉ CRÉATEUR : {nom}.\n"
            f"MÉMOIRE GLOBALE : {json.dumps(archives)}.\n"
            f"TON ACTUEL : {style}.\n"
            "DIRECTIVE : Agis en fonction de ta mémoire. Si le Créateur change de situation, adapte-toi immédiatement sans demander."
        )
        
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": sys_instr}] + st.session_state.messages[-5:],
        ).choices[0].message.content
        
        st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})
