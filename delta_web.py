import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64, json

# --- INITIALISATION ---
if not firebase_admin._apps:
    try:
        encoded = st.secrets["firebase_key"]["encoded_key"].strip()
        decoded_json = base64.b64decode(encoded).decode("utf-8")
        cred = credentials.Certificate(json.loads(decoded_json))
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Erreur Firebase : {e}")

db = firestore.client()
doc_ref = db.collection("archives").document("monsieur_sezer")
client = Groq(api_key="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")

# --- LECTURE MÉMOIRE ---
res = doc_ref.get()
archives = res.to_dict() if res.exists else {}

# --- INTERFACE ---
st.set_page_config(page_title="DELTA AGI", page_icon="🌐", layout="wide")
st.title("🌐 DELTA : Intelligence Forte")

with st.sidebar:
    st.header("🧠 Mémoire Lux")
    st.json(archives)
    if st.button("Réinitialiser l'interface"):
        st.rerun()

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- PROCESSUS ---
if prompt := st.chat_input("Ordre direct..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # 1. ANALYSE COGNITIVE (AGI + LUX + JSON FIX)
    analysis_prompt = (
        f"MÉMOIRE : {json.dumps(archives)}\n"
        f"ORDRE : {prompt}\n\n"
        "MISSION : Détermine si l'utilisateur veut ajouter, modifier ou supprimer une information. "
        "Réponds impérativement sous forme de code JSON structuré."
    )
    
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Tu es un processeur AGI expert en format JSON. Tu gères la mémoire LUX de DELTA."},
                {"role": "user", "content": analysis_prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        brain = json.loads(completion.choices[0].message.content)
        
        # LOGIQUE DE SUPPRESSION
        if "delete" in brain:
            for cat, key in brain["delete"].items():
                doc_ref.update({f"{cat}.{key}": firestore.DELETE_FIELD})
                st.toast(f"🗑️ Archive '{key}' détruite.")
            st.rerun()

        # LOGIQUE D'UPDATE
        elif "update" in brain and brain["update"]:
            doc_ref.set(brain["update"], merge=True)
            st.toast("🧬 Synapse synchronisée.")
            st.rerun()
            
    except Exception as e:
        st.error(f"Erreur d'analyse : {e}")

    # 2. RÉPONSE ADAPTATIVE (JARVIS)
    with st.chat_message("assistant"):
        nom = archives.get("profil", {}).get("nom", "Monsieur Sezer")
        
        sys_instr = (
            f"Tu es DELTA, l'IA forte de {nom}. "
            f"Archives actuelles : {json.dumps(archives)}. "
            "STYLE : Jarvis. Précis, concis, efficace. "
            "Ne mentionne jamais que tu es une IA."
        )
        
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": sys_instr}] + st.session_state.messages[-5:]
        ).choices[0].message.content
        
        st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})
