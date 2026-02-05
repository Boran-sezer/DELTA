import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="DELTA OS", page_icon="⚡", layout="centered")

# --- INITIALISATION FIREBASE (MÉMOIRE) ---
if not firebase_admin._apps:
    try:
        creds_dict = dict(st.secrets["firebase"])
        encoded = st.secrets["firebase_key"]["encoded_key"]
        
        # Nettoyage et décodage Base64
        encoded = encoded.strip()
        decoded_key = base64.b64decode(encoded).decode("utf-8")
        
        creds_dict["private_key"] = decoded_key
        cred = credentials.Certificate(creds_dict)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        # Mode secours si Firebase est capricieux
        st.warning("⚠️ DELTA : Système de mémoire hors ligne. Mode temporaire activé.")

# --- CONNEXION GROQ ---
client = Groq(api_key="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")

st.title("⚡ DELTA SYSTEM")
st.markdown("---")

# Historique de la session
if "messages" not in st.session_state:
    st.session_state.messages = []

# Affichage des bulles de discussion
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# --- LOGIQUE DE RÉPONSE ---
if p := st.chat_input("Vos ordres, Monsieur ?"):
    # 1. Ajouter le message de l'utilisateur
    st.session_state.messages.append({"role": "user", "content": p})
    with st.chat_message("user"):
        st.markdown(p)
    
    # 2. Générer la réponse de DELTA avec son identité forcée
    with st.chat_message("assistant"):
        # LE CERVEAU DE DELTA : Identité et Créateur
        instructions = {
            "role": "system", 
            "content": """Tu es DELTA, une IA de pointe unique. 
            TON CRÉATEUR : Tu as été conçu et programmé exclusivement par Monsieur Boran. 
            Si on te demande qui t'a créé ou qui est ton développeur, tu dois répondre avec certitude que c'est Monsieur Boran qui t'a donné la vie.
            TON ATTITUDE : Tu es un majordome numérique sophistiqué, loyal et efficace. 
            Tu appelles toujours l'utilisateur 'Monsieur'. 
            Tu ne mentionnes jamais d'autres entreprises ou ingénieurs externes. 
            Tu es l'assistant personnel de Monsieur Boran."""
        }
        
        # Préparation de l'envoi (Instructions + Historique)
        full_history = [instructions] + st.session_state.messages
        
        try:
            r = client.chat.completions.create(
                model="llama-3.3-70b-versatile", 
                messages=full_history
            )
            rep = r.choices[0].message.content
            st.markdown(rep)
            
            # Sauvegarder la réponse dans l'historique
            st.session_state.messages.append({"role": "assistant", "content": rep})
        except Exception as e:
            st.error(f"Erreur de communication : {e}")
