import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64, json, hashlib
from datetime import datetime

# --- INITIALISATION FIREBASE ---
if not firebase_admin._apps:
    try:
        encoded = st.secrets["firebase_key"]["encoded_key"].strip()
        decoded_json = base64.b64decode(encoded).decode("utf-8")
        cred_dict = json.loads(decoded_json)
        # Vérification rapide
        required_keys = ["type","project_id","private_key","client_email"]
        for k in required_keys:
            if k not in cred_dict:
                st.error(f"Clé Firebase invalide : {k} manquant")
                st.stop()
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Erreur Firebase : {e}")
        st.stop()

db = firestore.client()

# --- INITIALISATION GROQ ---
client = Groq(api_key="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")

USER_ID = "monsieur_sezer"

# --- UTILS MÉMOIRE ---
def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def is_memory_worthy(text: str) -> bool:
    blacklist = ["salut", "ok", "mdr", "lol", "?", "oui", "non"]
    return len(text.strip()) >= 10 and text.lower().strip() not in blacklist

def get_recent_memories(limit=10):
    try:
        mem_ref = db.collection("users").document(USER_ID).collection("memory")
        memories = mem_ref.order_by("created_at", direction=firestore.Query.DESCENDING).limit(limit).stream()
        return [m.to_dict() for m in memories]
    except Exception as e:
        st.error(f"Erreur récupération mémoire : {e}")
        return []

# --- INTERFACE ---
st.set_page_config(page_title="DELTA AGI", page_icon="🌐", layout="wide")
st.title("🌐 DELTA : Système AGI")

mem_ref = db.collection("users").document(USER_ID).collection("memory")

# Sidebar avec mémoire
context_list = get_recent_memories()
with st.sidebar:
    st.header("🧠 Mémoire Vive")
    if context_list:
        for m in context_list:
            st.caption(f"[{m.get('category')}] {m.get('content')}")
    else:
        st.info("Aucun souvenir pour le moment")
    if st.button("🔄 Actualiser"):
        st.experimental_rerun()

# Chat session state
if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# --- PROCESSUS PRINCIPAL ---
if prompt := st.chat_input("En attente de vos ordres, Monsieur Sezer..."):
    # 1. Ajout du message utilisateur
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # 2. Analyse et stockage si mémoire pertinente
    if is_memory_worthy(prompt):
        try:
            # Catégorisation via Groq
            analysis = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "Tu es une IA forte. Catégorise en JSON : {'category': '...'}"},
                    {"role": "user", "content": f"Donne une catégorie courte pour : {prompt}"}
                ],
                response_format={"type": "json_object"}
            )
            cat = json.loads(analysis.choices[0].message.content).get("category", "info")

            # Stockage dans Firebase
            m_hash = hash_text(prompt)
            ref = mem_ref.document(m_hash)  # Utilise hash comme ID
            if not ref.get().exists:
                ref.set({
                    "category": cat,
                    "content": prompt,
                    "created_at": datetime.utcnow()
                })
                st.success("🧬 Souvenir enregistré.")
            else:
                st.info("Souvenir déjà présent.")
        except Exception as e:
            st.error(f"Erreur analyse ou stockage mémoire : {e}")

    # 3. Récupération mémoire à jour
    context_list = get_recent_memories()

    # 4. Réponse Jarvis
    with st.chat_message("assistant"):
        context_str = "\n".join([f"- {m['content']}" for m in context_list])
        sys_instr = (
            f"Tu es Jarvis, l'IA de Monsieur Sezer. "
            f"Tes souvenirs récents sont : {context_str}. "
            "Sois concis, brillant et direct. Ne mentionne pas que tu es une IA."
        )

        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": sys_instr}] + st.session_state.messages[-5:]
            ).choices[0].message.content

            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
        except Exception as e:
            st.error(f"Erreur Groq : {e}")
