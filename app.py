import streamlit as st
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from geopy.distance import distance as geopy_dist
import numpy as np
import pandas as pd # Nouveau : pour gérer les tableaux de résultats
import pdfplumber
import re

# --- CONFIGURATION GÉNÉRALE ---
st.set_page_config(layout="wide", page_title="Fédération Colombophile - Portail")

# --- MENU DE NAVIGATION ---
st.sidebar.title("🕊️ Portail Colombophile")
page = st.sidebar.radio("Navigation", ["Analyse des Concours", "Résultats des Concours", "Informations"])

# ---------------------------------------------------------
# PAGE 1 : ANALYSE DES CONCOURS (Votre code précédent)
# ---------------------------------------------------------
all_points = [
        {"nom": "Pau", "lat": 43.3073, "lon": -0.3202, "rayon": 720000, "coul": "green"},
        {"nom": "Agen", "lat": 43.8883, "lon": 1.0064, "rayon": 700000, "coul": "blue"},
        {"nom": "Barcelone", "lat": 41.4030556, "lon": 2.215555555555556, "rayon": 865000, "coul": "red"},
        {"nom": "Dax", "lat": 43.6714, "lon": -1.0406, "rayon": 703000, "coul": "orange"},
        {"nom": "Marseille", "lat": 43.2962, "lon": 5.6133, "rayon": 675000, "coul": "purple"},
        {"nom": "Narbonne", "lat": 43.2785278, "lon": 2.597027777777778, "rayon": 700000, "coul": "cadetblue"},
        {"nom": "Perpignan", "lat": 42.6051, "lon": 3.0227, "rayon": 725000, "coul": "pink"}
    ]

# --- FONCTION DE DÉCODAGE GPS MULTI-FORMAT ---
def decode_gps(entree):
    """
    Décode différents formats :
    1. Décimal : 42.6051, 3.0227
    2. Compact (votre format) : 423618.2, 30121.7
    3. DMS simplifié : 42 36 18, 3 1 21
    """
    try:
        # Nettoyage de la chaîne
        entree = entree.replace(',', ' ').strip()
        parts = re.split(r'\s+', entree)
        
        if len(parts) == 2:
            # Cas 1 : Coordonnées décimales classiques
            if '.' in parts[0] and float(parts[0]) < 90:
                return float(parts[0]), float(parts[1])
            
            # Cas 2 : Votre format compact (ex: 423618.2 -> 42°36'18.2")
            # On considère que si le nombre est > 1000, c'est du compact
            coords_finales = []
            for p in parts:
                val = float(p)
                deg = int(val / 10000)
                reste = val - (deg * 10000)
                minutes = int(reste / 100)
                secondes = reste - (minutes * 100)
                coords_finales.append(deg + (minutes / 60) + (secondes / 3600))
            return coords_finales[0], coords_finales[1]
            
        return None
    except:
        return None

# --- PAGE 1 : ANALYSE DES CONCOURS ---
if page == "Analyse des Concours":
    st.title("🗺️ Analyse d'Éligibilité")

    couleurs_zones = {
        0: "#000000", 1: "#808080", 2: "#d62728", 3: "#ff7f0e",
        4: "#bcbd22", 5: "#17becf", 6: "#1f77b4", 7: "#2ca02c"
    }

    # --- BARRE LATÉRALE ---
    st.sidebar.header("1. Recherche Pigeonnier")
    
    # Choix du mode de saisie
    mode_saisie = st.sidebar.radio("Mode de saisie :", ["Adresse postale", "Coordonnées GPS"])
    
    point_recherche = None
    label_position = ""

    if mode_saisie == "Adresse postale":
        adresse = st.sidebar.text_input("📍 Entrez une adresse :", placeholder="ex: Lille, France")
        if adresse:
            geolocator = Nominatim(user_agent="colombo_app_v3")
            try:
                loc = geolocator.geocode(adresse)
                if loc:
                    point_recherche = (loc.latitude, loc.longitude)
                    label_position = loc.address
                else:
                    st.sidebar.error("Adresse introuvable.")
            except:
                st.sidebar.error("Erreur service localisation.")
    
    else:
        st.sidebar.write("🌐 Saisissez les coordonnées :")
        # Création de deux colonnes dans la barre latérale pour Lat et Lon
        col_lat, col_lon = st.sidebar.columns(2)
        
        lat_input = col_lat.text_input("Latitude", placeholder="ex: 423618.2", key="lat_in")
        lon_input = col_lon.text_input("Longitude", placeholder="ex: 30121.7", key="lon_in")

        if lat_input and lon_input:
            # On utilise une version adaptée de decode_gps pour traiter les entrées séparées
            try:
                def convertir_valeur(val_str):
                    val = float(val_str.replace(',', '.').strip())
                    # Si la valeur est > 1000, on applique votre format compact (DegMinSec)
                    if abs(val) > 1000:
                        deg = int(val / 10000)
                        reste = val - (deg * 10000)
                        minutes = int(reste / 100)
                        secondes = reste - (minutes * 100)
                        return deg + (minutes / 60) + (secondes / 3600)
                    return val

                lat_dec = convertir_valeur(lat_input)
                lon_dec = convertir_valeur(lon_input)
                
                point_recherche = (lat_dec, lon_dec)
                label_position = f"GPS : {lat_dec:.5f}, {lon_dec:.5f}"
                st.sidebar.success(f"Converti : {lat_dec:.4f} / {lon_dec:.4f}")
            except Exception as e:
                st.sidebar.error("Format invalide")

    st.sidebar.markdown("---")
    st.sidebar.header("2. Sélection des Concours")
    active_points = []
    cols_check = st.sidebar.columns(2)
    for i, p in enumerate(all_points):
        col = cols_check[i % 2]
        if col.checkbox(f"{p['nom']}", value=True, key=f"city_{p['nom']}"):
            active_points.append(p)

    # --- CALCULS ET RÉSULTATS ---
    resultats_adresse = {"ok": [], "ko": []}
    score_adresse = 0

    if point_recherche:
        for p in active_points:
            dist = geodesic(point_recherche, (p['lat'], p['lon'])).meters
            info = {"nom": p['nom'], "dist": round(dist/1000, 1), "min": round(p['rayon']/1000, 1)}
            if dist > p['rayon']:
                resultats_adresse["ok"].append(info)
                score_adresse += 1
            else:
                resultats_adresse["ko"].append(info)

    # --- MISE EN PAGE ---
    col_map, col_details = st.columns([3, 1])

    with col_map:
        start_loc = point_recherche if point_recherche else [50.0, 2.5]
        start_zoom = 8 if point_recherche else 6
        m = folium.Map(location=start_loc, zoom_start=start_zoom)

        def generer_arc_nord(centre_lat, centre_lon, rayon_metres):
            coords = []
            for azimut in range(270, 451, 3):
                dest = geopy_dist(meters=rayon_metres).destination((centre_lat, centre_lon), azimut)
                coords.append([dest.latitude, dest.longitude])
            return coords

        for p in active_points:
            points_arc = generer_arc_nord(p['lat'], p['lon'], p['rayon'])
            folium.PolyLine(
                locations=points_arc, color=p['coul'], weight=4, opacity=0.9,
                tooltip=f"Ligne {p['nom']} ({p['rayon']/1000} km)"
            ).add_to(m)

        if point_recherche:
            folium.Marker(
                point_recherche, popup=label_position,
                icon=folium.Icon(color="black", icon="home")
            ).add_to(m)

        st_folium(m, width="100%", height=750)

    with col_details:
        st.subheader("📋 Analyse Détaillée")
        if point_recherche:
            st.info(f"Position : {label_position}")
            st.markdown(f"### Score : {score_adresse} / {len(active_points)}")
            c_score = couleurs_zones.get(score_adresse, "#000")
            st.markdown(f'<div style="background-color:{c_score};height:15px;width:100%;border-radius:5px;"></div><br>', unsafe_allow_html=True)
            
            with st.expander("✅ JOUABLES", expanded=True):
                if resultats_adresse["ok"]:
                    for c in resultats_adresse["ok"]:
                        st.success(f"**{c['nom']}**\n\n+ {c['dist']} km (Min {c['min']})")
                else: st.write("Aucun.")

            with st.expander("❌ INTERDITS", expanded=True):
                if resultats_adresse["ko"]:
                    for c in resultats_adresse["ko"]:
                        st.error(f"**{c['nom']}**\n\n{c['dist']} km (Min {c['min']})")
                else: st.write("Aucun.")
        else:
            st.warning("👈 Recherchez une position à gauche.")

# ---------------------------------------------------------
# PAGE 2 : RÉSULTATS DES CONCOURS (La nouvelle partie)
# ---------------------------------------------------------
elif page == "Résultats des Concours":

    st.title("🏆 Analyse des Classements Officiels")
    st.write("Importez vos PDF pour les convertir en tableaux.")

    uploaded_file = st.file_uploader("Fichier PDF du concours", type="pdf")

    if uploaded_file:
        try:
            with pdfplumber.open(uploaded_file) as pdf:
                all_data = []
                # On analyse les premières pages pour trouver le classement
                for i in range(len(pdf.pages)):
                    page = pdf.pages[i]
                    
                    # Stratégie 1 : Tentative d'extraction de tableau structuré
                    table = page.extract_table({
                        "vertical_strategy": "text",
                        "horizontal_strategy": "text",
                        "snap_y_tolerance": 5,
                        "intersection_x_tolerance": 15
                    })
                    
                    if table:
                        all_data.extend(table)
                
                if not all_data:
                    st.error("Aucun tableau détecté. Tentative de lecture brute...")
                    # Stratégie 2 : Lecture ligne par ligne (plus robuste pour Francolomb)
                    text = pdf.pages[0].extract_text()
                    st.text_area("Aperçu du texte extrait :", text, height=200)
                else:
                    # Nettoyage des données
                    # On retire les lignes vides et on nettoie les espaces
                    df = pd.DataFrame(all_data)
                    df = df.apply(lambda x: x.str.replace('\n', ' ') if x.dtype == "object" else x)
                    df = df.dropna(how='all')

                    st.success("Données extraites !")
                    st.dataframe(df, use_container_width=True)
                    
                    # Bouton export
                    csv = df.to_csv(index=False).encode('utf-8')
                    st.download_button("Télécharger en CSV", csv, "resultats.csv", "text/csv")

        except Exception as e:
            st.error(f"Erreur lors de la lecture du fichier : {e}")
    
    # Sélecteur de concours
    concours_choisi = st.selectbox("Sélectionnez un concours :", [p['nom'] for p in all_points])
    
    # Simulation de données de résultats (Peut être remplacé par un fichier CSV/Excel)
    data = {
        "Rang": [1, 2, 3, 4, 5],
        "Amateur": ["Jean Dupont", "Pierre Martin", "Marie Curie", "Luc Durand", "Anne Petit"],
        "Pigeon ID": ["FR-22-12345", "BE-21-98765", "FR-23-44556", "FR-22-00112", "NL-20-88776"],
        "Heure d'arrivée": ["16:45:22", "16:48:10", "16:55:05", "17:02:40", "17:15:12"],
        "Vitesse (m/min)": [1150.4, 1142.1, 1130.5, 1110.2, 1095.8]
    }
    df = pd.DataFrame(data)

    st.subheader(f"Classement Officiel - {concours_choisi}")
    
    # Affichage du tableau interactif
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Graphique des vitesses
    st.bar_chart(df, x="Amateur", y="Vitesse (m/min)")

# ---------------------------------------------------------
# PAGE 3 : INFORMATIONS
# ---------------------------------------------------------
elif page == "Informations":
    st.title("ℹ️ À propos")
    st.write("Ce portail aide les amateurs à visualiser les zones de jeu et consulter les résultats officiels.")