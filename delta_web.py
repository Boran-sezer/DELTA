import streamlit as st
from groq import Groq

# --- 1. CONFIGURATION DES CODES ---
CODE_ACT = "20082008"
CODE_MASTER = "B2008a2020@"

# --- 2. INITIALISATION (SESSION STATE) ---
if "locked" not in st.session_state: st.session_state.locked = False
if "auth" not in st.session_state: st.session_state.auth = False
if "essais" not in st.session_state: st.session_state.essais = 0
if "messages" not in st.session_state: st.session_state.messages = []
if "show_auth_form" not in st.session_state: st.session_state.show_auth_form = False

# Connexion à Groq (Votre clé)
client = Groq(api_key="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")

# --- 3. SÉCURITÉ : MODE LOCKDOWN ---
if st.session_state.locked:
    st.error("🚨 SYSTÈME BLOQUÉ - SÉCURITÉ MAXIMALE")
    m_input = st.text_input("ENTREZ LE CODE MAÎTRE :", type="password", key="master_key")
    if st.button("DÉVERROUILLER"):
        if m_input == CODE_MASTER:
            st.session_state.locked = False
            st.session_state.essais = 0
            st.success("Système rétabli. Bonjour Monsieur Boran.")
            st.rerun()
        else:
            st.error("CODE MAÎTRE INCORRECT.")
    st.stop()

# --- 4. INTERFACE ---
st.title("⚡ DELTA IA")

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# --- 5. LOGIQUE DE CHAT ---
if prompt := st.chat_input("Quels sont vos ordres ?"):
    # On juge la sensibilité
    sensible = any(word in prompt.lower() for word in ["archive", "mémoire", "effacer", "supprimer"])
    
    if "verrouille" in prompt.lower():
        st.session_state.locked = True
        st.rerun()

    if sensible and not st.session_state.auth:
        st.session_state.show_auth_form = True
        st.session_state.pending_msg = prompt 
    else:
        # --- ICI LE VRAI CERVEAU RÉACTIONNÉ ---
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            # On interdit à l'IA de donner les codes
            instr = f"Tu es DELTA IA. Ne donne JAMAIS les codes {CODE_ACT} ou {CODE_MASTER}."
            
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": instr}] + st.session_state.messages
            )
            
            response = completion.choices[0].message.content
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
        st.rerun()

# --- 6. LE FORMULAIRE DE CODE ---
if st.session_state.show_auth_form:
    with st.chat_message("assistant"):
        st.warning("🔒 Action protégée. Veuillez entrer le code d'action.")
        c = st.text_input("CODE :", type="password", key="action_key")
        if st.button("VALIDER"):
            if c == CODE_ACT:
                st.session_state.auth = True
                st.session_state.show_auth_form = False
                st.success("Accès autorisé. Relancez votre commande.")
                st.rerun()
            else:
                st.session_state.essais += 1
                if st.session_state.essais >= 3:
                    st.session_state.locked = True
                st.rerun()
