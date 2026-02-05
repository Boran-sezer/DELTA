import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json

# --- CONFIGURATION ---
st.set_page_config(page_title="DELTA OS", page_icon="⚡", layout="wide")

# --- INITIALISATION FIREBASE ---
if not firebase_admin._apps:
    try:
        encoded = st.secrets["firebase_key"]["encoded_key"].strip()
        decoded_json = base64.b64decode(encoded).decode("utf-8")
        creds_dict = json.loads(decoded_json)
        cred = credentials.Certificate(creds_dict)
        firebase_admin.initialize_app(cred)
    except Exception:
        st.error("⚠️ Connexion Mémoire interrompue.")

db = firestore.client()
doc_profil = db.collection("memoire").document("profil_monsieur")

# --- CONNEXION GROQ ---
client = Groq(api_key="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")

# --- ÉTATS DE SESSION (VÉRIFICATION STRICTE) ---
if "messages" not in st.session_state: st.session_state.messages = []
if "unlocked" not in st.session_state: st.session_state.unlocked = False
if "security_mode" not in st.session_state: st.session_state.security_mode = None
if "attempts" not in st.session_state: st.session_state.attempts = 0
if "pending_data" not in st.session_state: st.session_state.pending_data = None

# --- CHARGEMENT DU PROFIL ---
res_profil = doc_profil.get()
data = res_profil.to_dict() if res_profil.exists else {}
faits_publics = data.get("faits", [])
faits_verrouilles = data.get("faits_verrouilles", [])

# --- SIDEBAR ---
with st.sidebar:
    st.title("🧠 Archives")
    for i, f in enumerate(faits_publics):
        col1, col2 = st.columns([4, 1])
        col1.info(f)
        if col2.button("🗑️", key=f"p_{i}"):
            faits_publics.pop(i)
            doc_profil.update({"faits": faits_publics})
            st.rerun()
    if st.session_state.unlocked:
        st.subheader("🔐 Scellées")
        for i, f in enumerate(faits_verrouilles):
            col1, col2 = st.columns([4, 1])
            col1.warning(f)
            if col2.button("🗑️", key=f"s_{i}"):
                faits_verrouilles.pop(i)
                doc_profil.update({"faits_verrouilles": faits_verrouilles})
                st.rerun()

# --- CHAT ---
for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- MOTEUR DE TRAITEMENT ---
if p := st.chat_input("Vos ordres, Monsieur ?"):
    st.session_state.messages.append({"role": "user", "content": p})
    with st.chat_message("user"): st.markdown(p)
    
    low_p = p.lower().strip()
    rep = ""

    # 1. SI UN MODE SÉCURITÉ EST ACTIF (ATTENTE DE CODE)
    if st.session_state.security_mode:
        code_normal = "20082008"
        code_secours = "B2008a2020@"
        
        # Vérification du code selon l'étape
        if st.session_state.attempts < 3:
            if p == code_normal:
                auth_ok = True
            else:
                auth_ok = False
                st.session_state.attempts += 1
        else:
            if p == code_secours:
                auth_ok = True
            else:
                auth_ok = False
                st.session_state.attempts += 1

        if auth_ok:
            # EXÉCUTION
            mode = st.session_state.security_mode
            info = st.session_state.pending_data
            if mode == "PURGE":
                doc_profil.set({"faits": [], "faits_verrouilles": []})
                rep = "✅ **SYSTÈME RÉINITIALISÉ.**"
            elif mode == "LOCK":
                faits_verrouilles.append(info)
                doc_profil.update({"faits_verrouilles": faits_verrouilles})
                rep = "✅ **INFORMATION SCELLÉE.**"
            elif mode == "UNLOCK":
                st.session_state.unlocked = True
                rep = "✅ **ACCÈS AU COFFRE ACCORDÉ.**"
            elif mode == "DELETE":
                t = info.lower()
                new_pub = [f for f in faits_publics if t not in f.lower()]
                new_priv = [f for f in faits_verrouilles if t not in f.lower()]
                doc_profil.set({"faits": new_pub, "faits_verrouilles": new_priv})
                rep = f"✅ **SUPPRESSION DE '{info}' EFFECTUÉE.**"
            
            # Reset
            st.session_state.security_mode = None
            st.session_state.attempts = 0
        else:
            if st.session_state.attempts < 3:
                rep = f"❌ **CODE ERRONÉ.** Essai {st.session_state.attempts}/3. Réessayez."
            elif st.session_state.attempts == 3:
                rep = "⚠️ **SÉCURITÉ MAXIMALE.** Veuillez entrer le code de secours (B2008a2020@)."
            else:
                rep = "🚨 **PROCÉDURE ANNULÉE.** Trop d'échecs."
                st.session_state.security_mode = None
                st.session_state.attempts = 0

    # 2. DÉTECTION DES ORDRES (DÉCLENCHEMENT)
    elif "réinitialisation complète" in low_p:
        st.session_state.security_mode = "PURGE"
        rep = "🔒 **ORDRE DE PURGE.** Monsieur, veuillez confirmer avec votre code."
    elif "verrouille" in low_p:
        st.session_state.security_mode = "LOCK"
        st.session_state.pending_data = p.replace("verrouille", "").strip()
        rep = "🔒 **SCELLAGE.** Code d'autorisation requis."
    elif "affiche les archives verrouillées" in low_p:
        st.session_state.security_mode = "UNLOCK"
        rep = "🔒 **COFFRE-FORT.** Veuillez vous authentifier."
    elif "supprime précisément" in low_p:
        st.session_state.security_mode = "DELETE"
        st.session_state.pending_data = p.replace("supprime précisément", "").strip()
        rep = f"🔒 **SUPPRESSION.** Code requis pour effacer '{st.session_state.pending_data}'."

    # 3. RÉPONSE IA NORMALE
    else:
        with st.chat_message("assistant"):
            instr = {"role": "system", "content": "Tu es DELTA, majordome de Monsieur Boran. Sois bref et efficace."}
            r = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[instr] + st.session_state.messages)
            rep = r.choices[0].message.content

    # AFFICHAGE FINAL
    with st.chat_message("assistant"):
        st.markdown(rep)
        st.session_state.messages.append({"role": "assistant", "content": rep})
