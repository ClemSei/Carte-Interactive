import streamlit as st
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from geopy.distance import geodesic

st.set_page_config(layout="wide")
st.title("Analyse de Proximité - Cercles GPS")

# 1. Vos données (Coordonnées décimales calculées précédemment)
points = [
    {"nom": "Pau", "lat": 43.3073, "lon": -0.3202, "rayon": 720000, "coul": "green"},
    {"nom": "Agun", "lat": 43.8883, "lon": 1.0064, "rayon": 700000, "coul": "blue"},
    {"nom": "Barcelone", "lat": 41.2199, "lon": 2.2828, "rayon": 865000, "coul": "red"},
    {"nom": "Dax", "lat": 43.6714, "lon": -1.0406, "rayon": 703000, "coul": "orange"},
    {"nom": "Marseille", "lat": 43.2962, "lon": 5.6133, "rayon": 675000, "coul": "purple"},
    {"nom": "Narbonne", "lat": 43.1009, "lon": 2.1713, "rayon": 700000, "coul": "cadetblue"},
    {"nom": "Perpignan", "lat": 42.6051, "lon": 3.0227, "rayon": 725000, "coul": "pink"}
]

# --- SIDEBAR (Barre latérale) ---
st.sidebar.title("Configuration")
st.sidebar.subheader("Sélection des villes")

# Création dynamique des cases à cocher
villes_selectionnees = []
for p in points:
    # On crée une case à cocher par ville, cochée par défaut
    if st.sidebar.checkbox(f"Afficher {p['nom']}", value=True, key=p['nom']):
        villes_selectionnees.append(p)

st.sidebar.markdown("---")
adresse = st.sidebar.text_input("📍 Rechercher une adresse :", placeholder="ex: Place du Capitole, Toulouse")

# --- LOGIQUE DE CALCUL ---
point_recherche = None
villes_hors_zone = []

if adresse:
    geolocator = Nominatim(user_agent="mon_app_geo_2026")
    location = geolocator.geocode(adresse)
    
    if location:
        point_recherche = (location.latitude, location.longitude)
        # Calculer la distance uniquement pour les villes COCHÉES
        for v in villes_selectionnees:
            dist = geodesic(point_recherche, (v['lat'], v['lon'])).meters
            if v['rayon'] < dist:
                villes_hors_zone.append({
                    "nom": v['nom'],
                    "distance": round(dist / 1000, 2),
                    "rayon": v['rayon'] / 1000
                })
    else:
        st.sidebar.error("Adresse introuvable.")

# --- AFFICHAGE PRINCIPAL ---
st.title("🗺️ Carte Interactive et Analyse de Distance")

col1, col2 = st.columns([3, 1])

with col1:
    # Création de la carte
    m = folium.Map(location=[42.5, 2.0], zoom_start=6)
    
    # Marqueur pour l'adresse recherchée
    if point_recherche:
        folium.Marker(
            point_recherche, 
            tooltip="Votre recherche", 
            icon=folium.Icon(color='black', icon='home')
        ).add_to(m)

    # Affichage des cercles uniquement pour les villes sélectionnées
    for p in villes_selectionnees:
        folium.Circle(
            location=[p['lat'], p['lon']],
            radius=p['rayon'],
            color=p['coul'],
            fill=False,
            weight=3,
            tooltip=f"{p['nom']} (Rayon: {p['rayon']}m)"
        ).add_to(m)
        
        folium.Marker(
            location=[p['lat'], p['lon']],
            popup=f"<b>{p['nom']}</b><br>Rayon: {p['rayon']}m",
            icon=folium.Icon(color=p['coul'])
        ).add_to(m)

    # Affichage de la carte dans Streamlit
    st_folium(m, width="100%", height=600, returned_objects=[])

with col2:
    st.subheader("📊 Résultats")
    if not adresse:
        st.info("Entrez une adresse dans la barre latérale pour lancer l'analyse.")
    elif point_recherche:
        st.write(f"**Villes sélectionnées dont le cercle ne couvre pas l'adresse :**")
        if villes_hors_zone:
            for v in villes_hors_zone:
                st.warning(f"⚠️ **{v['nom']}**\n- Dist. : {v['distance']} km\n- Rayon : {v['rayon']} km")
        else:
            st.success("L'adresse est située à l'intérieur de tous les cercles affichés !")