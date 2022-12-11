import arcpy
from scipy import stats
import math
import os

arcpy.env.overwriteOutput = True

pfad = r'C:\Users\Anwender\Downloads\Data\Data'
output = r'C:\Users\Anwender\Downloads\Data\Data\output'

# if field of type short is already available it is deleted and recreated
def deletefield(landmarkCand, fieldname):
    fields = arcpy.ListFields(landmarkCand)
    for field in fields:
        if field.name == fieldname:
            arcpy.DeleteField_management(landmarkCand, fieldname)
        else:
            # arcpy.AddMessage("New Field")
            continue
    arcpy.AddField_management(landmarkCand, fieldname, "SHORT")


def execute():
    """TODO Implement den alten *** hier..."""
    landmarke = os.path.join(pfad, 'Objects_LandmarkPath.shp') # TODO
    buffer = os.path.join(pfad, 'Buffer_Objects_50m.shp')  # TODO Pfad anpassen
    gebaeude = os.path.join(pfad, 'Buildings_Buffer_Objects_50m.shp')  # TODO Pfad anpassen

    LM_lyr = "LM_lyr"
    arcpy.MakeFeatureLayer_management(landmarke, LM_lyr)

    buffer_lyr = "buffer_lyr"
    arcpy.MakeFeatureLayer_management(buffer, buffer_lyr)
    # Buildings in 100m Buffer
    
    geb_lyr = "geb_lyr"
    arcpy.MakeFeatureLayer_management(gebaeude, geb_lyr)

    # Create New Fields in Landmarks (if already available, delete old ones)
    for field in [
        "SURAREASAL",
        "colorSal",
        "heightSal",
        "surStrSal",
        "SVIS",
        "explSal",
        "histSal",
        "cultSal",
        "SSEM",
        "crossSal",
        "distSal",
        "SSTR",
    ]:
        deletefield(landmarke, field)

        #go through each landmark
    cursor = arcpy.UpdateCursor(LM_lyr)
    for row in arcpy.SearchCursor(LM_lyr):
        rowlm = cursor.next()
        actOSMID = row.getValue("OSM_ID_NEU")
        actSURAREA = row.getValue("SURAREA")
        actSURSTR=row.getValue("SURSTR")
        actCOLOR = row.getValue("COLOR")
        actHOEHEGEB = row.getValue("HOEHEGEB")
        actCULTURALI = row.getValue("CULTURAL_I")
        actHISTORICAL = row.getValue("HISTORICAL")
        actEXPLICITM = row.getValue("EXPLICIT_M")
        actCROSSSROADS = row.getValue("CROSSROADS")
        actDISTANCE = row.getValue("DISTANCE")
        actIntersection = row.getValue("Kreuzungen")

        print(rowlm, actCOLOR, actCROSSSROADS, actCULTURALI, actDISTANCE)
        
        #Salience Surface Structure
        if actSURSTR == "1":
            fieldNameValue = '25'
            rowlm.setValue("surStrSal", fieldNameValue)
            cursor.updateRow(rowlm)
        
        #Salience Surface Area
        arcpy.SelectLayerByAttribute_management(LM_lyr, "CLEAR_SELECTION")   	
        Selection = arcpy.SelectLayerByAttribute_management(buffer_lyr, "NEW_SELECTION", "OSM_ID_NEU = '" + actOSMID + "'")
        Selection = arcpy.SelectLayerByLocation_management(geb_lyr, 'intersect', buffer_lyr)
        Selection = arcpy.SelectLayerByAttribute_management(geb_lyr, "SUBSET_SELECTION", "SURAREA = '" + actSURAREA + "'")
        matchcount = int(arcpy.GetCount_management(geb_lyr)[0]) 
        if matchcount == 1:
            fieldNameValue = '25'
            rowlm.setValue("surAreaSal", fieldNameValue)
            cursor.updateRow(rowlm)
        
        #Salience Color 
        Selection = arcpy.SelectLayerByLocation_management(geb_lyr, 'intersect', buffer_lyr)
        Selection = arcpy.SelectLayerByAttribute_management(geb_lyr, "SUBSET_SELECTION", "COLOR = '" + actCOLOR + "'")
        matchcount = int(arcpy.GetCount_management(geb_lyr)[0])
        if matchcount == 1:
            fieldNameValue = '25'
            rowlm.setValue("colorSal", fieldNameValue)
            cursor.updateRow(rowlm)
        
        #Salience Height
        Selection = arcpy.SelectLayerByLocation_management(geb_lyr, 'intersect', buffer_lyr)
        Selection = arcpy.SelectLayerByAttribute_management(geb_lyr, "REMOVE_FROM_SELECTION", "OSM_ID_NEU  = '" + actOSMID + "'")
        anzahl = int(arcpy.GetCount_management(geb_lyr)[0]) 

        if arcpy.Exists(str(output) + '\\' + "heightvalues.dbf"):
            arcpy.Delete_management(str(output) + '\\' + "heightvalues.dbf")
        outtableSUM = str(output) + '\\' + "heightvalues.dbf"

        arcpy.Statistics_analysis(geb_lyr, outtableSUM, [["HOEHEGEB", "MEAN"], ["HOEHEGEB", "STD"]])
        with arcpy.da.SearchCursor(outtableSUM, "MEAN_HOEHE") as cursor_MeanHoehe:
            for row in cursor_MeanHoehe:
                mwHoehe =row[0]     
        with arcpy.da.SearchCursor(outtableSUM, "STD_HOEHEG") as cursor_STDHoehe:
            for row in cursor_STDHoehe:
                stdHoehe = row[0]
        Quantil = stats.t.ppf(1-0.025, anzahl)
        if stdHoehe == 0:
            arcpy.AddMessage("std is zero!!!")
        elif anzahl == 0:
            fieldNameValue = '25'
            rowlm.setValue("heightSal", fieldNameValue)
            cursor.updateRow(rowlm)	
        else:
            t = (mwHoehe-actHOEHEGEB)/(stdHoehe/(math.sqrt(anzahl)))
            if t < 0:
                t = t * (-1)
            if t > Quantil:
                fieldNameValue = '25'
                rowlm.setValue("heightSal", fieldNameValue)
                cursor.updateRow(rowlm)	
        if arcpy.Exists(str(output) + '\\' + "heightvalues.dbf"):
            arcpy.Delete_management(str(output) + '\\' + "heightvalues.dbf")

        #Visual Salience 
        svis = rowlm.getValue("surAreaSal") + rowlm.getValue("colorSal") + rowlm.getValue("heightSal") + rowlm.getValue("surStrSal")
        fieldNameValue = svis
        rowlm.setValue("SVIS", fieldNameValue)
        cursor.updateRow(rowlm)
        
        #Salience Cultural Importance
        if actCULTURALI =="1":
            fieldNameValue = '25'
            rowlm.setValue("cultSal", fieldNameValue)
            cursor.updateRow(rowlm)
        
        #Salience Historical Importance
        if actHISTORICAL =="1":
            fieldNameValue = '25'
            rowlm.setValue("histSal", fieldNameValue)
            cursor.updateRow(rowlm)
        
        #Salience Explicit Marks
        if actEXPLICITM =="1":
            fieldNameValue = '50'
            rowlm.setValue("explSal", fieldNameValue)
            cursor.updateRow(rowlm)
        
        #Semantic Salience
        ssem = rowlm.getValue("cultSal") + rowlm.getValue("histSal") + rowlm.getValue("explSal")
        fieldNameValue = ssem
        rowlm.setValue("SSEM", fieldNameValue)
        cursor.updateRow(rowlm)
        
        #Salience Location at a Decisiont Point
        if actCROSSSROADS =="1":
            fieldNameValue = '50'
            rowlm.setValue("crossSal", fieldNameValue)
            cursor.updateRow(rowlm)
        
        #Salience Distance to the Decision Point 
        Selection = arcpy.SelectLayerByAttribute_management(LM_lyr, "NEW_SELECTION", "KREUZUNGEN = " + str(actIntersection))
        matchcount = int(arcpy.GetCount_management(LM_lyr)[0])
        minDist = 999
        a = 0 
        for rowDist in arcpy.SearchCursor(LM_lyr):
            Dist = rowDist.getValue("DISTANCE")
            if Dist < minDist:
                minDist = Dist
        if actDISTANCE == minDist:
            fieldNameValue = '50'
            rowlm.setValue("distSal", fieldNameValue)
            cursor.updateRow(rowlm)	
        
        #Structural Salience 
        sstr = rowlm.getValue("crossSal") + rowlm.getValue("distSal") 
        fieldNameValue = sstr
        rowlm.setValue("SSTR", fieldNameValue)
        cursor.updateRow(rowlm)


if __name__ == '__main__':
    execute()
    print("Fertig!")