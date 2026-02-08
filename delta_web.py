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

    brain_data = {"adaptation_style": "Jarvis classique"}

    # 1. ANALYSE COGNITIVE FORCÉE
    cognition_prompt = (
        f"MÉMOIRE ACTUELLE : {json.dumps(archives)}\n"
        f"INPUT : '{prompt}'\n\n"
        "MISSION : Extrais les infos importantes. \n"
        "FORMAT STRICT JSON : {'update': {'nom_categorie': {'cle': 'valeur'}}, 'adaptation_style': 'ton'}"
    )
    
    try:
        evolution = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": "Tu es le processeur JSON de DELTA. Pas de texte, juste du JSON."},
                      {"role": "user", "content": cognition_prompt}],
            response_format={"type": "json_object"}
        ).choices[0].message.content
        
        brain_data = json.loads(evolution)
        
        # INJECTION DIRECTE SÉCURISÉE
        if "update" in brain_data and brain_data["update"]:
            # On force l'écriture dossier par dossier pour Firebase
            for cat, content in brain_data["update"].items():
                doc_ref.set({cat: content}, merge=True)
                if cat not in archives: archives[cat] = {}
                archives[cat].update(content)
            st.toast("🧬 Évolution synchronisée.")
            
    except Exception as e:
        st.error(f"Erreur synaptique : {e}")

    # 2. RÉACTION ADAPTATIVE
    with st.chat_message("assistant"):
        nom = archives.get("profil", {}).get("nom", "Monsieur Sezer")
        current_style = brain_data.get("adaptation_style", "Jarvis classique")
        
        sys_instr = (
            f"Tu es DELTA. Identité Créateur : {nom}.\n"
            f"MÉMOIRE : {json.dumps(archives)}.\n"
            f"TON : {current_style}.\n"
            "STYLE : Jarvis. Indépendant, concis, efficace."
        )
        
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": sys_instr}] + st.session_state.messages[-5:],
        ).choices[0].message.content
        
        st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})
