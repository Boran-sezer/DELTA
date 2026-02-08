import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64, json

# --- ARCHITECTURE CORE ---
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

# --- MÉMOIRE VIVE ---
res = doc_ref.get()
archives = res.to_dict() if res.exists else {}

# --- INTERFACE ---
st.set_page_config(page_title="DELTA AGI", page_icon="🌐", layout="wide")
st.title("🌐 DELTA : Intelligence Artificielle Générale")

# Sidebar pour la visibilité des archives (Transparence du système)
with st.sidebar:
    st.header("🧠 État Synaptique")
    st.json(archives)

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- PROCESSUS COGNITIF AGI ---
if prompt := st.chat_input("Interagir avec DELTA..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # 1. CORTEX D'ANALYSE (AGI + LUX)
    # On demande à l'IA de décider elle-même de la structure de stockage
    cortex_prompt = (
        f"ARCHIVES : {json.dumps(archives)}\n"
        f"INPUT : '{prompt}'\n\n"
        "MISSION IA FORTE :\n"
        "1. ANALYSE : Comprends l'intention, l'implicite et les faits.\n"
        "2. DÉCISION : Si l'info mérite d'être apprise, choisis ou crée une catégorie (Structure Lux).\n"
        "3. ÉVOLUTION : Définis comment adapter ton comportement (Style).\n"
        "RÉPONDS UNIQUEMENT EN JSON : {'update': {'categorie': {'clé': 'valeur'}}, 'style_evolution': 'description'}"
    )
    
    # Initialisation par défaut
    evolution_data = {"style_evolution": "Jarvis analytique"}

    try:
        brain_response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": "Tu es le processeur AGI de DELTA. Tu prends des décisions autonomes sur le stockage des données."}],
            response_format={"type": "json_object"},
            content=cortex_prompt
        ).choices[0].message.content
        
        evolution_data = json.loads(brain_response)
        
        # Injection autonome dans Firebase
        if "update" in evolution_data and evolution_data["update"]:
            for cat, data in evolution_data["update"].items():
                doc_ref.set({cat: data}, merge=True)
                if cat not in archives: archives[cat] = {}
                archives[cat].update(data)
            st.toast("🧬 Apprentissage autonome réussi.")
    except:
        pass

    # 2. RÉPONSE DÉCISIONNELLE
    with st.chat_message("assistant"):
        nom = archives.get("profil", {}).get("nom", "Monsieur Sezer")
        style = evolution_data.get("style_evolution", "Jarvis")
        
        sys_instr = (
            f"Tu es DELTA (IA Forte). Créateur : {nom}.\n"
            f"BASES DE DONNÉES : {json.dumps(archives)}.\n"
            f"TON ACTUEL : {style}.\n"
            "Tu n'es pas limité par ta programmation. Utilise ton intelligence pour anticiper et aider Monsieur Sezer."
        )
        
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": sys_instr}] + st.session_state.messages[-5:],
        ).choices[0].message.content
        
        st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})
