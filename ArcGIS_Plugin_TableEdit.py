# -*- coding: utf-8 -*-

# Projectseminar: Applications for Landmark Navigation using Python
# Lecturer: Dr. Eva Nuhn
# Author Paul Höhn

# Own module with functions for editing tables 

# necessary library
import arcpy 

# Tool to search for column names 
# **kwargs = Arbitrary Keyword Arguments -> keywords and respective argument values come as key:value pairs
# This allows to query index values and strings with the same function -> only for Strings and Integers

def search_colname(table, **kwargs):
    
    col_found = []
    cols = arcpy.ListFields(table)
    
    # for each key:value pair in kwargs the function checks if the input value is a string or a integer
    # string means: Search for column names containing this string and return results
    # integer means: Return the column name with the corresponding index value
    for key, value in kwargs.items():
        if isinstance(value, str):
            for col in cols:
                if value in col.name:
                    col_found.append(col.name)
                else: 
                    continue
        elif isinstance(value, int) and int(value) <= len(cols):
                col_found.append(cols[value].name)
        else:
            print("Please use 'string' or 'index' as key arguments")
            break
        
    return col_found

# simple function to get the values out of an table with an whereClause and field informations (column names)
# saves defining a SeachCursor, empty list  etc. -> simpler syntax     

def get_values(shapefile_table, fields, whereClause):
    
    values = []
    with arcpy.da.SearchCursor(shapefile_table, fields, whereClause) as cursor:
        for row in cursor:
            for idx, field in enumerate(fields):
                values.append(row[idx])
    return values


# You could also cover this function with the above function by checking the result of get_values for the specific value;  
# but for practice i have written an extra function for it
# this function checks if an value exists in a shapefile 

def check_value(shapefile, fields, value):
    
    # shapefile data needs value as string
    if isinstance(value, (int, float)):
        value = str(value)
    else:
        value = value
    # returned variable (Boolean)    
    found = False
    with arcpy.da.SearchCursor(shapefile, fields) as cursor:
        for row in cursor:
            if value in row:
                found = True
                break
            else:
                continue
    return found





    




