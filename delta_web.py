import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64, json

# --- CONFIGURATION ---
GROQ_API_KEY = "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"

# --- CONNEXION FIREBASE ---
if not firebase_admin._apps:
    try:
        encoded = st.secrets["firebase_key"]["encoded_key"].strip()
        decoded_json = base64.b64decode(encoded).decode("utf-8")
        cred = credentials.Certificate(json.loads(decoded_json))
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Erreur d'accès : {e}")

db = firestore.client()
doc_ref = db.collection("archives").document("monsieur_sezer")
client = Groq(api_key=GROQ_API_KEY)

# --- CHARGEMENT DES ARCHIVES ---
res = doc_ref.get()
archives = res.to_dict() if res.exists else {}

# --- INTERFACE ---
st.set_page_config(page_title="DELTA", page_icon="🦾")
st.markdown("<style>#MainMenu, footer, header {visibility:hidden;}</style>", unsafe_allow_html=True)
st.title("DELTA - Core Operation")

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- CORE ENGINE ---
if prompt := st.chat_input("Ordre direct..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # 1. EXTRACTION PURIFIÉE (Llama 70B)
    brain_prompt = (
        f"ARCHIVES : {json.dumps(archives)}\n"
        f"MESSAGE : '{prompt}'\n\n"
        "MISSION : Extrais les faits réels. \n"
        "INTERDICTIONS :\n"
        "- Ne jamais enregistrer de salutations (salut, bonjour).\n"
        "- Ne jamais enregistrer les mots techniques (mission, ordre, analyse, greeting).\n"
        "FORMAT : {'update': {'categorie': {'clé': 'valeur'}}} ou {'delete': {'catégorie': 'clé'}}."
    )
    
    try:
        analysis = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": "Extracteur JSON chirurgical. Tu ignores le bruit et les politesses."},
                      {"role": "user", "content": brain_prompt}],
            response_format={"type": "json_object"}
        ).choices[0].message.content
        
        cmd = json.loads(analysis)
        
        # Action : Suppression
        if "delete" in cmd:
            cat, key = list(cmd["delete"].items())[0]
            doc_ref.update({f"{cat}.{key}": firestore.DELETE_FIELD})
            st.toast(f"🗑️ Archive '{key}' effacée.")
            if cat in archives: archives[cat].pop(key, None)
            
        # Action : Mise à jour avec filtrage final
        elif "update" in cmd:
            clean_update = {}
            for cat, data in cmd["update"].items():
                # On élimine les clés interdites manuellement pour sécurité
                clean_data = {k: v for k, v in data.items() if k.lower() not in ["mission", "ordre", "analyse", "greeting"]}
                if clean_data:
                    clean_update[cat] = clean_data
            
            if clean_update:
                doc_ref.set(clean_update, merge=True)
                for cat, data in clean_update.items():
                    if cat not in archives: archives[cat] = {}
                    archives[cat].update(data)
                st.toast("🧬 Mémoire synchronisée.")
    except:
        pass

    # 2. RÉPONSE JARVIS (Llama 70B)
    with st.chat_message("assistant"):
        nom_appel = archives.get("profil", {}).get("nom", "Monsieur Sezer")
        
        sys_instr = (
            f"Tu es DELTA, l'IA de {nom_appel}. "
            f"ARCHIVES : {json.dumps(archives)}. "
            "STYLE : Jarvis. Précis, distingué, ultra-concis. "
            "Réponds directement sans politesse inutile si la conversation est lancée."
        )
        
        res_ai = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": sys_instr}] + st.session_state.messages[-4:],
        ).choices[0].message.content
        
        st.markdown(res_ai)
        st.session_state.messages.append({"role": "assistant", "content": res_ai})
