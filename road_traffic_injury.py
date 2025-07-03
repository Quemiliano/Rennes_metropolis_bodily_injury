# Sujet: Accidents corporels sur Rennes Métropole
#[Importations]:
#! pip install bokeh
#! pip install shapely
import numpy as np
import pandas as pd
import json as js
from bokeh.models import ColumnDataSource,HoverTool, Dropdown, CustomJS, Select,ColorPicker,Tabs,TabPanel, DataTable, TableColumn
from bokeh.models.widgets import Div, DatePicker
from bokeh.plotting import figure, show, curdoc, output_file
from bokeh.layouts import layout, row, column
from bokeh.transform import factor_cmap
from bokeh.tile_providers import get_provider
import datetime as dt
from shapely.geometry import Point, Polygon
#[Fonctions]:



def lnglat_to_meters(longitude: float, latitude: float) -> tuple[float, float]:
    """Projette les valeurs (longitude, latitude) données en coordonnées de Web Mercator
    (mètres à l'est de Greenwich et mètres au nord de l'équateur).
    """
    origin_shift = np.pi * 6378137
    easting = longitude * origin_shift / 180.0
    northing = np.log(np.tan((90 + latitude) * np.pi / 360.0)) * origin_shift / np.pi
    return (easting, northing)

def polygon_lnglat_to_meters(polygon: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Projette les valeurs (longitude, latitude) de la liste de valeur constituant le polygon  en coordonnées de Web Mercator
    (mètres à l'est de Greenwich et mètres au nord de l'équateur).
    """

    return [lnglat_to_meters(longitude, latitude) for longitude, latitude in polygon]


def col_change(data,cols):
    """Transformation des colonnes pour calcule horizontale"""
    for col in cols:
        data[col]=  data[col].map(lambda x: False if x==None else True)

def as_quali_numeric(data,cols):
    """Transformation des variables qualitatif en facteur
    Prend en argument un table et des noms de colonne en chaine de caractère"""
    for col in cols:
        data[col]=  data[col].map(lambda x: True if x=="Oui" else False)
        data[col]= data[col].astype('int')
   


def inside_polygone(point_coords, polygone_coords):
    # Création d'un objet Point à partir des coordonnées du point
    point = Point(point_coords)
    polygone = Polygon(polygone_coords)
    return point.within(polygone)

#[Programme Tests]

#URL de récupération des données en rapport avec  la météo sur sur Rennes

#Importation de donnée

df_accident= pd.read_json("data/accidents_corporels.json")
keep_col= ['geo_shape', 'date', 'heure', 'inter', 'nomv', 'nomv_2', 'numvro_2',
       'vehicule1', 'vehicule2', 'vehicule3', 'vehicule4', 'vehicule5',
       'vehicule6', 'usager1', 'usager2', 'usager3', 'usager4', 'usager5',
       'usager6', 'usager7', 'usager8', 'ntu', 'nbh', 'nbnh', 'pieton', 'velo',
       'moto']


df_accident= df_accident.loc[:, keep_col]
#Ilots Regroupés pour l'Information Statistique (Iris) version Rennes Métropole

df_iris= pd.read_json("data/iris_version_rennes_metropole.json")
df_iris= df_iris.loc[:, ['geo_shape','nom_com', 'nom_iris']]



#----------------------------------------------Traitement des données-------------------------------------------------------------------------------
#----------------------------------------------------------------------------------------------------------------------------------------------------
 
df_accident["date"]=  df_accident["date"].map(lambda x: x[0:10]) # récupération de l'heure 
df_accident["date"]=  df_accident["date"] + " " + df_accident["heure"]

df_accident["date"]= pd.to_datetime(df_accident["date"],format='%Y-%m-%d %H:%M')# Formatage de la date en objet datetime de pandas
df_accident= df_accident.sort_values(by='date', ascending=False)
df_accident["date"]=  df_accident["date"].map(lambda x: x.strftime(format= "le %d/%m/%Y à %H:%M" ))

usagers= ['usager1', 'usager2', 'usager3', 'usager4', 'usager5', 'usager6','usager7', 'usager8']
vehicules= ['vehicule1', 'vehicule2', 'vehicule3', 'vehicule4', 'vehicule5', 'vehicule6']
mobility= ['pieton', 'velo', 'moto']

# Transformation des composants colonnes usagers, véhicule et du mobilité en type boléen
col_change(df_accident, usagers)
col_change(df_accident, vehicules)
as_quali_numeric(df_accident, mobility)

# 
df_accident["nb_usagers_implique"]= df_accident.loc[:,usagers].sum(axis= 1)
df_accident["nb_vehicules_implique"]= df_accident.loc[:,vehicules].sum(axis= 1)



#Récupération des coordonnées de localisation des points et des polygones
df_accident["coordinates"]= df_accident["geo_shape"].map(lambda x: x["geometry"]["coordinates"] )
df_iris["polygon"]=  df_iris["geo_shape"].map(lambda x: x["geometry"]["coordinates"][0])

# Appliquer la fonction inside_polygone à chaque ligne du DataFrame df_accident
df_accident["nom_iris"] = None  # Initialisation de la colonne nom_iris à None
df_accident["polygon"] = None  # Initialisation de la colonne polygon à None

#Conservation des données en relation les accidents s'étant uniquement sur la région Rennaise et quelques alentour de la ville notament Saint-Jacques-Gaîté
df_iris = df_iris[(df_iris['nom_com'] == "Rennes") |
                   (df_iris['nom_com'] == "Saint-Jacques-de-la-Lande")]


#Construction d'une dataframe général se badant sur les accidents s'étant uniquement sur la région Rennaise et quelques alentour de la ville notament Saint-Jacques-Gaîté
for index, row in df_accident.iterrows():
    for nom_iris, polygon_coords in zip(df_iris.nom_iris, df_iris.polygon):
        if inside_polygone(row["coordinates"], polygon_coords):
            df_accident.at[index, "nom_iris"] = nom_iris
            df_accident.at[index,"polygon"]= polygon_coords
            break  # Sortir de la boucle dès qu'un iris est trouvé pour éviter de vérifier les autres polygones

#Suppression des lignes ayant None comme nom de commune contenant des valeurs None car considérer comme étan des lignes en rapport avec des accident en dehors de la zone que nous avon considéré

df_accident = df_accident.dropna(subset=['nom_iris'])

# Transformation des coordonées de localisation en mètre mercator 

df_accident["long"]= df_accident["coordinates"].map(lambda x: lnglat_to_meters(x[0], x[1])[0] )
df_accident["lat"]= df_accident["coordinates"].map(lambda x: lnglat_to_meters(x[0], x[1])[1] )

#Transformation des coordonées des polynomes en localisation en mètre  mercator 


df_accident["polygon"]=  df_accident["polygon"].map(lambda x: polygon_lnglat_to_meters(x) )


#Suppression des colonnes inutile dans les dataframes
df_accident= df_accident.drop(usagers + vehicules + ["geo_shape", "coordinates", "numvro_2","nomv_2"],   axis= 1)


#Renommage des noms des colonnes 
df_accident= df_accident.rename(
    columns={"inter": "intersection", "nomv": "nom_voie", "ntu": "nbr_morts",
               "nbh" : "nbr_hospitalise", "nbnh" : "nb_non_hospitalise",
               "pieton": "presence_pieton", "velo" : "presence_velo",
                 "moto" : "presence_moto"
            })

#Récupération des donnée de 2022: Ce sont les données les plus récentes

df_accident_2022= df_accident[df_accident['date'].str.contains("2022")]

#Création de liste de longitude et de latitude pour chaque polygone
df_accident_2022["coords_x"]= df_accident_2022["polygon"].map(lambda x: [crds[0] for crds in x] )
df_accident_2022["coords_y"]= df_accident_2022["polygon"].map(lambda x: [crds[1] for crds in x] )



#----------------------------------------------------------------Fin Traitement de données-----------------------------------------------------------
#----------------------------------------------------------------------------------------------------------------------------------------------------


#Visualisation finale des données de 2012 à 2022:

# print(df_accident.describe())
# print(df_accident.shape)
# print(df_iris.shape)
# print(df_iris.columns)

#Visualisation finale des données de 2022:

#print(df_accident_2022.shape)
# print(df_accident_2022.describe())
#print(df_accident_2022.columns)
#print(df_accident_2022.columns)

#------------------------------------------------------Représentation graphique----------------------------------------------------------------
#----------------------------------------------------------------------------------------------------------------------------------------------------



#----------------------> Première carte: avec les points de localisations uniquement
#------------------------------------------------------------------------------------------------


# Cadrage des cartes sur Rennes / Création d'une visualisation Zommée  utilisé
long_rennes, lat_rennes =  -1.6774, 48.1173

EN = lnglat_to_meters(long_rennes, lat_rennes)

dE = 8000 # (m) Easting  plus-and-minus from map center
dN = 8000 # (m) Northing plus-and-minus from map center

x_range = (EN[0]-dE, EN[0]+dE) # (m) Easting  x_lo, x_hi
y_range = (EN[1]-dN, EN[1]+dN) # (m) Northing y_lo, y_hi


plot_rennes = figure(x_range=x_range, y_range=y_range,
                     x_axis_type="mercator", y_axis_type="mercator",
                     height=600, width=600, active_scroll="wheel_zoom",
                     title="Figure 1: Cartographie des accidents corporels survenu dans la ville de Rennes en 2022")

plot_rennes.toolbar.logo=None #Enlève le logo



provider = "OpenStreetMap Mapnik"
plot_rennes.add_tile(provider)

#Création de la source contenant les coordonées de localisation
source_coord= ColumnDataSource(data= df_accident_2022)



points= plot_rennes.triangle(x="long", y="lat" , size=20,angle=3.14,
              fill_color="gray",line_color="pink", fill_alpha=1,
              source=source_coord)

#Création du widget pour choisir de la couleur du pointeur
picker1= ColorPicker(title="Couleur de remplissage du pointeur",color=points.glyph.fill_color)
picker1.js_link('color', points.glyph, 'fill_color')


#Création d'outil de survol interactif
hover_tool_loc= HoverTool(tooltips=[("Date de l'accident", '@date'),('Adrresse', '@nom_voie'),
                                ('Intersection',   '@intersection'), ("Nombre de mort", '@nbr_morts'), ("Nombre lde personne hospitalisés", '@nbr_hospitalise'),
                                ("Nombre de personne non hospitalise", "@nb_non_hospitalise"), ("Piéton impliqué", "@presence_pieton"),
                                ("Cycliste impliqué", "@presence_velo"), ("Motard impliqué", "@presence_moto"),
                                ("Nombre d'usager impliqué", "@nb_usagers_implique"), ("Nombre de véhicule impliqué", "@nb_vehicules_implique")
                                ])

plot_rennes.add_tools(hover_tool_loc)


# Création du widget de sélection du fond de carte


#Liste des fonds de carte
options_provider=  dict([("OpenStreetMap Mapnik", get_provider("OpenStreetMap Mapnik")),
                         ("OpenTopoMap", get_provider("OpenTopoMap")),
                         ("CartoDB Positron", get_provider("CartoDB Positron")),
                         ("CartoDB Dark Matter", get_provider("CartoDB Dark Matter")),
                         ("CartoDB Voyager", get_provider("CartoDB Voyager")),
                         ("Esri World Imagery", get_provider("Esri World Imagery"))
                        ])


select_provider = Select(title="Choix du fond de carte", value=provider, options=list(options_provider.keys()))

# Callback JavaScript pour mise à jour du fond de carte 
callback_provider = CustomJS(args=dict(p=plot_rennes, select=select_provider, tile_providers=options_provider),
                    code="""
                            p.renderers[0].tile_source = tile_providers[select.value];
                        """)

#Etape de mis à jour des selection de l'utilisateur
select_provider.js_on_change('value', callback_provider) 



#----------------------> Deuxième carte: avec les polygones de localisations uniquement en périphérie et dans le centre de Rennes s
#------------------------------------------------------------------------------------------------

#Création de la figure
plt_iris_periph_center = figure(x_range=x_range, y_range=y_range,
                     x_axis_type="mercator", y_axis_type="mercator",
                     height=600, width=600,active_scroll="wheel_zoom",
                     title="Figure 2: Cartographie des accidents corporel groupé par iris de la ville de Rennes")

plt_iris_periph_center.toolbar.logo=None #Enlève le logo

#Création des CDS pour le centre et pour la périphérie

iris_periph= ['Portugal', 'Les Cloteaux', 'Canada', 'ZA Sud-Est',
              'Les Gayeulles', 'Plaine de Baud', 'Brno', 'Dalle Kennedy', 
              'Le Gallet - Les Longs Champs Nord', 'Suisse', 'Villejean Nord-Ouest',
              'Cleunay Ouest', 'Les Olympiades', 'Campus de Beaulieu',
              'Saint-Laurent', 'Villejean Sud-Est', 'Beauregard','ZA Nord',
              'Saint-Benoit', 'Emile Bernard', 'Le Pigeon Blanc', 'Saint-Yves',
               'Morbihan Ouest', 'Villejean Sud-Ouest', 'Le Landrel Ouest',
              'Champeaux', 'Le Landry', 'Villejean Nord-Est', 'Sainte-Elizabeth - Grèce',
              'Torigné Est', 'Les Champs Manceaux', 'Les Longs Champs Sud',
              'Torigné Ouest', 'La Poterie Sud', 'Stade Rennais', 'Le Bois Perrin', 
            'Morbihan Est', 'Le Gast Ouest', 'Le Gast Est', 'Le Landrel Est - Les Hautes Ourmes',
            'Henri Fréville Sud Est', 'Henri Fréville Sud Ouest', 'ZA Ouest']

#Groupement par nom d'iris
grp_iris= df_accident_2022.groupby("nom_iris", as_index= False)

matrice_gpr_iris= grp_iris.agg(Hosp_par_iris= ("nbr_hospitalise", "sum"), 
                                Non_Hosp_par_iris=("nb_non_hospitalise", "sum"),
                                Mort_par_iris= ("nbr_morts", "sum"),
                                Pieton_imp_par_iris= ("presence_pieton", "sum"),
                                Cycliste_imp_par_iris= ("presence_velo", "sum"),
                                Motard_imp_par_iris= ("presence_moto", "sum"),
                                coords_x= ("coords_x","first"),
                                coords_y= ("coords_y","first") )


source_periph = ColumnDataSource(matrice_gpr_iris[matrice_gpr_iris["nom_iris"].map(lambda x: x in iris_periph)] )

iris_centre= [ "Parlement", "Vieux Saint-Etienne",
                  "Cathédrale", "Hôtel-Dieu","Saint-Louis",
                   "Hoche", "Parcheminerie - Toussaints"]


source_centre = ColumnDataSource(matrice_gpr_iris[matrice_gpr_iris["nom_iris"].map(lambda x: x in iris_centre) ])

#Fond de carte polygone
plt_iris_periph_center.add_tile("CartoDB Positron")

plg_periph= plt_iris_periph_center.patches(xs="coords_x",ys="coords_y",source = source_periph, alpha=0.4, color= "gray" , line_color="white")
plg_center= plt_iris_periph_center.patches(xs="coords_x",ys="coords_y",source = source_centre, alpha=0.4, color= "pink" , line_color="gray")

#Création du widget pour choisir de la couleur du pointeur
picker2= ColorPicker(title="Couleur de remplissage des iris peripfériques ",color=plg_periph.glyph.fill_color)
picker3= ColorPicker(title="Couleur de remplissage des iris centraux",color=plg_center.glyph.fill_color)
picker2.js_link('color', plg_periph.glyph, 'fill_color')
picker3.js_link('color', plg_center.glyph, 'fill_color')


# Ajouter les polygones à la figure

# Création et ajout de l'Outil de survol
hover_tool_iris = HoverTool(tooltips=[  ( 'iris','@nom_iris'),
                                        ("Personnes non hospitalisés", "@Non_Hosp_par_iris"),
                                        ("Personnes non hospitalisés", "@Hosp_par_iris"),
                                        ("Personnes mortes", "@Mort_par_iris"),
                                        ("Total piétons impliqués", "@Pieton_imp_par_iris"),
                                        ("Total cyclistes impliqués", "@Cycliste_imp_par_iris"),
                                        ("Total motards impliqués", "@Motard_imp_par_iris"),
                                   ])


plt_iris_periph_center.add_tools(hover_tool_iris)



#----------------------> Troisième carte: avec les points de localisations uniquement
#------------------------------------------------------------------------------------------------

#Création de la figure
plt_iris_all = figure(x_range=x_range, y_range=y_range,
                     x_axis_type="mercator", y_axis_type="mercator",
                     height=600, width=600,active_scroll="wheel_zoom",
                     title="Figure 3: Cartographie des accidents corporel groupé par iris de la ville de Rennes")

plt_iris_all.toolbar.logo=None #Enlève le logo


#Création du CDS
source_all = ColumnDataSource(matrice_gpr_iris)

#Fond de carte polygone
plt_iris_all.add_tile("CartoDB Positron")

#Ajout des polygones
plgs= plt_iris_all.patches(xs="coords_x",ys="coords_y",source = source_all, alpha=0.4, color= "gray" , line_color="white")

#Création du widget pour choisir de la couleur des polygones
picker4= ColorPicker(title="Couleur de remplissage des iris",color=plgs.glyph.fill_color)
picker4.js_link('color', plgs.glyph, 'fill_color')

#On utilise le même type d'outils de survol que le précédent graphisue
plt_iris_all.add_tools(hover_tool_iris)

#------------------------------------->Fin  cartographie


#------------------------------->Première Courbe Etat des impliqué dans les accidents corporel sur Rennes
#---------------------------------------------------------------------------------

#Traitement des données pour Courbe représentatif de la statistique de l'état des impliqués

df_accident["annee"]= df_accident["date"].map(lambda x: x[9:13])
df_accident=  df_accident.sort_values(by='annee', ascending=True)

grp_annee= df_accident.groupby("annee", as_index= False)

matrice_accident= grp_annee.agg(Hosp_par_annee= ("nbr_hospitalise", "sum"), 
                                Non_Hosp_par_annee=("nb_non_hospitalise", "sum"),
                                Mort_par_annee= ("nbr_morts", "sum"),
                                Pieton_imp= ("presence_pieton", "sum"),
                                Cycliste_imp= ("presence_velo", "sum"),
                                Motard_imp= ("presence_moto", "sum"),
                                Usagers_imp=("nb_usagers_implique", "sum"), 
                                Vehicules_imp=("nb_vehicules_implique", "sum") )


#Courbe représentatif de la statistique de l'état des impliqués dans des accidents corporels sur rennes entre 2012 et 2022

plot_etat_imp= figure(title=  "Figure 4: Courbe représentatif de la statistique de l'état des impliqués dans des accidents corporels sur rennes",
                      x_axis_label= "annee", y_axis_label="Nombre de personnes impliqués",
                      width= 900, tools="crosshair", background_fill_color='#E6E7E4',
                      background_fill_alpha=0.4)

plot_etat_imp.line(x= 'annee', y= 'Non_Hosp_par_annee',source=matrice_accident,
                   legend_label= "Personnes non hospitalisés", color= "green", line_width=2)

plot_etat_imp.line(x= 'annee', y= 'Hosp_par_annee', source=matrice_accident,
                   legend_label= "Personnes hospitalisés", color= "gold", line_width=2)

plot_etat_imp.line(x= 'annee', y= 'Mort_par_annee', source=matrice_accident,
                   legend_label= "Personnes morts", color= "red", line_width=2)

#Quelsues utilitaires 
plot_etat_imp.toolbar.logo=None #Enlève le logo
plot_etat_imp.title.text_font_size="9pt" #Taille du titre
plot_etat_imp.legend.location = 'top_right'

plot_etat_imp.grid.grid_line_alpha = 0.4 # # Augmenter l'opacité du cadrillage
"https://data.rennesmetropole.fr/explore/dataset/prevision-meteo-rennes-arome/information/"
# Ajout de la grille en pointillés noirs
plot_etat_imp.grid.grid_line_dash = 'dotted'
plot_etat_imp.grid.grid_line_color = 'black'

# Outil de survol/ Hovertool

hover_etat_1 = HoverTool(tooltips=[("Temps", "@annee"),
                                   ("Personnes non hospitalisés", "@Non_Hosp_par_annee")],
                                   renderers=[plot_etat_imp.renderers[0]])

hover_etat_2 = HoverTool(tooltips=[("Temps", "@annee"),
                                   ("Personnes hospitalisés", "@Hosp_par_annee")],
                                   renderers=[plot_etat_imp.renderers[1]])

hover_etat_3 = HoverTool(tooltips=[("Temps", "@annee"),
                                   ("Personnes mort", "@Mort_par_annee")],
                                   renderers=[plot_etat_imp.renderers[2]])

plot_etat_imp.add_tools(hover_etat_1, hover_etat_2, hover_etat_3)

#-----------------------------------------Deuxieme Courbe graphique des différentes profils des  individus associé aux conducteurs
#-------------------------------------------------------------------------


#Création de la data source
source_imp= ColumnDataSource(matrice_accident)


plot_imp= figure(title=  "Figure 5: Evolution des impliqués dans les accidents corporels sur Rennes ",
                 x_axis_label= "Temps", y_axis_label="Nombre de personnes impliqué",width= 900,
                 tools="crosshair", background_fill_color='#E6E7E4',
                      background_fill_alpha=0.3)
plot_imp.toolbar.logo=None #Enlève le logo

# Ajout de la grille en pointillés noirs
plot_imp.grid.grid_line_dash = 'dotted'
plot_imp.grid.grid_line_color = 'black'
plot_imp.grid.grid_line_alpha = 0.4 # Augmenter l'opacité du cadrillage


#Tracage de la courbe
plot_imp.line(x= "annee", line_width=3, y="Usagers_imp",  source = source_imp, color= "pink" )

# Création de l'outil Hover
hover_tool_imp = HoverTool(tooltips=[('Année', '@annee'),
                                    ("Nombre de d'individus",
                                     '@Usagers_imp')], mode= "mouse")
plot_imp.add_tools(hover_tool_imp)


#Création du widgets
menu_dropdown = Dropdown(label ="Choix de la variable",
                         menu=[ ('Total individus impliqués','Usagers_imp'),
                                ('Nombre de piéton impliqués', 'Pieton_imp'),
                                ('Nombre de véhicules impliqués','Vehicules_imp'),
                                ("Nombre de cyclistes impliqués", "Cycliste_imp"),
                                ("Nombre de motard impliqués", "Motard_imp")
                                ])


#Création d'un callback javascript pour récupérer la valeur du choix de l'utilisateur
callback_imp = CustomJS(args=dict(source = source_imp),
                     code="""
                            const data = source.data;
                            const col= cb_obj.item
                            const Usagers_imp = data["Usagers_imp"]
                            const Usagers_imp_new = data[col]
                            for (let i = 0; i < Usagers_imp.length; i++) {
                                    Usagers_imp[i] = Usagers_imp_new[i]
                            }
                            source.change.emit();
                        """)


menu_dropdown.js_on_event('menu_item_click',callback_imp)#Un clic sur le menu va appeler le code de callback 

#-----------------------------------------Troisième Graphique: histogramme des différentes des accidents en fonction du type d' intersections
#-------------------------------------------------------------------------

grp_intersection= df_accident.groupby("intersection", as_index= False)

matrice_accident_inter= grp_intersection.agg(Pieton_imp= ("presence_pieton", "sum"),
                                Cycliste_imp= ("presence_velo", "sum"),
                                Motard_imp= ("presence_moto", "sum"),
                                Vehicules_imp=("nb_vehicules_implique", "sum") )

plot_ac_inter = figure(x_range=matrice_accident_inter["intersection"], height=350, title="Figure 6: Histogramme du nombre d'accident en fonction du type d'intersection",
           toolbar_location=None,width= 900, background_fill_color='#E6E7E4',
                      background_fill_alpha=0.1)

plot_ac_inter.toolbar.logo=None #Enlève le logo

source_imp= ColumnDataSource(matrice_accident_inter)

plot_ac_inter.vbar(x="intersection", top="Pieton_imp", width=0.9, source= source_imp, fill_color="pink", fill_alpha=0.3,)



plot_ac_inter.xgrid.grid_line_color = None
plot_ac_inter.y_range.start = 0.6

# Création de l'outil Hover
hover_tool_inter = HoverTool(tooltips=[('Intersection', '@intersection'),
                                    ("Nombre de d'individus",
                                     '@Pieton_imp')])
plot_ac_inter.add_tools(hover_tool_inter)

options_pro_inter= { "Accidents impliquant piétons":"Pieton_imp" ,
                    "Accident impliquant cyclistes":"Cycliste_imp", 
                    "Accident impliquant motards":"Motard_imp" ,
                    "Accident impliquant véhicules":"Vehicules_imp" }

select_inter = Select(title="Choix de la variable", value="Pieton_imp", options=list(options_pro_inter.keys()))

# Callback JavaScript pour mise à jour du fond de carte 
callback_inter = CustomJS(args=dict(select=select_inter,source=source_imp,tile_providers=options_pro_inter),
                          
                    code="""
                            const col= tile_providers[select.value];
                            const data = source.data
                            const Pieton_imp = data["Pieton_imp"]
                            const Pieton_imp_new = data[col]
                            for (let i = 0; i < Pieton_imp.length; i++) {
                            Pieton_imp[i] = Pieton_imp_new[i]
                            }
                            source.change.emit();
                        """)

#Etape de mis à jour des selection de l'utilisateur
select_inter.js_on_change('value', callback_inter) 

#--------------------------------fin Représentation Graphiques
#--------------------------------------------------------------

#--------------------------> Affichage tables
#----------------------------------------------------------
# Création de la source de données de la table accident
source_acc = ColumnDataSource(df_accident.head(7))

# Création des colonnes de la table
columns_acc = [
    TableColumn(field="heure", title="heure"),TableColumn(field="intersection", title="intersection"),
    TableColumn(field="nom_voie", title="nom_voie"),TableColumn(field="nbr_morts", title="nbr_morts"),
    TableColumn(field="nbr_hospitalise", title="nbr_hospitalise"),TableColumn(field="nb_non_hospitalise", title="nb_non_hospitalise"),
    TableColumn(field="presence_pieton", title="presence_pieton"),TableColumn(field="presence_velo", title="presence_velo"),
    TableColumn(field="presence_moto", title="presence_moto"),TableColumn(field="nb_usagers_implique", title="nb_usagers_implique"),
    TableColumn(field="nb_vehicules_implique", title="nb_vehicules_implique"),TableColumn(field="long", title="long"),TableColumn(field="lat", title="lat")]

# Création de la table
table1 = DataTable(source= source_acc, columns=columns_acc, width=1200, height=300)

# Création de la source de données de la table iris
source_ir = ColumnDataSource(df_iris.head(7))

# Création des colonnes de la table
columns_ir = [
    TableColumn(field="geo_shape", title="geo_shape"),TableColumn(field="nom_iris", title="nom_iris"),
    TableColumn(field="nom_voie", title="nom_voie"),TableColumn(field="nbr_morts", title="nbr_morts"),
    TableColumn(field="polygon", title="polygon")]
# Création de la table
table2 = DataTable(source= source_ir, columns=columns_ir, width=800, height=280)

#---------------------------> Insertion d'image
#-------------------------------------------------------------------------------

# Créer une figure
plot_image = figure(height=350,toolbar_location=None, tools="save", width=800, background_fill_color="#E0E2E8" )
plot_image_RM = figure(height=100,toolbar_location=None, tools="save", width=400)
plot_image_mto = figure(height=350,toolbar_location=None, tools="save", width=800, background_fill_color="#E0E2E8" )

# Charger une image
plot_image.image_url(url=["Images/image_accident.jpg"], x=3, y=3, w=1, h=1)
plot_image_RM.image_url(url=["Images/RENNES_Métropole_noir.svg.png"], x=0, y=0, w=1, h=1)
plot_image_mto.image_url(url=["Images/meteo_accident.jpg"], x=3, y=3, w=1, h=1)

# Désactiver les axes des abscisses et des ordonnées pour l'image 1

plot_image.xaxis.visible = False
plot_image.yaxis.visible = False
plot_image.grid.grid_line_alpha = 0

# Désactiver les axes des abscisses et des ordonnées pour l'image 2

plot_image_RM.xaxis.visible = False
plot_image_RM.yaxis.visible = False
plot_image_RM.grid.grid_line_alpha = 0

# Désactiver les axes des abscisses et des ordonnées pour l'image 2

plot_image_mto.xaxis.visible = False
plot_image_mto.yaxis.visible = False
plot_image_mto.grid.grid_line_alpha = 0


#----------------------------------Fin représentattion image
#---------------------------------------------------------


#Construction des onglets de la page web
titre = Div(text="""<h1> Analyse statistique des accidents corporels sur Rennes Métropole </h1>
""", styles= {"font-family": "Times New Roman"})

sous_titre1_1= Div(text="""<h3> Etude de l'art</h3>""",  styles={'font-style': 'italic', 'color': '#5E2B45', "font-family": "Times New Roman"})

div_panel1_1 = Div(text="""
<p>La circulation routière est un aspect crucial de la vie quotidienne en France, affectant non seulement la mobilité des individus, mais aussi le bon fonctionnement de l'économie nationale. Des infrastructures de transport efficaces sont essentielles pour garantir le flux constant des biens et des personnes à travers le pays.</p>
<p>Cependant, cette mobilité accrue s'accompagne malheureusement d'un risque accru d'accidents routiers, qui représentent une menace sérieuse pour la sécurité publique. </p>
<p>Ainsi, la gestion efficace de la circulation routière est un défi permanent auquel sont confrontées les autorités dans toutes les villes françaises, nécessitant une vigilance constante et des mesures proactives pour assurer la sécurité de tous.
</p>""", styles= {"font-size": "16px", "font-family": "Times New Roman"})
           
div_panel1_2 = Div(text="""
<p>Spécifiquement dans la ville de Rennes, nous avons porté notre attention sur les accidents corporels afin de mieux les comprendre. À cet effet, nous avons mené notre étude en nous basant sur une base de données sur <a href="https://data.rennesmetropole.fr/explore/dataset/accidents_corporels/information/">les accidents corporels sur Rennes métrople</a> issue du site de Rennes Métropole, qui traite des accidents corporels sur Rennes Métropole depuis 2012 jusqu'en 2022. </p>
<p>Pour une géolocalisation regroupée en fonction des iris, nous avons également récupéré une autre base de données fournissant des <a href="https://data.rennesmetropole.fr/explore/dataset/iris_version_rennes_metropole/information/">ilots regroupés pour l'Information Statistique (Iris) version Rennes Métropole</a> issue du même site .</p>
<p>Notre première base de données est composée de 5797 lignes et 39 colonnes.Tandis que notre deuxième base de données est composée de 172 lignes et 3 colonnes.</p>
<p>Bon à savoir : Pour rester dans le theme du logo Rennes metopole le scouleurs associé à nos représentations sont majotitairement roses, noir et gris</p>
""", styles= {"font-size": "16px", "font-family": "Times New Roman"})

sous_titre1_2 = Div(text="""
<h3> Traitement des données</h3> """,  styles={'font-style': 'italic', 'color': '#5E2B45, "font-family": "Times New Roman"'})          

div_panel1_3 = Div(text=""" 
<p>Lors du traitement de la base de données sur les accidents, nous avons supprimé les colonnes jugées inutiles, telles que les types de véhicules impliqués et les numéros de rue liés aux intersections, souvent mal renseignés ou contenant de nombreuses données manquantes.</p>
<p> Nous avons ensuite regroupé les usagers de la route et les véhicules impliqués par accident, tout en récupérant et en traitant les coordonnées de localisation.</p>
<p>À l'issue du traitement de la base de donnée sur les accident coorporel nous avons obtenu 4171 ligne et 16 colonnes</p>
<p></p>
<b>Je vous propose de visualiser apperçu de la table de donnée utilisé</b> 
""", styles= {"font-size": "16px", "font-family": "Times New Roman"})

div_panel1_4 = Div(text=""" 
<p>En ce qui concerne la deuxième table traitant des iris de Rennes Métropole, nous avons conservé au final trois colonnes, les autres étant jugées inutiles. Nous avons également filtré uniquement les iris de Rennes, ainsi que quelques iris entre Saint-Jacques et Rennes.</p>
<b>Ci suit une brève visualisation du tableau de données traitant des iris:</b>
""", styles= {"font-size": "16px", "font-family": "Times New Roman"})

div_panel1_5 = Div(text=""" 
<p>Nous avons décidé de fusionner ces deux tableaux en une seule base de données en utilisant l'appartenance d'un point de localisation d'un accident à un iris de la ville de Rennes.</p>
<p>En reliant chaque accident à une zone géographique spécifique, cette approche facilite l'analyse spatiale et la visualisation des données, ce qui peut révéler des tendances significatives et des schémas géographiques utiles pour comprendre les facteurs de risque et améliorer la sécurité routière.</p>
""", styles= {"font-size": "16px", "font-family": "Times New Roman"})

sous_titre2_1= Div(text="""<h3> Carte récapitulatif des accidents coorporels survenus en 2022 sur Rennes Métropole""",  styles={'font-style': 'italic', 'color': '#5E2B45', "font-family": "Times New Roman"})

div_panel2_1 = Div(text=""" 
<p></p>                   
<p>Nous avons jugé utile de visualiser la carte récapitulative des accidents corporels survenus en 2022 sur Rennes Métropole afin de mieux comprendre la répartition géographique de ces incidents et d'identifier les zones à risque potentiel.</p>
<p>En outre, une carte récapitulative des accidents peut être un outil précieux pour sensibiliser le public aux dangers de la route dans des zones spécifiques. En visualisant les données de manière graphique, les résidents locaux peuvent mieux comprendre les risques potentiels près de chez eux, les incitant ainsi à adopter des comportements plus prudents au volant et à respecter les règles de sécurité routière.</p>
<p></p>
<p>La concentration élevée d'accidents à Rennes, avec une nette diminution dans l'est de la ville, peut résulter de divers facteurs. Parmi eux, l'infrastructure routière, la densité de la population et les caractéristiques socio-économiques jouent un rôle clé. Des zones à forte densité de circulation et à activité économique intense sont souvent associées à plus d'accidents, tandis que des aménagements de sécurité insuffisants peuvent aggraver la situation. Une analyse plus poussée pourrait éclairer les mesures ciblées pour réduire les risques routiers.</p>    
""", styles= {"font-size": "16px", "font-family": "Times New Roman"})

sous_titre2_2= Div(text="""<h3>Carte récapitulative des accidents corporels survenus en2022 dans les iris périphériques et centraux de Rennes Métropole.</h3>""",  styles={'font-style': 'italic', 'color': '#5E2B45', "font-family": "Times New Roman"})

div_panel2_2 = Div(text=""" 
<p></p>
<p> En mettant en évidence les zones les plus touchées, cette carte pourrait aider les autorités locales à identifier les points chauds et à mettre en place des mesures de sécurité ciblées pour réduire les risques d'accidents. De plus, elle pourrait également être utilisée pour sensibiliser le public aux dangers de la route dans ces zones spécifiques et encourager l'adoption de comportements plus sûrs au volant.</p>
<p></p>
<p>On constate qu'il y a moins d'accidents qui se produisent en centre-ville comparativement à la périphérie de la ville, car plusieurs facteurs peuvent contribuer à cette tendance. D'abord, les vitesses de circulation plus réduites et la présence de nombreux dispositifs de sécurité, comme les feux de circulation et les passages pour piétons, dans les zones urbaines densement peuplées peuvent diminuer les risques d'accidents.</p>    
""", styles= {"font-size": "16px", "font-family": "Times New Roman"})

sous_titre2_3= Div(text="""<h3>Carte récapitulative des accidents corporels survenus en 2022 dans chaque iris de la ville de Rennes</h3>""",  styles={'font-style': 'italic', 'color': '#5E2B45', "font-family": "Times New Roman"})

div_panel2_3 = Div(text=""" 
<p> </p>
<p>
Il est intéressant de noter, à partir de la carte précédente, une variation du nombre d'individus impliqués dans les accidents, qui se concentre souvent dans les iris où l'on trouve des lieux pédagogiques ou commerciaux, notamment les universités, les lycées, les écoles primaires et les centres commerciaux. Cette observation soulève plusieurs points à considérer. Premièrement, la présence d'établissements éducatifs attire généralement un grand nombre de personnes, y compris des étudiants, des parents et des enseignants, ce qui peut augmenter le volume de circulation dans ces zones aux heures de pointe.</p>
""", styles= {"font-size": "16px", "font-family": "Times New Roman"})

sous_titre3_1= Div(text="""<h3>Courbe représentatif de la statistique de l'état des impliqués dans des accidents corporels sur rennes entre 2012 et 2022""",  styles={'font-style': 'italic', 'color': '#5E2B45', "font-family": "Times New Roman"})

div_panel3_1 = Div(text=""" 
<p>
La courbe représentative de la statistique de l'état des personnes impliquées dans des accidents corporels sur Rennes entre 2012 et 2022 offre un aperçu précieux de l'évolution des blessures survenues au cours de cette période. En examinant les données sur une décennie, cette courbe pourrait révéler des tendances significatives, telles que des augmentations ou des diminutions dans le nombre de blessures légères, graves ou mortelles. </p>                   
<p>Nous avons jugé utile de visualiser la carte récapitulative des accidents corporels survenus en 2022 sur Rennes Métropole afin de mieux comprendre la répartition géographique de ces incidents et d'identifier les zones à risque potentiel.</p>
<p>En outre, une carte récapitulative des accidents peut être un outil précieux pour sensibiliser le public aux dangers de la route dans des zones spécifiques. En visualisant les données de manière graphique, les résidents locaux peuvent mieux comprendre les risques potentiels près de chez eux, les incitant ainsi à adopter des comportements plus prudents au volant et à respecter les règles de sécurité routière.</p>
<p></p>""", styles= {"font-size": "16px", "font-family": "Times New Roman"})

sous_titre3_2= Div(text="""<h3>La courbe graphique représentant les différents profils des individus associés aux conducteurs sur rennes entre 2012 et 2022""",  styles={'font-style': 'italic', 'color': '#5E2B45', "font-family": "Times New Roman"})

div_panel3_2 = Div(text=""" 
<p></p>
<p>En examinant les données sur les accidents impliquant ces différents profils, cette courbe peut mettre en lumière des modèles distincts de comportement et de vulnérabilité. Par exemple, elle pourrait révéler une prévalence plus élevée d'accidents graves ou mortels impliquant des motards ou des piétons par rapport aux conducteurs de voiture.</p>
<p></p>""", styles= {"font-size": "16px", "font-family": "Times New Roman"})

sous_titre3_3= Div(text="""<h3>Histogramme des différents types d'accidents en fonction du type d'intersections de voie sur rennes entre 2012 et 2022""",  styles={'font-style': 'italic', 'color': '#5E2B45', "font-family": "Times New Roman"})

div_panel3_3 = Div(text=""" 
<p></p>
<p>En examinant les données sur les accidents impliquant ces différents profils, cette courbe peut mettre en lumière des modèles distincts de comportement et de vulnérabilité. Par exemple, elle pourrait révéler une prévalence plus élevée d'accidents graves ou mortels impliquant des motards ou des piétons par rapport aux conducteurs de voiture.</p>
<p> En classant les données selon les types d'intersections, tels que les carrefours en T, les giratoires, les intersections en croix, etc., cet histogramme permettrait d'identifier les configurations d'intersection les plus fréquemment associées aux accidents. </p>
<p>Par exemple, il pourrait révéler que les carrefours en T sont plus propices aux collisions que les giratoires. Une analyse de ces données pourrait orienter les efforts d'aménagement et de sécurité routière vers les types d'intersections présentant les plus grands risques, contribuant ainsi à réduire le nombre d'accidents et à améliorer la sécurité routière.</p>                  
                   """, styles= {"font-size": "16px", "font-family": "Times New Roman"})

sous_titre4_1= Div(text="""<h3>Pour aller plus loins""",  styles={'font-style': 'italic', 'color': '#5E2B45', "font-family": "Times New Roman"})

div_panel4_1 = Div(text=""" 
<p></p>
<p>Compléter l'étude en incorporant des données météorologiques pourrait apporter une dimension importante à notre compréhension des accidents routiers à Rennes. Les conditions météorologiques, telles que la pluie, la neige, le brouillard ou même simplement le vent, peuvent avoir un impact significatif sur les conditions de conduite et augmenter les risques d'accidents. Par exemple, la pluie peut rendre les routes glissantes, réduire la visibilité et augmenter les distances de freinage, ce qui augmente le risque de collisions. De même, la neige et le verglas peuvent rendre les routes dangereuses, en particulier si les conducteurs ne sont pas habitués à conduire dans de telles conditions.</p>
                   """, styles= {"font-size": "16px", "font-family": "Times New Roman"})


div_panel4_2= Div(text=""" 
<p></p>
<p>En incorporant des données météorologiques, en <a href="https://data.rennesmetropole.fr/explore/dataset/prevision-meteo-rennes-arome/information/">exemple</a> ceux proposé par Rennes Métropole  dans notre analyse, nous pourrions évaluer l'impact des conditions météorologiques sur la fréquence et la gravité des accidents routiers à Rennes. Cela nous permettrait de mieux comprendre comment les différents types de conditions météorologiques influent sur les schémas d'accidents et d'identifier les périodes ou les zones à risque accru en fonction des prévisions météorologiques. Cette information pourrait être utilisée pour informer les conducteurs, les autorités locales et les services de secours, leur permettant de prendre des mesures préventives et d'ajuster leurs pratiques de conduite en conséquence. En fin de compte, l'intégration de données météorologiques dans notre étude renforcerait notre capacité à améliorer la sécurité routière et à réduire le nombre d'accidents à Rennes.</p>
                   """, styles= {"font-size": "16px", "font-family": "Times New Roman"})

# Création des panneaux d'onglets
panel1 = TabPanel(child=column(plot_image_RM,titre, div_panel1_1, sous_titre1_1,
                                plot_image, div_panel1_2,
                                sous_titre1_2, div_panel1_3,
                                table1,  div_panel1_4,table2, div_panel1_5), title="Etude de l'art et traitement des données")
panel2 = TabPanel(child=column(sous_titre2_1, div_panel2_1,
                                picker1,select_provider,
                                plot_rennes,sous_titre2_2,
                                picker2, picker3,plt_iris_periph_center,
                                div_panel2_2, sous_titre2_3, picker4,
                                plt_iris_all,div_panel2_3 ), title= "Cartographie")

panel3 = TabPanel(child=column(sous_titre3_1,div_panel3_1,
                               plot_etat_imp, sous_titre3_2,
                               div_panel3_2, menu_dropdown,plot_imp, 
                               sous_titre3_3,div_panel3_3,select_inter, plot_ac_inter  ), title="Visualisation de données")
panel4 = TabPanel(child=column(sous_titre4_1, div_panel4_1,plot_image_mto,  div_panel4_2), title="Ouverture")

# Création des onglets avec la position des onglets à gauche
tabs = Tabs(tabs=[panel1, panel2, panel3, panel4], tabs_location="left", background="#E0E2E8")

show(tabs)


# Sortie vers un fichier HTML
output_file("projet_visualisation.html")