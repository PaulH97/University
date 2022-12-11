# -*- coding: utf-8 -*-
# Script Tool for ArcPro
# Projectseminar: Applications for Landmark Navigation using Python
# Lecturer: Dr. Eva Nuhn
# Author Paul Höhn

# import necessary libraries + own Module
import arcpy
import os
import TableEdit
import csv
import openpyxl

# Get inputs from Script Tool
shapefile = arcpy.GetParameterAsText(0)
landmarks = arcpy.GetParameterAsText(1)
survey = arcpy.GetParameterAsText(2)
interest_1 = arcpy.GetParameter(3)
interest_2 = arcpy.GetParameter(4)
interest_3 = arcpy.GetParameter(5)
aug_date = arcpy.GetParameterAsText(6)
result = arcpy.GetParameterAsText(7)

# Inform the user about the status of the tool, because in case of an error message it is easy to check from when approximately the error occurred.
arcpy.AddMessage("Inputs ready")
arcpy.AddMessage("----------")

# define main function 
def main():

    # -----------------------------PRE PROCESSING  ----------------------------
    arcpy.AddMessage("Starting preprocessing of the input data")
    # reduce input date to annual data, because data were collected as annual data and Day-Month-Year will never match with the survey data 
    aug_date_year = int(aug_date.split(".")[2].split(" ")[0])
    
    # in case the shapefile is not empty - all values in the feature layer are deleted 
    arcpy.DeleteFeatures_management(shapefile)
        
    # Default values and input values
    vals_input = [interest_1, interest_2, interest_3, aug_date_year]
    cols_default = [11, 12, 13, 21]
    
    # default values are added with columns containing the landmarks information (OSM_ID)
    cols_default.append("landmark") 
    
    # Use Search Modul to find all columns/fields with default index values (11,12...) + landmark information
    # later on we need only these columns for queries 
    fields = []
    
    # i created a function that takes index values and strings, thats why i need to work with kwarg ([11, 12, 13, 21, "landmark"])
    # this step is necessary, because the column names are shortened in arcgis after a certain length 
    # more elegant than determining the names of the columns manually -> just need an index value or a string that must be included in the column name
    for x in cols_default:
        cols = TableEdit.search_colname(survey, kwarg = x)
        for col in cols:
            fields.append(col)
    
    arcpy.AddMessage("Preprocessing of the input data is completed")
    arcpy.AddMessage("----------")
    
# ----------------------- Get OSM-ID from survey --------------------------------------------------------------
# =============================================================================================================
#   The idea in this code block is to find the OSM IDs in the survey table that match the user profile
#   For this purpose a SearchCursor and a whereClause with the personal informations of the user are used 
#   The problem is that the date ("Since then do you live in Augsburg") cannot be integrated into the whereClause   
#   Therefore an additional condition is set in the SearchCursor (for loop)
#   The found OSM Ids are written to a list called osm_id
# =============================================================================================================
    arcpy.AddMessage("Searching for OSM IDs of selected landmarks dependent on personal profile")
    
    # the where clause compares the profile (personal background and interest) of user with survey data
    # the majority of data is thus selected quickly in advance (better performance / speed)    
    whereClause = u'{} = {} AND {} = {} AND {} = {}'.format(
            arcpy.AddFieldDelimiters(survey, fields[0]), interest_1, 
            arcpy.AddFieldDelimiters(survey, fields[1]), interest_2,
            arcpy.AddFieldDelimiters(survey, fields[2]), interest_3
            )
    
    # get list of osm ID based on personal background and interest of user (see whereClause)
    osm_id = []

    with arcpy.da.SearchCursor(survey, fields, whereClause) as cursor:
        # compare date of user with date of every selected row
        for row in cursor:
            c = False # checks if field is empty and year of user is equal to survey data
            if row[3] is None:
                c = True # True means it is empty
            elif row[3].year == aug_date_year:     
                c = True
            else:
                continue
            # if c is true, a match could be found in the current row of the survey table -> get all OSM IDs of this row
            if c:
                # iterate over all columns containing landmark informations in form of the OSM ID 
                for idx in range(4, len(fields)):  
                    osm_id.append(int(row[idx])) # write the OSM ID in the osm_id list
            else:
                continue

    # classify osm_ids in two classes:
    # 1 selected as landmarks 2 selected as not a landmark
    # not 100 percent necessary, but as feedback quite interesting for the user 
    
    osm_id_like = [osm_id[i::2] for i in range(2)][0] 
    osm_id_dislike = [osm_id[i::2] for i in range(2)][1]
    
    # If the combination of the entered values (personal interests / background) in the survey table is not found, the program return that no data could be found 
    # If this is the case, the user has to change the input data
  
    if len(osm_id) == 0:
        arcpy.AddWarning("No matching data could be found, please change the input parameters (personal interests)")
        arcpy.AddMessage("No matching data could be found, please change the input parameters (personal interests)")
        arcpy.AddMessage("----------")
    else:
        # just wanted to give the user some information 
        arcpy.AddMessage("Found {} objects selected as landmark".format(len(osm_id_like)))
        arcpy.AddMessage("Found {} objects selected as not a landmark".format(len(osm_id_dislike)))
        arcpy.AddMessage("----------")

# ----------------- Create new SHP of selected Landmarks ----------------------------------------------------------
# ==================================================================================================================
#   In this section the found OSM Ids are used to get more information about the landmark
#   The landmark informations are then written to the new empty shapefile 
# ==================================================================================================================
    arcpy.AddMessage("Inserting the selected landmarks with additional informations in the input shapefile")
    
    # Itterate over all selected landmarks 
    for idx, lm in enumerate(osm_id):
        # check if the landmark exists with the check__value function of TableEdit modul
        # One or two OSM IDs are included in the survey table, but missing in the landmarks shapefile
        # therefore the check is done here with the function check_value
        if TableEdit.check_value(landmarks, "OSM_ID", lm):
            
            # use TableEdit for getting values from selected columns
            values = TableEdit.get_values(landmarks, ["KREUZUNGEN","Centroid_X", "Centroid_Y"], "OSM_ID = '" + str(lm) +  "'")
            # Extract information from values
            intersection = values[0]
            coord = arcpy.Point(values[1], values[2])
        
            # checks if the value is a liked or disliked value
            # this works because the IDs of the buildings in the list osm_id are stored as [like, dislike, like, dislike etc.]
            if idx % 2 == 0 and lm in osm_id_like:
                info = "selected as landmark"
            else: 
                info = "selected as not a landmark"
            
            # counts the landmarks at the respective intersection 
            # a query over the whole list is possible, because the landmarks are only at a certain intersection
            noSel = osm_id.count(lm)
            
            # new columns in shapefile (task)
            fields_shp = ["SHAPE@", "Id", "OSM_ID", "Intersect", "Info", "NoSel"]
            
            # inserting row in shp with arcpy cursor
            with arcpy.da.InsertCursor(shapefile, fields_shp) as cursor:
                
                cursor.insertRow(((coord), idx, str(lm), intersection, info, noSel))
        else:
            # Inform the user that a landmark with the OSM ID could not be found.
            arcpy.AddMessage(" There is no {} OSM ID in the landmark shapefile".format(lm))
            continue
        
    # Feedback for user     
    arcpy.AddMessage("Created {} new rows in the input shapefile".format(len(osm_id)))
    arcpy.AddMessage("Finished insert process")
    arcpy.AddMessage("----------")
    
# ------------------- Create personal input profil of user as CSV file ------------------------------------------------------
# =============================================================================
#   In the last step, the user's personal information is written to a csv file 
# =============================================================================
    # load workbook to create profile_list 
    # get the original column names from the survey table  
    survey_path = os.path.dirname(survey)
    wb = openpyxl.load_workbook(survey_path)
    # get active worksheet for Result.csv 
    ws = wb.active
    
    # empty list for original column names
    col_names = []
    
    # iterate over selected column names and store name in empty list 
    for x in cols_default[:4]:
        col_names.append(ws.cell(row = 1, column = x + 1).value)
     
    # write column names and related input values in csv file 
    with open(result, "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(col_names)
        writer.writerow(vals_input)
        
# call main function to run script tool       
if __name__ == "__main__":
    main()






