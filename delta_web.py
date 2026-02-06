# --- (Parties 1 à 4 identiques au code précédent) ---

    # --- 5. RÉPONSE AVEC EFFET DE FRAPPE ET SECOURS INTELLIGENT ---
    with st.chat_message("assistant"):
        instruction_delta = (
            f"Tu es DELTA. Créateur : Monsieur Sezer Boran. "
            f"Mémoire : {archives}. Sois extrêmement concis. "
            "INTERDICTION : Ne réponds jamais par des phrases automatiques comme 'Système opérationnel'."
        )
        
        placeholder = st.empty()
        full_response = ""
        
        try:
            # Essai avec le modèle principal (70b)
            stream = client.chat.completions.create(
                model="llama-3.3-70b-versatile", 
                messages=[{"role": "system", "content": instruction_delta}] + st.session_state.messages,
                temperature=0.3,
                stream=True
            )
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    full_response += chunk.choices[0].delta.content
                    placeholder.markdown(full_response + "▌")
            
        except Exception:
            # Secours avec le modèle rapide (8b) au lieu d'une phrase générique
            try:
                resp = client.chat.completions.create(
                    model="llama-3.1-8b-instant", 
                    messages=[{"role": "system", "content": instruction_delta}] + st.session_state.messages
                )
                full_response = resp.choices[0].message.content
            except:
                full_response = "Une erreur technique est survenue, Monsieur Sezer. Je reste à votre écoute."

        placeholder.markdown(full_response)
        st.session_state.messages.append({"role": "assistant", "content": full_response})
