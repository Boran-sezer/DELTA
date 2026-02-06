import streamlit as st
from groq import Groq
# ... (gardez vos imports habituels Firebase)

# --- INITIALISATION DES ÉTATS DE SÉCURITÉ ---
if "locked_mode" not in st.session_state:
    st.session_state.locked_mode = False
if "attempts" not in st.session_state:
    st.session_state.attempts = 0
if "auth_action" not in st.session_state:
    st.session_state.auth_action = False

# --- FONCTION DE VÉROUILLAGE TOTAL ---
def check_lockdown():
    if st.session_state.locked_mode:
        st.error("🚨 SYSTÈME EN MODE VERROUILLAGE TOTAL (LOCKDOWN)")
        master_code = st.text_input("ENTREZ LE CODE MAÎTRE POUR RÉINITIALISER :", type="password")
        if st.button("DÉBLOQUER LE SYSTÈME"):
            if master_code == "B2008a2020@":
                st.session_state.locked_mode = False
                st.session_state.attempts = 0
                st.success("Système réinitialisé. DELTA est de nouveau en ligne.")
                st.rerun()
            else:
                st.error("CODE MAÎTRE INCORRECT. ACCÈS TOUJOURS REFUSÉ.")
        st.stop()

# --- VÉRIFICATION DU LOCKDOWN DÈS LE DÉBUT ---
check_lockdown()

st.title("⚡ DELTA IA")

# --- LOGIQUE DE CHAT ---
if p := st.chat_input("Ordres..."):
    # 1. On juge si l'action demande le code d'action (20082008)
    sensible = any(m in p.lower() for m in ["archive", "mémoire", "supprimer", "effacer", "montre tes notes"])
    # 2. On juge si l'utilisateur demande le verrouillage manuel
    demande_lock = any(m in p.lower() for m in ["verrouille", "lock", "sécurité max"])

    # CAS A : Demande de verrouillage manuel
    if demande_lock:
        st.warning("⚠️ Confirmation du verrouillage total requise.")
        m_code = st.text_input("Code Maître pour verrouiller :", type="password")
        if st.button("CONFIRMER LE LOCKDOWN"):
            if m_code == "B2008a2020@":
                st.session_state.locked_mode = True
                st.rerun()

    # CAS B : Action Sensible (Archives)
    elif sensible and not st.session_state.auth_action:
        st.info("🔒 Action protégée. Identification requise.")
        code_act = st.text_input("Code d'action (20082008) :", type="password")
        
        if st.button("Valider l'action"):
            if code_act == "20082008":
                st.session_state.auth_action = True
                st.session_state.attempts = 0
                st.rerun()
            else:
                st.session_state.attempts += 1
                st.error(f"Code incorrect. Tentative {st.session_state.attempts}/3")
                if st.session_state.attempts >= 3:
                    st.session_state.locked_mode = True
                    st.rerun()
    
    # CAS C : Réponse normale de l'IA
    else:
        # Code habituel de réponse avec Groq...
        st.write("DELTA exécute votre demande...")
