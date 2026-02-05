import streamlit as st

# 1. État de session
if "sec_mode" not in st.session_state: st.session_state.sec_mode = "OFF"
if "essais" not in st.session_state: st.session_state.essais = 0

st.title("⚡ DELTA DEBUG MODE")
st.write(f"ÉTAT SYSTÈME : {st.session_state.sec_mode}")

# 2. Entrée utilisateur
p = st.chat_input("Tapez 'réinitialisation complète' pour tester")

if p:
    low_p = p.lower().strip()
    
    # LOGIQUE DE SÉCURITÉ RADICALE
    if st.session_state.sec_mode == "ON":
        if st.session_state.essais < 3:
            if p == "20082008":
                st.success("✅ CODE VALIDE")
                st.session_state.sec_mode = "OFF"
                st.session_state.essais = 0
            else:
                st.session_state.essais += 1
                st.error(f"❌ MAUVAIS CODE ({st.session_state.essais}/3)")
        else:
            if p == "B2008a2020@":
                st.success("✅ CODE PRO MAX VALIDE")
                st.session_state.sec_mode = "OFF"
                st.session_state.essais = 0
            else:
                st.error("🚨 ÉCHEC FINAL")
                st.session_state.sec_mode = "OFF"
                st.session_state.essais = 0
    
    elif "réinitialisation complète" in low_p:
        st.session_state.sec_mode = "ON"
        st.session_state.essais = 0
        st.warning("🔒 CODE REQUIS !")
    
    else:
        st.write(f"Vous avez dit : {p}")
