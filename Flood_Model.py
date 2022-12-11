
# Import arcpy module
import arcpy
import os

# inputs
workspaceFolder = arcpy.GetParameterAsText(0)
StrassenNRW = arcpy.GetParameterAsText(1)
WassertiefeRaster = arcpy.GetParameterAsText(2)
Beregnungsraster = arcpy.GetParameterAsText(3)
Fliessgeschwindigkeit = arcpy.GetParameterAsText(4)
Maske = arcpy.GetParameterAsText(5)

print('inputs ready')

# Environments
#arcpy.CreateFileGDB_management(workspaceFolder, "BewertungUeberflutungStrassenNRW.gdb")

arcpy.env.overwriteOutput = True
arcpy.env.workspace = workspaceFolder
Geodatenbank = workspaceFolder + os.sep + "BewertungUeberflutungStrassenNRW.gdb"
arcpy.env.overwriteOutput = True

print('environments ready')

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

print('License available')

#Auf Maske clippen

StrassenNRW_clip = Geodatenbank + os.sep + "StrassenNRW_clip"
arcpy.Clip_analysis(StrassenNRW, Maske, StrassenNRW_clip)


# Spalten fuer die Strassenbreite erstellen und die Strassenbreiten mit externen Daten berechnen
# Strassen auf zwei verscheidene Breiten buffern


arcpy.AddField_management(StrassenNRW_clip, "Buffer", "FLOAT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
arcpy.AddField_management(StrassenNRW_clip, "BuffKlein", "FLOAT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
arcpy.CalculateField_management(StrassenNRW_clip, "Buffer", "buffer( !STRKL! , !ABSAST! )", "PYTHON_9.3", "def buffer(x,y):\\n  if x == \"A\" and y ==\"Ast\":\\n    return 2\\n  elif x == \"A\" and y ==\"Abschnitt\":\\n    return 13\\n  elif x ==\"B\" and y ==\"Ast\":\\n    return 2\\n  elif x ==\"B\" and y ==\"Abschnitt\":\\n    return 5")
arcpy.CalculateField_management(StrassenNRW_clip, "BuffKlein", "[Buffer] - 0.05", "VB", "")

StrassenBreite = Geodatenbank + os.sep + "StrassenBreite"
StrassenBreite100 = Geodatenbank + os.sep + "StrassenBuffer100"

arcpy.Buffer_analysis(StrassenNRW_clip, StrassenBreite, "Buffer", "FULL", "ROUND", "ALL", "", "PLANAR")
arcpy.Buffer_analysis(StrassenNRW_clip, StrassenBreite100, "100 Meters", "FULL", "ROUND", "ALL", "", "PLANAR")


print('Strassen Buffer finished')


# Strassen Buffer 100m in Rasterformat
# Ueberflutungstiefe reklassifizieren
# Raster der Ueberflutungsflaechen berechnen


StrassenBuffer100Raster = Geodatenbank + os.sep + "StrassenBuffer100Raster"
UeberflutungsflaechenRaster = Geodatenbank + os.sep + "UeberflutungsflaechenRaster"
UF_StrassenRaster = Geodatenbank + os.sep + "UF_StrassenRaster"

arcpy.PolygonToRaster_conversion(StrassenBreite100, "OBJECTID", StrassenBuffer100Raster, "CELL_CENTER", "NONE", "5")
arcpy.gp.Reclassify_sa(WassertiefeRaster, "VALUE", "0,001000 0,030000 NODATA;0,030000 0,100000 2;0,100000 0,500000 2;0,500000 1 2;1 5 2", UeberflutungsflaechenRaster, "DATA")
arcpy.gp.RasterCalculator_sa('Con(IsNull("' + StrassenBuffer100Raster + '"), 0,"' + UeberflutungsflaechenRaster + '")', UF_StrassenRaster)

print('UF finished')

# Herausfiltern der nicht/wenig ueberfluteten Bereiche
# Gruppieren der Flaechen in Regionen
# Selektieren, diesmal die zu kleinen Flaechen
# Raster in Polygon (FC) umwandeln

UF_StrassenRasterSingle = Geodatenbank + os.sep + "UF_StrassenRasterSingle"
UF_Regionen = Geodatenbank + os.sep + "UF_Regionen"
UF_RegionenSelect = Geodatenbank + os.sep + "UF_RegionenSelect"
UF_RegionenFeatureClass = Geodatenbank + os.sep + "UF_RegionenFeatureClass"

arcpy.gp.ExtractByAttributes_sa(UF_StrassenRaster, "\"Value\" = 2", UF_StrassenRasterSingle)
arcpy.gp.RegionGroup_sa(UF_StrassenRasterSingle, UF_Regionen, "EIGHT", "WITHIN", "NO_LINK", "")
arcpy.gp.RasterCalculator_sa('SetNull(Lookup("' + UF_Regionen + '","Count") <= 2,"' + UF_Regionen + '")', UF_RegionenSelect)
arcpy.RasterToPolygon_conversion(UF_RegionenSelect, UF_RegionenFeatureClass, "NO_SIMPLIFY")

print('Regionen finished')

# Klasse 1
# Feld hinzufuegen, was angibt ob die Region die Strasse beruehrt
# Selektieren von den Regionen die auf der Strasse liegen
# Feld fuer Klasse 1 berechnen und alle Regionen, die an der Strasse liegen (diese Beruehren), hinzufuegen
# Feauture Class zwischenspeichern

arcpy.AddField_management(UF_RegionenFeatureClass, "StBeruehrt", "SHORT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
arcpy.MakeFeatureLayer_management(UF_RegionenFeatureClass, "UF_Regionen_lyr")
arcpy.MakeFeatureLayer_management(StrassenBreite,"Strassenbreite_lyr")
arcpy.SelectLayerByLocation_management("UF_Regionen_lyr", "INTERSECT", "StrassenBreite_lyr", "", "NEW_SELECTION", "NOT_INVERT")

print("Count Select By Location: ", arcpy.GetCount_management("UF_Regionen_lyr"))

arcpy.CalculateField_management("UF_Regionen_lyr", "StBeruehrt", "1", "VB", "")
arcpy.SelectLayerByAttribute_management("UF_Regionen_lyr", "CLEAR_SELECTION", "")

UF_RegionenKlasse1 = Geodatenbank + os.sep + "UF_RegionenKlasse1"
arcpy.CopyFeatures_management("UF_Regionen_lyr", UF_RegionenKlasse1)

print('Klasse 1 finished')

# Strassenrandlinien erstellen Rechts + Links
# Erstellte Spalten fuer das Durchbrechen der Strasse werden gefuellt/berechnet
# Regionen der Klasse 1 und 2 sind entstanden

arcpy.AddField_management(UF_RegionenKlasse1, "crossRight", "SHORT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
arcpy.AddField_management(UF_RegionenKlasse1, "crossLeft", "SHORT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
arcpy.AddField_management(UF_RegionenKlasse1, "Strassendurchbrechung", "SHORT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

StrassenBufferLinksGross = Geodatenbank + os.sep + "StrassenBufferLinksGross"
StrassenBufferLinksKlein = Geodatenbank + os.sep + "StrassenBufferLinksKlein"
StrassenrandLinks = Geodatenbank + os.sep + "StrassenrandLinks"

arcpy.Buffer_analysis(StrassenNRW_clip, StrassenBufferLinksGross, "Buffer", "LEFT", "FLAT", "ALL", "", "PLANAR")
arcpy.Buffer_analysis(StrassenNRW_clip, StrassenBufferLinksKlein, "BuffKlein", "LEFT", "FLAT", "ALL", "", "PLANAR")
arcpy.Erase_analysis(StrassenBufferLinksGross, StrassenBufferLinksKlein, StrassenrandLinks, "")

StrassenBufferRechtsGross = Geodatenbank + os.sep + "StrassenBufferRechtsGross"
StrassenBufferRechtsKlein = Geodatenbank + os.sep + "StrassenBufferRechtsKlein"
StrassenrandRechts = Geodatenbank + os.sep + "StrassenrandRechts"

arcpy.Buffer_analysis(StrassenNRW_clip, StrassenBufferRechtsGross, "Buffer", "RIGHT", "FLAT", "ALL", "", "PLANAR")
arcpy.Buffer_analysis(StrassenNRW_clip, StrassenBufferRechtsKlein, "BuffKlein", "RIGHT", "FLAT", "ALL", "", "PLANAR")
arcpy.Erase_analysis(StrassenBufferRechtsGross, StrassenBufferRechtsKlein, StrassenrandRechts, "")

arcpy.MakeFeatureLayer_management(UF_RegionenKlasse1, "UF_RegionenKlasse1_lyr")
arcpy.MakeFeatureLayer_management(StrassenrandLinks, "StrassenrandLinks_lyr")
arcpy.SelectLayerByLocation_management("UF_RegionenKlasse1_lyr", "INTERSECT", "StrassenrandLinks_lyr", "", "NEW_SELECTION", "NOT_INVERT")
arcpy.CalculateField_management("UF_RegionenKlasse1_lyr", "crossLeft", "1", "VB", "")

arcpy.SelectLayerByAttribute_management("UF_RegionenKlasse1_lyr", "CLEAR_SELECTION", "")

arcpy.MakeFeatureLayer_management(StrassenrandRechts, "StrassenrandRechts_lyr")
arcpy.SelectLayerByLocation_management("UF_RegionenKlasse1_lyr", "INTERSECT", "StrassenrandRechts_lyr", "", "NEW_SELECTION", "NOT_INVERT")
arcpy.CalculateField_management("UF_RegionenKlasse1_lyr", "crossRight", "1", "VB", "")
arcpy.SelectLayerByAttribute_management("UF_RegionenKlasse1_lyr", "CLEAR_SELECTION", "")


UF_RegionenKlasse1und2 = Geodatenbank + os.sep + "UF_RegionenKlasse1und2"

arcpy.CalculateField_management("UF_RegionenKlasse1_lyr", "Strassendurchbrechung", "complete( !crossLeft! , !crossRight! )", "PYTHON_9.3", "def complete(x,y):\\n  if x == 1 and y == 1:\\n    return 1\\n  else:\\n    return 0")
arcpy.CopyFeatures_management("UF_RegionenKlasse1_lyr", UF_RegionenKlasse1und2)


print('Klasse2 finished')

# Regionen auf der Strasse
# Regionen, die auf der Strasse liegen werden ausgeschnitten (Intersect)
# Zu kleine Regionen werden herausselektiert (FC to FC)
# Formatwechsel in Raster, da dadurch die Berechnung der Statistik ermoeglicht wird

UF_RegionenStrasse = Geodatenbank + os.sep + "UF_RegionenStrasse"
UF_RegionenStrasseSelect = Geodatenbank + os.sep + "UF_RegionenStrasseSelect"
UF_RegionenStrasseSelectRaster = Geodatenbank + os.sep + "UF_RegionenStrasseSelectRaster"

InFeatures = [StrassenBreite, UF_RegionenKlasse1und2]
arcpy.Intersect_analysis(InFeatures, UF_RegionenStrasse, "ALL", "", "INPUT")
arcpy.MakeFeatureLayer_management(UF_RegionenStrasse, "UF_RegionenStrasse_lyr")
arcpy.SelectLayerByAttribute_management("UF_RegionenStrasse_lyr", "NEW_SELECTION", "Shape_Area >= 15")
arcpy.CopyFeatures_management("UF_RegionenStrasse_lyr", UF_RegionenStrasseSelect)
arcpy.PolygonToRaster_conversion(UF_RegionenStrasseSelect, "FID_UF_RegionenKlasse1und2", UF_RegionenStrasseSelectRaster, "CELL_CENTER", "FID_UF_RegionenKlasse1und2", "5")

print('Regionen auf Strasse finished')

# Statistiken fuer Einstaudauer - Max Werte - End-Werte
# Fliessgeschwindigkeit hinzufuegen
# Zwischenspeichern

UF_RegionenStrasseMaxWerte = Geodatenbank + os.sep + "UF_RegionenStrasseMaxWerte"

arcpy.gp.ZonalStatisticsAsTable_sa(UF_RegionenStrasseSelectRaster, "Value", WassertiefeRaster, UF_RegionenStrasseMaxWerte, "NODATA", "MAXIMUM")
arcpy.MakeFeatureLayer_management(UF_RegionenKlasse1und2, "UF_RegionenKlasse1und2_lyr")
arcpy.AddJoin_management("UF_RegionenKlasse1und2_lyr", "Id", UF_RegionenStrasseMaxWerte, "Value", "KEEP_ALL")
UF_RegionenStrasseEndWerte = Geodatenbank + os.sep + "UF_RegionenStrasseEndWerte"

arcpy.gp.ZonalStatisticsAsTable_sa(UF_RegionenStrasseSelectRaster, "Value", Beregnungsraster, UF_RegionenStrasseEndWerte, "NODATA", "MAXIMUM")
arcpy.AddJoin_management("UF_RegionenKlasse1und2_lyr", "Id", UF_RegionenStrasseEndWerte, "Value", "KEEP_ALL")
UF_RegionenStrasseFG = Geodatenbank + os.sep + "UF_RegionenStrasseFG"

arcpy.gp.ZonalStatisticsAsTable_sa(UF_RegionenStrasseSelectRaster, "Value", Fliessgeschwindigkeit, UF_RegionenStrasseFG, "NODATA", "MAXIMUM")
arcpy.AddJoin_management("UF_RegionenKlasse1und2_lyr", "Id", UF_RegionenStrasseFG, "Value", "KEEP_ALL")

UF_RegionenData = Geodatenbank + os.sep + "UF_RegionenData"
arcpy.CopyFeatures_management("UF_RegionenKlasse1und2_lyr", UF_RegionenData)

print('Zonale Statistik finished')

# Einstaudauer Spalte berechnen
UF_RegionenData = Geodatenbank + os.sep + "UF_RegionenData"
UF_RegionenData2 = Geodatenbank + os.sep + "UF_RegionenData2"

arcpy.AddField_management(UF_RegionenData, "Einstaudauer", "TEXT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
arcpy.CalculateField_management(UF_RegionenData, "Einstaudauer", "einstaudauer( !UF_RegionenStrasseMaxWerte_MAX!, !UF_RegionenStrasseEndWerte_MAX! )", "PYTHON_9.3", "def einstaudauer(x,y):\\n  if x > y and (x - 0.02) > y:\\n    return \"nimmt ab\"\\n  else:\\n    return \"bleibt\"")
arcpy.SpatialJoin_analysis(UF_RegionenData, StrassenNRW, UF_RegionenData2, "JOIN_ONE_TO_ONE", "KEEP_ALL", "", "WITHIN_A_DISTANCE", "30 Meters", "")

print('Einstaudauer finished')

# Shape Area der Bereiche, die auf der Strasse liegen, werden an die Regionen FC angehaengt
# Zwischenspeichern

UF_RegionenStrasse = Geodatenbank + os.sep + "UF_RegionenStrasse"
UF_RegionenData3 = "UF_RegionenData3"

arcpy.MakeFeatureLayer_management(UF_RegionenData2, "UF_RegionenData2_lyr")
arcpy.AddJoin_management("UF_RegionenData2_lyr", "UF_RegionenKlasse1und2_Id", UF_RegionenStrasse, "FID_UF_RegionenKlasse1und2", "KEEP_ALL")
"""arcpy.CopyFeatures_management("UF_RegionenData2_lyr", UF_RegionenData3)"""
arcpy.FeatureClassToFeatureClass_conversion("UF_RegionenData2_lyr", Geodatenbank, UF_RegionenData3)

print('Join Shape Area UF Strassen finished')


# Flood Hazard Index berechnen und dazu benoetigte Felder hinzufuegen

UF_RegionenData3 = Geodatenbank + os.sep + "UF_RegionenData3"

arcpy.AddField_management(UF_RegionenData3, "FHI_UT", "FLOAT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
arcpy.AddField_management(UF_RegionenData3, "FHI_UA", "FLOAT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
arcpy.AddField_management(UF_RegionenData3, "FHI_FG", "FLOAT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
arcpy.AddField_management(UF_RegionenData3, "FHI_ED", "FLOAT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
arcpy.AddField_management(UF_RegionenData3, "FHI_FD", "FLOAT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")


arcpy.CalculateField_management(UF_RegionenData3, "FHI_UT", "rating( !UF_RegionenData2_UF_RegionenStrasseMaxWerte_MAX! )", "PYTHON_9.3", "def rating(x):\\n  if 0.05 < x <= 0.01:\\n    return 1*0.41\\n  elif 0.1 < x <= 0.5:\\n     return 2*0.41\\n  elif x > 0.5:\\n    return 3*0.41\\n  else:\\n    return 0\\n")
arcpy.CalculateField_management(UF_RegionenData3, "FHI_UA", "rating( !UF_RegionenStrasse_Shape_Area! )", "PYTHON_9.3", "def rating(x):\\n  if 15 < x <= 30:\\n    return 1*0.17\\n  elif 30 < x <= 50:\\n     return 2*0.17\\n  elif x > 50:\\n    return 3*0.17\\n  else:\\n    return 0")
arcpy.CalculateField_management(UF_RegionenData3, "FHI_ED", "rating( !UF_RegionenData2_Einstaudauer! )", "PYTHON_9.3", "def rating(x):\\n  if  x == 'bleibt':\\n    return 0.046\\n  elif x == 'nimmt ab':\\n    return 0\\n  else:\\n    return 0")
arcpy.CalculateField_management(UF_RegionenData3, "FHI_FD", "rating( !UF_RegionenStrasse_Strassendurchbrechung! )", "PYTHON_9.3", "def rating(x):\\n  if  x == 1:\\n    return 1*0.21\\n  else:\\n    return 0\\n")
arcpy.CalculateField_management(UF_RegionenData3, "FHI_FG", "rating( !UF_RegionenData2_UF_RegionenStrasseFG_MAX! )", "PYTHON_9.3", "def rating(x):\\n  if 0.2 < x <= 0.5:\\n    return 1*0.16\\n  elif 0.5 < x <= 2:\\n     return 2*0.16\\n  elif x > 2:\\n    return 3*0.16\\n  else:\\n    return 0\\n")

FHI_Regionen = Geodatenbank + os.sep + "FHI_Regionen"

"""arcpy.FeatureClassToFeatureClass_conversion(UF_RegionenData3, Geodatenbank, FHI_Regionen)"""
arcpy.CopyFeatures_management(UF_RegionenData3, FHI_Regionen)

arcpy.AddField_management(FHI_Regionen, "FHI", "FLOAT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
arcpy.CalculateField_management(FHI_Regionen, "FHI", "[FHI_UT] + [FHI_UA] + [FHI_FG] + [FHI_ED] + [FHI_FD]", "VB", "")

print ('FINAL: FHI finished')
