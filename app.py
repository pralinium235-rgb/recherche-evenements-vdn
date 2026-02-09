import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import re
import uuid

# Version de l'application
APP_VERSION = "2.0.0"

st.set_page_config(page_title="Recherche Événements - Voix du Nucléaire", page_icon="🔬", layout="wide")

# Initialize session state for institutions
if 'institutions' not in st.session_state:
    st.session_state.institutions = []

# Titre
st.title("🔬 Recherche d'Événements - Voix du Nucléaire")
st.markdown(f"*Trouvez automatiquement les événements universitaires (forums, JPO, journées orientation)* • **v{APP_VERSION}**")

# Tabs
tab1, tab2 = st.tabs(["🔍 Recherche", "🏫 Institutions"])

# ===== TAB 2: INSTITUTIONS =====
with tab2:
    st.header("Gestion des institutions")
    st.markdown("Ajoutez les sites web des institutions à surveiller (universités, écoles d'ingénieurs, etc.)")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        new_institution = st.text_input(
            "Ajouter une institution",
            placeholder="https://www.ec-lyon.fr/",
            help="Entrez l'URL complète du site (ex: https://www.ec-lyon.fr/)"
        )
    
    with col2:
        st.write("")  # Spacing
        st.write("")  # Spacing
        if st.button("➕ Ajouter", use_container_width=True):
            if new_institution and new_institution.startswith('http'):
                if new_institution not in st.session_state.institutions:
                    st.session_state.institutions.append(new_institution)
                    st.success(f"✅ Ajouté: {new_institution}")
                else:
                    st.warning("⚠️ Cette institution existe déjà")
            else:
                st.error("❌ Veuillez entrer une URL valide (commençant par http)")
    
    # Display institutions list
    if st.session_state.institutions:
        st.markdown(f"### 📋 Institutions enregistrées ({len(st.session_state.institutions)})")
        
        for i, inst in enumerate(st.session_state.institutions):
            col1, col2 = st.columns([5, 1])
            with col1:
                st.text(inst)
            with col2:
                if st.button("🗑️", key=f"del_{i}"):
                    st.session_state.institutions.pop(i)
                    st.rerun()
    else:
        st.info("ℹ️ Aucune institution enregistrée. Ajoutez-en pour rechercher spécifiquement sur leurs sites.")

# ===== TAB 1: RECHERCHE =====
with tab1:

# Sidebar pour la clé API
with st.sidebar:
    st.header("⚙️ Configuration")
    st.caption(f"Version {APP_VERSION}")
    
    api_key = st.text_input("Clé API Serper", type="password", help="Entrez votre clé API Serper.dev")
    
    fetch_dates = st.checkbox("Chercher les dates sur les pages web", value=False, help="Plus précis mais plus lent (1-2 sec par résultat)")
    debug_mode = st.checkbox("Mode debug", help="Affiche les résultats bruts avant filtrage")
    
    st.markdown("---")
    st.markdown("**Comment obtenir une clé API?**")
    st.markdown("1. Allez sur [serper.dev](https://serper.dev)")
    st.markdown("2. Créez un compte")
    st.markdown("3. Copiez votre clé API")

    # ===== TAB 1: RECHERCHE =====
with tab1:
    # Search mode selection
    if st.session_state.institutions:
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

st.info("ℹ️ **Note:** Les résultats sont automatiquement filtrés pour exclure le tourisme, l'hôtellerie, la restauration et autres domaines non pertinents.")

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
            
            with st.spinner("🔍 Recherche en cours..."):
                results, raw_results = search_events(
                    search_query, 
                    region, 
                    api_key, 
                    num_results, 
                    fetch_dates, 
                    st.session_state.institutions,
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

# Footer
st.markdown("---")
st.markdown("*Outil créé pour Voix du Nucléaire • Événements gratuits pour intervenants*")