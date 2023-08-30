#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Create Bedrock Cross Section Reference Lines
# Created by Sarah Francis, Minnesota Geological Survey
# Created Date: June 2023
'''
This script will create reference lines for bedrock cross sections. There will
be two outputs: elevation lines and x coordinate lines. Elevation lines can be
used to view elevations in cross section view. X coordinate lines can be used 
to find mapview location in utmx coordinates. 
The output line files will have "rank" and "label" fields. "Rank" field will be
populated with "major" or "minor", and "label" will be populated with the 
elevation or UTM value for the line.
'''

#%% 1 Import modules

import arcpy
import os
import sys
import datetime

# Record tool start time
toolstart = datetime.datetime.now()

# Define print statement function for testing and compiled geoprocessing tool

def printit(message):
    if (len(sys.argv) > 1):
        arcpy.AddMessage(message)
    else:
        print(message)
        
def printerror(message):
    if (len(sys.argv) > 1):
        arcpy.AddError(message)
    else:
        print(message)

#%% 2 Set parameters to work in testing and compiled geopocessing tool

if (len(sys.argv) > 1):
    xsln_file = arcpy.GetParameterAsText(0)  #mapview cross section line file
    xsln_id_field = arcpy.GetParameterAsText(1) #must be text data type
    output_dir = arcpy.GetParameterAsText(2)
    vertical_exaggeration = int(arcpy.GetParameterAsText(3))
    min_z = int(arcpy.GetParameterAsText(4)) # minimum elevation for ref lines
    max_z = int(arcpy.GetParameterAsText(5)) #maximum elevation for ref lines
    major_vert_interval = int(arcpy.GetParameterAsText(6)) #feet
    minor_vert_interval = int(arcpy.GetParameterAsText(7)) #feet
    major_horiz_interval = int(arcpy.GetParameterAsText(8)) #meters
    minor_horiz_interval = int(arcpy.GetParameterAsText(9)) #meters
    printit("Variables set with tool parameter inputs.")

else:
    # hard-coded parameters used for testing
    xsln_file = r'D:\Bedrock_Xsec_Scripting\Reference_grid_062923.gdb\xsln_diagonal' #mapview cross section line file
    xsln_id_field = 'et_id' #must be text data type
    output_dir = r'D:\Bedrock_Xsec_Scripting\Reference_grid_063023.gdb'
    vertical_exaggeration = 50 
    min_z = 0 # minimum elevation for ref lines
    max_z = 2500 #maximum elevation for ref lines
    major_vert_interval = 50 #feet
    minor_vert_interval = 10 #feet
    major_horiz_interval = 1000 #meters
    minor_horiz_interval = 250 #meters

    printit("Variables set with hard-coded parameters for testing.")

#%% 3 set min and max extents

#get maximum cross section line length from xsln file

#set starting max length value of 0 
max_length = 0

#use search cursor to read length field and find the maximum length
with arcpy.da.SearchCursor(xsln_file, ['SHAPE@LENGTH', xsln_id_field]) as cursor:
    for row in cursor:
        line = row[1]
        length = row[0]
        if length > max_length:
            max_length = length

printit("Maximum line length is {0}.".format(max_length))

#get min and max utmx extent from xsln file
xsln_desc = arcpy.Describe(xsln_file)
utmx_min_raw = int(xsln_desc.Extent.XMin)
utmx_max_raw = int(xsln_desc.Extent.XMax)

#Round above to the nearest 1000
#round down for utmx min
utmx_min_raw_sub = utmx_min_raw - major_horiz_interval
utmx_min = round(utmx_min_raw_sub, -3)
#round up for utmx max
utmx_max_raw_add = utmx_max_raw + major_horiz_interval
utmx_max = round(utmx_max_raw_add, -3)

#set min and max x for output display
min_x_disp = 0
#convert from meters to feet and divide by VE factor to squish coordinates
max_x_disp = int((max_length/0.3048)/vertical_exaggeration)

#%% 4 Create empty line feature class with elevation field

arcpy.env.overwriteOutput = True

out_line_fc = os.path.join(output_dir, 'elevation_ref_lines' + "_" + str(vertical_exaggeration) + "x")

#get filename of output
output_name = 'elevation_ref_lines' + "_" + str(vertical_exaggeration) + "x"

printit("Creating empty line file for geometry creation.")
arcpy.management.CreateFeatureclass(output_dir, output_name, 'POLYLINE')

#%% 5 add fields
label_field = "label"
arcpy.management.AddField(out_line_fc, label_field, 'LONG')

rank_field = "rank" #populated with "major" or "minor"
arcpy.management.AddField(out_line_fc, rank_field, "TEXT")

#%% 6 Create list of elevations
major_elevations_raw = list(range(min_z, max_z, major_vert_interval))
minor_elevations_raw = list(range(min_z, max_z, minor_vert_interval))

#remove major elevations from minor list
for elevation in minor_elevations_raw:
    if elevation in major_elevations_raw:
        minor_elevations_raw.remove(elevation)

#%% 7 Create new list of elevations that are not above county max or below county min

below_min_z = int(min_z - minor_vert_interval)
above_max_z = int(max_z + minor_vert_interval)
major_elevations = []
minor_elevations = []

for elevation in major_elevations_raw:
    if elevation < below_min_z:
        continue
    elif elevation > above_max_z:
        continue
    else:
        major_elevations.append(elevation)
    
for elevation in minor_elevations_raw:
    if elevation < below_min_z:
        continue
    elif elevation > above_max_z:
        continue
    else:
        minor_elevations.append(elevation)

printit("Major elevations are {0}.".format(major_elevations))
printit("Minor elevations are {0}.".format(minor_elevations))

#%% 8 Create geometry in elevation file

for ele in major_elevations:
    pointlist = []
    line_rank = "major"
    #define endpoints as min and max x
    pt1 = arcpy.Point(min_x_disp, ele)
    pt2 = arcpy.Point(max_x_disp, ele)
    #add points to pointlist
    pointlist.append(pt1)
    pointlist.append(pt2)
    #turn into array and create geometry object
    array = arcpy.Array(pointlist)
    geom = arcpy.Polyline(array)
    #insert geometry into output. Store true elevation in elevation attribute.
    with arcpy.da.InsertCursor(out_line_fc, [label_field, rank_field, 'SHAPE@']) as cursor:
        cursor.insertRow([ele, line_rank, geom])

# Create line geometry for minor elevations
#printit("Creating line geometry for minor elevations.")
#create geometry
for ele in minor_elevations:
    pointlist = []
    line_rank = "minor"
    #define endpoints as min and max x at display elevation
    pt1 = arcpy.Point(min_x_disp, ele)
    pt2 = arcpy.Point(max_x_disp, ele)
    #add points to pointlist
    pointlist.append(pt1)
    pointlist.append(pt2)
    #turn into array and create geometry object
    array = arcpy.Array(pointlist)
    geom = arcpy.Polyline(array)
    #insert geometry into output. Store true elevation in elevation attribute.
    with arcpy.da.InsertCursor(out_line_fc, [label_field, rank_field, 'SHAPE@']) as cursor:
        cursor.insertRow([ele, line_rank, geom])

#%% 9 Create empty feature classes for storing UTMX reference files
'''
#Create feature dataset
printit("Creating feature dataset for storing x coordinate reference lines.")
arcpy.management.CreateFeatureDataset(output_dir, "xcoord_ref_lines" + "_" + str(vertical_exaggeration) + "x")
x_ref_fd = os.path.join(output_dir, "xcoord_ref_lines" + "_" + str(vertical_exaggeration) + "x")

#get all cross section IDs
xsec_id_list = []
with arcpy.da.SearchCursor(xsln_file, [xsln_id_field]) as cursor:
    for row in cursor:
        xsec_id = row[0]
        xsec_id_list.append(xsec_id)
'''
#create line feature class for storing output utmx reference files
printit("Creating x coordinate reference line feature class")
fc_name = "xcoord_ref_lines" + "_" + str(vertical_exaggeration) + "x"
arcpy.management.CreateFeatureclass(output_dir, fc_name, 'POLYLINE')
out_fc = os.path.join(output_dir, fc_name)
#add fields
fields_list = [["label", 'LONG'], ['rank', 'TEXT'], [xsln_id_field, 'TEXT']]
arcpy.management.AddFields(out_fc, fields_list)

#remove first cross section ID from list
#xsec_id_list.remove(xsec_id_list[0])
'''
#create duplicate feature classes for all remaining lines
for xsec in xsec_id_list:
    printit("Creating x coordinate reference line feature class for xsec {0}.".format(xsec))
    fc_name = "xcoord_ref_lines" + "_" + str(xsec) + "_" + str(vertical_exaggeration) + "x"
    arcpy.conversion.FeatureClassToFeatureClass(fc_name_1, x_ref_fd, fc_name)
'''
#%% 10 Create list of utmx values

major_utmx = list(range(utmx_min,utmx_max,major_horiz_interval))
minor_utmx = list(range(utmx_min,utmx_max,minor_horiz_interval))

#remove major utmx from minor list
for utmx in minor_utmx:
    if utmx in major_utmx:
        minor_utmx.remove(utmx)
        
#%% 11 Create line geometry for major utmx
printit("Creating line geometry for x coordinate divisions.")
#WILL NEED TO USE MEASURE ALONG LINE FOR THESE

#vertical lines: same x coordinate, diferent y coordinates
#y coordinates will be min and max elevation
#x coordinate will be measured from start of line to specified utmx, then VE factor calculated

#loop thru xsln one line at a time
with arcpy.da.SearchCursor(xsln_file, ['SHAPE@', xsln_id_field]) as xsln:
    for line in xsln:
        xsec = line[1]
        printit("Working on major divisions for line {0}".format(xsec))
        #out_fc = os.path.join(x_ref_fd, "xcoord_ref_lines" + "_" + str(xsec)) + "_" + str(vertical_exaggeration) + "x"
        pointlist = []
        for vertex in line[0].getPart(0):
            # Creates a polyline geometry object from xsln vertex points.
            # Necessary for MeasureOnLine method used later.
            point = arcpy.Point(vertex.X, vertex.Y)
            pointlist.append(point)
        array = arcpy.Array(pointlist)
        xsln_geometry = arcpy.Polyline(array)
        #create a vertical line for each major utmx
        for utmx in major_utmx:
            label = int(utmx)
            rank = "major"
            #find the point (x,y) along the xsln line that has the matching utmx coordinate
            #create geometry object for utmx line covering whole state of MN
            utmx_pointlist = []
            utmx_pt1 = arcpy.Point(utmx, 4800000)
            utmx_pt2 = arcpy.Point(utmx, 5500000)
            utmx_pointlist.append(utmx_pt1)
            utmx_pointlist.append(utmx_pt2)
            utmx_array = arcpy.Array(utmx_pointlist)
            utmx_geometry = arcpy.Polyline(utmx_array)
            #check to see if this utmx intersects the xsln
            disjoint = arcpy.Polyline.disjoint(utmx_geometry, xsln_geometry)
            if disjoint: 
                #printit("no intersection at {0}. Continuing to next utmx".format(utmx))
                continue
            #find intersection of utmx_geometry and xsln_geometry
            intersect_pt_mp = arcpy.Polyline.intersect(utmx_geometry, xsln_geometry, 1)
            #returns multipoint object. Should make two utmx lines if the xsln intersects the same utmx twice
            #iterate through the multipoint object
            for intersect_point in intersect_pt_mp.getPart():
                intersect_pt = arcpy.Point(intersect_point.X, intersect_point.Y)
                #use measure along line to find the distance to it, then calculate VE
                x_raw = arcpy.Polyline.measureOnLine(xsln_geometry, intersect_pt)
                #convert meters to feet and divide by VE factor
                x = (x_raw/0.3048)/vertical_exaggeration
                #create top and bottom points for vertical line
                geom_pointlist = []
                pt1 = arcpy.Point(x, min_z)
                pt2 = arcpy.Point(x, max_z)
                geom_pointlist.append(pt1)
                geom_pointlist.append(pt2)
                geom_array = arcpy.Array(geom_pointlist)
                geom = arcpy.Polyline(geom_array)
                #insert geometry into output file for the current line
                with arcpy.da.InsertCursor(out_fc, ["SHAPE@", 'label', 'rank', xsln_id_field]) as insert_cursor:
                    insert_cursor.insertRow([geom, label, rank, xsec])
        #good job! Now do the minor divisions.
        printit("Working on minor divisions for line {0}".format(xsec))          
        for utmx in minor_utmx:
            label = int(utmx)
            rank = "minor"
            #find the point (x,y) along the xsln line that has the matching utmx coordinate
            #create geometry object for utmx line covering whole state of MN
            utmx_pointlist = []
            utmx_pt1 = arcpy.Point(utmx, 4800000)
            utmx_pt2 = arcpy.Point(utmx, 5500000)
            utmx_pointlist.append(utmx_pt1)
            utmx_pointlist.append(utmx_pt2)
            utmx_array = arcpy.Array(utmx_pointlist)
            utmx_geometry = arcpy.Polyline(utmx_array)
            #check to see if this utmx intersects the xsln
            disjoint = arcpy.Polyline.disjoint(utmx_geometry, xsln_geometry)
            if disjoint: 
                #printit("no intersection at {0}. Continuing to next utmx".format(utmx))
                continue
            #find intersection of utmx_geometry and xsln_geometry
            intersect_pt_mp = arcpy.Polyline.intersect(utmx_geometry, xsln_geometry, 1)
            #returns multipoint object. Should make two utmx lines if the xsln intersects the same utmx twice
            #iterate through the multipoint object
            for intersect_point in intersect_pt_mp.getPart():
                intersect_pt = arcpy.Point(intersect_point.X, intersect_point.Y)
                #use measure along line to find the distance to it, then calculate VE
                x_raw = arcpy.Polyline.measureOnLine(xsln_geometry, intersect_pt)
                #convert meters to feet and divide by VE factor
                x = (x_raw/0.3048)/vertical_exaggeration
                #create top and bottom points for vertical line
                geom_pointlist = []
                pt1 = arcpy.Point(x, min_z)
                pt2 = arcpy.Point(x, max_z)
                geom_pointlist.append(pt1)
                geom_pointlist.append(pt2)
                geom_array = arcpy.Array(geom_pointlist)
                geom = arcpy.Polyline(geom_array)
                #insert geometry into output file for the current line
                with arcpy.da.InsertCursor(out_fc, ["SHAPE@", 'label', 'rank', xsln_id_field]) as insert_cursor:
                    insert_cursor.insertRow([geom, label, rank, xsec])
            

#%% 12 Record and print tool end time
toolend = datetime.datetime.now()
toolelapsed = toolend - toolstart
printit('Tool completed at {0}. Elapsed time: {1}. Youre a wizard!'.format(toolend, toolelapsed))