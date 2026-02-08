import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import hashlib

# ===== INIT FIREBASE =====
if not firebase_admin._apps:
    cred = credentials.Certificate("firebase_key.json")  # ta clé Firebase
    firebase_admin.initialize_app(cred)

db = firestore.client()

# ===== UTILS =====
def hash_text(text: str) -> str:
    """Empêche les doublons"""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def is_memory_worthy(text: str) -> bool:
    """Filtre ce qui mérite d’être mémorisé"""
    blacklist = ["salut", "ok", "mdr", "lol", "?", "oui", "non"]
    if len(text.strip()) < 15:
        return False
    if text.lower().strip() in blacklist:
        return False
    return True

# ===== MÉMOIRE =====
def save_memory(user_id: str, category: str, content: str, confidence: float = 0.9):
    """Enregistre une mémoire utile"""
    if not is_memory_worthy(content):
        return "Ignoré (inutile)"

    memory_hash = hash_text(content)

    ref = db.collection("users") \
            .document(user_id) \
            .collection("memory") \
            .document(memory_hash)

    if ref.get().exists:
        return "Déjà en mémoire"

    ref.set({
        "category": category,
        "content": content,
        "created_at": datetime.utcnow(),
        "confidence": confidence
    })

    return "Mémoire enregistrée"

def load_memories(user_id: str, category: str = None, limit: int = 10):
    """Récupère les mémoires importantes"""
    query = db.collection("users") \
              .document(user_id) \
              .collection("memory") \
              .order_by("created_at", direction=firestore.Query.DESCENDING)

    if category:
        query = query.where("category", "==", category)

    docs = query.limit(limit).stream()
    return [doc.to_dict() for doc in docs]

def clean_memory(user_id: str):
    """Supprime les mémoires peu fiables ou obsolètes"""
    memories = db.collection("users") \
                 .document(user_id) \
                 .collection("memory") \
                 .stream()

    deleted = 0
    for mem in memories:
        data = mem.to_dict()
        if data.get("confidence", 1) < 0.5:
            mem.reference.delete()
            deleted += 1

    return f"{deleted} mémoires supprimées"

# ===== CONTEXTE CONVERSATIONNEL =====
def get_context(user_id: str, limit: int = 5):
    """Récupère les dernières mémoires importantes pour le contexte"""
    memories = db.collection("users") \
                 .document(user_id) \
                 .collection("memory") \
                 .order_by("created_at", direction=firestore.Query.DESCENDING) \
                 .limit(limit).stream()
    return [m.to_dict() for m in memories]

# ===== RÉPONSE STYLE JARVIS =====
def format_response(user_id: str, content: str):
    """Formate la réponse façon Jarvis"""
    context = get_context(user_id)
    intro = "Bien sûr, Boran. "
    context_note = ""

    if context:
        context_note = f"(Pour rappel : {context[0]['content']}) "

    return f"{intro}{context_note}{content}"

# ===== EXEMPLE D'UTILISATION =====
if __name__ == "__main__":
    user_id = "boran"

    # 1. Ajouter une mémoire
    print(save_memory(user_id, "preference_utilisateur", "Boran aime les IA intelligentes et stylées.", 0.95))

    # 2. Ajouter une autre mémoire
    print(save_memory(user_id, "projets", "Créer un assistant virtuel façon Jarvis.", 0.98))

    # 3. Charger le contexte
    context = get_context(user_id)
    print("Contexte :", context)

    # 4. Réponse Jarvis
    response = format_response(user_id, "Je peux lancer votre programme principal dès maintenant.")
    print(response)

    # 5. Nettoyer la mémoire (optionnel)
    print(clean_memory(user_id))
