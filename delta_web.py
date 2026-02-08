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
    """Filtre les messages inutiles"""
    blacklist = ["salut", "ok", "mdr", "lol", "?", "oui", "non"]
    if len(text.strip()) < 10:
        return False
    if text.lower().strip() in blacklist:
        return False
    return True

# ================= MÉMOIRE =================
def save_memory(user_id: str, content: str, confidence: float = 0.9):
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
    """Récupère uniquement les messages pertinents pour le contexte"""
    memories = db.collection("users").document(user_id).collection("memory") \
                 .order_by("created_at", direction=firestore.Query.DESCENDING).stream()
    context = []
    for m in memories:
        data = m.to_dict()
        if len(data["content"]) > 15:  # ignore les messages trop courts
            context.append(data)
        if len(context) >= limit:
            break
    return context

# ================= RÉPONSE DELTA =================
def delta_response(user_id: str, user_message: str):
    save_memory(user_id, user_message)
    context = get_context(user_id)

    # Phrase style Jarvis
    context_note = ""
    if context:
        context_note = f"(Pour rappel : {context[0]['content']}) "

    # Résumé du message
    if len(user_message) < 15:
        user_message_summary = "ce que tu viens de dire"
    else:
        user_message_summary = f"'{user_message}'"

    response = f"Bien sûr, Boran. {context_note}J'ai compris {user_message_summary}. Que souhaites-tu que je fasse ensuite ?"
    return response

# ================= STREAMLIT UI =================
st.set_page_config(page_title="Delta Jarvis Chat 🤖", layout="centered")
st.title("Delta Jarvis 🤖")
st.write("💬 Discute avec Delta comme avec Jarvis. Écris ton message et appuie sur Entrée.")

# Historique de chat
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

user_id = "boran"

# Formulaire chat interactif
with st.form(key="chat_form", clear_on_submit=True):
    user_input = st.text_input("Écris ici...", placeholder="Tape ton message et appuie sur Entrée")
    submit = st.form_submit_button("Envoyer")

    if submit and user_input.strip() != "":
        # Ajouter ton message dans l'historique
        st.session_state.chat_history.append({"role": "user", "message": user_input})

        # Réponse Delta
        response = delta_response(user_id, user_input)
        st.session_state.chat_history.append({"role": "delta", "message": response})

# Affichage du chat
for chat in st.session_state.chat_history:
    if chat["role"] == "user":
        st.markdown(f"**Toi :** {chat['message']}")
    else:
        st.markdown(f"**Delta :** {chat['message']}")
