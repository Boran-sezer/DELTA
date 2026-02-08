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
        st.error(f"Erreur : {e}")

db = firestore.client()
doc_ref = db.collection("archives").document("monsieur_sezer")
client = Groq(api_key=GROQ_API_KEY)

# --- CHARGEMENT ---
res = doc_ref.get()
archives = res.to_dict() if res.exists else {}

# --- INTERFACE ---
st.set_page_config(page_title="DELTA", page_icon="🦾")
st.title("DELTA - Système Central")

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- CORE ENGINE ---
if prompt := st.chat_input("En attente d'ordres..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # 1. EXTRACTION AVEC CARTOGRAPHIE (Llama 70B)
    brain_prompt = (
        f"ARCHIVES ACTUELLES : {json.dumps(archives)}\n"
        f"ORDRE : '{prompt}'\n"
        "MISSION : Extrais les informations selon ce schéma STRICT :\n"
        "- 'profil' : Pour nom, prénom, âge, localisation.\n"
        "- 'projets' : Pour tout ce qui concerne DELTA ou vos créations.\n"
        "- 'preferences' : Pour les goûts et habitudes.\n"
        "Si l'info ne rentre pas, crée une catégorie logique.\n"
        "Si l'ordre demande de SUPPRIMER : {'delete': {'catégorie': 'clé'}}.\n"
        "Réponds UNIQUEMENT en JSON."
    )
    
    try:
        analysis = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": "Tu es le processeur de données de Monsieur Sezer. Précision absolue."},
                      {"role": "user", "content": brain_prompt}],
            response_format={"type": "json_object"}
        ).choices[0].message.content
        
        cmd = json.loads(analysis)
        
        # Gestion des suppressions
        if "delete" in cmd:
            cat, key = list(cmd["delete"].items())[0]
            doc_ref.update({f"{cat}.{key}": firestore.DELETE_FIELD})
            st.toast(f"🗑️ Donnée '{key}' effacée.")
        # Gestion des mises à jour
        elif cmd:
            doc_ref.set(cmd, merge=True)
            for k, v in cmd.items():
                if k not in archives: archives[k] = {}
                archives[k].update(v)
            st.toast("🧬 Mémoire synchronisée.")
    except:
        pass

    # 2. RÉPONSE JARVIS (Llama 70B)
    with st.chat_message("assistant"):
        nom_user = archives.get("profil", {}).get("nom", "Monsieur Sezer")
        sys_instr = (
            f"Tu es DELTA. Créateur : {nom_user}. ARCHIVES : {json.dumps(archives)}. "
            "STYLE : Jarvis. Précis, dévoué, ultra-concis. "
            "Tu sais exactement où chercher les informations dans tes archives."
        )
        
        res_ai = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": sys_instr}] + st.session_state.messages[-4:],
        ).choices[0].message.content
        
        st.markdown(res_ai)
        st.session_state.messages.append({"role": "assistant", "content": res_ai})
