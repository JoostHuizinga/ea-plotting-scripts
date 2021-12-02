#!/usr/bin/env python
import os.path

import math
import sys
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.colors
import matplotlib.cm
from scipy.optimize import curve_fit
from scipy.stats.stats import pearsonr
import createPlotUtils as util
import global_options as go
import parse_file as pf
import treatment_list as tl
import configure_plots as cp


# Derived defaults
def def_output_dir(): return pf.base(go.get_str("config_file")) + "_out"


def def_y_data_columns(): return go.get_list("to_plot")


def def_input(): return go.get_list("input_directories")


def def_xticks():
    if go.get_bool("one_plot_per_treatment"):
        return [go.get_str_list('treatment_names', i) for i in go.get_indices("treatment_names")]
    else:
        return [[go.get_str('treatment_names', i) for i in go.get_indices("treatment_names")]]


def def_legend_font_size(): return go.get_int("font_size") - 4


def def_title_font_size(): return go.get_int("font_size") + 4


def def_tick_font_size(): return go.get_int("font_size") - 6


###################
##### CLASSES #####
###################
class MedianAndCI:
    def __init__(self):
        self.median_and_ci = dict()

    def __getitem__(self, column):
        return self.median_and_ci[column]

    def __setitem__(self, column, y_value):
        self.median_and_ci[column] = y_value

    def keys(self):
        return self.median_and_ci.keys()

    def add(self, column, x_value, median, ci_min, ci_max, nr_of_items):
        if column not in self.median_and_ci:
            self.median_and_ci[column] = dict()
        self.median_and_ci[column][x_value] = (median, ci_min, ci_max, nr_of_items)

    def to_cache(self, cache_file_name):
        with open(cache_file_name, 'w') as cache_file:
            print("Writing " + cache_file_name + "...")
            for column in self.keys():
                median_array = self.get_median_array(column)
                ci_min_array = self.get_ci_min_array(column)
                ci_max_array = self.get_ci_max_array(column)
                nr_of_items_array = self.get_ci_max_array(column)
                cache_file.write(str(column) + " ")
                for i in range(len(median_array)):
                    cache_file.write(str(median_array[i]) + " ")
                    cache_file.write(str(ci_min_array[i]) + " ")
                    cache_file.write(str(ci_max_array[i]) + "\n")
                    cache_file.write(str(nr_of_items_array[i]) + "\n")

    def get_median_array(self, column):
        local_list = []
        sorted_keys = sorted(self.median_and_ci[column].keys())
        for key in sorted_keys:
            local_list.append(self.median_and_ci[column][key][0])
        return np.array(local_list)

    def get_ci_min_array(self, column):
        local_list = []
        sorted_keys = sorted(self.median_and_ci[column].keys())
        for key in sorted_keys:
            local_list.append(self.median_and_ci[column][key][1])
        return np.array(local_list)

    def get_ci_max_array(self, column):
        local_list = []
        sorted_keys = sorted(self.median_and_ci[column].keys())
        for key in sorted_keys:
            local_list.append(self.median_and_ci[column][key][2])
        return np.array(local_list)

    def get_nr_of_items_array(self, column):
        local_list = []
        sorted_keys = sorted(self.median_and_ci[column].keys())
        for key in sorted_keys:
            local_list.append(self.median_and_ci[column][key][3])
        return np.array(local_list)


class RawData:
    def __init__(self):
        self.x_data_raw = dict()
        self.x_data_binned = dict()
        self.y_data = dict()
        self.map = dict()

    def get_x_data(self, y_data_column):
        return self.x_data_binned[y_data_column]

    def get_x_data_raw(self, y_data_column):
        return self.x_data_raw[y_data_column]

    def get_y_data(self, y_data_column):
        return self.y_data[y_data_column]

    def add(self, y_data_column, x_value, y_value):
        bin_greater_than = go.get_any("bin_greater_than")
        x_bin_size = go.get_float("x_bin_size")

        if y_data_column not in self.x_data_raw:
            self.x_data_raw[y_data_column] = list()
        if y_data_column not in self.x_data_binned:
            self.x_data_binned[y_data_column] = list()
        if y_data_column not in self.y_data:
            self.y_data[y_data_column] = list()
        if y_data_column not in self.map:
            self.map[y_data_column] = dict()

        self.x_data_raw[y_data_column].append(x_value)

        if bin_greater_than is not None:
            bin_greater_than = float(bin_greater_than)
            if x_value > bin_greater_than:
                x_value = bin_greater_than

        if x_bin_size > 0:
            bin_nr = math.ceil(x_value / x_bin_size)
            x_value = bin_nr * x_bin_size

        self.x_data_binned[y_data_column].append(x_value)
        self.y_data[y_data_column].append(y_value)
        if x_value not in self.map[y_data_column]:
            self.map[y_data_column][x_value] = list()
        self.map[y_data_column][x_value].append(y_value)

    def get(self, y_data_column, x_value):
        return self.map[y_data_column][x_value]

    def merge(self, other):
        for y_data_column in self.map:
            self.x_data_raw[y_data_column].append(other.x_data_raw[y_data_column])
            self.x_data_binned[y_data_column].append(other.x_data_binned[y_data_column])
            self.y_data[y_data_column].append(other.y_data[y_data_column])
            for key in other.map[y_data_column]:
                self.map[y_data_column][key] = other.map[y_data_column][key]


class DataSingleTreatment:
    def __init__(self, treatment):
        self.treatment = treatment
        self.raw_data = None
        self.median_and_ci = dict()
        # self.max_generation = None
        self.max_x = None
        self.min_x = None

    def get_raw_data(self):
        if not self.raw_data:
            self.init_raw_data()
        return self.raw_data

    def get_median_and_ci(self):
        if not self.median_and_ci:
            self.init_median_and_ci()
        return self.median_and_ci

    def get_max_x(self):
        if self.max_x is None:
            self.init_raw_data()
        return self.max_x

    def get_min_x(self):
        if self.min_x is None:
            self.init_raw_data()
        return self.min_x

    def init_raw_data(self):
        # Read global data
        separator = go.get_str("separator")
        parse_last_line = go.get_bool("parse_last_line")
        generation_based_file = go.get_exists("max_generation")
        generation = go.get_int("max_generation")

        # Init raw data
        self.raw_data = RawData()

        for file_name in self.treatment.files:
            with open(file_name, 'r') as separated_file:
                print("Reading raw data from " + file_name + "...")

                # If the first line of the file is a header line, skip it, otherwise start from the beginning again.
                first_line = separated_file.readline()
                if not pf.is_header_line(first_line):
                    util.debug_print("input", "skipping header")
                    separated_file.seek(0)
                if parse_last_line:
                    # Parse only the last line of the input files,
                    # useful to plot the properties of the last generation
                    # of an evolutionary run.
                    util.debug_print("input", "parsing last line only")
                    for line in separated_file:
                        last_line = line
                    self._add_raw_data(last_line.split(separator))
                elif generation_based_file:
                    # Parse the file, assuming that the first number on each line indicates the current generation
                    util.debug_print("input", "parsing as generation based file")
                    for line in separated_file:
                        split_line = line.split(separator)
                        if int(split_line[0]) == generation:
                            self._add_raw_data(line.split(separator))
                else:
                    # Parse the entire file as raw data without making any assumptions
                    util.debug_print("input", "parsing as raw data")
                    for line in separated_file:
                        self._add_raw_data(line.split(separator))

    def _add_raw_data(self, split_line):
        # Read global data
        read_x_data = go.get_exists("x_data_column")
        x_data_column = go.get_int("x_data_column")
        y_data_columns = go.get_int_list("y_data_column")
        one_plot_per_treatment = go.get_bool("one_plot_per_treatment")

        if x_data_column >= 0 and read_x_data:
            x_value = float(split_line[x_data_column])
        elif one_plot_per_treatment:
            x_value = 0
        else:
            x_value = self.treatment.get_id()
        if self.max_x is None or self.max_x < x_value:
            self.max_x = x_value
        if self.min_x is None or self.min_x > x_value:
            self.min_x = x_value
        for y_data_column in y_data_columns:
            self.raw_data.add(y_data_column, x_value, float(split_line[int(y_data_column)]))

    def init_median_and_ci(self):
        # Get global data
        self.init_median_and_ci_from_data()

    def init_median_and_ci_from_data(self):
        # Read global data
        bootstrap = go.get_bool("bootstrap")
        plot_means = go.get_bool("plot_means")

        # Initialize empty median and ci
        self.median_and_ci = MedianAndCI()

        # Calculate median and confidence intervals
        for column in self.get_raw_data().map.keys():
            for key in self.get_raw_data().map[column].keys():
                item = self.get_raw_data().map[column][key]
                util.debug_print("input", "calculating median and ci over:", item)
                if bootstrap:
                    if plot_means:
                        median, ci_min, ci_max = util.calc_stats(item, "mean_and_bootstrap_pivotal")
                    else:
                        median, ci_min, ci_max = util.calc_stats(item, "median_and_bootstrap_pivotal")

                else:
                    if plot_means:
                        median, ci_min, ci_max = util.calc_mean_and_std_error(item)
                    else:
                        median, ci_min, ci_max = util.calc_median_and_interquartile_range(item)
                util.debug_print("input", "median:", median, "ci:", ci_min, ci_max)
                self.median_and_ci.add(column, key, median, ci_min, ci_max, len(item))

    def merge(self, other):
        self.raw_data = self.get_raw_data()
        other_raw_data = other.get_raw_data()
        self.raw_data.merge(other_raw_data)
        self.median_and_ci = self.get_median_and_ci()
        for column in other.get_median_and_ci().keys():
            for key in other.get_median_and_ci()[column].keys():
                self.median_and_ci[column][key] = other.get_median_and_ci()[column][key]
        # self.max_generation = max(self.max_generation, other.max_generation)
        self.max_x = max(self.max_x, other.max_x)
        self.min_x = min(self.min_x, other.min_x)


class DataOfInterest:
    def __init__(self, treatment_list):
        self.treatment_list = treatment_list
        self.treatment_data = dict()
        self.comparison_cache = None
        # self.max_generation = None

    def get_treatment_list(self):
        return self.treatment_list

    def get_treatment(self, treatment_id):
        return self.treatment_list[treatment_id]

    def get_treatment_data(self, treatment):
        treatment_id = treatment.get_id()
        if treatment_id not in self.treatment_data:
            self.treatment_data[treatment_id] = DataSingleTreatment(self.treatment_list[treatment_id])
        return self.treatment_data[treatment_id]

    def merge_treatment_data(self):
        merged_data = DataSingleTreatment(self.treatment_list[0])
        for treatment_index in range(1, len(self.treatment_list)):
            merged_data.merge(self.get_treatment_data(self.treatment_list[treatment_index]))
        return merged_data


######################
# PLOTTING FUNCTIONS #
######################
def func(x, a, b, c):
    return a * np.exp(-b * x) + c


def create_barplot(treatment_list, data_single_treatment, plot_id):
    column = go.get_int("y_data_column", plot_id, when_not_exist=go.RETURN_FIRST)
    # x_data_column = go.get_int("x_data_column", plot_id, when_not_exist=go.RETURN_FIRST)
    # set_y_lim = go.get_exists("y_axis_min") or go.get_exists("y_axis_max")
    # y_min = go.get_float("y_axis_min", plot_id, when_not_exist=go.RETURN_FIRST)
    # y_max = go.get_float("y_axis_max", plot_id, when_not_exist=go.RETURN_FIRST)
    set_x_lim = go.get_exists("x_axis_min") or go.get_exists("x_axis_max")
    x_min = go.get_float("x_axis_min", plot_id, when_not_exist=go.RETURN_FIRST, default=None)
    x_max = go.get_float("x_axis_max", plot_id, when_not_exist=go.RETURN_FIRST, default=None)
    # outputFileName = go.get_str("output", plot_id)
    use_color_map = go.get_bool("add_color_map")
    perform_linear_fit = go.get_bool("linear_fit")
    perform_curve_fit = go.get_bool("curve_fit")
    calculate_pearson_correlation = go.get_bool("pearson_correlation")
    color_map = go.get_str("color_map")
    one_plot_per_treatment = go.get_bool("one_plot_per_treatment")
    set_x_labels = go.get_exists("x_tick_labels")
    colors_provided = go.get_exists("colors")
    if one_plot_per_treatment:
        x_labels = go.get_str_list("x_tick_labels", plot_id)
        provided_colors = go.get_str_list("colors", plot_id)
    else:
        x_labels = go.get_str_list("x_tick_labels")
        provided_colors = [go.get_str("colors", i) for i in go.get_indices("colors")]
    x_bin_size = go.get_float("x_bin_size")
    bar_width = go.get_float("bar_width")
    bar_align = go.get_str("bar_align")
    nr_of_treatments = len(treatment_list)
    align_ticks = go.get_bool("align_ticks")
    tick_rotation = go.get_float("tick_rotation")
    output_dir = go.get_str("output_directory")
    nr_of_bars = len(data_single_treatment.get_median_and_ci().get_nr_of_items_array(column))

    # Setup plot details
    # fig, ax = setup_plot(plot_id)
    fig = plt.figure(plot_id)
    ax = fig.gca()

    # Set defaults
    if not one_plot_per_treatment and not set_x_lim:
        x_min = -x_bin_size / 2
        x_max = (nr_of_treatments - 1) + x_bin_size / 2
        set_x_lim = True
    elif not set_x_lim:
        x_min = min(data_single_treatment.get_median_and_ci()[column].keys()) - x_bin_size / 2
        x_max = max(data_single_treatment.get_median_and_ci()[column].keys()) + x_bin_size / 2
        set_x_lim = True

    # Normal
    # if set_y_lim:
    #     plt.ylim([y_min, y_max])
    if set_x_lim:
        plt.xlim([x_min, x_max])
    plt.xticks(np.arange(x_min + x_bin_size/2, x_max, x_bin_size))

    if set_x_labels or align_ticks:
        candidate_ticks = sorted(data_single_treatment.get_median_and_ci()[column].keys())
        actual_ticks = []
        for candidate_tick in candidate_ticks:
            if (x_min is None or candidate_tick >= x_min) and (x_max is None or candidate_tick <= x_max):
                actual_ticks.append(candidate_tick)
        plt.xticks(np.array(actual_ticks))
    plt.xticks(rotation=tick_rotation, ha='center')
    # ax = plt.gca()
    # help(ax.tick_params)align_ticks
    # ax.tick_params(direction='out', pad=15)
    # for tick in ax.xaxis.get_major_ticks():
    #    print tick.label1.get_text()
    #    tick.label1.set_text(tick.label1.get_text() + "\n\n\n")
    # Zoom
    # plt.ylim([0.235, 0.36])
    # plt.xlim([0.0, 10.0])

    # Set color map
    if use_color_map:
        util.debug_print("color", "Colormap:", color_map)
        # normalize_class = mpl.colors.Normalize()
        normalize_class = matplotlib.colors.LogNorm()
        bin_size_array = data_single_treatment.get_median_and_ci().get_nr_of_items_array(column)
        colorMap = matplotlib.cm.ScalarMappable(norm=normalize_class, cmap=color_map)
        colorMap.set_array(bin_size_array)
        colors = colorMap.to_rgba(bin_size_array)
        color_bar = plt.colorbar(colorMap)
        color_bar.set_label("Number of Images")
    elif colors_provided:
        colors = provided_colors
        while len(colors) < nr_of_bars:
            colors.append("#000082")
    else:
        colors = [0.0, 0.0, 0.8, 1.0] * nr_of_bars

    # Create bar plot
    x_axis = np.array(sorted(data_single_treatment.get_median_and_ci()[column].keys()))
    y_data = data_single_treatment.get_median_and_ci().get_median_array(column)
    ci_lower = y_data - data_single_treatment.get_median_and_ci().get_ci_min_array(column)
    ci_upper = data_single_treatment.get_median_and_ci().get_ci_max_array(column) - y_data
    # if one_plot_per_treatment: x_axis += (bar_width/2)

    util.debug_print("data", "x-data:", x_axis)
    util.debug_print("data", "y-data:", y_data)
    util.debug_print("data", "bar_width:", bar_width)

    rects1 = ax.bar(x_axis, y_data, bar_width, color=colors, yerr=[ci_lower, ci_upper], align=bar_align)
    plt.axhline(0, color='black')

    # Perform linear fit
    if perform_linear_fit:
        x_data = data_single_treatment.get_raw_data().get_x_data_raw(column)
        y_data = data_single_treatment.get_raw_data().get_y_data(column)
        z = np.polyfit(x_data, y_data, 1)
        p = np.poly1d(z)
        max_x = data_single_treatment.get_max_x() + 1
        linear_fit = plt.plot([x_min, max_x], [p(x_min), p(max_x)], "k-", label='Linear fit')

    # Perform curve fit
    if perform_curve_fit:
        x_data = data_single_treatment.get_raw_data().get_x_data(column)
        y_data = data_single_treatment.get_raw_data().get_y_data(column)
        x_axis_array = np.array(x_data)
        y_axis_array = np.array(y_data)
        popt, pcov = curve_fit(func, x_axis_array, y_axis_array)
        x_axis_array_assymp = np.arange(0, max_x, 0.1)
        y_fit = func(x_axis_array_assymp, *popt)
        exponential_fit = plt.plot(x_axis_array_assymp, y_fit, "g-", label='Exponential fit')

    # Calculate correlation
    if calculate_pearson_correlation:
        correlation_coefficient, two_tailed_p_value = pearsonr(x_data, y_data)
        print("Correlation coefficient: ", correlation_coefficient, " P-value: ", two_tailed_p_value)
        with open(output_dir + '/statistics.txt', 'w') as output_file:
            output_file.write("Correlation coefficient: ")
            output_file.write(str(correlation_coefficient))
            output_file.write(" P-value: ")
            output_file.write(str(two_tailed_p_value))

    # Setup plot details
    if perform_linear_fit or perform_curve_fit:
        if go.get_exists("legend_loc", plot_id) and go.get_str("legend_loc", plot_id) != "none":
            plt.legend(loc=go.get_str("legend_loc", plot_id))

    if set_x_labels:
        ax.set_xticklabels(x_labels)
    return fig


######################
#   CONFIGURE PLOTS  #
######################
# def setup_plot(plot_id):
#     """A setup for the different plots"""
#
#     # Setup the matplotlib params
#     preamble = [r'\usepackage[T1]{fontenc}',
#                 r'\usepackage{amsmath}',
#                 r'\usepackage{txfonts}',
#                 r'\usepackage{textcomp}']
#     matplotlib.rc('font', **{'family': 'sans-serif', 'sans-serif': ['Helvetica']})
#     matplotlib.rc('text.latex', preamble=preamble)
#     params = {'backend': 'pdf',
#               'axes.labelsize': go.get_int("font_size"),
#               'font.size': go.get_int("font_size"),
#               'legend.fontsize': go.get_int("legend_font_size"),
#               'xtick.labelsize': go.get_int("tick_font_size"),
#               'ytick.labelsize': go.get_int("tick_font_size"),
#               'text.usetex': util.latex_available()}
#     matplotlib.rcParams.update(params)
#
#     fig, ax = plt.subplots(figsize=go.get_float_list("fig_size"))
#     if go.get_exists("y_labels", plot_id):
#         ax.set_ylabel(go.get_str("y_labels", plot_id))
#     if go.get_exists("x_labels", plot_id):
#         ax.set_xlabel(go.get_str("x_labels", plot_id))
#     if go.get_bool("title") and go.get_exists("titles", plot_id):
#         plt.title(go.get_str("titles", plot_id), fontsize=go.get_int("title_size"))
#     return fig, ax


def write_plot(fig, filename):
    fig.set_tight_layout(True)
    print("Writing plot to:", filename)
    fig.savefig(filename)


def add_options():
    tl.add_options()
    pf.add_options()
    cp.add_options()

    # Directory settings
    # go.add_option("templates", ".*")
    # go.add_option("output_directory", def_output_dir, nargs=1)

    # General plot settings
    # go.add_option("title", True)
    # go.add_option("titles", "")
    # go.add_option("x_labels")
    # go.add_option("y_labels")
    # go.add_option("y_axis_min")
    # go.add_option("y_axis_max")
    # go.add_option("x_axis_min")
    # go.add_option("x_axis_max")
    go.add_option("to_plot", 1)
    # go.add_option("file_names")
    go.add_option("max_generation")
    go.add_option("parse_last_line", False)
    go.add_option("x_data_column")
    go.add_option("y_data_column", def_y_data_columns)
    # go.add_option("legend_loc", "upper right")
    # go.add_option("input_directories")
    go.add_option("input", def_input)
    go.add_option("output", "")
    # go.add_option("colors")
    # go.add_option("fig_size", [8, 6])
    # go.add_option("separator", " ")
    go.add_option("bootstrap", False)
    # go.add_option("treatment_names")
    go.add_option("x_tick_labels", def_xticks)
    go.add_option("align_ticks", False)
    go.add_option("linear_fit", False)
    go.add_option("curve_fit", False)
    go.add_option("pearson_correlation", False)
    go.add_option("bin_greater_than", None)
    go.add_option("color_map", "jet")
    go.add_option("add_color_map", False)
    go.add_option("x_bin_size", 1.0)
    go.add_option("bar_width", 0.7)
    go.add_option("plot_means", False)
    go.add_option("bar_align", "center")
    go.add_option("one_plot_per_treatment", False)
    go.add_option("tick_rotation", 0)

    # Font settings
    # go.add_option("font_size", 18, nargs=1)
    # go.add_option("title_size", def_title_font_size, nargs=1)
    # go.add_option("legend_font_size", def_legend_font_size, nargs=1)
    # go.add_option("tick_font_size", def_tick_font_size, nargs=1)


def init_options():
    go.init_options("Script for creating bar-plots.", "[input [input ...]] [OPTIONS]", "2.0")
    add_options()


######################
#    PARSE OPTIONS   #
######################
def parse_options(command_line_args):
    go.parse_global_options(command_line_args)
    treatment_list = tl.read_treatments()

    # treatment_list = util.TreatmentList()
    # for i in range(len(go.get_list("input"))):
    #     input_dir = go.get_str("input", i)
    #     treat_name = go.get_str("treatment_names", i)
    #     treat_name_s = go.get_str("treatment_names_short", i)
    #     treatment_list.add_treatment(input_dir, treat_name, treat_name_s)

    if len(treatment_list) < 1:
        print("No treatments provided")
        sys.exit(1)

    data_of_interest = DataOfInterest(treatment_list)

    return treatment_list, data_of_interest


def create_plots(data_of_interest, treatment_list):
    cp.init_params()

    output_dir = go.get_str("output_directory")
    one_plot_per_treatment = go.get_bool("one_plot_per_treatment")
    nr_of_columns = len(go.get_list("y_data_column"))

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for plot_id in range(nr_of_columns):
        if one_plot_per_treatment:
            for treatment_nb, treatment in enumerate(treatment_list):
                print("Writing plot for treatment:", treatment)
                l_plot_id = plot_id * len(treatment_list) + treatment_nb
                print("file_names:", go.get_glb("file_names"), "plot_id:", l_plot_id)
                plot_config = cp.setup_figure(l_plot_id)
                cp.setup_plot(plot_config)
                fig = create_barplot(treatment_list, data_of_interest.get_treatment_data(treatment), l_plot_id)

                # write_plot(fig, output_dir + "/" + go.get_str("file_names", l_plot_id) + ".pdf")
                cp.write_plot(plot_config)
        else:
            plot_config = cp.setup_figure(plot_id)
            cp.setup_plot(plot_config)
            fig = create_barplot(treatment_list, data_of_interest.merge_treatment_data(), plot_id)
            # write_plot(fig, output_dir + "/" + go.get_str("file_names", plot_id) + ".pdf")
            cp.write_plot(plot_config)


def execute_plots(command_line_args):
    treatment_list, data_of_interest = parse_options(command_line_args)

    # Plot all treatments
    create_plots(data_of_interest, treatment_list)


######################
#        MAIN        #
######################
def main():
    init_options()
    execute_plots(sys.argv[1:])

    # output_dir = go.get_str("output_directory")
    # one_plot_per_treatment = go.get_bool("one_plot_per_treatment")
    # nr_of_columns = len(go.get_list("y_data_column"))
    #
    # if not os.path.exists(output_dir):
    #     os.makedirs(output_dir)

    # for plot_id in range(nr_of_columns):
    #     if one_plot_per_treatment:
    #         for treatment in treatment_list:
    #             fig = createBarplot(data_of_interest.get_treatment_data(treatment), plot_id)
    #             write_plot(fig, output_dir + "/" + go.get_str("file_names", plot_id) + ".pdf")
    #     else:
    #         fig = createBarplot(data_of_interest.merge_treatment_data(), plot_id)
    #         write_plot(fig, output_dir + "/" + go.get_str("file_names", plot_id) + ".pdf")


if __name__ == '__main__':
    main()
