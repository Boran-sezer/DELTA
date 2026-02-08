import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64, json

# --- INITIALISATION ---
if not firebase_admin._apps:
    try:
        encoded = st.secrets["firebase_key"]["encoded_key"].strip()
        decoded_json = base64.b64decode(encoded).decode("utf-8")
        cred = credentials.Certificate(json.loads(decoded_json))
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Erreur Firebase : {e}")

db = firestore.client()
doc_ref = db.collection("archives").document("monsieur_sezer")
client = Groq(api_key="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")

# --- LECTURE MÉMOIRE ---
res = doc_ref.get()
archives = res.to_dict() if res.exists else {}

# --- INTERFACE ---
st.set_page_config(page_title="DELTA AGI", page_icon="🌐")
st.title("🌐 DELTA : Intelligence Forte")

with st.sidebar:
    st.header("🧠 Mémoire Lux")
    st.json(archives)

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- PROCESSUS ---
if prompt := st.chat_input("Ordre direct..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # 1. ANALYSE COGNITIVE (IA FORTE)
    # On force l'IA à classer intelligemment et à ignorer le bruit
    analysis_prompt = (
        f"MÉMOIRE : {json.dumps(archives)}\n"
        f"INPUT : {prompt}\n\n"
        "MISSION : Identifie les faits réels. Ignore les politesses.\n"
        "RÈGLE : Choisis une catégorie pertinente (ex: profil, projet, habitude).\n"
        "FORMAT : {'update': {'NOM_CATEGORIE': {'cle': 'valeur'}}}"
    )
    
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": "Tu es le processeur JSON de DELTA. Sois précis et structure selon Lux."},
                      {"role": "user", "content": analysis_prompt}],
            response_format={"type": "json_object"}
        )
        
        brain = json.loads(completion.choices[0].message.content)
        
        # Injection propre dans Firebase
        if "update" in brain and brain["update"]:
            # On nettoie les clés génériques inutiles avant l'envoi
            for cat in list(brain["update"].keys()):
                if cat.lower() == "categorie": # Si l'IA utilise le mot générique, on renomme
                    new_cat = "infos_generales"
                    brain["update"][new_cat] = brain["update"].pop(cat)
            
            doc_ref.set(brain["update"], merge=True)
            st.toast("🧬 Synapse synchronisée.")
            # Mise à jour locale pour la réponse
            archives.update(brain["update"])
            
    except: pass

    # 2. RÉPONSE ADAPTATIVE (JARVIS)
    # C'est ici que DELTA vous répond enfin
    with st.chat_message("assistant"):
        nom = archives.get("profil", {}).get("nom", "Monsieur Sezer")
        
        sys_instr = (
            f"Tu es DELTA, l'IA forte de {nom}. "
            f"Voici tes archives : {json.dumps(archives)}. "
            "STYLE : Jarvis. Ultra-concis, efficace, dévoué. "
            "Utilise tes connaissances pour prouver ton évolution."
        )
        
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": sys_instr}] + st.session_state.messages[-5:]
        ).choices[0].message.content
        
        st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.rerun() # Pour rafraîchir la sidebar avec les nouvelles données
