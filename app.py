import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import re
import uuid

# Version de l'application
APP_VERSION = "2.1.1"

st.set_page_config(page_title="Recherche Événements - Voix du Nucléaire", page_icon="🔬", layout="wide")

def load_from_google_sheet(sheet_url):
    """Charge les institutions depuis une Google Sheet publique"""
    try:
        # Extraire l'ID de la sheet depuis l'URL
        if '/d/' in sheet_url:
            sheet_id = sheet_url.split('/d/')[1].split('/')[0]
        else:
            return None, "❌ URL invalide. Utilisez le lien complet de votre Google Sheet."
        
        # Construire l'URL CSV
        csv_url = f'https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv'
        
        # Charger les données
        df = pd.read_csv(csv_url, header=None)
        
        # Extraire les URLs (première colonne)
        institutions = []
        for url in df[0].dropna():
            url_str = str(url).strip()
            if url_str.startswith('http'):
                institutions.append(url_str)
        
        return institutions, None
    except Exception as e:
        return None, f"❌ Erreur lors du chargement: {str(e)}"

# Initialize session state for institutions
if 'institutions' not in st.session_state:
    st.session_state.institutions = []
if 'sheet_url' not in st.session_state:
    st.session_state.sheet_url = ''
if 'temp_institutions' not in st.session_state:
    st.session_state.temp_institutions = []

# Charger automatiquement depuis Google Sheets au démarrage
if st.session_state.sheet_url and not st.session_state.institutions:
    institutions, error = load_from_google_sheet(st.session_state.sheet_url)
    if not error and institutions:
        st.session_state.institutions = institutions

# Titre
st.title("🔬 Recherche d'Événements - Voix du Nucléaire")
st.markdown(f"*Trouvez automatiquement les événements universitaires (forums, JPO, journées orientation)* • **v{APP_VERSION}**")

# Sidebar pour la clé API
with st.sidebar:
    st.header("⚙️ Configuration")
    st.caption(f"Version {APP_VERSION}")
    
    api_key = st.text_input("Clé API Serper", type="password", help="Entrez votre clé API Serper.dev")
    
    st.markdown("---")
    st.subheader("📊 Google Sheet")
    
    sheet_url_input = st.text_input(
        "Lien de votre Google Sheet",
        value=st.session_state.sheet_url,
        placeholder="https://docs.google.com/spreadsheets/d/...",
        help="Collez le lien de votre Google Sheet (en lecture seule publique)"
    )
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Sauvegarder", use_container_width=True):
            st.session_state.sheet_url = sheet_url_input
            if sheet_url_input:
                institutions, error = load_from_google_sheet(sheet_url_input)
                if error:
                    st.error(error)
                else:
                    st.session_state.institutions = institutions
                    st.success(f"✅ {len(institutions)} institution(s) chargée(s)")
                    st.rerun()
    
    with col2:
        if st.button("🔄 Recharger", use_container_width=True, disabled=not st.session_state.sheet_url):
            institutions, error = load_from_google_sheet(st.session_state.sheet_url)
            if error:
                st.error(error)
            else:
                st.session_state.institutions = institutions
                st.session_state.temp_institutions = []
                st.success(f"✅ {len(institutions)} institution(s) rechargée(s)")
                st.rerun()
    
    if st.session_state.institutions:
        st.caption(f"✅ {len(st.session_state.institutions)} institution(s) chargée(s) depuis Sheets")
    
    st.markdown("---")
    
    fetch_dates = st.checkbox("Chercher les dates sur les pages web", value=False, help="Plus précis mais plus lent (1-2 sec par résultat)")
    debug_mode = st.checkbox("Mode debug", help="Affiche les résultats bruts avant filtrage")
    
    st.markdown("---")
    st.markdown("**Comment configurer Google Sheets?**")
    st.markdown("1. Créez une Sheet avec vos institutions (URL en colonne A)")
    st.markdown("2. Partager → Tous les utilisateurs → Lecteur")
    st.markdown("3. Copiez le lien ci-dessus")
    
    st.markdown("---")
    st.markdown("**Comment obtenir une clé API?**")
    st.markdown("1. Allez sur [serper.dev](https://serper.dev)")
    st.markdown("2. Créez un compte")
    st.markdown("3. Copiez votre clé API")

def extract_date(text):
    """Extrait une date du texte - version améliorée"""
    if not text:
        return None
    
    text = text.lower()
    
    months_fr = {
        'janvier': '01', 'février': '02', 'fevrier': '02', 'mars': '03', 'avril': '04',
        'mai': '05', 'juin': '06', 'juillet': '07', 'août': '08', 'aout': '08',
        'septembre': '09', 'octobre': '10', 'novembre': '11', 'décembre': '12', 'decembre': '12',
        'jan': '01', 'fév': '02', 'fev': '02', 'mar': '03', 'avr': '04',
        'sept': '09', 'oct': '10', 'nov': '11', 'déc': '12', 'dec': '12'
    }
    
    # Pattern 1: "15 janvier 2025" ou "15 janvier" ou "janvier 2025"
    pattern1 = r'(\d{1,2})\s+(' + '|'.join(months_fr.keys()) + r')(?:\s+(\d{4}))?'
    match = re.search(pattern1, text)
    if match:
        day = match.group(1) if match.group(1) else ''
        month = months_fr[match.group(2)]
        year = match.group(3) if match.group(3) else str(datetime.now().year)
        if day:
            return f"{day}/{month}/{year}"
        else:
            return f"{month}/{year}"
    
    # Pattern 2: "du 15 au 17 janvier 2025"
    pattern2 = r'du\s+(\d{1,2})\s+au\s+(\d{1,2})\s+(' + '|'.join(months_fr.keys()) + r')\s+(\d{4})'
    match = re.search(pattern2, text)
    if match:
        day1 = match.group(1)
        day2 = match.group(2)
        month = months_fr[match.group(3)]
        year = match.group(4)
        return f"{day1}-{day2}/{month}/{year}"
    
    # Pattern 3: "15/01/2025" ou "15-01-2025" ou "15.01.2025"
    pattern3 = r'(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{2,4})'
    match = re.search(pattern3, text)
    if match:
        return f"{match.group(1)}/{match.group(2)}/{match.group(3)}"
    
    # Pattern 4: "2025-01-15" (format ISO)
    pattern4 = r'(\d{4})[\/\-](\d{1,2})[\/\-](\d{1,2})'
    match = re.search(pattern4, text)
    if match:
        return f"{match.group(3)}/{match.group(2)}/{match.group(1)}"
    
    # Pattern 5: "samedi 15 janvier" ou "lundi 3 mars 2025"
    days = r'(?:lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche)'
    pattern5 = days + r'\s+(\d{1,2})\s+(' + '|'.join(months_fr.keys()) + r')(?:\s+(\d{4}))?'
    match = re.search(pattern5, text)
    if match:
        day = match.group(1)
        month = months_fr[match.group(2)]
        year = match.group(3) if match.group(3) else str(datetime.now().year)
        return f"{day}/{month}/{year}"
    
    return None

def parse_date(date_str):
    """Convertit une date string en objet datetime pour comparaison"""
    if not date_str or date_str == 'Date à confirmer':
        return None
    
    try:
        # Essayer différents formats
        formats = [
            '%d/%m/%Y',      # 15/01/2025
            '%d/%m/%y',      # 15/01/25
            '%m/%Y',         # 01/2025
        ]
        
        # Nettoyer la date (enlever les plages "15-17/01/2025" -> prendre la première date)
        if '-' in date_str and '/' in date_str:
            # Format "15-17/01/2025" -> "15/01/2025"
            parts = date_str.split('-')
            if len(parts) > 1:
                date_str = parts[0] + date_str[date_str.index('/'):]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except:
                continue
        
        return None
    except:
        return None

def is_future_event(date_str):
    """Vérifie si un événement est futur"""
    if date_str == 'Date à confirmer':
        return True  # Garder les événements sans date confirmée
    
    parsed_date = parse_date(date_str)
    if not parsed_date:
        return True  # En cas de doute, garder
    
    # Comparer avec aujourd'hui
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    return parsed_date >= today

def extract_date_from_url(url):
    """Tente d'extraire une date en allant chercher sur la page web"""
    try:
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            # Chercher des dates dans le HTML (sans parser tout le HTML pour rester rapide)
            html = response.text[:5000]  # Premiers 5000 caractères seulement
            date = extract_date(html)
            return date
    except:
        pass
    return None

def search_events(query, region, api_key, num_results=20, fetch_dates_from_web=False, institutions=None, search_scope="web", debug=False):
    """Recherche les événements via Serper API avec requêtes multiples"""
    if not api_key:
        st.error("⚠️ Veuillez entrer votre clé API Serper dans la barre latérale")
        return None, None
    
    region_part = region if region != "Toute la France" else ""
    year = datetime.now().year
    
    # Définir les variations de requête selon le nombre demandé et le scope
    variations = []
    
    # Si recherche ciblée sur institutions
    if search_scope == "institutions" and institutions:
        if debug:
            st.info(f"🏫 Recherche ciblée sur {len(institutions)} institution(s)")
        
        # Créer une requête par institution (limité aux 5 premières pour ne pas dépasser les quotas)
        for inst in institutions[:5]:
            # Extraire le domaine de l'URL
            domain = inst.replace('https://', '').replace('http://', '').split('/')[0]
            base_query = f'{query} site:{domain} {year}'
            variations.append(base_query)
    
    # Recherche web standard (avec priorité institutions si disponibles)
    else:
        if num_results <= 10:
            # Une seule recherche
            base = f'{query} {region_part if region_part else "France"} {year}'
            
            # Ajouter les institutions en priorité
            if institutions and len(institutions) > 0:
                domains = ' OR '.join([f'site:{inst.replace("https://", "").replace("http://", "").split("/")[0]}' for inst in institutions[:3]])
                variations = [f'{query} ({domains}) {year}', base]
            else:
                variations = [base]
        
        elif num_results <= 30:
            base = f'{query} {region_part if region_part else "France"} {year}'
            variations = [
                base,
                f'{query} université {region_part if region_part else "France"} {year}',
                f'{query} "école ingénieurs" {region_part if region_part else "France"} {year}'
            ]
        else:
            base = f'{query} {region_part if region_part else "France"} {year}'
            variations = [
                base,
                f'{query} université {region_part if region_part else "France"} {year}',
                f'{query} "école ingénieurs" {region_part if region_part else "France"} {year}',
                f'{query} IUT {region_part if region_part else "France"} {year}',
                f'{query} étudiant {region_part if region_part else "France"} {year}'
            ]
    
    if debug:
        st.info(f"🔍 {len(variations)} requête(s) pour obtenir ~{num_results} résultats")
    
    all_raw_results = []
    seen_urls = set()
    
    try:
        for i, full_query in enumerate(variations):
            if debug:
                st.info(f"📡 Requête {i+1}/{len(variations)}: `{full_query}`")
            
            response = requests.post(
                'https://google.serper.dev/search',
                headers={
                    'X-API-KEY': api_key,
                    'Content-Type': 'application/json'
                },
                json={
                    'q': full_query,
                    'gl': 'fr',
                    'hl': 'fr'
                },
                timeout=10
            )
            
            if response.status_code == 401:
                st.error("❌ Clé API invalide. Vérifiez votre clé Serper.")
                return None, None
            elif response.status_code != 200:
                st.error(f"❌ Erreur API: {response.status_code}")
                continue
            
            data = response.json()
            
            if 'organic' in data:
                for item in data['organic']:
                    url = item.get('link', '')
                    # Éviter les doublons
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        all_raw_results.append(item)
        
        if debug:
            st.info(f"📊 Total: {len(all_raw_results)} résultats uniques obtenus")
        
        if len(all_raw_results) == 0:
            return [], []
        
        # Résultats bruts
        raw_results = []
        for item in all_raw_results:
            date = extract_date(item.get('snippet', '') + ' ' + item.get('title', ''))
            
            # Si pas de date trouvée et option activée, chercher sur la page
            if not date and fetch_dates_from_web:
                url = item.get('link', '')
                if url:
                    date = extract_date_from_url(url)
            
            raw_results.append({
                'Date': date or 'Date à confirmer',
                'Événement': item.get('title', ''),
                'Description': item.get('snippet', ''),
                'Lien': item.get('link', '')
            })
        
        # Mots-clés à filtrer côté client
        exclude_keywords = ['tourisme', 'hôtellerie', 'restauration', 'cuisine', 'gastronomie', 
                           'hôtelier', 'culinaire', 'arts culinaires', 'service en salle']
        
        filtered_results = []
        past_events_count = 0
        
        for item in all_raw_results:
            title_lower = item.get('title', '').lower()
            snippet_lower = item.get('snippet', '').lower()
            
            # Filtrer les résultats non pertinents
            if any(keyword in title_lower or keyword in snippet_lower for keyword in exclude_keywords):
                continue
            
            date = extract_date(item.get('snippet', '') + ' ' + item.get('title', ''))
            
            # Si pas de date trouvée et option activée, chercher sur la page
            if not date and fetch_dates_from_web:
                url = item.get('link', '')
                if url:
                    date = extract_date_from_url(url)
            
            date_final = date or 'Date à confirmer'
            
            # Filtrer les événements passés
            if not is_future_event(date_final):
                past_events_count += 1
                continue
            
            filtered_results.append({
                'Date': date_final,
                'Événement': item.get('title', ''),
                'Description': item.get('snippet', ''),
                'Lien': item.get('link', '')
            })
        
        if debug and past_events_count > 0:
            st.info(f"🗓️ {past_events_count} événement(s) passé(s) exclu(s)")
        
        return filtered_results, raw_results if debug else None
    
    except Exception as e:
        st.error(f"❌ Erreur: {str(e)}")
        return None, None

# Tabs
tab1, tab2, tab3 = st.tabs(["🔍 Recherche", "🏫 Institutions", "ℹ️ À propos"])

# ===== TAB 2: INSTITUTIONS =====
with tab2:
    st.header("Gestion des institutions")
    
    if st.session_state.sheet_url:
        st.success(f"📊 Liste chargée depuis Google Sheets : {len(st.session_state.institutions)} institution(s)")
        st.info("💡 Pour modifier la liste de façon permanente, éditez directement votre Google Sheet et cliquez sur 🔄 Recharger dans la barre latérale.")
    else:
        st.warning("⚠️ Aucune Google Sheet configurée. Configurez-la dans la barre latérale pour sauvegarder vos institutions.")
    
    # Display institutions from Google Sheets
    if st.session_state.institutions:
        st.markdown(f"### 📋 Institutions (depuis Google Sheets)")
        for i, inst in enumerate(st.session_state.institutions):
            st.text(f"• {inst}")
    
    st.markdown("---")
    
    # Temporary institutions (session only)
    st.markdown("### ➕ Ajouts temporaires (cette session uniquement)")
    st.caption("Ces ajouts ne seront PAS sauvegardés dans Google Sheets. Pour un ajout permanent, modifiez votre Sheet.")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        new_institution = st.text_input(
            "Ajouter temporairement",
            placeholder="https://www.ec-lyon.fr/",
            help="Cette institution sera disponible uniquement pour cette session"
        )
    
    with col2:
        st.write("")
        st.write("")
        if st.button("➕ Ajouter", use_container_width=True):
            if new_institution and new_institution.startswith('http'):
                all_institutions = st.session_state.institutions + st.session_state.temp_institutions
                if new_institution not in all_institutions:
                    st.session_state.temp_institutions.append(new_institution)
                    st.success(f"✅ Ajouté temporairement: {new_institution}")
                    st.rerun()
                else:
                    st.warning("⚠️ Cette institution existe déjà")
            else:
                st.error("❌ Veuillez entrer une URL valide (commençant par http)")
    
    # Display temporary institutions
    if st.session_state.temp_institutions:
        st.markdown(f"### 🕐 Institutions temporaires ({len(st.session_state.temp_institutions)})")
        st.caption("Ces institutions disparaîtront quand vous fermerez l'app")
        for i, inst in enumerate(st.session_state.temp_institutions):
            col1, col2 = st.columns([5, 1])
            with col1:
                st.text(inst)
            with col2:
                if st.button("🗑️", key=f"del_temp_{i}"):
                    st.session_state.temp_institutions.pop(i)
                    st.rerun()

# ===== TAB 1: RECHERCHE =====
with tab1:
    # Combiner les institutions Google Sheets + temporaires
    all_institutions = st.session_state.institutions + st.session_state.temp_institutions
    
    # Search mode selection
    if all_institutions:
        search_scope = st.radio(
            "Où chercher ?",
            ["🏫 Uniquement dans mes institutions", "🌐 Sur le web (+ priorité aux institutions)"],
            horizontal=True
        )
    else:
        search_scope = "🌐 Sur le web (+ priorité aux institutions)"
        st.info("💡 Ajoutez des institutions dans l'onglet 'Institutions' pour rechercher spécifiquement sur leurs sites.")
    
    # Formulaire de recherche
    col1, col2 = st.columns([2, 1])

    with col1:
        search_mode = st.radio(
            "Mode de recherche",
            ["Recherche rapide", "Recherche personnalisée"],
            horizontal=True
        )
        
        if search_mode == "Recherche rapide":
            event_type = st.selectbox(
                "Type d'événement",
                ["forum des métiers", "journée orientation", "portes ouvertes", "journée découverte"]
            )
            search_query = event_type
        else:
            search_query = st.text_input(
                "Tapez votre recherche personnalisée",
                placeholder='Ex: "forum emploi ingénieur" ou "salon innovation technologique"'
            )

    with col2:
        regions = [
            "Toute la France",
            "Auvergne-Rhône-Alpes",
            "Bourgogne-Franche-Comté",
            "Bretagne",
            "Centre-Val de Loire",
            "Corse",
            "Grand Est",
            "Hauts-de-France",
            "Île-de-France",
            "Normandie",
            "Nouvelle-Aquitaine",
            "Occitanie",
            "Pays de la Loire",
            "Provence-Alpes-Côte d'Azur"
        ]
        region = st.selectbox("Région", regions)
        
        num_results = st.selectbox("Nombre de résultats", [10, 20, 50], index=1)

    search_button = st.button("🔍 Rechercher", type="primary", use_container_width=True)

    if fetch_dates:
        st.warning("⏱️ **Recherche de dates sur les pages web activée** : La recherche sera plus lente mais plus précise.")
    else:
        st.info("ℹ️ **Note**: Les événements passés et les domaines non pertinents (tourisme, hôtellerie, etc.) sont automatiquement filtrés.")

    # Recherche
    if search_button:
        # Générer un ID unique pour cette recherche
        search_id = str(uuid.uuid4())[:8]
        st.info(f"🔢 **ID de recherche : `{search_id}`**")
        
        if not search_query:
            st.warning("⚠️ Veuillez entrer un type d'événement")
        else:
            # Déterminer le scope de recherche
            scope = "institutions" if "institutions" in search_scope else "web"
            
            # Combiner institutions Google Sheets + temporaires
            all_institutions = st.session_state.institutions + st.session_state.temp_institutions
            
            with st.spinner("🔍 Recherche en cours..."):
                results, raw_results = search_events(
                    search_query, 
                    region, 
                    api_key, 
                    num_results, 
                    fetch_dates, 
                    all_institutions,
                    scope,
                    debug_mode
                )
            
            if results is None:
                pass  # L'erreur a déjà été affichée
            elif len(results) == 0:
                if debug_mode and raw_results:
                    st.warning(f"⚠️ {len(raw_results)} résultat(s) trouvé(s) mais tous filtrés (tourisme, hôtellerie, etc.)")
                    st.markdown("### 🔍 Résultats bruts (avant filtrage)")
                    df_raw = pd.DataFrame(raw_results)
                    st.dataframe(
                        df_raw,
                        column_config={
                            "Lien": st.column_config.LinkColumn("Lien", display_text="Voir")
                        },
                        hide_index=True,
                        use_container_width=True
                    )
                else:
                    st.info("ℹ️ Aucun résultat trouvé. Essayez avec d'autres termes ou une autre région.")
            else:
                if debug_mode and raw_results:
                    filtered_count = len(raw_results) - len(results)
                    st.success(f"✅ {len(results)} événement(s) pertinent(s) ({filtered_count} filtré(s))")
                else:
                    st.success(f"✅ {len(results)} événement(s) trouvé(s)")
                
                # Créer un DataFrame
                df = pd.DataFrame(results)
                
                # Boutons d'export
                col1, col2 = st.columns(2)
                with col1:
                    csv = df.to_csv(index=False, encoding='utf-8-sig')
                    st.download_button(
                        label="📥 Télécharger CSV",
                        data=csv,
                        file_name=f"evenements-vdn-{datetime.now().strftime('%Y-%m-%d')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                
                with col2:
                    # Copie pour Excel (format TSV)
                    tsv = df.to_csv(index=False, sep='\t')
                    st.download_button(
                        label="📋 Télécharger pour Excel",
                        data=tsv,
                        file_name=f"evenements-vdn-{datetime.now().strftime('%Y-%m-%d')}.txt",
                        mime="text/plain",
                        use_container_width=True
                    )
                
                # Affichage du tableau
                st.markdown("### Résultats filtrés")
                
                # Configuration des colonnes pour l'affichage
                st.dataframe(
                    df,
                    column_config={
                        "Lien": st.column_config.LinkColumn("Lien", display_text="Voir")
                    },
                    hide_index=True,
                    use_container_width=True
                )
                
                # Afficher les résultats bruts en mode debug
                if debug_mode and raw_results and len(raw_results) > len(results):
                    st.markdown("### 🔍 Tous les résultats (avant filtrage)")
                    df_raw = pd.DataFrame(raw_results)
                    st.dataframe(
                        df_raw,
                        column_config={
                            "Lien": st.column_config.LinkColumn("Lien", display_text="Voir")
                        },
                        hide_index=True,
                        use_container_width=True
                    )
                
                st.info("💡 **Astuce:** Vérifiez chaque lien pour confirmer que l'événement est gratuit pour les intervenants")

# ===== TAB 3: À PROPOS =====
with tab3:
    st.header("ℹ️ À propos de cet outil")
    
    st.markdown("""
    ## 🎯 Qu'est-ce que cet outil ?
    
    Cet outil aide **Voix du Nucléaire** à trouver automatiquement des événements universitaires 
    (forums des métiers, portes ouvertes, journées orientation) où présenter l'association et 
    discuter de l'énergie nucléaire.
    
    Au lieu de chercher manuellement sur Google, l'outil fait le travail pour vous et affiche 
    les résultats dans un tableau facile à exporter.
    
    ---
    
    ## 🔑 Pourquoi une clé API Serper ?
    
    **Serper** est un service qui permet de faire des recherches Google de manière automatisée.
    
    **Pourquoi c'est nécessaire :**
    - Google ne permet pas de faire des recherches automatiques gratuitement
    - Serper sert d'intermédiaire pour accéder aux résultats Google
    - Chaque utilisateur doit avoir sa propre clé (gratuite)
    
    **Ce que ça coûte :**
    - ✅ **100 recherches gratuites par jour** (largement suffisant !)
    - Après 100 recherches : environ 5€ pour 1000 recherches supplémentaires
    - Pour un usage normal : vous resterez dans le quota gratuit
    
    **Comment obtenir votre clé :**
    1. Allez sur [serper.dev](https://serper.dev)
    2. Créez un compte (avec Google ou email)
    3. Copiez votre clé API (affichée sur le dashboard)
    4. Collez-la dans la barre latérale de cet outil
    
    **Sécurité :**
    - Votre clé n'est jamais sauvegardée sur nos serveurs
    - Elle reste dans votre navigateur uniquement
    - Ne partagez jamais votre clé avec d'autres personnes
    
    ---
    
    ## 📊 Pourquoi Google Sheets ?
    
    **Google Sheets** permet à chaque utilisateur d'avoir sa propre liste d'institutions à surveiller.
    
    **Avantages :**
    - ✅ Facile à modifier (interface familière)
    - ✅ Accessible de partout (ordinateur, téléphone)
    - ✅ Partage possible avec des collègues
    - ✅ Historique des modifications
    
    **Comment configurer :**
    1. Créez une nouvelle Google Sheet
    2. Mettez vos URLs d'institutions en colonne A (une par ligne)
       ```
       https://www.ec-lyon.fr/
       https://www.insa-lyon.fr/
       https://www.cpe.fr/
       ```
    3. Partager → "Tous les utilisateurs disposant du lien" → **Lecteur**
    4. Copiez le lien de la Sheet
    5. Collez-le dans la barre latérale de l'outil
    6. Cliquez "💾 Sauvegarder"
    
    **Pour modifier votre liste :**
    - Éditez directement votre Google Sheet
    - Revenez dans l'outil et cliquez "🔄 Recharger"
    
    ---
    
    ## 🚀 Comment utiliser l'outil ?
    
    ### Workflow typique :
    
    1. **Configuration initiale** (une seule fois)
       - Obtenez votre clé Serper
       - Créez votre Google Sheet avec vos institutions
       - Configurez les deux dans la barre latérale
    
    2. **Recherche d'événements**
       - Allez dans l'onglet "🔍 Recherche"
       - Choisissez le type d'événement (forum, portes ouvertes, etc.)
       - Choisissez la région (ou "Toute la France")
       - Décidez si vous cherchez uniquement dans vos institutions ou sur tout le web
       - Cliquez "🔍 Rechercher"
    
    3. **Exploitation des résultats**
       - Consultez le tableau
       - Cliquez sur les liens pour vérifier les événements
       - Téléchargez en CSV ou pour Excel
       - Partagez avec votre équipe
    
    ---
    
    ## 🎛️ Options de recherche
    
    **Deux modes de recherche :**
    - **🏫 Uniquement dans mes institutions** : Cherche SEULEMENT sur les sites de votre liste
    - **🌐 Sur le web (+ priorité aux institutions)** : Cherche partout, mais privilégie vos institutions
    
    **Nombre de résultats :**
    - **10** : Rapide, pour un coup d'œil
    - **20** : Équilibré (recommandé)
    - **50** : Recherche exhaustive (plus lent)
    
    **Options avancées (barre latérale) :**
    - **Chercher les dates sur les pages web** : Plus précis mais plus lent (1-2 sec par résultat)
    - **Mode debug** : Affiche des informations techniques sur la recherche
    
    ---
    
    ## 📋 Filtres automatiques
    
    L'outil filtre automatiquement :
    - ❌ **Événements passés** (garde uniquement les événements futurs)
    - ❌ **Tourisme, hôtellerie, restauration** (non pertinents pour VDN)
    - ❌ **Événements sans rapport** avec les écoles/universités
    
    ---
    
    ## ❓ Questions fréquentes
    
    **Q : Pourquoi certaines dates sont "Date à confirmer" ?**  
    R : La date n'apparaît pas dans le titre ou la description Google. Cliquez sur le lien pour la trouver sur le site.
    
    **Q : Puis-je partager ma clé Serper avec des collègues ?**  
    R : Non, chaque personne doit avoir sa propre clé. C'est gratuit et rapide à créer.
    
    **Q : Puis-je partager ma Google Sheet avec des collègues ?**  
    R : Oui ! Vous pouvez collaborer sur la même Sheet. Chacun devra juste mettre le même lien dans son outil.
    
    **Q : L'outil sauvegarde-t-il mes recherches ?**  
    R : Non, les recherches ne sont pas sauvegardées. Téléchargez les résultats en CSV si vous voulez les garder.
    
    **Q : Combien de recherches puis-je faire ?**  
    R : 100 recherches gratuites par jour avec Serper. Une "recherche" peut générer 10-50 résultats.
    
    **Q : Les données sont-elles sécurisées ?**  
    R : Oui. Votre clé API reste dans votre navigateur et n'est jamais envoyée à nos serveurs.
    
    ---
    
    ## 🆘 Besoin d'aide ?
    
    **Problème avec Serper :**
    - Vérifiez que votre clé est bien copiée (pas d'espaces)
    - Vérifiez que vous n'avez pas dépassé les 100 recherches/jour
    
    **Problème avec Google Sheets :**
    - Vérifiez que la Sheet est bien en "Lecteur" pour "Tous les utilisateurs"
    - Vérifiez que le lien est complet (commence par https://docs.google.com)
    
    **Aucun résultat trouvé :**
    - Essayez avec des termes différents
    - Essayez une autre région
    - Essayez "Sur le web" au lieu de "Uniquement dans mes institutions"
    
    **Contactez l'équipe VDN si vous avez d'autres questions !**
    
    ---
    
    ## 📊 Statistiques de cette session
    
    - **Version de l'outil :** {APP_VERSION}
    - **Institutions chargées :** {len(st.session_state.institutions)} (Google Sheets) + {len(st.session_state.temp_institutions)} (temporaires)
    - **Clé API configurée :** {"✅ Oui" if api_key else "❌ Non"}
    - **Google Sheet configurée :** {"✅ Oui" if st.session_state.sheet_url else "❌ Non"}
    """.format(
        APP_VERSION=APP_VERSION,
        len=len,
        st=st,
        api_key=api_key
    ))

# Footer
st.markdown("---")
st.markdown("*Outil créé pour Voix du Nucléaire • Événements gratuits pour intervenants*")