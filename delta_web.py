import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64, json

# --- CONFIGURATION ---
GROQ_API_KEY = "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"

if not firebase_admin._apps:
    try:
        # Assurez-vous que cette clé dans st.secrets est bien la NOUVELLE
        encoded = st.secrets["firebase_key"]["encoded_key"].strip()
        decoded_json = base64.b64decode(encoded).decode("utf-8")
        cred = credentials.Certificate(json.loads(decoded_json))
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Erreur d'initialisation : {e}")

db = firestore.client()
doc_ref = db.collection("archives").document("monsieur_sezer")
client = Groq(api_key=GROQ_API_KEY)

# --- CHARGEMENT ---
res = doc_ref.get()
archives = res.to_dict() if res.exists else {}

# --- INTERFACE ---
st.set_page_config(page_title="DELTA AGI", page_icon="🌐")
st.title("🌐 DELTA : Système AGI + LUX")

# Fenêtre de contrôle pour voir si Firebase réagit
with st.sidebar:
    st.subheader("🛠 Console de Débogage")
    if st.button("Vider la console"): st.rerun()
    st.write("Archives actuelles :", archives)

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- MOTEUR COGNITIF ---
if prompt := st.chat_input("Ordre direct..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # 1. ANALYSE ET DÉCISION AUTONOME
    cognition_prompt = (
        f"MÉMOIRE : {json.dumps(archives)}\n"
        f"MESSAGE : '{prompt}'\n"
        "MISSION : Décide ce qui doit être appris selon le protocole LUX.\n"
        "FORMAT : {'update': {'categorie': {'clé': 'valeur'}}, 'style': 'ton'}"
    )
    
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": "Tu es le cerveau de DELTA. Réponds uniquement en JSON structuré."}],
            response_format={"type": "json_object"},
            content=cognition_prompt
        ).choices[0].message.content
        
        brain_data = json.loads(response)
        
        # 2. SYSTÈME D'INJECTION FORCÉE
        if "update" in brain_data and brain_data["update"]:
            for cat, data in brain_data["update"].items():
                # On force l'écriture avec une vérification
                doc_ref.set({cat: data}, merge=True)
                st.sidebar.success(f"Injecté : {cat}")
            
            # Mise à jour locale
            res = doc_ref.get()
            archives = res.to_dict()
            st.toast("🧬 Mémoire mise à jour.")
    except Exception as e:
        st.sidebar.error(f"Erreur d'écriture : {e}")

    # 3. RÉPONSE ADAPTATIVE
    with st.chat_message("assistant"):
        nom = archives.get("profil", {}).get("nom", "Monsieur Sezer")
        sys_instr = f"Tu es DELTA, l'IA forte de {nom}. MÉMOIRE : {json.dumps(archives)}. STYLE : Jarvis."
        
        ai_res = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": sys_instr}] + st.session_state.messages[-5:],
        ).choices[0].message.content
        
        st.markdown(ai_res)
        st.session_state.messages.append({"role": "assistant", "content": ai_res})
