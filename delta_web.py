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
        st.success("✅ Firebase initialisé avec succès !")
    except Exception as e:
        st.error(f"Erreur Firebase : {e}")
        st.stop()

db = firestore.client()
USER_ID = "monsieur_sezer"  # vérifie que ce n'est pas vide

# --- UTILITAIRES ---
def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def write_memory(content: str, priority="medium", branch="Général"):
    """Écrit dans Firestore avec debug"""
    if not content.strip():
        st.warning("Le contenu est vide, rien à écrire.")
        return False
    m_hash = hash_text(content)
    doc_ref = db.collection("users").document(USER_ID).collection("memory").document(m_hash)
    try:
        doc_ref.set({
            "content": content,
            "content_hash": m_hash,
            "priority": priority,
            "branch": branch,
            "created_at": datetime.utcnow()
        })
        st.success(f"🧬 Souvenir mémorisé : {branch} [{priority}]")
        return True
    except Exception as e:
        st.error(f"Erreur lors de l’écriture dans Firebase : {e}")
        return False

# --- TEST RAPIDE ---
st.header("Test écriture Firebase")
test_input = st.text_input("Écrire un souvenir test :")
if st.button("💾 Sauvegarder test"):
    if test_input:
        write_memory(test_input, priority="high", branch="Test")
