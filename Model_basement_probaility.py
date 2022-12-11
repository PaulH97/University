# coding=utf-8
# Berechnungsmodell Unterkellerungswahrscheinlichkeit
# Autor Paul Höhn

# Importieren von ArcPy und os

import arcpy
import os

# Es kann optional eine Maske verwendet werden --> if true dann clippen ansonsten wird die AUßengrenze der anderen Input-Daten verwendet
# Es fehlt noch die Angabe der Wahrscheinlichkeit als Zahl
# generell müssen fehler abgefangen werden
# angabe der keepers durch den Benutzer, also welche felder die wichtigen Informationen enthalten

# inputs
workspaceFolder = arcpy.GetParameterAsText(0)
Maske = arcpy.GetParameterAsText(1)
DGM = arcpy.GetParameterAsText(2)
fullhaus = arcpy.GetParameterAsText(3)
BK50 = arcpy.GetParameterAsText(4)
GebNutzungTabelle = arcpy.GetParameterAsText(5)
Hochwassergebiet = arcpy.GetParameterAsText(6)
Wahrscheinlichkeit = arcpy.GetParameterAsText(7)

arcpy.AddMessage("Inputs ready")

# Environments
# Test mit Maske im Namen, muss auch nicht gemacht werden, waere nur fancy
arcpy.CreateFileGDB_management(workspaceFolder, "Kellerwahrscheinlichkeit.gdb")
arcpy.env.overwriteOutput = True
arcpy.env.workspace = workspaceFolder
Geodatenbank = workspaceFolder + os.sep + "Kellerwahrscheinlichkeit.gdb"

print 'environments ready'


# check License


class LicenseError(Exception):
    pass


try:
    if arcpy.CheckExtension("3D") == "Available":
        arcpy.CheckOutExtension("3D")
    else:
        raise LicenseError

except LicenseError:
    print("3D Analyst license is unavailable")

try:
    if arcpy.CheckExtension("Spatial") == "Available":
        arcpy.CheckOutExtension("Spatial")
    else:
        raise LicenseError

except LicenseError:
    print("Spatial Analyst license is unavailable")

print 'License available'

print 'PHASE 1 started'
# ---PHASE1------PHASE1------PHASE1------PHASE1------PHASE1------PHASE1------PHASE1------PHASE1------PHASE1------PHASE1------PHASE1------PHASE1------PHASE1------PHASE1---
# Zurechtschneiden der Inputdaten auf Maske
# fullhaus Daten und DGM
# kann im Falle ohne Masken Input weggelassen werden (Feinschliff)
# koennte kompliziert werden, da der rechteckausschnit automatisch ins Tool Clip Management übernommen werden muss
# es muss eventuell automatisiert die jeweilige Koordinate X1 X2 Y1 Y2 aus der Maske extrahiert werden -> Lösung gefunden


fullhaus_AOI = Geodatenbank + os.sep + "fullhaus_AOI"
DGM_AOI = Geodatenbank + os.sep + "DGM_AOI"
BK50_AOI = Geodatenbank + os.sep + "BK50_AOI"
Hochwassergebiet_AOI = Geodatenbank + os.sep + "Hochwassergebiet_AOI"

descMaske = arcpy.Describe(Maske)
extent = descMaske.extent

arcpy.Clip_analysis(fullhaus, Maske, fullhaus_AOI, "")
arcpy.Clip_management(DGM, str(extent), DGM_AOI)
arcpy.Clip_analysis(BK50, Maske, BK50_AOI, "")
arcpy.Clip_analysis(Hochwassergebiet, Maske, Hochwassergebiet_AOI, "")

print 'Clip finished'

print 'PHASE 1 finished'
print 'PHASE 2 started'
# ---PHASE2------PHASE2------PHASE2------PHASE2------PHASE2------PHASE2------PHASE2------PHASE2------PHASE2------PHASE2------PHASE2------PHASE2------PHASE2------PHASE2------PHASE2---

# +++++++++++++++++++++++++++++++++++++++++++ PARAMETER 1 +++++++++++++++++++++++++++++++++++++++++++++

# Berechnung der Hangneigung in Prozent

DGM_AOI_Slope = Geodatenbank + os.sep + "DGM_AOI_Slope"
arcpy.gp.Slope_sa(DGM_AOI, DGM_AOI_Slope, "PERCENT_RISE", "1", "GEODESIC", "METER")

print 'Slope finished'

# Übertragung der Hangneigung auf Gebäude
# Mittelwert der Hangneigung wird verwendet

Slope_building_mean = Geodatenbank + os.sep + "Slope_building_mean"
arcpy.gp.ZonalStatistics_sa(fullhaus_AOI, "OBJECTID", DGM_AOI_Slope, Slope_building_mean, "MEAN", "DATA")

print 'Zonal Statistics Slope finished'

# Reklassifizierung der Hangneigungswerte der Gebäude
# Einteilung in drei Klassen
# Für uns relevant sind alle Gebäude mit einem mittleren Hangneigungswert größer als 6%
# hier muss ich auch noch einen Weg finden, die Klassen auf 3 zu setzen und die Grenzen bei 6 und 15 liegen

Slope_building_mean_reclass = Geodatenbank + os.sep + "Slope_building_mean_reclass"
arcpy.gp.Reclassify_sa(Slope_building_mean, "VALUE", "0.333258 6 1;6 15 2;15 140.251144 3", Slope_building_mean_reclass, "DATA")

print 'Reclassify finished'

# Raster to Polygon
# Vorbereitung auf Join mit fullhaus Daten

Geb_Hang = Geodatenbank + os.sep + "Geb_Hang"
arcpy.RasterToPolygon_conversion(Slope_building_mean_reclass, Geb_Hang, "NO_SIMPLIFY", "Value", "SINGLE_OUTER_PART", "")

# Durchführung des Zusammenführen der Hangneigungsdaten an Gebäudetabelle (räumliche Verbindung)
# Methode = Intersect

fieldmappings = arcpy.FieldMappings()
fieldmappings.addTable(fullhaus_AOI)
fieldmappings.addTable(Geb_Hang)

keepers = ["gebid", "stockwerk", "gebaeudety", "nutzmix", "gridcode"]

for field in fieldmappings.fields:  # loop through each field
    # cant overwrite these Fieldtypes, so go to the next field
    if field.name == "FID" or field.name == "Shape":
        continue
    elif field.name not in keepers:
        fieldmappings.removeFieldMap(fieldmappings.findFieldMapIndex(field.name))

targetFeature = arcpy.MakeFeatureLayer_management(fullhaus_AOI, "fullhaus_AOI_lyr")
joinFeature = arcpy.MakeFeatureLayer_management(Geb_Hang, "Geb_Hang_lyr")

Geb_Hang_fullhaus = Geodatenbank + os.sep + "Geb_Hang_fullhaus"
arcpy.SpatialJoin_analysis(targetFeature, joinFeature, Geb_Hang_fullhaus, "JOIN_ONE_TO_ONE", "KEEP_ALL", fieldmappings, "INTERSECT", "", "")

arcpy.AlterField_management(Geb_Hang_fullhaus, "gridcode", "Slope_Klassen")

# Replace a layer/table view name with a path to a dataset (which can be a layer file) or create the layer/table view within the script
# The following inputs are layers or table views: "fullhausAOI", "Geb_Hang"

print 'Parameter 1 finished '

# +++++++++++++++++++++++++++++++++++++++++++ PARAMETER 2 und 3 +++++++++++++++++++++++++++++++++++++++++++++

# Zusammenführen der fullhaus Daten (mit Hangneigung) und den BK50 Daten (Bodeneigenschaften)
# Methode = Intersect
# Staunässe und Grundwasser; allgmein alle Bodendaten


fieldmappings = arcpy.FieldMappings()
fieldmappings.addTable(Geb_Hang_fullhaus)
fieldmappings.addTable(BK50_AOI)

keepers = ["gebid", "stockwerk", "gebaeudety", "nutzmix", "Slope_Klassen", "gbk_1m", "gbk_2m", "gbknass", "gbkstau", "GW", "SW"]

for field in fieldmappings.fields:  # loop through each field
    # cant overwrite these Fieldtypes, so go to the next field
    if field.name == "FID" or field.name == "Shape":
        continue
    elif field.name not in keepers:
        fieldmappings.removeFieldMap(fieldmappings.findFieldMapIndex(field.name))

targetFeature = arcpy.MakeFeatureLayer_management(Geb_Hang_fullhaus, "Geb_Hang_fullhaus_lyr")
joinFeature = arcpy.MakeFeatureLayer_management(BK50_AOI, "BK50_AOI_lyr")

Geb_Hang_fullhaus_bk50 = Geodatenbank + os.sep + "Geb_Hang_fullhaus_bk50"
arcpy.SpatialJoin_analysis(targetFeature, joinFeature, Geb_Hang_fullhaus_bk50, "JOIN_ONE_TO_ONE", "KEEP_ALL", fieldmappings, "INTERSECT", "", "")

print 'Parameter 2 & 3 finished'

# +++++++++++++++++++++++++++++++++++++++++++ PARAMETER 4 +++++++++++++++++++++++++++++++++++++++++++++
# Erstellen des 4. Parameter
# Reliefanalyse um Gebaeude

# Buffer 2 Meter
fullhaus_AOI_buf2m = Geodatenbank + os.sep + "fullhaus_AOI_buf2m"
arcpy.Buffer_analysis(fullhaus_AOI, fullhaus_AOI_buf2m, "2 Meters", "FULL", "ROUND", "NONE", "", "PLANAR")

# Min und Max Hoehenwerte pro Gebaeude ermitteln
GebBuf_maxHoehe = Geodatenbank + os.sep + "Geb_maxHoehe"
GebBuf_minHoehe = Geodatenbank + os.sep + "Geb_minHoehe"

arcpy.gp.ZonalStatistics_sa(fullhaus_AOI_buf2m, "OBJECTID", DGM_AOI, GebBuf_maxHoehe, "MAXIMUM", "DATA")
arcpy.gp.ZonalStatistics_sa(fullhaus_AOI_buf2m, "OBJECTID", DGM_AOI, GebBuf_minHoehe, "MINIMUM", "DATA")

# Klassifikation aller Gebäude, die ein extremen Hoehenunterschied aufweisen (hier: max - min > 2m, dann wird Gebäude ausgewählt)
Geb_DiffDGM = Geodatenbank + os.sep + "Geb_mithoherDiffDGM"
arcpy.gp.RasterCalculator_sa('Con(("' + GebBuf_maxHoehe + '" - "' + GebBuf_minHoehe + '") > 2,1,0)', Geb_DiffDGM)

# Vorbereitung und Zusammenführen der DGM Daten mit den fullhaus Daten
Geb_DiffDGM_shape = Geodatenbank + os.sep + "Geb_DiffDGM_shape"
arcpy.RasterToPolygon_conversion(Geb_DiffDGM, Geb_DiffDGM_shape, "NO_SIMPLIFY", "Value", "SINGLE_OUTER_PART", "")

fieldmappings = arcpy.FieldMappings()
fieldmappings.addTable(Geb_Hang_fullhaus_bk50)
fieldmappings.addTable(Geb_DiffDGM_shape)

keepers = ["gebid", "stockwerk", "gebaeudety", "nutzmix", "Slope_Klassen", "gbk_1m", "gbk_2m", "gbknass", "gbkstau", "GW", "SW", "gridcode"]

for field in fieldmappings.fields:  # loop through each field
    # cant overwrite these Fieldtypes, so go to the next field
    if field.name == "FID" or field.name == "Shape":
        continue
    elif field.name not in keepers:
        fieldmappings.removeFieldMap(fieldmappings.findFieldMapIndex(field.name))

targetFeature = arcpy.MakeFeatureLayer_management(Geb_Hang_fullhaus_bk50, "Geb_Hang_fullhaus_bk50_lyr")
joinFeature = arcpy.MakeFeatureLayer_management(Geb_DiffDGM_shape, "Geb_DiffDGM_shape_lyr")

Geb_Hang_fullhaus_bk50_diffDGM = Geodatenbank + os.sep + "Geb_Hang_fullhaus_bk50_diffDGM"
arcpy.SpatialJoin_analysis(targetFeature, joinFeature, Geb_Hang_fullhaus_bk50_diffDGM, "JOIN_ONE_TO_ONE", "KEEP_ALL", fieldmappings, "INTERSECT", "", "")

arcpy.AlterField_management(Geb_Hang_fullhaus_bk50_diffDGM, "gridcode", "DiffDGM")

print 'Parameter 4 finished'

# +++++++++++++++++++++++++++++++++++++++++++ PARAMETER 5 +++++++++++++++++++++++++++++++++++++++++++++
# Hochwassergebiete an vorhanden Datensatz joinen


fieldmappings = arcpy.FieldMappings()
fieldmappings.addTable(Geb_Hang_fullhaus_bk50_diffDGM)
fieldmappings.addTable(Hochwassergebiet_AOI)

keepers = ["gebid", "stockwerk", "gebaeudety", "nutzmix", "Slope_Klassen", "gbk_1m", "gbk_2m", "gbknass", "gbkstau", "GW", "SW", "DiffDGM", "GEWKZ", "NAME"]

for field in fieldmappings.fields:  # loop through each field
    # cant overwrite these Fieldtypes, so go to the next field
    if field.name == "FID" or field.name == "Shape":
        continue
    elif field.name not in keepers:
        fieldmappings.removeFieldMap(fieldmappings.findFieldMapIndex(field.name))

targetFeature = arcpy.MakeFeatureLayer_management(Geb_Hang_fullhaus_bk50_diffDGM, "Geb_Hang_fullhaus_bk50_diffDGM_lyr")
joinFeature = arcpy.MakeFeatureLayer_management(Hochwassergebiet_AOI, "Hochwassergebiet_AOI_lyr")

Geb_Hang_fullhaus_bk50_diffDGM_ug = Geodatenbank + os.sep + "Geb_Hang_fullhaus_bk50_diffDGM_ug"
arcpy.SpatialJoin_analysis(targetFeature, joinFeature, Geb_Hang_fullhaus_bk50_diffDGM_ug, "JOIN_ONE_TO_ONE", "KEEP_ALL", fieldmappings, "INTERSECT", "", "")

print 'Parameter 5 finished'

# +++++++++++++++++++++++++++++++++++++++++++ PARAMETER 6 +++++++++++++++++++++++++++++++++++++++++++++
# Input Tabelle Gebaudenutzung in Geodatenbank uebertragen

inTable = GebNutzungTabelle
outLocation = Geodatenbank
outTable = "GebNutzung"

GebNutzungTabelle_inGDB = arcpy.TableToTable_conversion(inTable, outLocation, outTable)

# arcpy.env.workspace = Geodatenbank
# join_table = arcpy.ListTables()
LayerName = "Geb_Hang_fullhaus_bk50_diffDGM_ug_lyr"
in_field = "nutzmix"
join_field = "code"

arcpy.MakeFeatureLayer_management(Geb_Hang_fullhaus_bk50_diffDGM_ug, LayerName)

arcpy.AddJoin_management(LayerName, in_field, GebNutzungTabelle_inGDB, join_field, "KEEP_ALL")

print 'Parameter 6 finished'

# Zwischenspeichern
# Join dauerhaft in Datensatz schreiben

# fieldmappings = arcpy.FieldMappings()
# fieldmappings.addTable(LayerName)

Geb_Parameter_complete = Geodatenbank + os.sep + "Geb_Parameter_complete"
arcpy.CopyFeatures_management(LayerName, Geb_Parameter_complete)
# arcpy.FeatureClassToFeatureClass_conversion(LayerName, Geodatenbank, "Geb_Parameter_complete", "", fieldmappings)

print 'Copy finished'

fields = arcpy.ListFields(Geb_Parameter_complete)

for field in fields:  # loop through each field
    fname = field.name
    # cant overwrite these Fieldtypes, so go to the next field
    if field.name == "FID" or field.name == "Shape":
        continue
    # replace the beginning part and rename the field name
    if fname.startswith("Geb_Hang_fullhaus_bk50_diffDGM_ug_"):
        new_name = fname.replace("Geb_Hang_fullhaus_bk50_diffDGM_ug_", "Geb_")
        arcpy.AlterField_management(Geb_Parameter_complete, fname, new_name)

print 'PHASE 2 finished'
print 'PHASE 3 started'
# ------PHASE 3------PHASE 3------PHASE 3------PHASE 3------PHASE 3------PHASE 3------PHASE 3------PHASE 3------PHASE 3------PHASE 3------PHASE 3------PHASE 3------PHASE 3

# Felder hinzufügen zur Berechnung der Kellerwahrscheinlichkeit
# Daten aus der Tabelle nochmal selektieren und übersichtlicher darstellen
# Berrechnug der Hangneigung auf Grundlage der Spalte gridcode (drei Klassen)
# eventuell zwischenspeichern mit arcpy.MakeFeatureLayer()

# KellerHangneigung
arcpy.AddField_management(Geb_Parameter_complete, "KellerHangneigung", "FLOAT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
arcpy.CalculateField_management(Geb_Parameter_complete, "KellerHangneigung", "reclass( !Geb_Slope_Klassen!)", "PYTHON_9.3", "def reclass(x):\\n  if x >= 2:\\n    return 1\\n  else:\\n    return 0\\n")

print 'Keller in Hangneigung calculated'

# KellerGrabbarkeit
arcpy.AddField_management(Geb_Parameter_complete, "KellerGrabbarkeit", "FLOAT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
arcpy.CalculateField_management(Geb_Parameter_complete, "KellerGrabbarkeit", "reclass( !Geb_gbk_1m!, !Geb_gbk_2m! )", "PYTHON_9.3", "def reclass(x,y):\\n  if x >= 40 and y >= 40:\\n    return 0\\n  else:\\n    return 1 \\n")

print 'Keller Grabbarkeit calculated'

# KellerGebNutzungsart
arcpy.AddField_management(Geb_Parameter_complete, "KellerNutzungsart", "FLOAT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
arcpy.CalculateField_management(Geb_Parameter_complete, "KellerNutzungsart", "reclass( !GebNutzung_Kellernutzung! )", "PYTHON_9.3", "def reclass(x):\\n  if x == 'ja':\\n    return 1\\n  else:\\n    return 0")

print 'Gebäude Nutzungsform calculated'
# Kartoffel
# KellerReliefDifferenz
arcpy.AddField_management(Geb_Parameter_complete, "KellerReliefanalyse", "FLOAT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
arcpy.CalculateField_management(Geb_Parameter_complete, "KellerReliefanalyse", "[Geb_DiffDGM]", "VB", "")

print 'ReliefDiff calculated'

# Keller in Überflutungsgebiet
arcpy.AddField_management(Geb_Parameter_complete, "KellerUeberflutung", "FLOAT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
arcpy.CalculateField_management(Geb_Parameter_complete, "KellerUeberflutung", "reclass( !Geb_GEWKZ! )", "PYTHON_9.3", "def reclass(x):\\n  if x >= 1:\\n    return 0\\n  else:\\n    return 1")

print 'Keller Überflutungsgebiet calculated'

# Keller Staunässe Einwirkungen
arcpy.AddField_management(Geb_Parameter_complete, "KellerStaunaesse", "FLOAT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
arcpy.CalculateField_management(Geb_Parameter_complete, "KellerStaunaesse", "reclass( !Geb_SW! )", "PYTHON_9.3", "def reclass(x):\\n  if x >= 3:\\n    return 1\\n  else: \\n    return 0")

print 'Keller Staunässe calculated'

# Keller Grundwasser Einwirkungen
arcpy.AddField_management(Geb_Parameter_complete, "KellerGrundwasser", "FLOAT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
arcpy.CalculateField_management(Geb_Parameter_complete, "KellerGrundwasser", "reclass( !Geb_GW! )", "PYTHON_9.3", "def reclass(x):\\n  if x == 1 or x == 2:\\n    return 1\\n  else:\\n    return 0")

print 'Keller Grundwasser calculated'

# Wahrscheinlichkeitswert des Benutzer einsetzten


Ableitungsparameter = ["KellerHangneigung", "KellerGrabbarkeit", "KellerNutzungsart", "KellerReliefanalyse", "KellerUeberflutung", "KellerStaunaesse", "KellerGrundwasser"]

rows = arcpy.UpdateCursor(Geb_Parameter_complete)
Fields = arcpy.ListFields(Geb_Parameter_complete)

for row in rows:
    for field in Fields:
        if field.name in Ableitungsparameter:
            if row.getValue(field.name) == 1:
                row.setValue(field.name, Wahrscheinlichkeit)
    rows.updateRow(row)

print 'Wahrscheinlichkeit angepasst'

# Kellerwahrscheinlichkeit berrechnen
arcpy.AddField_management(Geb_Parameter_complete, "Kellerwahrscheinlichkeit", "FLOAT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
arcpy.CalculateField_management(Geb_Parameter_complete, "Kellerwahrscheinlichkeit", "[KellerNutzungsart] + [KellerHangneigung] + [KellerReliefanalyse] + [KellerStaunaesse] + [KellerGrundwasser] + 0.5 * [KellerGrabbarkeit]", "VB", "")

# Bedingungen auf Kellerwahrscheinlichkeit anwenden
#
rows = arcpy.UpdateCursor(Geb_Parameter_complete)
Fields = arcpy.ListFields(Geb_Parameter_complete)

# Diese Nutzungstypen kann eventuell auch noch der Benutzer auswählen
GebNutz_ohneKeller = ["Garage", u"Überdachung", u"Gebäude zum Parken", "Schuppen", "Gartenhaus", "Funkmast" ]

for row in rows:
    for field in Fields:
        if field.name == "GebNutzung_Beschreibung":
            if row.getValue(field.name) in GebNutz_ohneKeller:
                row.setValue("Kellerwahrscheinlichkeit", 0)
    rows.updateRow(row)

print 'Complete'
