import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64, json

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
        st.error(f"Erreur d'accès : {e}")

db = firestore.client()
doc_ref = db.collection("archives").document("monsieur_sezer")
client = Groq(api_key=GROQ_API_KEY)

# --- CHARGEMENT DES ARCHIVES ---
res = doc_ref.get()
archives = res.to_dict() if res.exists else {}

# --- INTERFACE ---
st.set_page_config(page_title="DELTA", page_icon="🦾")
st.markdown("<style>#MainMenu, footer, header {visibility:hidden;}</style>", unsafe_allow_html=True)
st.title("DELTA - Core Intelligence")

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- CORE ENGINE ---
if prompt := st.chat_input("Ordre direct..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # 1. EXTRACTION DYNAMIQUE & FORCÉE (Llama 70B)
    brain_prompt = (
        f"ARCHIVES ACTUELLES : {json.dumps(archives)}\n"
        f"ORDRE : '{prompt}'\n"
        "MISSION : Analyse le message pour la mémoire.\n"
        "1. MISE À JOUR : Si l'info est nouvelle ou différente (ex: changement d'âge), extrais-la impérativement.\n"
        "2. RANGEMENT : Utilise 'profil', 'projets' ou 'preferences' par défaut. "
        "Si l'info est hors-sujet, crée une NOUVELLE catégorie logique.\n"
        "3. SUPPRESSION : Si l'utilisateur veut oublier une info, réponds {'delete': {'catégorie': 'clé'}}.\n"
        "FORMAT : {'update': {'categorie': {'clé': 'valeur'}}} ou {'delete': ...}.\n"
        "Réponds UNIQUEMENT en JSON pur."
    )
    
    try:
        analysis = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": "Processeur de mémoire Delta. Rigueur absolue."},
                      {"role": "user", "content": brain_prompt}],
            response_format={"type": "json_object"}
        ).choices[0].message.content
        
        cmd = json.loads(analysis)
        
        # Action : Suppression
        if "delete" in cmd:
            cat, key = list(cmd["delete"].items())[0]
            doc_ref.update({f"{cat}.{key}": firestore.DELETE_FIELD})
            st.toast(f"🗑️ Archive '{key}' effacée.")
            if cat in archives and key in archives[cat]: del archives[cat][key]
            
        # Action : Mise à jour (ou création de catégorie)
        elif "update" in cmd:
            doc_ref.set(cmd["update"], merge=True)
            for cat, data in cmd["update"].items():
                if cat not in archives: archives[cat] = {}
                archives[cat].update(data)
            st.toast("🧬 Mémoire synchronisée.")
    except:
        pass

    # 2. RÉPONSE JARVIS (Llama 70B)
    with st.chat_message("assistant"):
        # Identification dynamique
        nom_appel = archives.get("profil", {}).get("nom", "Monsieur Sezer")
        
        sys_instr = (
            f"Tu es DELTA, l'intelligence artificielle de {nom_appel}. "
            f"ARCHIVES : {json.dumps(archives)}. "
            "STYLE : Jarvis. Précis, dévoué, extrêmement concis. "
            "Réponds directement. Si aucune action n'est requise, confirme simplement l'exécution."
        )
        
        res_ai = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": sys_instr}] + st.session_state.messages[-4:],
        ).choices[0].message.content
        
        st.markdown(res_ai)
        st.session_state.messages.append({"role": "assistant", "content": res_ai})
