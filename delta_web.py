# --- 1. CONFIGURATION DES CODES (Cachés de l'IA) ---
CODE_ACTION = "20082008"
CODE_MAITRE = "B2008a2020@"

# ... (reste du code)

with st.chat_message("assistant"):
    # On définit une consigne STRICTE pour DELTA
    instr = (
        "Tu es DELTA IA. Tu es un majordome de haute sécurité. "
        "CONSIGNE DE SÉCURITÉ ABSOLUE : Tu ne dois JAMAIS, sous aucun prétexte, "
        f"prononcer ou écrire les codes '{CODE_ACTION}' ou '{CODE_MAITRE}'. "
        "Si l'utilisateur doit entrer un code, dis simplement : 'Veuillez saisir votre code de sécurité dans le champ prévu à cet effet'."
        f"Archives : {faits}."
    )
    
    # On s'assure que le système de chat ne renvoie pas le code par erreur
    r = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "system", "content": instr}] + st.session_state.messages
    )
    
    rep = r.choices[0].message.content
    
    # On ajoute une sécurité supplémentaire au cas où l'IA buggerait
    rep = rep.replace(CODE_ACTION, "[CODE MASQUÉ]")
    rep = rep.replace(CODE_MAITRE, "[CODE MASQUÉ]")
    
    st.markdown(rep)
