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
        st.error(f"Erreur d'accès : {e}")

db = firestore.client()
doc_ref = db.collection("archives").document("monsieur_sezer")
client = Groq(api_key=GROQ_API_KEY)

# --- INITIALISATION SYSTÈME ---
res = doc_ref.get()
archives = res.to_dict() if res.exists else {
    "profil": {"nom": "Sezer", "role": "Créateur"},
    "projets": {},
    "preferences": {}
}

# --- INTERFACE ---
st.set_page_config(page_title="DELTA", page_icon="🦾")
st.title("DELTA - Hybrid Intelligence")

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- CORE LOGIC ---
if prompt := st.chat_input("Ordre direct..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # 1. LE GARDIEN (Llama 8B - Économe)
    # Détecte si une action sur la mémoire est requise
    check_prompt = f"Le message '{prompt}' demande-t-il de mémoriser une info ou d'en supprimer une ? Réponds par OUI ou NON."
    check = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": check_prompt}]
    ).choices[0].message.content

    # 2. L'EXPERT (Llama 70B - Précision)
    # Activé uniquement si nécessaire pour économiser le quota
    if "OUI" in check.upper():
        brain_prompt = (
            f"ARCHIVES : {json.dumps(archives)}\n"
            f"ORDRE : '{prompt}'\n"
            "MISSION : Extrais les infos dans ce schéma STRICT :\n"
            "- 'profil': {'nom': '...', 'prenom': '...', 'age': ...}\n"
            "- 'projets': {'nom_du_projet': 'description'}\n\n"
            "Retourne un JSON avec 'update' (ajout) ou 'delete' (suppression)."
        )
        
        analysis = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": "Extracteur JSON chirurgical."},
                      {"role": "user", "content": brain_prompt}],
            response_format={"type": "json_object"}
        ).choices[0].message.content
        
        try:
            cmd = json.loads(analysis)
            if "update" in cmd:
                doc_ref.set(cmd["update"], merge=True)
                for k, v in cmd["update"].items():
                    if k in archives: archives[k].update(v)
                st.toast("🧬 Mémoire synchronisée (Expert 70B)")
            elif "delete" in cmd:
                cat, key = list(cmd["delete"].items())[0]
                doc_ref.update({f"{cat}.{key}": firestore.DELETE_FIELD})
                st.toast("🗑️ Donnée effacée.")
        except: pass

    # 3. RÉPONSE JARVIS (Llama 70B)
    with st.chat_message("assistant"):
        sys_instr = (
            f"Tu es DELTA, l'IA de Monsieur Sezer. "
            f"MÉMOIRE : {json.dumps(archives)}. "
            "TON : Jarvis. Précis, distingué, extrêmement concis. "
            "Ne salue pas si la conversation est déjà engagée. Va à l'essentiel."
        )
        
        res_ai = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": sys_instr}] + st.session_state.messages[-4:],
        ).choices[0].message.content
        
        st.markdown(res_ai)
        st.session_state.messages.append({"role": "assistant", "content": res_ai})
