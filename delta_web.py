import streamlit as st

# --- CONFIGURATION DE LA PAGE & STYLE ---
st.set_page_config(page_title="DELTA IA", page_icon="⚡")

# --- SYSTÈME DE VÉROUILLAGE (ÉTAPE 1) ---
def check_password():
    """Vérifie si le code secret est correct."""
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if not st.session_state["authenticated"]:
        # Écran de verrouillage épuré
        st.markdown("<h1 style='text-align: center;'>🔒 DELTA IA SYSTÈME</h1>", unsafe_allow_html=True)
        st.write("---")
        
        # Champ de saisie pour le code
        code_entre = st.text_input("Veuillez entrer le code d'accès :", type="password")
        
        if st.button("Déverrouiller"):
            if code_entre == "20082008":
                st.session_state["authenticated"] = True
                st.success("Accès autorisé, Monsieur Boran. Initialisation...")
                st.rerun() # Relance l'app pour afficher le contenu
            else:
                st.error("Code incorrect. Accès refusé.")
        return False
    return True

# --- LANCEMENT DU SYSTÈME ---
if check_password():
    # Tout le reste de votre code (Chat, Logo, Groq, Firebase) va ici
    st.title("⚡ DELTA IA")
    st.write("Système opérationnel. Que puis-je faire pour vous ?")
    
    # C'est ici qu'on placera la suite (Archivage et Contrôle PC)
