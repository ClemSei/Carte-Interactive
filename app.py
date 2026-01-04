import streamlit as st
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from geopy.distance import distance as geopy_dist
import numpy as np

st.set_page_config(layout="wide", page_title="Master Colombophilie - Analyse Complète")

# --- 1. DONNÉES (Rayons immenses) ---
all_points = [
    {"nom": "Pau", "lat": 43.3073, "lon": -0.3202, "rayon": 720000, "coul": "green"},
    {"nom": "Agun", "lat": 43.8883, "lon": 1.0064, "rayon": 700000, "coul": "blue"},
    {"nom": "Barcelone", "lat": 41.2199, "lon": 2.2828, "rayon": 865000, "coul": "red"},
    {"nom": "Dax", "lat": 43.6714, "lon": -1.0406, "rayon": 703000, "coul": "orange"},
    {"nom": "Marseille", "lat": 43.2962, "lon": 5.6133, "rayon": 675000, "coul": "purple"},
    {"nom": "Narbonne", "lat": 43.1009, "lon": 2.1713, "rayon": 700000, "coul": "cadetblue"},
    {"nom": "Perpignan", "lat": 42.6051, "lon": 3.0227, "rayon": 725000, "coul": "pink"}
]

# Couleurs des zones de fond (Nombre de concours)
couleurs_zones = {
    0: "#000000", 1: "#808080", 2: "#d62728", 3: "#ff7f0e",
    4: "#bcbd22", 5: "#17becf", 6: "#1f77b4", 7: "#2ca02c"
}

st.title("🕊️ Outil d'Analyse Colombophile")

# --- 2. BARRE LATÉRALE (CONTROLES) ---

st.sidebar.header("1. Recherche Pigeonnier")
adresse = st.sidebar.text_input("📍 Entrez une adresse :", placeholder="ex: Lille, France")

st.sidebar.markdown("---")
st.sidebar.header("2. Sélection des Concours")
st.sidebar.write("Décochez une ville pour l'exclure des calculs.")

# Filtrage des villes actives
active_points = []
cols_check = st.sidebar.columns(2)
for i, p in enumerate(all_points):
    col = cols_check[i % 2]
    if col.checkbox(f"{p['nom']}", value=True, key=f"city_{p['nom']}"):
        active_points.append(p)

st.sidebar.markdown("---")
st.sidebar.header("3. Filtres Visuels")
st.sidebar.write("Afficher les zones (fond de carte) :")

# Filtrage des zones à afficher
affichage_zones = {}
for i in range(len(all_points), -1, -1):
    if i > len(active_points): continue # On ne montre pas les options impossibles
    checked = True if i >= 4 else False
    label = f"{i} Concours possibles"
    affichage_zones[i] = st.sidebar.checkbox(label, value=checked, key=f"z_{i}")

resolution = st.sidebar.select_slider("Précision", options=[0.4, 0.25, 0.15], value=0.25, format_func=lambda x: "Moyenne" if x==0.25 else ("Haute (Lent)" if x==0.15 else "Basse"))


# --- 3. FONCTIONS DE CALCUL ---

def generer_arc_nord(centre_lat, centre_lon, rayon_metres):
    """Génère l'arc de cercle (demi-cercle Nord)"""
    coords = []
    # De 270° (Ouest) à 450° (Est)
    for azimut in range(270, 451, 3):
        dest = geopy_dist(meters=rayon_metres).destination((centre_lat, centre_lon), azimut)
        coords.append([dest.latitude, dest.longitude])
    return coords

@st.cache_data
def calculer_grille_zones(res, _villes_actives):
    """Calcule les zones de couleur (Grid Analysis)"""
    # Zone Nord France / Belgique / Pays-Bas
    lat_min, lat_max = 48.0, 53.0
    lon_min, lon_max = -5.0, 7.0
    
    zones = {i: [] for i in range(len(all_points) + 1)}
    lats = np.arange(lat_min, lat_max, res)
    lons = np.arange(lon_min, lon_max, res)
    
    for lat in lats:
        for lon in lons:
            pt = (lat, lon)
            score = 0
            for p in _villes_actives:
                # Calcul simple pour la grille
                if geodesic(pt, (p['lat'], p['lon'])).meters > p['rayon']:
                    score += 1
            zones[score].append([
                [lat - res/2, lon - res/2],
                [lat + res/2, lon + res/2]
            ])
    return zones

# --- 4. LOGIQUE PRINCIPALE ---

# A. Géocodage de l'adresse (Si renseignée)
point_recherche = None
resultats_adresse = {"ok": [], "ko": []}
score_adresse = 0

if adresse:
    geolocator = Nominatim(user_agent="colombo_app_v3")
    try:
        loc = geolocator.geocode(adresse)
        if loc:
            point_recherche = (loc.latitude, loc.longitude)
            # Calcul précis pour l'adresse trouvée
            for p in active_points:
                dist = geodesic(point_recherche, (p['lat'], p['lon'])).meters
                info = {
                    "nom": p['nom'],
                    "dist": round(dist/1000, 1),
                    "min": round(p['rayon']/1000, 1)
                }
                if dist > p['rayon']:
                    resultats_adresse["ok"].append(info)
                    score_adresse += 1
                else:
                    resultats_adresse["ko"].append(info)
        else:
            st.error("Adresse introuvable.")
    except:
        st.error("Erreur de service localisation.")

# B. Calcul de la grille (Zones)
with st.spinner("Calcul des zones en cours..."):
    zones_calculees = calculer_grille_zones(resolution, active_points)


# --- 5. MISE EN PAGE (COLONNES) ---
col_map, col_details = st.columns([3, 1])

with col_map:
    # Centrage : Sur l'adresse si trouvée, sinon sur le Nord
    start_loc = point_recherche if point_recherche else [50.0, 2.5]
    start_zoom = 8 if point_recherche else 6
    
    m = folium.Map(location=start_loc, zoom_start=start_zoom)

    # 1. Dessin des ZONES (Fond)
    for score, rectangles in zones_calculees.items():
        if score in affichage_zones and affichage_zones[score]:
            fg = folium.FeatureGroup(name=f"Fond: {score} concours")
            for rect in rectangles:
                folium.Rectangle(
                    bounds=rect, color=None, fill=True,
                    fill_color=couleurs_zones.get(score, "#333333"),
                    fill_opacity=0.4, tooltip=f"{score} concours"
                ).add_to(fg)
            fg.add_to(m)

    # 2. Dessin des ARCS (Lignes)
    for p in active_points:
        points_arc = generer_arc_nord(p['lat'], p['lon'], p['rayon'])
        folium.PolyLine(
            locations=points_arc, color=p['coul'], weight=4, opacity=0.9,
            tooltip=f"Ligne {p['nom']}"
        ).add_to(m)

    # 3. Marqueur ADRESSE
    if point_recherche:
        folium.Marker(
            point_recherche, popup=loc.address,
            icon=folium.Icon(color="black", icon="home")
        ).add_to(m)

    st_folium(m, width="100%", height=750)

with col_details:
    st.subheader("📋 Analyse Détaillée")
    
    if point_recherche:
        st.info(f"Position : {adresse}")
        
        st.markdown(f"### Score : {score_adresse} / {len(active_points)}")
        # Barre de couleur
        c_score = couleurs_zones.get(score_adresse, "#000")
        st.markdown(f'<div style="background-color:{c_score};height:15px;width:100%;border-radius:5px;"></div><br>', unsafe_allow_html=True)
        
        with st.expander("✅ JOUABLES (Distance OK)", expanded=True):
            if resultats_adresse["ok"]:
                for c in resultats_adresse["ok"]:
                    st.success(f"**{c['nom']}**\n\n+ {c['dist']} km (Min {c['min']})")
            else:
                st.write("Aucun.")

        with st.expander("❌ INTERDITS (Trop près)", expanded=True):
            if resultats_adresse["ko"]:
                for c in resultats_adresse["ko"]:
                    st.error(f"**{c['nom']}**\n\n{c['dist']} km (Min {c['min']})")
            else:
                st.write("Aucun.")
                
    else:
        st.warning("👈 Entrez une adresse dans le menu à gauche pour voir la liste des concours autorisés.")
        
    st.markdown("---")
    st.write("**Légende Carte :**")
    st.caption("Couleur des zones = Nb de concours jouables")
    for i in range(len(active_points), -1, -1):
        c = couleurs_zones.get(i, "#000")
        st.markdown(f"<span style='color:{c}'>■</span> {i} Concours", unsafe_allow_html=True)