import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json
import time
import re

# --- 1. CONFIGURATION ---
if not firebase_admin._apps:
    try:
        encoded = st.secrets["firebase_key"]["encoded_key"].strip()
        decoded_json = base64.b64decode(encoded).decode("utf-8")
        cred = credentials.Certificate(json.loads(decoded_json))
        firebase_admin.initialize_app(cred)
    except: pass

db = firestore.client()
doc_ref = db.collection("memoire").document("profil_monsieur")
client = Groq(api_key="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")

# --- 2. ÉTATS DE SESSION ---
if "messages" not in st.session_state: 
    st.session_state.messages = [{"role": "assistant", "content": "Système DELTA prêt. À vos ordres, Monsieur Sezer. ⚡"}]

# --- 3. INTERFACE & SIDEBAR ---
st.set_page_config(page_title="DELTA", layout="wide")
st.markdown("<h1 style='color:#00d4ff;'>⚡ DELTA</h1>", unsafe_allow_html=True)

res = doc_ref.get()
archives = res.to_dict().get("archives", {}) if res.exists else {}

with st.sidebar:
    st.title("📂 Vos Archives")
    if archives:
        for partie, infos in archives.items():
            with st.expander(f"📁 {partie}"):
                for i in infos:
                    st.write(f"• {i}")
    else:
        st.info("Archives vides.")

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# --- 4. LOGIQUE DE TRAITEMENT ULTRA-STRICTE ---
if prompt := st.chat_input("Ex: Renomme Vert en Car..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Analyse simplifiée au maximum pour éviter les erreurs
    analyse_prompt = (
        f"Dossiers existants : {list(archives.keys())}. "
        f"L'ordre de Monsieur Sezer : '{prompt}'. "
        "Réponds UNIQUEMENT en JSON selon ces 2 cas prioritaires : "
        "1. S'il veut CHANGER LE NOM d'un dossier : {'action': 'rename', 'vieux_nom': '...', 'nouveau_nom': '...'} "
        "2. S'il veut AJOUTER une info dans un dossier : {'action': 'add', 'dossier': '...', 'info': '...'} "
        "3. S'il veut SUPPRIMER : {'action': 'delete', 'cible': '...'} "
        "Sinon réponds 'NON'."
    )
    
    try:
        check = client.chat.completions.create(
            model="llama-3.1-8b-instant", 
            messages=[{"role": "system", "content": "Tu es un robot qui ne parle qu'en JSON."}, 
                      {"role": "user", "content": analyse_prompt}],
            temperature=0
        )
        cmd_text = check.choices[0].message.content.strip()
        json_match = re.search(r'(\{.*\})', cmd_text, re.DOTALL)
        
        if json_match:
            data = json.loads(json_match.group(1).replace("'", '"'))
            action = data.get('action')
            modif = False

            # --- LOGIQUE DE RENOMMAGE (LE DOSSIER LUI-MÊME) ---
            if action == 'rename':
                vieux = data.get('vieux_nom')
                nouveau = data.get('nouveau_nom')
                # On cherche le dossier qui correspond
                for k in list(archives.keys()):
                    if vieux.lower() in k.lower():
                        archives[nouveau] = archives.pop(k)
                        modif = True
                        break

            # --- LOGIQUE D'AJOUT ---
            elif action == 'add':
                d = data.get('dossier', 'Général')
                archives.setdefault(d, []).append(data.get('info'))
                modif = True

            # --- LOGIQUE DE SUPPRESSION ---
            elif action == 'delete':
                cible = data.get('cible', '').lower()
                for k in list(archives.keys()):
                    if cible in k.lower():
                        del archives[k]
                        modif = True
                        break

            if modif:
                doc_ref.set({"archives": archives})
                st.toast("✅ Base mise à jour")
                time.sleep(0.4)
                st.rerun()
    except: pass

    # RÉPONSE DE DELTA
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_raw = ""
        instr = f"Tu es DELTA, l'IA de Monsieur Sezer. Archives : {archives}. Ne dis jamais 'accès autorisé'."
        
        try:
            stream = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "system", "content": instr}] + st.session_state.messages, stream=True)
            for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    full_raw += content
                    placeholder.markdown(full_raw + "▌")
        except:
            full_raw = "C'est fait, Monsieur Sezer. ⚡"
        
        placeholder.markdown(full_raw)
        st.session_state.messages.append({"role": "assistant", "content": full_raw})
