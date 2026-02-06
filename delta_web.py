import streamlit as st
from groq import Groq

# --- CONFIGURATION ---
CODE_ACTION = "20082008"
CODE_MAITRE = "B2008a2020@"

if "auth_action" not in st.session_state:
    st.session_state.auth_action = False
if "locked_mode" not in st.session_state:
    st.session_state.locked_mode = False
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- 1. SÉCURITÉ : MODE LOCKDOWN ---
if st.session_state.locked_mode:
    st.error("🚨 SYSTÈME VERROUILLÉ")
    master_input = st.text_input("Code Maître :", type="password")
    if st.button("Réinitialiser"):
        if master_input == CODE_MAITRE:
            st.session_state.locked_mode = False
            st.rerun()
    st.stop()

# --- 2. INTERFACE PRINCIPALE ---
st.title("⚡ DELTA IA")

# Affichage du chat
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# --- 3. LOGIQUE D'ENTRÉE ---
if p := st.chat_input("Ordres..."):
    # On vérifie si l'action est sensible
    actions_sensibles = ["archive", "supprimer", "mémoire", "effacer"]
    demande_sensible = any(mot in p.lower() for mot in actions_sensibles)

    if demande_sensible and not st.session_state.auth_action:
        # On enregistre le message pour plus tard
        st.session_state.temp_prompt = p 
        st.session_state.asking_code = True
    else:
        # Réponse normale de l'IA
        st.session_state.messages.append({"role": "user", "content": p})
        # (Ici votre appel à Groq...)
        st.rerun()

# --- 4. LE FORMULAIRE DE CODE (S'affiche seulement si besoin) ---
if st.session_state.get("asking_code", False):
    with st.chat_message("assistant"):
        st.warning("🔒 Identification requise pour accéder aux archives.")
        input_code = st.text_input("Entrez le code :", type="password", key="verif_code")
        
        if st.button("Confirmer"):
            if input_code == CODE_ACTION:
                st.session_state.auth_action = True
                st.session_state.asking_code = False
                # On traite le message qui était en attente
                st.success("Accès accordé.")
                st.rerun()
            else:
                st.error("Code incorrect.")
