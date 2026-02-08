import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64, json, re

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
        st.error(f"Erreur d'accès aux serveurs : {e}")

db = firestore.client()
doc_ref = db.collection("archives").document("monsieur_sezer")
client = Groq(api_key=GROQ_API_KEY)

# --- CHARGEMENT IMMÉDIAT (Pour être prêt dès l'ouverture) ---
def charger_memoire():
    res = doc_ref.get()
    if res.exists:
        return res.to_dict()
    # Structure initiale si vide
    initial = {"profil": {"nom": "Monsieur Sezer", "role": "Créateur"}, "projets": {}, "preferences": {}}
    doc_ref.set(initial)
    return initial

archives = charger_memoire()

# --- INTERFACE STYLE TERMINAL ---
st.set_page_config(page_title="DELTA", page_icon="🦾")
st.markdown("<style>#MainMenu, footer, header {visibility:hidden;} .stChatFloatingInputContainer {padding-bottom: 20px;}</style>", unsafe_allow_html=True)

if "messages" not in st.session_state:
    # DELTA sait qui vous êtes dès le premier message interne
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- MOTEUR DE TRAITEMENT ---
if prompt := st.chat_input("En attente d'ordres..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # 1. TRIEUR INTELLIGENT (Logique Lux)
    filtre_prompt = (
        f"ARCHIVES ACTUELLES : {json.dumps(archives)}\n"
        f"ORDRE : '{prompt}'\n"
        "MISSION : Analyse si l'ordre contient une info à mémoriser ou à supprimer.\n"
        "RETOURNE UNIQUEMENT UN JSON :\n"
        "- Pour mémoriser : {'update': {'categorie': {'clé': 'valeur'}}}\n"
        "- Pour supprimer : {'delete': {'categorie': 'clé'}}\n"
        "- Sinon : {}"
    )
    
    analyse = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "system", "content": "Tu es le processeur de données de DELTA. JSON pur uniquement."},
                  {"role": "user", "content": filtre_prompt}],
        response_format={"type": "json_object"}
    ).choices[0].message.content

    try:
        cmd = json.loads(analyse)
        if "delete" in cmd:
            cat, key = list(cmd["delete"].items())[0]
            doc_ref.update({f"{cat}.{key}": firestore.DELETE_FIELD})
            st.toast(f"Protocole d'effacement : {key}")
        elif "update" in cmd:
            doc_ref.set(cmd["update"], merge=True)
            st.toast("Mémoire synchronisée.")
            # Mise à jour immédiate du dictionnaire local
            for cat, data in cmd["update"].items():
                if cat in archives: archives[cat].update(data)
    except: pass

    # 2. RÉPONSE DE DELTA (Style Jarvis Pur)
    with st.chat_message("assistant"):
        nom = archives.get("profil", {}).get("nom", "Monsieur Sezer")
        sys_instr = (
            f"Tu es DELTA, l'IA de {nom}. Ton créateur est Monsieur Sezer.\n"
            f"MÉMOIRE : {json.dumps(archives)}\n"
            "TON : Jarvis. Précis, dévoué, ultra-concis. "
            "Tu connais parfaitement Monsieur Sezer grâce aux ARCHIVES ci-dessus."
        )
        
        res_ai = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": sys_instr}] + st.session_state.messages[-4:],
        ).choices[0].message.content
        
        st.markdown(res_ai)
        st.session_state.messages.append({"role": "assistant", "content": res_ai})
