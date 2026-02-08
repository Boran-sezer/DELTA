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

# --- CHARGEMENT DYNAMIQUE (Pas de pré-création) ---
res = doc_ref.get()
archives = res.to_dict() if res.exists else {}

# --- INTERFACE ---
st.set_page_config(page_title="DELTA", page_icon="🦾")
st.title("DELTA - Architecture Organique")

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- CORE ENGINE ---
if prompt := st.chat_input("En attente d'ordres..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # 1. LE GARDIEN (Vérifie si une mémorisation est utile)
    check_prompt = f"Analyse : '{prompt}'. L'utilisateur donne-t-il une info à mémoriser ? Réponds par OUI ou NON."
    check = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": check_prompt}]
    ).choices[0].message.content

    # 2. L'EXPERT (70B) - Crée les structures uniquement si besoin
    if "OUI" in check.upper() or any(x in prompt.lower() for x in ["nom", "prénom", "âge", "projet", "aime"]):
        brain_prompt = (
            f"ARCHIVES ACTUELLES : {json.dumps(archives)}\n"
            f"ORDRE : '{prompt}'\n"
            "MISSION : Identifie l'information et crée une catégorie logique (ex: profil, projets, etc.). "
            "Format attendu : {'update': {'NOM_CATEGORIE': {'CLE': 'VALEUR'}}} "
            "Réponds UNIQUEMENT en JSON."
        )
        
        analysis = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": "Extracteur JSON intelligent."},
                      {"role": "user", "content": brain_prompt}],
            response_format={"type": "json_object"}
        ).choices[0].message.content
        
        try:
            cmd = json.loads(analysis)
            if "update" in cmd:
                # doc_ref.set avec merge=True créera le dossier s'il n'existe pas
                doc_ref.set(cmd["update"], merge=True)
                # Mise à jour de la mémoire locale pour la réponse immédiate
                for cat, data in cmd["update"].items():
                    if cat not in archives: archives[cat] = {}
                    archives[cat].update(data)
                st.toast("🧬 Structure créée et synchronisée.")
        except: pass

    # 3. RÉPONSE JARVIS
    with st.chat_message("assistant"):
        # On cherche le nom si présent, sinon valeur par défaut
        nom_appel = archives.get("profil", {}).get("nom", "Monsieur Sezer")
        
        sys_instr = (
            f"Tu es DELTA. Créateur : {nom_appel}. "
            f"MÉMOIRE ACTUELLE (peut être vide) : {json.dumps(archives)}. "
            "STYLE : Jarvis. Précis, dévoué, ultra-concis. "
            "Si la mémoire est vide, reste poli et attends les ordres."
        )
        
        res_ai = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": sys_instr}] + st.session_state.messages[-4:],
        ).choices[0].message.content
        
        st.markdown(res_ai)
        st.session_state.messages.append({"role": "assistant", "content": res_ai})
