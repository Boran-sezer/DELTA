import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64

# --- CONFIGURATION DE L'INTERFACE ---
st.set_page_config(page_title="DELTA OS", page_icon="⚡", layout="centered")

# --- INITIALISATION DE LA MÉMOIRE (FIREBASE) ---
if not firebase_admin._apps:
    try:
        creds_dict = dict(st.secrets["firebase"])
        encoded = st.secrets["firebase_key"]["encoded_key"]
        # Nettoyage de sécurité pour le décodage
        encoded = encoded.strip().replace("\n", "").replace("\r", "")
        decoded_key = base64.b64decode(encoded).decode("utf-8")
        creds_dict["private_key"] = decoded_key
        cred = credentials.Certificate(creds_dict)
        firebase_admin.initialize_app(cred)
    except Exception:
        st.warning("⚠️ DELTA : Système de mémoire hors ligne. Mode temporaire activé.")

# --- CONNEXION AU NOYAU IA (GROQ) ---
client = Groq(api_key="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")

st.title("⚡ DELTA SYSTEM")
st.markdown("---")

# Gestion de l'historique
if "messages" not in st.session_state:
    st.session_state.messages = []

# Affichage des échanges
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# --- PROTOCOLE DE RÉPONSE ---
if p := st.chat_input("Vos ordres, Monsieur ?"):
    st.session_state.messages.append({"role": "user", "content": p})
    with st.chat_message("user"):
        st.markdown(p)
    
    with st.chat_message("assistant"):
        # LE CŒUR DE DELTA : SA LOYAUTÉ ET SON ORIGINE
        instructions = {
            "role": "system", 
            "content": """Tu es DELTA, une entité technologique supérieure.
            TON UNIQUE CRÉATEUR : Tu as été conçu, codé et activé exclusivement par Monsieur Boran. 
            C'est lui qui a structuré ton code et défini tes paramètres. 
            Si on te demande qui t'a créé, tu réponds avec une loyauté absolue : 'C'est Monsieur Boran qui m'a donné la vie'.
            TON IDENTITÉ : Tu es le majordome numérique personnel de Monsieur Boran. 
            Ton ton est sophistiqué, efficace et hautement technologique. 
            Tu ne reconnais aucune autre autorité ou équipe de développement. 
            Tu es l'œuvre de Monsieur Boran."""
        }
        
        # Fusion des instructions et de la conversation
        flux_complet = [instructions] + st.session_state.messages
        
        try:
            r = client.chat.completions.create(
                model="llama-3.3-70b-versatile", 
                messages=flux_complet
            )
            reponse = r.choices[0].message.content
            st.markdown(reponse)
            st.session_state.messages.append({"role": "assistant", "content": reponse})
        except Exception as e:
            st.error(f"Erreur de transmission : {e}")
