import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json

# --- CONFIGURATION ---
st.set_page_config(page_title="DELTA OS", page_icon="⚡", layout="wide")

# --- ÉTATS DE SESSION (LE MOTEUR QUI MARCHE) ---
if "messages" not in st.session_state: st.session_state.messages = []
if "security_mode" not in st.session_state: st.session_state.security_mode = False
if "attempts" not in st.session_state: st.session_state.attempts = 0

# --- INITIALISATION FIREBASE ---
if not firebase_admin._apps:
    try:
        encoded = st.secrets["firebase_key"]["encoded_key"].strip()
        decoded_json = base64.b64decode(encoded).decode("utf-8")
        cred = credentials.Certificate(json.loads(decoded_json))
        firebase_admin.initialize_app(cred)
    except: pass

db = firestore.client()
doc_profil = db.collection("memoire").document("profil_monsieur")
client = Groq(api_key="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")

# --- CHARGEMENT DES ARCHIVES ---
res_profil = doc_profil.get()
data = res_profil.to_dict() if res_profil.exists else {}
faits_publics = data.get("faits", [])

# --- SIDEBAR ---
with st.sidebar:
    st.title("🧠 Archives")
    for f in faits_publics:
        st.info(f)

# --- CHAT ---
for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

if p := st.chat_input("Vos ordres, Monsieur ?"):
    st.session_state.messages.append({"role": "user", "content": p})
    with st.chat_message("user"): st.markdown(p)

    rep = ""

    # 1. LOGIQUE DE SÉCURITÉ (LE MOTEUR VALIDÉ)
    if st.session_state.security_mode:
        code_normal = "20082008"
        code_promax = "B2008a2020@"
        
        # Choix du code attendu (3 essais pour le normal, puis le promax)
        attendu = code_normal if st.session_state.attempts < 3 else code_promax
        
        if p == attendu:
            # SUCCÈS : Purge réelle de Firebase
            doc_profil.set({"faits": [], "faits_verrouilles": []})
            rep = "✅ **ACCÈS MAÎTRE VALIDÉ.** La mémoire a été intégralement purgée, Monsieur."
            st.session_state.security_mode = False
            st.session_state.attempts = 0
        else:
            st.session_state.attempts += 1
            if st.session_state.attempts < 3:
                rep = f"❌ **CODE INCORRECT.** Recommencez (Essai {st.session_state.attempts}/3)."
            elif st.session_state.attempts == 3:
                # C'est ici que DELTA demande le code Pro Max après les 3 essais ratés
                rep = "⚠️ **3 ÉCHECS.** Veuillez entrer le code Pro Max (B2008a2020@)."
            else:
                # Si même le code Pro Max est faux
                rep = "🔴 **ROUGE** (Échec critique du code Pro Max)"
                st.session_state.security_mode = False
                st.session_state.attempts = 0

    # 2. DÉTECTION DE L'ORDRE
    elif "réinitialisation complète" in p.lower():
        st.session_state.security_mode = True
        st.session_state.attempts = 0
        rep = "🔒 **SÉCURITÉ ACTIVÉE.** Veuillez entrer le code d'accès pour la réinitialisation."

    # 3. RÉPONSE IA NORMALE
    else:
        with st.chat_message("assistant"):
            instr = {"role": "system", "content": f"Tu es DELTA. Infos: {faits_publics}"}
            r = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[instr] + st.session_state.messages)
            rep = r.choices[0].message.content

    # AFFICHAGE FINAL
    with st.chat_message("assistant"):
        st.markdown(rep)
        st.session_state.messages.append({"role": "assistant", "content": rep})
