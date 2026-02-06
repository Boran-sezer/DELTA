import streamlit as st
from groq import Groq

# --- 1. CONFIGURATION DES CODES (A déplacer dans st.secrets plus tard) ---
CODE_ACTION = "20082008"
CODE_MAITRE = "B2008a2020@"

# --- 2. INITIALISATION DES ÉTATS (Le cerveau de l'app) ---
if "locked" not in st.session_state: st.session_state.locked = False
if "auth" not in st.session_state: st.session_state.auth = False
if "essais" not in st.session_state: st.session_state.essais = 0
if "messages" not in st.session_state: st.session_state.messages = []
if "attente_code" not in st.session_state: st.session_state.attente_code = False

# --- 3. ÉCRAN DE VERROUILLAGE TOTAL (LOCKDOWN) ---
if st.session_state.locked:
    st.error("🚨 SYSTÈME BLOQUÉ - SÉCURITÉ MAXIMALE")
    unlock = st.text_input("Entrez le code MAÎTRE (B...)", type="password")
    if st.button("DÉVERROUILLER LE NOYAU"):
        if unlock == CODE_MAITRE:
            st.session_state.locked = False
            st.session_state.essais = 0
            st.success("Système rétabli.")
            st.rerun()
        else:
            st.error("Code incorrect.")
    st.stop() # Arrête tout le reste ici

# --- 4. INTERFACE PRINCIPALE ---
st.title("⚡ DELTA IA")

# Affichage du chat historique
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# --- 5. ZONE DE SAISIE ET LOGIQUE ---
prompt = st.chat_input("Ordres...")

if prompt:
    # On détecte si c'est une demande sensible
    actions_privees = ["archive", "mémoire", "effacer", "supprimer", "montre"]
    is_sensible = any(x in prompt.lower() for x in actions_privees)
    
    # On détecte si vous demandez le verrouillage manuel
    if "verrouille" in prompt.lower():
        st.session_state.locked = True
        st.rerun()

    if is_sensible and not st.session_state.auth:
        st.session_state.attente_code = True
        st.session_state.dernier_prompt = prompt # On garde l'idée en mémoire
    else:
        # Réponse IA normale
        st.session_state.messages.append({"role": "user", "content": prompt})
        # Simulation réponse IA (Remplacez par votre appel Groq)
        reponse = "Je traite votre demande..." 
        st.session_state.messages.append({"role": "assistant", "content": reponse})
        st.rerun()

# --- 6. LE POP-UP DE SÉCURITÉ (S'affiche par-dessus le reste) ---
if st.session_state.attente_code:
    with st.chat_message("assistant"):
        st.warning("🔒 Action protégée. Veuillez entrer le code d'action.")
        c = st.text_input("Code (2008...) :", type="password", key="pwd_zone")
        if st.button("Valider l'accès"):
            if c == CODE_ACTION:
                st.session_state.auth = True
                st.session_state.attente_code = False
                st.success("Accès autorisé. Répétez votre commande, Monsieur.")
                st.rerun()
            else:
                st.session_state.essais += 1
                if st.session_state.essais >= 3:
                    st.session_state.locked = True
                    st.rerun()
                st.error(f"Erreur ({st.session_state.essais}/3)")
