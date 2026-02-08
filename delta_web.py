import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import hashlib

# ================= INIT FIREBASE =================
if not firebase_admin._apps:
    cred_json = st.secrets["firebase_key"]  # clé Firebase dans Streamlit secrets
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
    """Filtre les messages inutiles"""
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
        return "Ignoré (inutile)"
    category = categorize_message(content)
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
    return f"Mémoire enregistrée sous [{category}]"

def get_context(user_id: str, limit: int = 5):
    """Récupère le contexte récent pour Delta"""
    memories = db.collection("users").document(user_id).collection("memory") \
                 .order_by("created_at", direction=firestore.Query.DESCENDING) \
                 .limit(limit).stream()
    return [m.to_dict() for m in memories]

# ================= RÉPONSE JARVIS =================
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

    # Exemple simple de réponse stylée
    response = f"{intro}{context_note}J'ai bien compris : '{user_message}'. Que souhaites-tu que je fasse ensuite ?"
    return response

# ================= STREAMLIT UI =================
st.set_page_config(page_title="Delta Jarvis 🤖", layout="centered")
st.title("Delta Jarvis 🤖")
st.write("💬 Écris ton message et Delta va te répondre avec style, se souvenir et garder le contexte.")

user_id = "boran"

# Chat input
user_input = st.text_input("Ton message ici")

if st.button("Envoyer"):
    if user_input.strip() == "":
        st.warning("Écris quelque chose avant d'envoyer !")
    else:
        response = delta_response(user_id, user_input)
        st.success(response)

# Bouton pour voir le contexte actuel
if st.button("Afficher le contexte"):
    context = get_context(user_id)
    if not context:
        st.write("Aucune mémoire enregistrée pour l'instant.")
    else:
        st.write("🧠 Contexte actuel de Delta :")
        for mem in context:
            st.write(f"- [{mem['category']}] {mem['content']} (Confiance : {mem['confidence']})")
