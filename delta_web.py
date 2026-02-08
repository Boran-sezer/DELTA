import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import hashlib

# ===== INIT FIREBASE =====
if not firebase_admin._apps:
    cred_json = st.secrets["firebase_key"]  # récupère ta clé Firebase depuis les secrets
    cred = credentials.Certificate(cred_json)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# ===== UTILS =====
def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def is_memory_worthy(text: str) -> bool:
    blacklist = ["salut", "ok", "mdr", "lol", "?", "oui", "non"]
    if len(text.strip()) < 15:
        return False
    if text.lower().strip() in blacklist:
        return False
    return True

# ===== MÉMOIRE =====
def save_memory(user_id: str, category: str, content: str, confidence: float = 0.9):
    if not is_memory_worthy(content):
        return "Ignoré (inutile)"
    memory_hash = hash_text(content)
    ref = db.collection("users").document(user_id).collection("memory").document(memory_hash)
    if ref.get().exists:
        return "Déjà en mémoire"
    ref.set({
        "category": category,
        "content": content,
        "created_at": datetime.utcnow(),
        "confidence": confidence
    })
    return "Mémoire enregistrée"

def get_context(user_id: str, limit: int = 5):
    memories = db.collection("users").document(user_id).collection("memory") \
                 .order_by("created_at", direction=firestore.Query.DESCENDING) \
                 .limit(limit).stream()
    return [m.to_dict() for m in memories]

# ===== RÉPONSE STYLE JARVIS =====
def format_response(user_id: str, user_message: str):
    context = get_context(user_id)
    intro = "Bien sûr, Boran. "
    context_note = ""
    if context:
        context_note = f"(Pour rappel : {context[0]['content']}) "
    return f"{intro}{context_note}{user_message}"

# ===== STREAMLIT UI =====
st.set_page_config(page_title="Delta Jarvis 🤖", layout="centered")
st.title("Delta Jarvis 🤖")
st.write("Tape ton message, et Jarvis va te répondre en style intelligent avec mémoire.")

user_id = "boran"

# Input utilisateur
user_input = st.text_input("💬 Ton message ici")

if st.button("Envoyer"):
    if user_input.strip() == "":
        st.warning("Écris quelque chose avant d'envoyer !")
    else:
        # Sauvegarde mémoire
        save_msg = save_memory(user_id, "conversation", user_input)
        st.info(f"Mémoire : {save_msg}")

        # Génère réponse Jarvis
        response = format_response(user_id, f"Réponse : {user_input}")
        st.success(response)

# Voir contexte actuel
if st.button("Afficher le contexte"):
    context = get_context(user_id)
    if not context:
        st.write("Aucune mémoire enregistrée pour l'instant.")
    else:
        for mem in context:
            st.write(f"- [{mem['category']}] {mem['content']} (Confiance : {mem['confidence']})")
