
import arcpy
import datetime
import pathlib


# Das jetzt kein Tool mehr sondern ein Script?!
arcpy.CheckOutExtension("network")

# Ergebnisse können überschrieben werden!
arcpy.env.overwriteOutput = True

pfad = pathlib.Path("C:/Users/User/OneDrive/Uni/Geoinformatik/3. Semester/Advanced Landmarks/Data_neu")
output = pathlib.Path("C:/Users/User/OneDrive/Uni/Geoinformatik/3. Semester/Advanced Landmarks/Data_neu/Output")

intersections = str(pfad) + "\\" + "Intersections.shp"
edges = str(pfad) + "\\" + "Edges_Routing.shp"

outputpfad = str(output) + "\\"


# Name der gdb
gdb_name = "Landmarks.gdb"

# Name Feature Dataset
featureDatasetName = "fds_routing"
# Feature Dataset Pfad
fgdb_path = outputpfad + gdb_name

# Name des Layers im Feature Dataset in welchem die Routin Ergebnisse sind.
layer_name = "Routing"

travel_mode = ""  # TODO Travel Mode!


def createNessaryFiles():
    """
    Funktion welche Nicht für jeden Run ausgeführt werden muss;
    sondern nur beim ersten Mal oder wenn die GDB gelöscht wurde.
    """
    # Create a spatial reference object
    sr = arcpy.SpatialReference(31468)

    # Create a FileGDB for the fds
    arcpy.CreateFileGDB_management(str(output), gdb_name)

    # Execute CreateFeaturedataset
    arcpy.CreateFeatureDataset_management(fgdb_path, featureDatasetName, sr)

    # Add Layer to FeatureDatasSet
    arcpy.management.CopyFeatures(
        intersections, fgdb_path + "//" + featureDatasetName + "\\" + "Intersections"
    )
    # Add Layer to FeatureDatasSet
    arcpy.management.CopyFeatures(
        edges, fgdb_path + "//" + featureDatasetName + "\\" + "edges"
    )

    # Create Network Dataset
    arcpy.na.CreateNetworkDataset(
        fgdb_path + "//" + featureDatasetName, "routing_ND", ["edges", "Intersections"]
    )
    
    # Build Network Dataset
    arcpy.na.BuildNetwork(fgdb_path + "//" + featureDatasetName + "//" + "routing_ND")


def do_the_analysis(liste):
    """
    Die Parameter sind nur dafür da, dass ich multiprocessing ausprobieren kann =)
    Das die Funktion wo eigentlich die ganze Magic passiert.
    """
    s, l = liste

    # Create RouteAnalyis Layer
    RoutingLayer = arcpy.na.MakeRouteAnalysisLayer(
        fgdb_path + "//" + featureDatasetName + "//" + "routing_ND",
        layer_name,
        # travel_mode, # TODO
        # accumulate_attributes=["Landmarken", "Distanz"],
    )

    # Hier den IntersectionsLayer Vorladen weil schneller...
    arcpy.MakeFeatureLayer_management(intersections, "intersections_Temp")

    # Layer Object ist unser Routing Layer
    layer_object = RoutingLayer.getOutput(0)

    sublayer_names = arcpy.na.GetNAClassNames(layer_object)

    # Printed alle sublayers...
    # print([x for x in sublayer_names])

    stops_layer_name = sublayer_names["Stops"]


    # s und l kann auch einfach wieder durch 79 ersetzt werden.
    for start in range(s, l):
        for ziel in range(79):

            if start == ziel:
                print(f"Skipped Run: Start = {start}, Ziel = {ziel};")
                continue

            start_time = datetime.datetime.now()
            # print(f"Current Run: Start = {start}, Ziel = {ziel};")

            add_Locations_which_represent_Start_Stop(
                layer_object, stops_layer_name, start, ziel
            )

            # Funktion welche das Routing macht.
            arcpy.na.Solve(layer_object)

            # Diese Sublayer Object besteht aus mehrerne Layern.
            # Wir wählen hier den richtigen für uns aus.
            routes_layer_name = sublayer_names["Routes"]
            routes_sublayer = layer_object.listLayers(routes_layer_name)[0]

            routes_sublayer = add_additional_fields_to_layer(
                routes_sublayer, start, ziel
            )

            # ! Pfad ist hier hardcoded !
            save_route_to_shape(routes_sublayer, start, ziel)

            stop_time = datetime.datetime.now()

            print(
                f"Start = {start}, Ziel = {ziel}; Gestarted um {start_time}; Beendet um {stop_time}; Dauer {(stop_time-start_time).total_seconds()} Sekunden."
            )


def add_Locations_which_represent_Start_Stop(
    layer_object, stops_layer_name, start, ziel
):
    """
    Hier werden der Start und das Ziel des Routings Selektiert.
    Es wirde nix zurückgegeben weil hier immer Object direkt mutiert werden.
    Glaub ich....
    """
    startIntersection = '"ID"' + "=" + str(start)
    stopIntersection = '"ID"' + "=" + str(ziel)

    # Auswaehlen des Startes mit where Clausel
    stops = arcpy.SelectLayerByAttribute_management(
        "intersections_Temp", "NEW_SELECTION", startIntersection
    )

    # Das Clear hier ist wichtig damit die alten Werte (aus vorherigen Loops) wieder rausgehen.
    arcpy.na.AddLocations(layer_object, stops_layer_name, stops, append="CLEAR")

    # Auswaehlen des Stops mit where Clausel
    stops = arcpy.SelectLayerByAttribute_management(
        "intersections_Temp", "NEW_SELECTION", stopIntersection
    )
    # Ziel hinzufügen
    arcpy.na.AddLocations(layer_object, stops_layer_name, stops)


def add_additional_fields_to_layer(routes_sublayer, start, ziel):
    """
    Hier werden die Zusätzlichen Felder erzeugt und gefüllt.
    """
    arcpy.AddField_management(routes_sublayer, "Start", "SHORT")
    arcpy.AddField_management(routes_sublayer, "Ziel", "SHORT")
    arcpy.AddField_management(routes_sublayer, "TravelMode", "TEXT")

    cursor = arcpy.UpdateCursor(routes_sublayer)

    for row in cursor:
        row.setValue("Start", start)
        row.setValue("TravelMode", travel_mode)
        row.setValue("Ziel", ziel)
        cursor.updateRow(row)

    # Cursor wieder schliessen. Geht so auch is dann halt aber kacke...
    del cursor

    return routes_sublayer


def save_route_to_shape(routes_sublayer, start, ziel):
    """
    File als Shapedatei an Spezifizierte Stelle schreiben.
    """

    # Das der Pfad der jeweils generierten Shapes.
    output = (
        outputpfad
        + "Shape_Sammlung\\Route-"
        + str(start)
        + "_zu_"
        + str(ziel)
        + "-"
        + travel_mode
        + ".shp"
    )

    arcpy.management.CopyFeatures(routes_sublayer, output)


def do_the_analysis_with_try_block(liste):
    try:
        do_the_analysis(liste)
    except Exception as E:
        print(E)


def do_the_analysis_in_parralel():
    from multiprocessing import Pool

    ranges = [
        [0, 10],
        [10, 20],
        [20, 30],
        [30, 40],
        [40, 50],
        [50, 60],
        [60, 70],
        [70, 79],
    ]
    pool = Pool(processes=len(ranges))
    pool.map(do_the_analysis_with_try_block, ranges)


if __name__ == "__main__":
    """
    Hinweise:
        - Noch nie ganz durchgelaufen
        - Gibt noch keine Travel Modes
        - Ordner Shapes_Sammlung muss händisch angelegt werden.
    """

    """    
    Das hier muss nur beim ersten Mal ausgeführt werden,
    Oder wenn die gdb gelöscht oder geändert wurde.
    """
    #  createNessaryFiles()

    """    
    Das hier macht die Analyse 1 nach dem anderen
    """
    do_the_analysis([0, 79])

    """
    Das hier macht die Ausführung in Parallel
    """
    # do_the_analysis_in_parralel()
