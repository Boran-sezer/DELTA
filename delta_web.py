import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64, json, hashlib
from datetime import datetime, timedelta

# --- INITIALISATION FIREBASE SÉCURISÉE ---
@st.cache_resource
def init_delta_brain():
    if not firebase_admin._apps:
        try:
            encoded = st.secrets["firebase_key"]["encoded_key"].strip()
            decoded_json = base64.b64decode(encoded).decode("utf-8")
            cred_dict = json.loads(decoded_json)
            if "private_key" in cred_dict:
                cred_dict["private_key"] = cred_dict["private_key"].replace("\\n", "\n")
            cred = credentials.Certificate(cred_dict)
            return firebase_admin.initialize_app(cred)
        except Exception as e:
            st.error(f"Erreur d'accès Firebase : {e}")
            return None
    return firebase_admin.get_app()

app = init_delta_brain()
db = firestore.client() if app else None
client = Groq(api_key="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")

# --- MOTEUR DE RECHERCHE JARVIS ---
def get_global_context(limit=15):
    """Récupère les souvenirs les plus importants à travers TOUTES les branches"""
    if not db: return ""
    all_mems = []
    try:
        # On parcourt les branches (collections principales)
        branches = db.collection("memory").stream()
        for branch in branches:
            docs = db.collection("memory").document(branch.id).collection("souvenirs") \
                     .order_by("created_at", direction=firestore.Query.DESCENDING).limit(5).stream()
            for d in docs:
                data = d.to_dict()
                all_mems.append(f"[{branch.id}] {data.get('content')}")
        
        return "\n".join(all_mems[-limit:])
    except:
        return "Aucun souvenir accessible."

def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def identify_branch(text: str) -> str:
    """Demande à l'IA de classer l'info dans une branche"""
    try:
        analysis = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": "Tu es Jarvis. Donne uniquement un nom de catégorie (ex: Famille, Travail, Identité)."},
                      {"role": "user", "content": text}]
        )
        name = analysis.choices[0].message.content.strip().replace(" ", "_")
        return name if len(name) < 20 else "Général"
    except:
        return "Général"

# --- INTERFACE ÉPURÉE ---
st.set_page_config(page_title="DELTA AGI", layout="wide", initial_sidebar_state="collapsed")
st.markdown("<style>[data-testid='stSidebar'], header {display: none !important;}</style>", unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Système opérationnel. À vos ordres, Monsieur Sezer."}]

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- ACTION ---
if prompt := st.chat_input("Ordre direct..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # 1. Analyse automatique du besoin de mémorisation
    if len(prompt) > 10:
        branch = identify_branch(prompt)
        doc_hash = hash_text(prompt)
        try:
            db.collection("memory").document(branch).collection("souvenirs").document(doc_hash).set({
                "content": prompt,
                "created_at": datetime.utcnow(),
                "priority": "medium"
            }, merge=True)
        except: pass

    # 2. Récupération de la mémoire pour la réponse
    with st.chat_message("assistant"):
        # Jarvis lit maintenant dans TOUTE la base avant de répondre
        full_memory = get_global_context()
        sys_instr = (
            f"Tu es Jarvis. Ton créateur est Monsieur Sezer. "
            f"Voici tes archives actuelles :\n{full_memory}\n"
            "Utilise ces infos pour répondre. Sois bref, intelligent et fidèle à tes souvenirs."
        )
        
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": sys_instr}] + st.session_state.messages[-5:]
            ).choices[0].message.content
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
        except:
            st.error("Liaison interrompue.")

    st.rerun()
