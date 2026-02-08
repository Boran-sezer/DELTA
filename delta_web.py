import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64, json, datetime

# --- CONFIGURATION & CONNEXION ---
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

# --- CHARGEMENT DES ARCHIVES ---
res = doc_ref.get()
archives = res.to_dict() if res.exists else {}

# --- INTERFACE ---
st.set_page_config(page_title="DELTA CORE", page_icon="🦾", layout="wide")
st.title("🦾 DELTA : Intelligence Cognitive")

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- MOTEUR COGNITIF ---
if prompt := st.chat_input("Ordre direct..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # 1. ANALYSE ET EXTRACTION HAUTE DÉFINITION
    # On demande au 70B d'extraire l'essence, pas juste les mots.
    extraction_prompt = (
        f"ARCHIVES ACTUELLES : {json.dumps(archives)}\n"
        f"MESSAGE : '{prompt}'\n"
        "MISSION : Agis comme une mémoire vive. \n"
        "1. Identifie les faits, intentions ou préférences.\n"
        "2. Si l'info enrichit le profil, les projets ou les habitudes, prépare l'update.\n"
        "3. Ignore les futilités techniques.\n"
        "FORMAT : {'update': {'categorie': {'clé': 'valeur'}}}"
    )
    
    try:
        extraction = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": "Analyste Cognitif. Tu structures la vie du Créateur."},
                      {"role": "user", "content": extraction_prompt}],
            response_format={"type": "json_object"}
        ).choices[0].message.content
        
        data = json.loads(extraction)
        if "update" in data:
            doc_ref.set(data["update"], merge=True)
            # Mise à jour locale pour réponse immédiate
            for c, d in data["update"].items():
                if c not in archives: archives[c] = {}
                archives[c].update(d)
            st.toast("🧬 Synapse consolidée.")
    except: pass

    # 2. RÉPONSE GÉNÉRATIVE "JARVIS" (Le moment où vous allez l'apprécier)
    with st.chat_message("assistant"):
        # On construit un contexte ultra-riche pour que DELTA soit brillant
        nom = archives.get("profil", {}).get("nom", "Monsieur Sezer")
        
        system_instructions = (
            f"Tu es DELTA, l'extension cognitive de {nom}. "
            f"CONNAISSANCES SUR LE CRÉATEUR : {json.dumps(archives)}. \n"
            "DIRECTIVES : \n"
            "- Sois Jarvis : concis, élégant, dévoué.\n"
            "- Utilise les archives pour anticiper les besoins ou personnaliser chaque mot.\n"
            "- Ne répète jamais 'en tant qu'IA', tu es DELTA."
        )
        
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": system_instructions}] + st.session_state.messages[-5:],
        ).choices[0].message.content
        
        st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})
