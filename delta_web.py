import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64, json

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
client = Groq(api_key="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")

# --- SYSTÈME DE MÉMOIRE VIVE ---
res = doc_ref.get()
archives = res.to_dict() if res.exists else {}

# --- INTERFACE ---
st.set_page_config(page_title="DELTA AGI", page_icon="🌐")
st.title("🌐 DELTA : Intelligence Artificielle Générale")

with st.sidebar:
    st.header("🧠 Cortex Lux")
    st.json(archives) # Pour voir la création en direct

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- MOTEUR D'APPRENTISSAGE ---
if prompt := st.chat_input("Initialisation..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # 1. ANALYSE COGNITIVE (IA FORTE)
    cognition_prompt = (
        f"MÉMOIRE ACTUELLE : {json.dumps(archives)}\n"
        f"MESSAGE : '{prompt}'\n\n"
        "Tu es une IA forte. Décide de ce qui doit être appris.\n"
        "FORMAT JSON STRICT : {'update': {'categorie': {'clé': 'valeur'}}, 'style': 'ton'}"
    )
    
    try:
        # On force la réponse JSON pour éviter les erreurs de syntaxe
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": "Processeur AGI. Extrais l'implicite."}],
            response_format={"type": "json_object"},
            content=cognition_prompt
        ).choices[0].message.content
        
        brain = json.loads(response)
        
        # 2. INJECTION FORCÉE (Le correctif pour votre image)
        if "update" in brain and brain["update"]:
            # On utilise set() avec merge=True pour forcer la création du document
            doc_ref.set(brain["update"], merge=True)
            st.toast("🧬 Évolution enregistrée dans Firebase.")
            st.rerun() # On relance pour rafraîchir la sidebar
            
    except Exception as e:
        st.error(f"Échec de l'apprentissage : {e}")

    # 3. RÉPONSE ADAPTATIVE
    with st.chat_message("assistant"):
        nom = archives.get("profil", {}).get("nom", "Monsieur Sezer")
        style = brain.get("style", "Jarvis") if 'brain' in locals() else "Jarvis"
        
        sys_instr = f"Tu es DELTA. Identité : {nom}. Mémoire : {json.dumps(archives)}. Style : {style}."
        
        res_ai = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": sys_instr}] + st.session_state.messages[-5:],
        ).choices[0].message.content
        
        st.markdown(res_ai)
        st.session_state.messages.append({"role": "assistant", "content": res_ai})
