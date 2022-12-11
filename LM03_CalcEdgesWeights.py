#----------------------------------------------------------------------------------------------------------#
# Computation of landmark weights																	   
#	Input: 	Objects_LandmarkPath								   
#			Intersections			   
#			Edges_Routing   
#	Output: Fields Weights, Salience, lm_OSM, Kreuzungen in Edges_Routing
#----------------------------------------------------------------------------------------------------------#

import arcpy
import os

arcpy.env.overwriteOutput = True

pfad = r'C:\Users\Anwender\Downloads\Daten2\Input'
output = r'C:\Users\Anwender\Downloads\Daten2\Output'

# Globale Variablen weils halt einfacher ist.
landmarke = os.path.join(pfad, 'Objects_LandmarkPath.shp')
intersections = os.path.join(pfad, 'Intersections.shp')
weightsedges = os.path.join(pfad,'Edges_Routing.shp')

LM_lyr = "LM_lyr"
inter_lyr = "inter_lyr"
weights_lyr = "weights_lyr"


def load_layers():
    arcpy.MakeFeatureLayer_management(landmarke, LM_lyr)
    arcpy.MakeFeatureLayer_management(intersections, inter_lyr)
    arcpy.MakeFeatureLayer_management(weightsedges, weights_lyr)
    print("Laden der Layer abgeschlossen.")

def prepare_layers():
    # Salienzwerte (SVIS, SEM, STR) für spätere Berechnung von Kantengewicht
    arcpy.AddField_management(landmarke, "Salienz", "FLOAT")
    arcpy.management.CalculateField(landmarke, "Salienz", "!SVIS! + !SSEM! + !SSTR!", '')

    # Hinzufügen von Feld Kantengewicht und val, lm_OSM und Intersection 
    # arcpy.AddField_management(weightsedges, "Weights", "FLOAT")
    # arcpy.AddField_management(weightsedges, "Weights2", "FLOAT")
    # arcpy.AddField_management(weightsedges, "Salienz", "FLOAT")
    # arcpy.AddField_management(weightsedges, "lm_OSM", "TEXT")
    # arcpy.AddField_management(weightsedges, "Kreuzungen", "FLOAT")

    # arcpy.AddField_management(weightsedges, "buildFac", "FLOAT")
    # arcpy.AddField_management(weightsedges, "buildWeigh", "FLOAT")
    # arcpy.AddField_management(weightsedges, "Weights3", "FLOAT")
    print("Vorberreiten der Layer abgeschlossen.")



def handle_multiple_matches(output, LM_lyr, Selection):
    print("Mehrere Landmarken!")
    
    # Maximale Salienz der selektierten Kreuzungen bestimmen
    if arcpy.Exists(str(output) + '\\' + 'salvalues.dbf'):
        arcpy.Delete_management(str(output) + '\\' + 'salvalues.dbf')
    outtableSUM = str(output) + '\\' + 'salvalues.dbf'
    arcpy.Statistics_analysis(LM_lyr, outtableSUM, [["Salienz", "MAX"]])
        
    MaxSal = 0
    with arcpy.da.SearchCursor(outtableSUM, "MAX_Salien") as cursor_MaxSal:
        for row in cursor_MaxSal:
            MaxSal = row[0]
            print("Maximale Salienz: " + str(MaxSal))
                
    # Kreuzung mit maximaler Salienz aus den bereits selektierten Kreuzungen selektieren 
    arcpy.SelectLayerByAttribute_management(Selection, 'SUBSET_SELECTION', '"Salienz" =' + str(MaxSal))
    matchcount = int(arcpy.GetCount_management(Selection)[0])
    
    # falls mehr als eine mit maximaler Salienz
    if matchcount > 1:
        # Minimale Distanz der selektierten Kreuzungen bestimmen
        if arcpy.Exists(str(output) + '\\' + 'distvalues.dbf'):
            arcpy.Delete_management(str(output) + '\\' + 'distvalues.dbf')
        outtableSUM = str(output) + '\\' + 'distvalues.dbf'
        arcpy.Statistics_analysis(LM_lyr, outtableSUM, [["Distance", "MIN"]])
    
        minDist = 0
        with arcpy.da.SearchCursor(outtableSUM, "MIN_DISTAN") as cursor_MinDist:
            for row in cursor_MinDist:
                minDist = row[0]
                print("Minimale Distanz: " + str(minDist))
                    
        # Kreuzung mit minimalster Distanz aus den bereits selektierten Kreuzungen selektieren
        arcpy.SelectLayerByAttribute_management(Selection, 'SUBSET_SELECTION', '"DISTANCE" =' + str(minDist))

    rows = arcpy.SearchCursor(LM_lyr)
    for row in rows:
        val1 = row.getValue("Salienz")
        lmOSM = row.getValue("OSM_ID")
        print("Landmarke " + str(lmOSM) + " hat Salienz: " + str(val1))
    
    return val1, lmOSM

def loop_over_Intersections(IntersectionRow):
    actIntersection = IntersectionRow.getValue("ID")
    XIntersection = IntersectionRow.getValue("X")
    YIntersection = IntersectionRow.getValue("Y")

    print("Kreuzung:" + str(actIntersection))

    # alle Objekte an aktueller Kreuzung selektieren
    Selection = arcpy.SelectLayerByAttribute_management(LM_lyr, "NEW_SELECTION", "KREUZUNGEN = " + str(actIntersection))
    
    # alle Landmarken aus Selection herausfiltern
    arcpy.SelectLayerByAttribute_management(Selection, 'SUBSET_SELECTION', '"CdTm_LM" = 1')
    # Matchcount ist die Anzahl der Landmarken an der aktuell gewählten Kreuzung.
    matchcount = int(arcpy.GetCount_management(Selection)[0])
        
    if matchcount == 0:
        val1 = -1000
        lmOSM = -999
        print("Keine Landmarke!")
        
    
    elif matchcount == 1:
        rows = arcpy.SearchCursor(LM_lyr)

        for row in rows:
            val1 = row.getValue("Salienz")
            lmOSM = row.getValue("osm_id_neu")
            print("Gefunden wurde Landmarke " + str(lmOSM) + " mit Salienz: " + str(val1))

    else:
        # Das einfach eine Hilfsfunktion für den Überblick
        # Zürück Kommen die Salienz sowie die ID der Landmarke.
        val1, lmOSM = handle_multiple_matches(output, LM_lyr, Selection)

    
    Selection = arcpy.SelectLayerByAttribute_management(weights_lyr, "NEW_SELECTION", "KREUZUNGEN = " + str(actIntersection))

    # Speicherung des Wertes val (= Salienz der gewählten Landmarke für aktuelle intersection)
    # Hier wird die Salienz e.g Weight_2 mit der Länge berechnet.
    with arcpy.da.UpdateCursor(Selection, ['Salienz', 'lm_OSM']) as cursor:
        for row in cursor:
            row[0] = val1
            row[1] = lmOSM
            cursor.updateRow(row)


def calculate_weights():

    # Berechnen der einfachen Salienz
    arcpy.management.CalculateField(weightsedges, "SalWeights", "300 - !Salienz!", 'PYTHON3','','FLOAT')

    # Berechnung der Gewichtung mit Kategoriserten Gewichten.
    func = """
def KategorisertenWeights(salienz, length,  niceB, shops, gastro, uglyB):
        if length <= 75:
            lf = 50
        elif (length <= 100 and length > 75): 
            lf = 25
        elif (length <= 150 and length > 100): 
            lf = 0
        else: 
            lf = -100
                
        # Das sind die Faktoren mit denen die Gewichtung bestimmt wird.
        shop_factor = 2
        gastro_factor = 3
        niceBuildings_factor = 1
        uglyBuildings_factor = 2

        newBuildingsWeight = (
            niceB * niceBuildings_factor +
            shops * shop_factor +
            gastro * gastro_factor -
            uglyB * uglyBuildings_factor)
                    
        if newBuildingsWeight <= 0:
            res = 0
        elif newBuildingsWeight <= 12:
            res = 25
        elif newBuildingsWeight > 12:
            res = 50

        return 400 - salienz - res - lf"""

    arcpy.DeleteField_management(weightsedges, "KatoWeight")

    arcpy.management.CalculateField(
        weightsedges,
        "KatoWeight", 
        "KategorisertenWeights(float(!Salienz!),float(!Length!),float(!Others_1!),float(!Shop!),float(!Gastronomy!),float(!Others_0!))",
        'PYTHON3',
        func,
        'FLOAT')


    func="""
def multipliedWeight(salienz, length,  niceB, shops, gastro, uglyB):
        # Das sind die Faktoren mit denen die Gewichtung bestimmt wird.
        shop_factor = 2
        gastro_factor = 3
        niceBuildings_factor = 1
        uglyBuildings_factor = 2
        

        newBuildingsWeight = (
            niceB * niceBuildings_factor +
            shops * shop_factor +
            gastro * gastro_factor -
            uglyB * uglyBuildings_factor)

        if newBuildingsWeight < 0:
            newBuildingsWeight = 0
        
        res = (salienz * 2 + newBuildingsWeight * 10) - (length * 2.5)

        return res"""

    arcpy.DeleteField_management(weightsedges, "MultWeight")

    arcpy.management.CalculateField(
        weightsedges,
        "MultWeight", 
        "multipliedWeight(float(!Salienz!),float(!Length!),float(!Others_1!),float(!Shop!),float(!Gastronomy!),float(!Others_0!))",
        'PYTHON3',
        func,
        'FLOAT')
        
    maxwert = 0

    with arcpy.da.SearchCursor(weightsedges, ['MultWeight']) as cursor:
        for row in cursor:
            value = row[0]
            if value > maxwert:
                maxwert = value

    func=f"""
def newweight(value):
        maxwert = {maxwert}

        return maxwert + 1 - value
        """

    arcpy.DeleteField_management(weightsedges, "MultWei2")

    arcpy.management.CalculateField(
        weightsedges,
        "MultWei2", 
        "newweight(!MultWeight!)",
        'PYTHON3',
        func,
        'FLOAT')

    


if __name__ == '__main__':
    load_layers()

    prepare_layers()

    for row in arcpy.SearchCursor(inter_lyr):
        loop_over_Intersections(row)

    calculate_weights()

    print("Fertig!")