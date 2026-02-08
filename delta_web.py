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
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Erreur Firebase : {e}")
        st.stop()

db = firestore.client()
USER_ID = "monsieur_sezer"

# --- UTILS MÉMOIRE ---
def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def is_memory_worthy(text: str) -> bool:
    blacklist = ["salut", "ok", "mdr", "lol", "?", "oui", "non"]
    # Un seuil de 5 caractères est suffisant pour capturer les infos cruciales
    return len(text.strip()) >= 5 and text.lower().strip() not in blacklist

def get_recent_memories(limit=10):
    try:
        # Accès direct pour éviter les erreurs de contexte
        memories = db.collection("users").document(USER_ID).collection("memory") \
                     .order_by("created_at", direction=firestore.Query.DESCENDING) \
                     .limit(limit).stream()
        return [m.to_dict() for m in memories]
    except Exception as e:
        return []

# --- INITIALISATION GROQ ---
client = Groq(api_key="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")

# --- INTERFACE ---
st.set_page_config(page_title="DELTA AGI", page_icon="🌐", layout="wide")
st.title("🌐 DELTA : Système AGI")

# Récupération immédiate du contexte
context_list = get_recent_memories()

with st.sidebar:
    st.header("🧠 Mémoire Vive")
    if context_list:
        for m in context_list:
            st.caption(f"[{m.get('category')}] {m.get('content')}")
    else:
        st.info("Aucun souvenir")
    if st.button("🔄 Actualiser"):
        st.rerun()

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- PROCESSUS PRINCIPAL ---
if prompt := st.chat_input("En attente de vos ordres, Monsieur Sezer..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # 1. ANALYSE ET INJECTION FORCÉE
    if is_memory_worthy(prompt):
        try:
            # Force l'IA à extraire une information structurée
            analysis = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "Tu es une IA forte. Extrais l'info clé en JSON. Format: {'category': '...', 'content': '...'}"},
                    {"role": "user", "content": f"Archive ceci : {prompt}"}
                ],
                response_format={"type": "json_object"}
            )
            
            data = json.loads(analysis.choices[0].message.content)
            m_hash = hash_text(prompt)
            
            # Injection directe dans la sous-collection
            doc_ref = db.collection("users").document(USER_ID).collection("memory").document(m_hash)
            
            # Utilisation de set avec merge pour garantir l'écriture
            doc_ref.set({
                "category": data.get("category", "info"),
                "content": prompt,
                "created_at": datetime.utcnow()
            }, merge=True)
            
            st.toast("🧬 Synapse enregistrée dans Firebase.")
        except Exception as e:
            st.error(f"Erreur d'écriture : {e}")

    # 2. GÉNÉRATION DE RÉPONSE (AVEC CONTEXTE MIS À JOUR)
    with st.chat_message("assistant"):
        updated_context = get_recent_memories()
        context_str = "\n".join([f"- {m['content']}" for m in updated_context])
        
        sys_instr = (
            f"Tu es Jarvis. Créateur : Monsieur Sezer. "
            f"Contexte mémoriel : {context_str}. "
            "Sois concis et brillant. Ne dis jamais que tu es une IA."
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
    
    # Rafraîchissement pour voir la sidebar à jour
    st.rerun()
