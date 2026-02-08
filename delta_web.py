import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64, json
from datetime import datetime

# --- CONFIGURATION ---
GROQ_API_KEY = "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"

# --- CONNEXION FIREBASE ---
if not firebase_admin._apps:
    try:
        encoded = st.secrets["firebase_key"]["encoded_key"].strip()
        decoded_json = base64.b64decode(encoded).decode("utf-8")
        cred = credentials.Certificate(json.loads(decoded_json))
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Erreur Firebase : {e}")

db = firestore.client()
doc_ref = db.collection("memoire").document("profil_monsieur")
client = Groq(api_key=GROQ_API_KEY)

# --- CHARGEMENT DE LA MÉMOIRE ---
res = doc_ref.get()
# On récupère l'historique pour que DELTA sache ce qui a été dit avant
donnees_memoire = res.to_dict() if res.exists else {"historique": []}
memoire_texte = ", ".join(donnees_memoire.get("historique", []))

# --- INTERFACE ---
st.set_page_config(page_title="DELTA", layout="wide")
st.markdown("<style>button {display:none;} #MainMenu, footer, header {visibility:hidden;}</style>", unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- TRAITEMENT ---
if prompt := st.chat_input("Ordre..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # 1. SAUVEGARDE PAR EMPILEMENT (Firestore ArrayUnion)
    try:
        # Ajoute le nouveau message à la liste sans effacer les anciens
        doc_ref.update({
            "historique": firestore.ArrayUnion([prompt]),
            "derniere_maj": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    except:
        # Crée le document s'il n'existe pas encore
        doc_ref.set({"historique": [prompt]}, merge=True)

    # 2. RÉPONSE AVEC CONTEXTE MÉMOIRE
    with st.chat_message("assistant"):
        sys_instr = (
            f"Tu es DELTA. Ton créateur est Monsieur Sezer. "
            f"Voici ce que tu sais de lui (MÉMOIRE) : {memoire_texte}. "
            "Sois concis, dévoué et utilise ces infos pour tes réponses."
        )
        
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": sys_instr},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.3-70b-versatile",
        )
        response = chat_completion.choices[0].message.content
        st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})
