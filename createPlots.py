#!/usr/bin/env python
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.patches import Polygon

import os
import sys

import argparse as ap
from createPlotUtils import *

initOptions("Script for creating line-plots.",
            "[input_directories [input_directories ...]] [OPTIONS]")

#Constants
MAX_GEN_NOT_PROVIDED = -1
NO_LINE = 0
LINE_WIDTH = 2
FILL_ALPHA = 0.5

#Derived defaults
def def_output_dir():
    if getExists("config_file"):
        return base(getStr("config_file")) + "_out"
    else:
        number = 1
        name = "my_plot_" + str(number)
        while os.path.exists(name):
            number += 1
            name = "my_plot_" + str(number)
        return name
def def_comp_cache(): return base(getStr("config_file")) + ".cache"
def def_box_height(): return max((len(getList("input_directories"))-1)*0.35, 0.5)
def def_marker_step():
    if getInt("max_generation") > 5:
        return getInt("max_generation")/5
    else:
        return None
def def_marker_offset(): 
    marker_step = get("marker_step")
    if hasattr(marker_step, '__call__'):
        marker_step = marker_step()
    if isinstance(marker_step, list):
        marker_step =  int(marker_step[0])
    if marker_step == 0 or marker_step is None:
        marker_step = 1
    num_treatments = len(getList("input_directories")) + len(getList("file"))
    if num_treatments < 1:
        num_treatments = 1
    step = marker_step/num_treatments
    if step < 1:
        step = 1
    return range(0, marker_step, step)
def def_legend_font_size(): return getInt("font_size")-4
def def_title_font_size(): return getInt("font_size")+4
def def_tick_font_size(): return getInt("font_size")-6
def def_sig_marker(): return getList("marker")
def def_treatment_names():
    if len(getList("input_directories")) > 0:
        return [os.path.basename(x) for x in getList("input_directories")]
    else:
        return [os.path.basename(x) for x in getList("file")]
def def_treatment_names_short(): return getList("treatment_names")
def def_background_colors(): 
    result = []
    colors = getList("colors")
    for color in colors:
        byte = ""
        new_color = "#"
        for char in color:
            if char == '#':
                continue
            byte += char
            if len(byte) == 2:
                byte_as_int = int(byte, 16)
                new_value = min(byte_as_int+128, 255)
                new_value_as_string = "%x" % new_value
                new_color += new_value_as_string
                byte = ""
        result.append(new_color)
    return result
            

#Directory settings
addOption("templates", ".*",
          help="Directories to traverse to find files to plot. "
          "Accepts regular expressions.")
addOption("pool",
          help="Pool the results in this directory together by taking the "
          "maximum. Accepts regular expressions.")
addOption("output_directory", def_output_dir, nargs=1,
          help="Resulting plots will be put into this directory.")


#General plot settings
addOption("max_generation", MAX_GEN_NOT_PROVIDED, nargs=1,
          help="The maximum number of generations to plot."
          "If not provided, the maximum will be determined from the data.")
addOption("step", 1, nargs=1,
          help="Step-size with which to plot the data.")
addOption("stat_test_step", 1, nargs=1,
          help="Step-size at which to perform statistical comparisons between "
          "treatments.")
addOption("marker_step",  def_marker_step, nargs=1,
          help="Step-size at which to place treatment markers.")
addOption("bootstrap", False, nargs=1,
          help="If true, the shaded area will be based on bootstrapped "
          "confidence intervals. Otherwise the shaded area represents the "
          "inter-quartile range.")
addOption("smoothing", 11, nargs=1,
          help="Applies a median window of the provided size to smooth the "
          "line plot.")
addOption("main_treatment", 0, nargs=1,
          help="Statistical comparisons are performed against this treatment.")
addOption("box_height", def_box_height, nargs=1,
          help="The height of the box showing significance indicators.")
addOption("box_sep", 0, nargs=1,
          help="Space between significance box and the main plot.")
addOption("fig_size", [8, 6], nargs=2,
          help="The size of the resulting figure.")
addOption("separator", " ", nargs=1,
          help="The separator used for the input data.")
addOption("marker_size", 18, nargs=1,
          help="The size of the treatment markers.")
addOption("x_from_file", False, nargs=1,
          help="If true, x-values will be read from file, rather than assumed "
          "to be from 0 to the number of data-points.")
addOption("x_column", 0, nargs=1,
          help="If x_from_file is true, this parameter determines which colomn "
          "contains the x data.")
addOption("x_values",
          help="Use the provided values for the x-axis.")
addOption("x_ticks",
          help="Use the provided strings as labels for the x-ticks.")
addOption("one_value_per_dir", False, nargs=1,
          help="If true, assumes that every file found holds a single value, "
          "to be plotted sequentially.")
addOption("comparison_offset_x", 0, nargs=1,
          help="Allows moving the labels next the significance indicator box.")
addOption("comparison_offset_y", 0.1, nargs=1,
          help="Allows moving the labels next the significance indicator box.")
addOption("sig_label", "p<0.05 vs ", nargs=1,
          help="Label next to the significance indicator box.")
addOption("type", "pdf", nargs=1,
          help="The file type in which the plot will be written.")

#Font settings
addOption("sig", True, nargs=1)
addOption("title", True, nargs=1,
          help="Show the title of the plot.")
addOption("font_size", 18, nargs=1,
          help="The base font-size for the plot "
          "(other font-sizes are relative to this one).")
addOption("title_size", def_title_font_size, nargs=1,
          help="Font size for the titel.")
addOption("legend_font_size", def_legend_font_size, nargs=1,
          help="Font size for the legend.")
addOption("tick_font_size", def_tick_font_size, nargs=1,
          help="Font size for the tick-labels.")
addOption("legend_columns", 1, nargs=1,
          help="Number of columns for the legend.")
addOption("legend_x_offset", 0, nargs=1,
          help="Allows for fine movement of the legend.")
addOption("legend_y_offset", 0, nargs=1,
          help="Allows for fine movement of the legend.")

#Per plot settings
addOption("to_plot", 1, aliases=["plot_column"],
          help="The columns from the input files that should be plotted.")
addOption("file_names", "my_plot", aliases=["plot_output"],
          help="The names of the output files for each plotted column.")
addOption("titles", "Unnamed plot", aliases=["plot_title"],
          help="The titles for each plot.")
addOption("x_labels",  "Number of Generations", aliases=["plot_x_label"],
          help="The x labels for each plot.")
addOption("y_labels", "Value", aliases=["plot_y_label"],
          help="The x labels for each plot.")
addOption("legend_loc", "best", aliases=["plot_legend_loc"],
          help="Legend location for each plot.")
addOption("y_axis_min", aliases=["plot_y_min"],
          help="The minimum value for the y axis.")
addOption("y_axis_max", aliases=["plot_y_max"],
          help="The maximum value for the y axis.")
addOption("x_axis_max", aliases=["plot_x_max"],
          help="The minimum value for the x axis.")
addOption("x_axis_min", aliases=["plot_x_min"],
          help="The maximum value for the x axis.")

#Cache settings
addOption("read_cache", True, nargs=1,
          help="If false, script will not attempt to read data from cache.")
addOption("write_cache", True, nargs=1,
          help="If false, script will not write cache files.")
addOption("read_median_ci_cache", True, nargs=1,
          help="If false, script will not read median values from cache.")
addOption("write_median_ci_cache", True, nargs=1,
          help="If false, script will not write median values to cache.")
addOption("read_comparison_cache", True, nargs=1,
          help="If false, script will not read statistical results from cache.")
addOption("write_comparison_cache", True, nargs=1,
          help="If false, script will not write statistical results to cache.")
addOption("comparison_cache", def_comp_cache, nargs=1,
          help="Name of the cache file that holds statistical results.")

#Per treatment settings
addOption("input_directories", aliases=["treatment_dir"],
          help="Directories containing the files for each specific treatment.")
addOption("treatment_names", def_treatment_names, aliases=["treatment_name"],
          help="The names of each treatment, used for the legend.")
addOption("treatment_names_short",  def_treatment_names_short,
          aliases=["treatment_name_short"],
          help="A short name for each treatment, used when the regular name "
          "does not fit.")
addOption("colors",
          ["#000082", "#008200", "#820000", "#008282", "#828200", "#820082"],
          aliases=["treatment_color"],
          help="The color for each treatment.")
addOption("background_colors",  def_background_colors,
          help="The color of the shaded region, for each treatment.")
addOption("marker",
          ["o", "^", "v", "<", ">", "*"],
          aliases=["treatment_marker"],
          help="The marker used for each treatment.")
addOption("sig_marker", def_sig_marker,
          help="The marker used in the signficance indicator box.")
addOption("marker_offset", def_marker_offset,
          help="Offset between the markers of different treatments, so they "
          "are not plotted on top of each other.")


addPositionalOption("file", nargs="*",
                    help="Files or directories from which to read the data.")


###################
##### CLASSES #####
###################
class Treatment:
    def __init__(self, treatment_id, directory, treatment_name, short_name):
        #Get Global data
        self.templates = getList("templates")
        self.pool = getList("pool")
        if len(self.pool) > 0:
            debug_print("files", "Pooling:", self.pool)
            self.root_directory = directory
            self.dirs = getDirs(self.pool, directory)
            self.files = []
            self.files_per_pool = [] 
            for pool_dir in self.dirs:
                files = get_files(self.templates, pool_dir)
                self.files += files
                self.files_per_pool.append(files)
            self.cache_file_name_prefix = (self.root_directory + "/ch_" +
                                           self.templates[-1] + "_")
        if os.path.isdir(directory):
            debug_print("files", "Retrieving files from directory:", directory,
                        "with template:", self.templates)
            self.root_directory = directory
            self.files = get_files(self.templates, directory)
            self.cache_file_name_prefix = (self.root_directory + "/ch_" +
                                           self.templates[-1] + "_")
        elif os.path.isfile(directory):
            debug_print("files", "Retrieving file:", directory)
            self.root_directory = os.path.dirname(os.path.realpath(directory))
            self.files = [directory]
            self.cache_file_name_prefix = (self.root_directory + "/ch_" +
                                           os.path.basename(directory) + "_")
        else:
            debug_print("files", "File not found.")
            self.root_directory = None
            self.files = []
            self.cache_file_name_prefix = "unknown_"
        self.name = treatment_name
        self.short_name = short_name
        self.id = treatment_id
        self.parts = [self.files]

    def __str__(self):
        return (str(self.root_directory) + " " + str(self.name) + " " +
                str(self.short_name) + " " + str(self.id))

    def add_dir(self, directory):
        self.parts.append(get_files(self.templates, directory))

    def get_id(self):
        return self.id

    def get_name(self):
        return self.name

    def get_name_short(self):
        return self.short_name

    def get_cache_file_name(self, plot_id):
        return self.cache_file_name_prefix + str(plot_id) + ".cache"


class TreatmentList:
    def __init__(self):
        self.treatments = []
        self.unnamed_treatment_count = 0

    def __len__(self):
        return len(self.treatments)

    def __iter__(self):
        return iter(self.treatments)

    def __getitem__(self, index):
        return self.treatments[index]

    def __str__(self):
        return str(self.treatments)

    def add_treatment(self, treat_dir, suggest_name=None, short_name=None):
        treat_id = len(self.treatments)
        if suggest_name and short_name:
            self.treatments.append(Treatment(treat_id, treat_dir, suggest_name,
                                             short_name))
        elif suggest_name:
            self.treatments.append(Treatment(treat_id, treat_dir, suggest_name,
                                             suggest_name))
        else:
            self.unnamed_treatment_count += 1
            name = "Unnamed " + str(self.unnamed_treatment_count)
            self.treatments.append(Treatment(treat_id, treat_dir, name, name))

    def get_treatment_directories(self):
        treatment_directories = []
        for treatment in self.treatments:
            treatment_directories.append(treatment.root_directory)
        return treatment_directories

    def get_treatment_names(self):
        treatment_names = []
        for treatment in self.treatments:
            treatment_names.append(treatment.name)
        return treatment_names

    def get_treatment_short_names(self):
        treatment_names = []
        for treatment in self.treatments:
            treatment_names.append(treatment.short_name)
        return treatment_names


class MedianAndCI:
    def __init__(self):
        self.median = dict()
        self.ci_min = dict()
        self.ci_max = dict()

    def __len__(self):
        return len(self.median)

    def add(self, generation, median, ci_min, ci_max):
        self.median[generation] = median
        self.ci_min[generation] = ci_min
        self.ci_max[generation] = ci_max

    def to_cache(self, cache_file_name):
        sorted_keys = sorted(self.median)
        median_array = self.get_median_array()
        ci_min_array = self.get_ci_min_array()
        ci_max_array = self.get_ci_max_array()

        with open(cache_file_name, 'w') as cache_file:
            print ("Writing " + cache_file_name + "...")
            for i in xrange(len(median_array)):
                cache_file.write(str(median_array[i]) + " ")
                cache_file.write(str(ci_min_array[i]) + " ")
                cache_file.write(str(ci_max_array[i]) + " ")
                cache_file.write(str(sorted_keys[i]) + "\n")

    def get_median_array(self):
        return dict_to_np_array(self.median)

    def get_ci_min_array(self):
        return dict_to_np_array(self.ci_min)

    def get_ci_max_array(self):
        return dict_to_np_array(self.ci_max)


class RawData:
    def __init__(self):
        self.raw_data = dict()
        self.max_generation = None

    def __getitem__(self, plot_id):
        return self.raw_data[plot_id]

    def __contains__(self, plot_id):
        return plot_id in self.raw_data

    def get_max_generation(self, plot_id=None):
        if plot_id is None:
            if not self.max_generation:
                self.init_max_generation()
            return self.max_generation
        else:
            return max(self.raw_data[plot_id].keys())

    def add(self, plot_id, generation, value):
        #print "Adding", plot_id, generation, value
        debug_print("raw_data", "For plot", plot_id, "added:", generation, value) 
        if plot_id not in self.raw_data:
            self.raw_data[plot_id] = dict()
        if generation not in self.raw_data[plot_id]:
            self.raw_data[plot_id][generation] = list()
        self.raw_data[plot_id][generation].append(value)

    def get(self, plot_id, generation):
        return self.raw_data[plot_id][generation]

    def init_max_generation(self):
        #Read global data
        self.max_generation = getInt("max_generation")
        if self.max_generation == MAX_GEN_NOT_PROVIDED:
            for data in self.raw_data.itervalues():
                generations = max(data.keys())
                debug_print("plot", "generations: " + str(generations))
                if generations > self.max_generation:
                    self.max_generation = generations


class DataSingleTreatment:
    def __init__(self, treatment):
        self.treatment = treatment
        self.raw_data = None
        self.median_and_ci = dict()
        self.max_generation = None

    def get_raw_data(self):
        if not self.raw_data:
            self.init_raw_data()
        return self.raw_data

    def get_median_and_ci(self, plot_id):
        if plot_id not in self.median_and_ci:
            self.init_median_and_ci(plot_id)
        return self.median_and_ci[plot_id]

    def get_max_generation(self):
        if not self.max_generation:
            self.init_max_generation()
        return self.max_generation

    def to_cache(self):
        #Read global data
        to_plot = getIntList("to_plot")

        for plot_id in to_plot:
            median_and_ci = self.get_median_and_ci(plot_id)
            median_and_ci.to_cache(self.treatment.get_cache_file_name(plot_id))

    def init_max_generation(self):
        #Read global data
        self.max_generation = getInt("max_generation")
        if self.max_generation == MAX_GEN_NOT_PROVIDED:
            raw_data = self.get_raw_data()
            self.max_generation = raw_data.get_max_generation()

    def init_raw_data(self):
        #Read global data
        separator = getStr("separator")
        to_plot = getIntList("to_plot")
        y_column = getInt("x_column")
        one_value_per_dir = getBool("one_value_per_dir")
        pool = len(getList("pool")) > 0

        #Init raw data
        self.raw_data = RawData()

        if len(self.treatment.files) == 0:
            print("Warning: treatment " + self.treatment.get_name() +
                  " has no files associated with it.")

        if one_value_per_dir:
            generation = 0
            for file_names in self.treatment.parts:
                debug_print("files", "Parts: ", file_names)
                for file_name in file_names:
                    with open(file_name, 'r') as separated_file:
                        print("Reading raw data for value " + str(generation) +
                              " from " + file_name + "...")
                        skip_header(separated_file)
                        for line in separated_file:
                            split_line = get_split_line(line, separator)
                            self._add(split_line, generation)
                generation += 1
        elif pool:
            for dir_name, file_names in zip(self.treatment.dirs,
                                            self.treatment.files_per_pool):
                print "Pooling for directory: ", dir_name
                results = []
                for file_name in file_names:
                    with open(file_name, 'r') as separated_file:
                        print("Reading raw data from " + file_name + "...")
                        skip_header(separated_file)
                        generation = 0
                        for line in separated_file:
                            split_line = get_split_line(line, separator)
                            result = self._parse_pool(split_line, generation)
                            #print "Value read: ", result
                            if len(results) < (generation+1):
                                results.append(result)
                            else:
                                for i in xrange(len(result)):
                                    old_value = results[generation][i]
                                    new_value = result[i]
                                    if new_value > old_value:
                                        results[generation][i] = new_value
                            generation += 1
                generation = 0
                for result in results:
                    for plot_id, value in zip(to_plot, result):
                        #print "Value used:", value 
                        self.raw_data.add(plot_id, generation, value)
                    generation += 1

        else:
            for file_name in self.treatment.files:
                with open(file_name, 'r') as separated_file:
                    print("Reading raw data from " + file_name + "...")
                    skip_header(separated_file)
                    generation = 0
                    for line in separated_file:
                        #split_line_temp = line.split(separator)
                        split_line = get_split_line(line, separator)
                        self._add(split_line, generation)
                        generation += 1

    def init_median_and_ci(self, plot_id):
        #Get global data
        read_cache = getBool("read_cache") and getBool("read_median_ci_cache")

        if read_cache:
            try:
                self.init_median_and_ci_from_cache(plot_id)
                return
            except IOError:
                pass
            except CacheException:
                pass
        self.init_median_and_ci_from_data(plot_id)

    def init_median_and_ci_from_cache(self, plot_id):
        # Read global data
        step = getInt("step")

        # Get the max generation for which we have data
        max_generation = self.get_max_generation()
        generations_to_plot = range(0, max_generation, step)
        data_points = len(generations_to_plot)
        cache_file_name = self.treatment.get_cache_file_name(plot_id)

        # Count the number of data points we have in
        count = get_nr_of_lines(cache_file_name)

        # If the number of points in the cache file is smaller than, or equal
        # to, the number of points requested, we probably want to plot every
        # single data-point we have.
        if count-1 <= data_points:
            cache_step = 1
        else:
            cache_step = step

        #Read the cache file
        with open(cache_file_name, 'r') as cache_file:
            print("Reading from cache file " + cache_file_name + "...")
            self.median_and_ci[plot_id] = MedianAndCI()
            line_number = 0
            data_point_number = 0
            for line in cache_file:
                try:
                    if line_number % cache_step == 0:
                        generation = generations_to_plot[data_point_number]
                        split_line = line.split()
                        if len(split_line) == 3:
                            self.median_and_ci[plot_id].add(generation,
                                                            split_line[0],
                                                            split_line[1],
                                                            split_line[2])
                        elif len(split_line) == 4:
                            self.median_and_ci[plot_id].add(int(split_line[3]),
                                                            split_line[0],
                                                            split_line[1],
                                                            split_line[2])
                        data_point_number += 1
                    line_number += 1
                except IndexError:
                    break

    def init_median_and_ci_from_data(self, plot_id):
        #Read global data
        step = getInt("step")
        bootstrap = getBool("bootstrap")
        write_cache = (getBool("write_cache") and
                       getBool("write_median_ci_cache"))
        x_from_file = getBool("x_from_file")

        #Initialize empty median and ci
        self.median_and_ci[plot_id] = MedianAndCI()
        max_generation = self.get_max_generation()

        if plot_id not in self.get_raw_data():
            print "Warning: no data available for plot", plot_id, "skipping."
            return
        if x_from_file:
            max_generation_available = self.get_raw_data().get_max_generation(plot_id)
        else:
            max_generation_available = len(self.get_raw_data()[plot_id])
        if max_generation_available < max_generation:
            print("Warning: data does not extent until max generation: " +
                  str(max_generation))
            print("Maximum generation available is: " +
                  str(max_generation_available))
            max_generation = max_generation_available

        #Calculate median and confidence intervals
        print("Calculating confidence intervals...")
        y_values = sorted(self.get_raw_data()[plot_id].keys())
        generations_to_plot = y_values[0:len(y_values):step]
        debug_print("plot", "generations_to_plot: " + str(generations_to_plot) +
                    " max generation: " +str(max_generation))
        for generation in generations_to_plot:
            raw_data = self.get_raw_data()[plot_id][generation]
            if bootstrap:
                print("Generation: " + str(generation))
                median, ci_min, ci_max = calc_median_and_bootstrap(raw_data)
                debug_print("ci", str(median) + " " +
                            str(ci_min) + " " + str(ci_max))
            else:
                median, ci_min, ci_max = calc_median_and_interquartile_range(raw_data)
            self.median_and_ci[plot_id].add(generation, median, ci_min, ci_max)
        if write_cache:
            self.to_cache()


    def _parse_pool(self, split_line, generation):
        to_plot = getIntList("to_plot")
        x_values_passed = getExists("x_values")
        x_values = getIntList("x_values")

        result = []
        debug_print("read_values", "Split line:", split_line,
                    "plot requested:", to_plot)
        for plot_id in to_plot:
            if len(split_line) <= plot_id:
                print("Error: no data for requested column" + str(plot_id) +
                      "in line (length" + str(len(split_line)) + ")" +
                      split_line)
            else:
                result.append(float(split_line[plot_id]))
        return result


    def _add(self, split_line, generation):
        to_plot = getIntList("to_plot")
        x_from_file = getBool("x_from_file")
        x_column = getInt("x_column")
        x_values_passed = getExists("x_values")
        x_values = getIntList("x_values")

        debug_print("read_values", "Split line:", split_line,
                    "plot requested:", to_plot)
        for plot_id in to_plot:
            if len(split_line) <= plot_id:
                print ("Error: no data for requested column", plot_id,
                       "in line (length", len(split_line), ")", split_line)
            elif x_from_file and len(split_line) > 1:
                self.raw_data.add(plot_id, int(split_line[x_column]),
                                  float(split_line[plot_id]))
            elif x_values_passed and generation < len(x_values):
                self.raw_data.add(plot_id, x_values[generation],
                                  float(split_line[plot_id]))
            else:
                self.raw_data.add(plot_id, generation,
                                  float(split_line[plot_id]))


class DataOfInterest:
    def __init__(self, treatment_list):
        self.treatment_list = treatment_list
        self.treatment_data = dict()
        self.comparison_cache = None
        self.max_generation = None

    def get_treatment_list(self):
        return self.treatment_list

    def get_treatment(self, treatment_id):
        return self.treatment_list[treatment_id]

    def get_treatment_data(self, treatment):
        treatment_id = treatment.get_id()
        if treatment_id not in self.treatment_data:
            self.treatment_data[treatment_id] = DataSingleTreatment(self.treatment_list[treatment_id])
        return self.treatment_data[treatment_id]

    def get_max_generation(self):
        if not self.max_generation:
            self.init_max_generation()
        return self.max_generation

    def get_min_generation(self):
        return 0
    
    def get_x_values(self, treatment, plot_id):
        #Read global data
        max_generation = getInt("max_generation")
        first_plot = getInt("to_plot")
        x_from_file = getBool("x_from_file")

        treatment_data = self.get_treatment_data(treatment)
        med_ci = treatment_data.get_median_and_ci(first_plot)
        if max_generation == MAX_GEN_NOT_PROVIDED or x_from_file:
            keys = sorted(med_ci.median.keys())
            return keys[0:len(med_ci.median.keys()):getInt("step")]
        else:
            return range(0, len(med_ci.median)*getInt("step"), getInt("step"))
            

    def get_comparison(self, treatment_id_1, treatment_id_2):
        if not self.comparison_cache:
            self.init_compare()
        if (treatment_id_1, treatment_id_2) not in self.comparison_cache:
            print("Error: no comparison entry for values" +
                  str((treatment_id_1, treatment_id_2)))
            return []
        return self.comparison_cache[(treatment_id_1, treatment_id_2)]

    def to_cache(self):
        #Read global data
        cache_file_name = getStr("comparison_cache")
        main_treatment_id = getInt("main_treatment")
        stat_test_step = getInt("stat_test_step")

        with open(cache_file_name, 'w') as cache_file:
            print ("Writing " + cache_file_name + "...")
            for entry in self.comparison_cache.iteritems():
                key, generations = entry
                other_treatment_id, plot_id = key
                cache_file.write(str(plot_id) + " ")
                cache_file.write(str(main_treatment_id) + " ")
                cache_file.write(str(other_treatment_id) + " ")
                cache_file.write(str(stat_test_step) + " ")
                for generation in generations:
                    cache_file.write(str(generation) + " ")
                cache_file.write("\n")

    def init_max_generation(self):
        #Read global data
        self.max_generation = getInt("max_generation")

        #Calculate max generation if necessary
        if self.max_generation == MAX_GEN_NOT_PROVIDED:
            for treatment in self.treatment_list:
                treatment_data = self.get_treatment_data(treatment)
                if treatment_data.get_max_generation() > self.max_generation:
                    self.max_generation = treatment_data.get_max_generation()

    def init_compare(self):
        #Read global data
        read_cache = getBool("read_cache") and getBool("read_comparison_cache")

        self.comparison_cache = DictOfLists()
        if read_cache:
            try:
                self.init_compare_from_cache()
                return
            except IOError:
                pass
            except CacheException:
                pass
        self.init_compare_from_data()

    def init_compare_from_cache(self):
        #Read global data
        plot_ids = getIntList("to_plot")
        comparison_cache_file_name = getStr("comparison_cache")
        main_treatment_id = getInt("main_treatment")
        stat_test_step = getInt("stat_test_step")

        with open(comparison_cache_file_name, 'r') as cache_file:
            print("Reading from comparison cache " +
                  comparison_cache_file_name + "...")

            #Read data from file
            for line in cache_file:
                numbers = line.split()
                if len(numbers) < 4:
                    raise CacheException("Entry does not have the right amount "
                                         "of numbers")
                plot_id_cache = int(numbers[0])
                main_treatment_id_cache = int(numbers[1])
                other_treatment_id_cache = int(numbers[2])
                stat_test_step_cache = int(numbers[3])
                if main_treatment_id != main_treatment_id_cache:
                    raise CacheException("Main treatment changed")
                if stat_test_step != stat_test_step_cache:
                    raise CacheException("Cache created with different step")
                key = (other_treatment_id_cache, plot_id_cache)
                self.comparison_cache.init_key(key)
                for i in xrange(4, len(numbers)):
                    self.comparison_cache.add(key, int(numbers[i]))

        for plot_id in plot_ids:
            for other_treatment in self.treatment_list:
                other_treatment_id = other_treatment.get_id()
                key = (other_treatment_id, plot_id)
                if other_treatment_id == main_treatment_id:
                    continue
                if key not in self.comparison_cache:
                    raise CacheException("Cache does not hold entries for all "
                                         "treatments")

    def init_compare_from_data(self):
        #Get global data
        plot_ids = getIntList("to_plot")
        main_treatment_id = getInt("main_treatment")
        stat_test_step = getInt("stat_test_step")
        write_cache = (getBool("write_cache") and
                       getBool("write_comparison_cache"))

        #Get main treatment
        main_treatment = self.treatment_list[main_treatment_id]

        #Compare data for all plots and all treatments
        main_data = self.get_treatment_data(main_treatment).get_raw_data()
        for plot_id in plot_ids:
            if plot_id not in main_data:
                print("Warning: no data available for plot", plot_id,
                      "treatment", main_treatment.get_name(), ", skipping...")
                continue

            for other_treat in self.treatment_list:
                other_data = self.get_treatment_data(other_treat).get_raw_data()
                other_treatment_id = other_treat.get_id()
                key = (other_treatment_id, plot_id)
                if other_treatment_id == main_treatment_id:
                    continue
                self.comparison_cache.init_key(key)
                debug_print("cache", "Comparing: " + str(other_treatment_id) +
                            " with " + str(main_treatment_id))

                if plot_id not in other_data:
                    print("Warning: no data available for plot", plot_id,
                          "treatment", other_treat.get_name(),
                          ", skipping...")
                    continue

                max_generation = self.get_max_generation()
                max_gen_main = main_data.get_max_generation(plot_id)
                max_gen_other = other_data.get_max_generation(plot_id)
                max_generation_available = min(max_gen_main, max_gen_other)
                                                               
                if max_generation_available < max_generation:
                    print ("Warning: data does extent until max generation: " +
                           str(max_generation))
                    print ("Maximum generation available is: " +
                           str(max_generation_available))
                    max_generation = max_generation_available

                main_gen = set(main_data[plot_id].keys())
                other_gen = set(other_data[plot_id].keys())
                generations = list(main_gen.intersection(other_gen))
                generations.sort()
                for generation in generations[::stat_test_step]:
                    data1 = main_data[plot_id][generation]
                    data2 = other_data[plot_id][generation]
                    p_value = mann_whitney_u(data1, data2)
                    print "Generation:", generation, "p-value:", p_value, "mean 1:", np.mean(data1), "mean 2:", np.mean(data2)
                    if p_value < 0.05:
                        self.comparison_cache.add(key, generation)
        if write_cache:
            self.to_cache()

######################
## HELPER FUNCTIONS ##
######################
def getSigMarker(compare_to_symbol):
    sig_marker = getStr("sig_marker", compare_to_symbol)
    try:
        matplotlib.markers.MarkerStyle(sig_marker)
    except ValueError:
        print "Warning: invalid significance marker, marker replaced with *."
        sig_marker = "*"
    return sig_marker 

def getMarker(compare_to_symbol):
    sig_marker = getStr("marker", compare_to_symbol)
    try:
        matplotlib.markers.MarkerStyle(sig_marker)
    except ValueError:
        print "Warning: invalid significance marker, marker replaced with *."
        sig_marker = "*"
    return sig_marker 

def getFgColor(compare_to_symbol):
    color = getStr("colors", compare_to_symbol)
    try: 
        matplotlib.colors.colorConverter.to_rgb(color)
    except ValueError:
        print "Warning: invalid treatment color, color replaced with grey."
        color = "#505050"
    return color

def getBgColor(compare_to_symbol):
    back_color = getStr("background_colors", compare_to_symbol)
    try: 
        matplotlib.colors.colorConverter.to_rgb(back_color)
    except ValueError:
        print "Warning: invalid background color, color replaced with grey."
        back_color = "#505050"
    return back_color


######################
# PLOTTING FUNCTIONS #
######################
def create_plots(data_of_interest):
    for plot_id in getIntList("to_plot"):
        create_plot(plot_id, data_of_interest)


def create_plot(plot_id, data_of_interest):
    for treatment in data_of_interest.get_treatment_list():
        plot_treatment(plot_id, treatment, data_of_interest)


def plot_treatment(plot_id, treatment, data_of_interest):
    #Get data
    max_generation = data_of_interest.get_max_generation()
    treatment_name = treatment.get_name()
    treatment_index = treatment.get_id()
    treatment_data = data_of_interest.get_treatment_data(treatment)
    mean_and_ci = treatment_data.get_median_and_ci(plot_id)

    marker = getMarker(treatment_index)
    marker_size = getFloat("marker_size")
    marker_offset = getInt("marker_offset", treatment_index)
    color = getFgColor(treatment_index)
    bg_color = getBgColor(treatment_index)

    debug_print("plot", "Max generation: " + str(max_generation))
    debug_print("plot", "Step: " + str(getInt("step")))

    print("For plot " + str(plot_id) + " plotting treatment: " +
          treatment.get_name())
    if len(mean_and_ci) == 0:
        print("Warning: no data available for plot", plot_id, "of treatment",
              treatment.get_name(), ", skipping.")
        return
        
    plot_mean = mean_and_ci.get_median_array()
    var_min = mean_and_ci.get_ci_min_array()
    var_max = mean_and_ci.get_ci_max_array()

    #Apply median filter
    plot_mean = median_filter(plot_mean, getInt("smoothing"))
    var_min = median_filter(var_min, getInt("smoothing"))
    var_max = median_filter(var_max, getInt("smoothing"))

    #Calculate plot markers
    data_step_x = data_of_interest.get_x_values(treatment, plot_id)
    debug_print("plot", "X len", len(data_step_x), "X data: ", data_step_x)
    debug_print("plot", "Y len", len(plot_mean), "Y data: ", plot_mean)
    assert(len(data_step_x) == len(plot_mean))

    if get("marker_step")[0] is not None:
        marker_step = getInt("marker_step")
    else:
        marker_step = max_generation / 10
        if marker_step < 1:
            marker_step = 1
    adj_marker_step = marker_step/getInt("step")
    adjusted_marker_offset = marker_offset/getInt("step")

    #Debug statements
    debug_print("plot", "Marker step: " + str(marker_step) +
                " adjusted: " + str(adj_marker_step))
    debug_print("plot", "Marker offset: " + str(marker_offset) +
                " adjusted: " + str(adjusted_marker_offset))

    #Calculate markers
    plot_marker_y = plot_mean[adjusted_marker_offset:len(plot_mean):adj_marker_step]
    plot_marker_x = data_step_x[adjusted_marker_offset:len(plot_mean):adj_marker_step]
    
    #Debug statements
    debug_print("plot", "Plot marker X len", len(plot_marker_x),
                "X data: ", plot_marker_x)
    debug_print("plot", "Plot marker Y len", len(plot_marker_y),
                "Y data: ", plot_marker_y)
    assert(len(plot_marker_x) == len(plot_marker_y))

    #Calculate data step

    #if getBool("y_from_file"):
    #    data_step_x = sorted(data_of_interest.get_raw_data()[plot_id].keys())
    #else:
    #    data_step_x = range(0, len(plot_mean)*getInt("step"), getInt("step"))

    #Plot mean
    plt.figure(int(plot_id))    

    #The actual median
    plt.plot(data_step_x, plot_mean, color=color, linewidth=LINE_WIDTH,
             linestyle="-")

    #Fill confidence interval
    plt.fill_between(data_step_x, var_min, var_max, edgecolor=bg_color,
                     facecolor=bg_color, alpha=FILL_ALPHA, linewidth=NO_LINE)  

    #Markers used on top of the line in the plot
    plt.plot(plot_marker_x, plot_marker_y,
             color=color,
             linewidth=NO_LINE,
             marker=marker,
             markersize=marker_size)

    #Markers used in the legend
    #To plot the legend markers, plot a point completely outside of the plot.
    plt.plot([data_step_x[0] - max_generation], [0], color=color,
             linewidth=LINE_WIDTH, linestyle="-", marker=marker,
             label=treatment_name, markersize=marker_size)



def plot_significance(gs, data_intr):
    max_generation = data_intr.get_max_generation()
    min_generation = data_intr.get_min_generation()
    nr_of_treatments = len(data_intr.get_treatment_list())
    main_treatment = data_intr.get_treatment_list()[getInt("main_treatment")]

    print("Calculating significance...")
    for i in xrange(len(getList("to_plot"))):
        print("  Calculating significance for plot: " + str(i))
        sig_label = getStr("sig_label")
        sig_label = sig_label.replace('\\n', '\n')
        lbl = sig_label + main_treatment.get_name_short()
        #f = plt.figure(getInt("to_plot", i))
        #r = f.canvas.get_renderer()
        #t = plt.text(0.5, 0.5, lbl)
        #bb = t.get_window_extent(renderer=r)
        #print(bb.width)
        #print(bb.height)
        ax = plt.subplot(gs[1])
        ax.set_xlim(0, max_generation)
        ax.get_yaxis().set_ticks([])
        ax.set_ylim(0.5, nr_of_treatments-0.5)
        ax.set_ylabel(lbl,
                      rotation='horizontal',
                      fontsize=getInt("tick_font_size"),
                      horizontalalignment='right')
        #lbl_x = (-bb.width/1200.0) + getFloat("comparison_offset_x")
        #lbl_x = 0
        ax.get_yaxis().set_label_coords(getFloat("comparison_offset_x"),
                                        getFloat("comparison_offset_y"))
        ax.set_xlabel(getStrDefaultFirst("x_labels", i))
        ax.tick_params(bottom=True, top=False)
        odd = True
        ast_height = 0
        for compare_to in xrange(nr_of_treatments-1, -1, -1):
            if compare_to == getInt("main_treatment"):
                continue
            compare_to_symbol = compare_to
            ast_height += 1

            sig_marker = getStr("sig_marker", compare_to_symbol)
            color = getStr("colors", compare_to_symbol)
            back_color = getStr("background_colors", compare_to_symbol)

            try:
                matplotlib.markers.MarkerStyle(sig_marker)
            except ValueError:
                print "Warning: invalid marker, marker replaced with *."
                sig_marker = "*"

            try: 
                matplotlib.colors.colorConverter.to_rgb(color)
            except ValueError:
                print "Warning: invalid treatment color, replaced with grey."
                color = "#505050"

            try: 
                matplotlib.colors.colorConverter.to_rgb(back_color)
            except ValueError:
                print "Warning: invalid background color, replaced with grey."
                back_color = "#505050"

            #Add the background box
            pol_top = ast_height+0.5
            pol_bot = ast_height-0.5
            box = Polygon([(min_generation, pol_bot),
                           (min_generation, pol_top),
                           (max_generation, pol_top),
                           (max_generation, pol_bot)],
                          facecolor=back_color,
                          zorder=-100)
            ax.add_patch(box)

            #Add the line separating the treatments
            ax.plot([min_generation, max_generation],
                    [ast_height-0.5,ast_height-0.5],
                    color='black',
                    linestyle='-',
                    linewidth=1.0,
                    solid_capstyle="projecting")

            comparison = data_intr.get_comparison(compare_to,
                                                  getInt("to_plot", i))
            for index in comparison:
                ax.scatter(index,
                        ast_height,
                        marker=sig_marker,
                        c=color,
                        s=50)
            if odd:
                offset = max_generation*1.015
            else:
                offset = max_generation*1.040
                ax.plot([max_generation, offset],
                        [ast_height, ast_height],
                        color='black',
                        linestyle='-',
                        linewidth=1.0,
                        solid_capstyle="projecting",
                        clip_on=False, 
                        zorder=90)
            ax.scatter(offset, ast_height, marker=sig_marker, c=color, s=100,
                       clip_on=False, zorder=100)
            odd = not odd
    print("Calculating significance done.")


######################
### CONFIGURE PLOTS ##
######################
def setup_plots(nr_of_generations):
    """
    A setup for the different plots 
    (both the main plot and the small bar at the bottom).
    """

    # Setup the matplotlib params
    preamble=[r'\usepackage[T1]{fontenc}',
              r'\usepackage{amsmath}',
              r'\usepackage{txfonts}',
              r'\usepackage{textcomp}']
    matplotlib.rc('font', **{'family':'sans-serif', 'sans-serif':['Helvetica']})
    matplotlib.rc('text.latex', preamble=preamble)
    params = {'backend': 'pdf',
              'axes.labelsize': getInt("font_size"),
              'font.size': getInt("font_size"),
              'legend.fontsize': getInt("legend_font_size"),
              'xtick.labelsize': getInt("tick_font_size"),
              'ytick.labelsize': getInt("tick_font_size"),
              'text.usetex': latex_available()}
    matplotlib.rcParams.update(params)

    # If we want to plot significance indicators we have to make an additional
    # box below the plot
    if getBool("sig"):
        gs = gridspec.GridSpec(2, 1, height_ratios=[10, getFloat("box_height")])
        gs.update(hspace=getFloat("box_sep"))
    else:
        gs = gridspec.GridSpec(1, 1)

    # Set all labels and limits for the main window (gs[0])
    for i in xrange(len(getList("to_plot"))):
        plot_id = getInt("to_plot", i)
        fig = plt.figure(plot_id,  figsize=getFloatPair("fig_size"))
        ax = fig.add_subplot(gs[0])
        ax.set_ylabel(getStr("y_labels", i))
        if getExists("y_axis_min", i) and getExists("y_axis_max", i):
            ax.set_ylim(getFloat("y_axis_min", i), getFloat("y_axis_max", i))
        x_max = nr_of_generations
        x_min = 0
        if getExists("x_axis_max"): x_max = getFloat("x_axis_max")
        if getExists("x_axis_min"): x_min = getFloat("x_axis_min")
        ax.set_xlim(x_min, x_max)
        ax.set_xlabel(getStrDefaultFirst("x_labels", i))
        if getBool("sig"): 
            ax.tick_params(labelbottom=False)
            ax.set_xlabel("")
        else:
            ax.set_xlabel(getStrDefaultFirst("x_labels", i))
        if getBool("title"):
            plt.title(getStr("titles", i), fontsize=getInt("title_size"))
        if getExists("x_ticks"):
            ax.set_xticks(getIntList("x_ticks"))
        ax.tick_params(axis='x', bottom='off')

    return gs


def write_plots():
    print("Writing plots...")
    output_dir = getStr("output_directory")
    ext = "." + getStr("type")

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for i in xrange(len(getList("to_plot"))):
        print("Writing plot " + str(i) + " ...")
        fig = plt.figure(getInt("to_plot", i))
        ax = fig.get_axes()[0]
        if getFloat("box_sep") == 0:
            plt.tight_layout()
        if getStr("legend_loc", i) != "none":
            loc = getStr("legend_loc", i)
            columns = getInt("legend_columns")
            anchor_x = getFloat("legend_x_offset")
            anchor_y = getFloat("legend_y_offset")
            debug_print("legend", "location:", loc, "columns:", columns ,
                        "anchor x:", anchor_x, "anchor y:", anchor_y)
            lgd = ax.legend(loc=loc, ncol=columns,
                            bbox_to_anchor=(anchor_x, anchor_y, 1, 1))
            if lgd:
                plt.savefig(output_dir + "/" + getStr("file_names", i) + ext,
                            bbox_extra_artists=(lgd,), bbox_inches='tight')
            else:
                print "Warning: insufficient data to create legend."
                plt.savefig(output_dir + "/" + getStr("file_names", i) + ext,
                            bbox_inches='tight')
        else:
            plt.savefig(output_dir + "/" + getStr("file_names", i) + ext)
        print("Writing plot " + str(i) + " done.")


######################
#### PARSE OPTIONS ###
######################
def parse_options():
    parse_global_options()

    treatment_list = TreatmentList()
    for i in xrange(len(getList("input_directories"))):
        if getBool("one_value_per_dir"):
            if len(treatment_list) < 1:
                treatment_list.add_treatment(getStr("input_directories", i),
                                             getStr("treatment_names", i),
                                             getStr("treatment_names_short", i))
            else:
                treatment_list[0].add_dir(getStr("input_directories", i))
        else:
            treatment_list.add_treatment(getStr("input_directories", i),
                                         getStr("treatment_names", i),
                                         getStr("treatment_names_short", i))

    for i in xrange(len(getList("file"))):
        treatment_list.add_treatment(getStr("file", i),
                                     getStr("treatment_names", i),
                                     getStr("treatment_names_short", i))

    if len(treatment_list) < 1:
        print "No treatments provided"
        sys.exit(1)

    if len(treatment_list) == 1:
        setGlb("sig", [False])

    if not getExists("comparison_cache"):
        setGlb("comparison_cache",
               [getStr("output_directory") + "/comparison.cache"])

    data_intr = DataOfInterest(treatment_list)

    if not getExists("marker_step"):
        setGlb("marker_step", [int(data_intr.get_max_generation()/10)])

    return treatment_list, data_intr


######################
######## MAIN ########
######################
def main():
    treatment_list, data_of_interest = parse_options()
    gs = setup_plots(data_of_interest.get_max_generation())

    #Plot all treatments
    create_plots(data_of_interest)

    #Plots the dots indicating significance
    if getBool("sig"):
        plot_significance(gs, data_of_interest)

    #Writes the plots to disk
    write_plots()


if __name__ == '__main__':
    main()
