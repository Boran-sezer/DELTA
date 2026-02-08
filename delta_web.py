import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import hashlib

# ================= INIT FIREBASE =================
if not firebase_admin._apps:
    cred_json = st.secrets["firebase_key"]  # clé Firebase depuis Streamlit secrets
    cred = credentials.Certificate(cred_json)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# ================= UTILS =================
def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def categorize_message(text: str) -> str:
    """Classe automatiquement le type de message"""
    text_lower = text.lower()
    if any(k in text_lower for k in ["projet", "créer", "développer", "assistant"]):
        return "projet"
    elif any(k in text_lower for k in ["aime", "préférence", "goût"]):
        return "preference"
    elif any(k in text_lower for k in ["règle", "instruction", "doit"]):
        return "regle"
    else:
        return "conversation"

def is_memory_worthy(text: str) -> bool:
    blacklist = ["salut", "ok", "mdr", "lol", "?", "oui", "non"]
    if len(text.strip()) < 10:
        return False
    if text.lower().strip() in blacklist:
        return False
    return True

# ================= MÉMOIRE =================
def save_memory(user_id: str, content: str, confidence: float = 0.9):
    """Enregistre une mémoire Delta"""
    if not is_memory_worthy(content):
        return
    category = categorize_message(content)
    memory_hash = hash_text(content)
    ref = db.collection("users").document(user_id).collection("memory").document(memory_hash)
    if not ref.get().exists:
        ref.set({
            "category": category,
            "content": content,
            "created_at": datetime.utcnow(),
            "confidence": confidence
        })

def get_context(user_id: str, limit: int = 5):
    """Récupère le contexte récent pour Delta"""
    memories = db.collection("users").document(user_id).collection("memory") \
                 .order_by("created_at", direction=firestore.Query.DESCENDING) \
                 .limit(limit).stream()
    return [m.to_dict() for m in memories]

# ================= RÉPONSE DELTA =================
def delta_response(user_id: str, user_message: str):
    """Génère une réponse Delta façon Jarvis"""
    # Sauvegarde mémoire
    save_memory(user_id, user_message)

    # Contexte récent
    context = get_context(user_id)
    intro = "Bien sûr, Boran. "
    context_note = ""
    if context:
        context_note = f"(Pour rappel : {context[0]['content']}) "

    response = f"{intro}{context_note}J'ai compris : '{user_message}'. Que souhaites-tu que je fasse ensuite ?"
    return response

# ================= STREAMLIT UI =================
st.set_page_config(page_title="Delta Jarvis Chat 🤖", layout="centered")
st.title("Delta Jarvis 🤖")
st.write("💬 Discute avec Delta comme avec Jarvis. Écris ton message et appuie sur Entrée.")

# Initialise l'historique de chat
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

user_id = "boran"

# Barre de saisie
user_input = st.text_input("Écris ici...", key="input", placeholder="Tape ton message et appuie sur Entrée")

# Envoi du message
if user_input:
    # Ajouter ton message dans l'historique
    st.session_state.chat_history.append({"role": "user", "message": user_input})

    # Réponse Delta
    response = delta_response(user_id, user_input)
    st.session_state.chat_history.append({"role": "delta", "message": response})

    # Efface le champ texte après envoi
    st.session_state.input = ""

# Affichage du chat
for chat in st.session_state.chat_history:
    if chat["role"] == "user":
        st.markdown(f"**Toi :** {chat['message']}")
    else:
        st.markdown(f"**Delta :** {chat['message']}")
