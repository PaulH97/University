# -*- coding: utf-8 -*-

import arcpy
from csv import reader
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import StratifiedKFold
from sklearn.model_selection import GridSearchCV
from sklearn import tree
import graphviz
import pathlib
import os

# Input pat
path = pathlib.Path(r'D:/Master/Advanced Landmark Applications/Abgabe/Daten/Input')

#Löschen des Feldes und Neuanlegen
def deletefield(landmarkCand, fieldname):
    fields = arcpy.ListFields(landmarkCand)
    for field in fields:
        if field.name == fieldname:
            arcpy.DeleteField_management(landmarkCand, fieldname)
        else:
            arcpy.AddMessage("Field is not there - new")
    arcpy.AddField_management(landmarkCand, fieldname, "SHORT")

def load_csv(filename):
    dataset = list()
    with open(filename, 'r') as file:
        csv_reader = reader(file)
        for row in csv_reader:
            if not row:
                continue
            dataset.append(row)
    return dataset

def str_column_to_float(dataset, column):
    for row in dataset:
        row[column] = float(row[column].strip())

def execute():

    #Read Objects
    landmark = os.path.join(path, "Objects_LandmarkPath.shp")
    CdTm_Train = os.path.join(path,'Input_CdTm_Train.csv')
    
    obj_lyr = "Obj_lyr"
    arcpy.MakeFeatureLayer_management(landmark, obj_lyr)

    dataset = load_csv(CdTm_Train)
    for i in range(len(dataset[0])):
        str_column_to_float(dataset, i)
    x = []
    xpart = []
    y = []
    for row in dataset:
        for i in range(len(row)):
            if i != (len(row) - 1):
                xpart.append(row[i])
            else:
                y.append(row[i])
        x.append(xpart)
        xpart = []

    #build the tree on training data
    features_names = ['visual', 'semantic', 'structural']
    labels = ['LM', 'NAL']

    dtree=DecisionTreeClassifier(criterion='gini',
        min_samples_leaf=1,
        min_samples_split=2, random_state=0, splitter='random', max_depth = 4)
    dtree.fit(x,y)

    #Visualisation of the tree
    dot_data = tree.export_graphviz(dtree, out_file=None)
    graph = graphviz.Source(dot_data)
    graph.render("Tree_Test_CdTm")
    dot_data = tree.export_graphviz(dtree, out_file=None,
                        feature_names= features_names,
                        class_names=labels,
                        filled=True, rounded=True,
                        special_characters=True)
    graph = graphviz.Source(dot_data)
    graph.format = 'png'
    graph.render('Tree_Test_CdTm', view = True)

    #create field to store whether object is a landmark or a NAL
    arcpy.SelectLayerByAttribute_management(obj_lyr, "CLEAR_SELECTION")
    
    deletefield(landmark, "CdTm_LM")
    cursor = arcpy.UpdateCursor(obj_lyr)
    #go through Objects
    for row in arcpy.SearchCursor(obj_lyr):
        rowlm = cursor.next()
        vis = row.getValue("SVIS")
        sem = row.getValue("SSEM")
        str = row.getValue("SSTR")
        intersection = row.getValue("Kreuzungen")
        osmId = row.getValue("osm_id_neu")

        #predict with the tree whether object is a landmark
        prediction = dtree.predict([[vis, sem, str]])

        #in case object is a landmark
        if dtree.predict([[vis, sem, str]]) == [1.]:
            fieldNameValue = "1"
            rowlm.setValue("CdTm_LM", fieldNameValue)
            cursor.updateRow(rowlm)


if __name__ == '__main__':
    execute()
    print("Fertig!")