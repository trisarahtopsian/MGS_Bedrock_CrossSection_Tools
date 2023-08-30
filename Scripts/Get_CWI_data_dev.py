#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Get CWI Data
# Created by Sarah Francis, Minnesota Geological Survey
# Created Date: July 2023
'''
This script retrieves CWI data and creates a well point file and stratigraphy
table inside of a geodatabase. It attaches cross section attributes to the 
well point file. Required before running the "make lixpys" script.
'''

# %% 1 Import modules

import arcpy
import sys
import os
import datetime

# Record tool start time
toolstart = datetime.datetime.now()

# Define print statement function for testing and compiled geoprocessing tool

def printit(message):
    if (len(sys.argv) > 1):
        arcpy.AddMessage(message)
    else:
        print(message)

def printwarning(message):
    if (len(sys.argv) > 1):
        arcpy.AddWarning(message)
    else:
        print(message)
        
def printerror(message):
    if (len(sys.argv) > 1):
        arcpy.AddError(message)
    else:
        print(message)

# %% 2 Set parameters to work in testing and compiled geopocessing tool

if (len(sys.argv) > 1):
    #variable retrieved by esri geoprocessing tool
    output_gdb = arcpy.GetParameterAsText(0) 
    xsln = arcpy.GetParameterAsText(1) 
    buffer_distance = int(arcpy.GetParameterAsText(2)) #meters
    printit("Variables set with tool parameter inputs.")

else:
    # hard-coded parameters used for testing
    output_gdb = r'D:\Bedrock_Xsec_Scripting\construction.gdb'
    xsln = r'D:\Bedrock_Xsec_Scripting\demo_data_steele.gdb\Bedrock_cross_section_lines'
    buffer_distance = 500 #meters
    strat_table_boo = False
    const_table_boo = True
    printit("Variables set with hard-coded parameters for testing.")

#%% 3 Buffer xsln file
printit("Buffering xsln file.")

xsln_buffer = os.path.join(output_gdb, "xsln_buffer")
arcpy.analysis.Buffer(xsln, xsln_buffer, buffer_distance)

#%% 4 Clip statewide wwpt file by xsln buffer

printit("Clipping statewide CWI wwpt file with xsln buffer.")
arcpy.env.overwriteOutput = True
#papg = os.path.join(output_gdb, 'papg')
state_wwpt = r'J:\ArcGIS_scripts\mgs_sitepackage\layer_files\MGSDB4.mgs_cwi.mgsstaff.sde\mgs_cwi.cwi.loc_wells'
wwpt_temp = os.path.join(output_gdb, 'wwpt_temp')

arcpy.analysis.Clip(state_wwpt, xsln_buffer, wwpt_temp)

#%% Join attributes from xsln to wwpt

printit("Spatial join xsln attributes to well points.")
arcpy.env.overwriteOutput = True
wwpt = os.path.join(output_gdb, 'wwpt')
arcpy.analysis.SpatialJoin(wwpt_temp, xsln_buffer, wwpt, 'JOIN_ONE_TO_MANY')

'''
printit("Creating archival wwpt file with today's date.")
#create copy of wwpt file with date for archival purposes
now = datetime.datetime.now()
month = now.strftime("%m")
day = now.strftime("%d")
year = now.strftime("%y")
date = str(month + day + year)

arcpy.conversion.FeatureClassToFeatureClass(wwpt, output_gdb, "wwpt" + date)
'''
#%% Make strat table

if strat_table_boo == True:
    printit("Clipping statewide stratigraphy data with xsln buffer.")
    #I think this point file has all of the attributes needed?
    state_strat_points = r'J:\ArcGIS_scripts\mgs_sitepackage\layer_files\MGSDB4.mgs_cwi.mgsstaff.sde\mgs_cwi.cwi.stratigraphy'
    
    #clip statewide strat points
    strat_points_temp = os.path.join(output_gdb, "strat_temp")
    arcpy.analysis.Clip(state_strat_points, xsln_buffer, strat_points_temp)
    
    #spatial join with xsln buffer
    printit("Spatial join xsln attributes to stratigraphy points.")
    strat_points_temp2 = os.path.join(output_gdb, "strat_temp2")
    arcpy.analysis.SpatialJoin(strat_points_temp, xsln_buffer, strat_points_temp2, 'JOIN_ONE_TO_MANY')
    
    #export strat points temp2 to geodatabase table
    printit("Exporting temp stratigraphy points to geodatabase table.")
    temp_table_view = "temp_table_view"
    arcpy.management.MakeTableView(strat_points_temp2, temp_table_view)
    strat_table = os.path.join(output_gdb, "strat_cwi")
    try:
        #TableToTable is apparently depricated, but the newer version (ExportTable)
        #isn't working? This way, one of them should work.
        arcpy.conversion.ExportTable(temp_table_view, strat_table)
    except:
        arcpy.conversion.TableToTable(temp_table_view, output_gdb, "strat_cwi")

#%% Make construction table
if const_table_boo == True:
    arcpy.env.overwriteOutput = True
    #define path of cwi construction table
    state_constr_table = r'J:\ArcGIS_scripts\mgs_sitepackage\layer_files\MGSDB4.mgs_cwi.mgsstaff.sde\mgs_cwi.cwi.loc_wells_c5c2'
    #define path of temp table used in search cursor loop
    temp_dir = r'in_memory' 
    temp_constr_table = os.path.join(temp_dir, "constr_cwi_temp")
    #create empty table with all of the fields from c5c2
    arcpy.management.CreateTable(output_gdb, "constr_cwi", state_constr_table)
    constr_table = os.path.join(output_gdb, "constr_cwi")
    #go through each well and find matching construction records
    with arcpy.da.SearchCursor(wwpt, ["relateid"]) as cursor:
        for well in cursor:
            relateid = well[0]
            printit("Working on well {0}".format(relateid))
            #select construction table records with matching relateid
            where_clause = "{0}='{1}'".format("relateid", relateid)
            arcpy.analysis.TableSelect(state_constr_table, temp_constr_table, where_clause)
            #append these temp records to the working table
            arcpy.management.Append(temp_constr_table, constr_table)
    
    #join elevation field to construction table from wwpt
    printit("Joining elevation field from well point file.")
    arcpy.management.JoinField(constr_table, 'relateid', wwpt, 'relateid', ['elevation'])
    #create and calculate "elev_top" and "elev_bot" fields
    arcpy.management.AddField(constr_table, 'elev_top', 'DOUBLE')
    arcpy.management.AddField(constr_table, 'elev_bot', 'DOUBLE')
    with arcpy.da.UpdateCursor(constr_table, ["elevation", "from_depth", "to_depth", "elev_top", "elev_bot"]) as cursor:
        for row in cursor:
            elevation = row[0]
            from_depth = row[1]
            to_depth = row[2]
            if elevation is None:
                continue
            if from_depth is None:
                continue
            if to_depth is None:
                continue
            top = elevation - from_depth
            bot = elevation - to_depth
            row[3] = top
            row[4] = bot
            cursor.updateRow(row)

 #%% Delete temporary files
printit("Deleting temporary files.")

try: arcpy.management.Delete(wwpt_temp)
except: printit("Unable to delete {0}.".format(wwpt_temp))

if strat_table_boo == True:
    try: arcpy.management.Delete(strat_points_temp)
    except: printit("Unable to delete {0}.".format(strat_points_temp))
    
    try: arcpy.management.Delete(strat_points_temp2)
    except: printit("Unable to delete {0}.".format(strat_points_temp2))
    
if const_table_boo == True:
    try: arcpy.management.Delete(temp_constr_table)
    except: printit("Unable to delete {0}.".format(temp_constr_table))

# %% 10 Record and print tool end time
toolend = datetime.datetime.now()
toolelapsed = toolend - toolstart
printit('Tool completed at {0}. Elapsed time: {1}. Youre a wizard!'.format(toolend, toolelapsed))