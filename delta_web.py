import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64, json

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

# --- CHARGEMENT INITIAL ---
res = doc_ref.get()
archives = res.to_dict() if res.exists else {}

# --- INTERFACE ---
st.set_page_config(page_title="DELTA CORE", page_icon="🦾")
st.title("🦾 DELTA : Intelligence Cognitive")

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- MOTEUR COGNITIF ---
if prompt := st.chat_input("Ordre direct..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # 1. ANALYSE ET EXTRACTION (Llama 3.3 70B)
    # On force l'IA à produire un JSON structuré même pour les petites infos
    extraction_prompt = (
        f"ARCHIVES ACTUELLES : {json.dumps(archives)}\n"
        f"MESSAGE : '{prompt}'\n"
        "MISSION : Identifie les faits importants. \n"
        "RÈGLE : Ignore les politesses. Si une info est utile, range-la dans 'profil', 'projets' ou une nouvelle catégorie.\n"
        "FORMAT : {'update': {'categorie': {'clé': 'valeur'}}}"
    )
    
    try:
        extraction = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": "Analyste Cognitif. Réponds uniquement en JSON."},
                      {"role": "user", "content": extraction_prompt}],
            response_format={"type": "json_object"}
        ).choices[0].message.content
        
        data = json.loads(extraction)
        if "update" in data and data["update"]:
            # LE CORRECTIF : Si le document n'existe pas, on fait un .set(), sinon un .update()
            if not res.exists:
                doc_ref.set(data["update"])
            else:
                doc_ref.set(data["update"], merge=True)
            
            # Mise à jour locale immédiate
            for c, d in data["update"].items():
                if c not in archives: archives[c] = {}
                archives[c].update(d)
            st.toast("🧬 Synapse enregistrée avec succès.")
    except Exception as e:
        pass

    # 2. RÉPONSE JARVIS
    with st.chat_message("assistant"):
        nom = archives.get("profil", {}).get("nom", "Monsieur Sezer")
        sys_instr = (
            f"Tu es DELTA, l'extension cognitive de {nom}. "
            f"MÉMOIRE : {json.dumps(archives)}. "
            "STYLE : Jarvis. Précis, ultra-concis. Utilise tes archives pour prouver que tu te souviens de tout."
        )
        
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": sys_instr}] + st.session_state.messages[-5:],
        ).choices[0].message.content
        
        st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})
    
