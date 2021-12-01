#!/usr/bin/env python3
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.markers
import matplotlib.colors
from matplotlib.patches import Polygon
import treatment_list as tl
import parse_file as pf
import configure_plots as cp
import global_options as go
from createPlotUtils import *

__author__ = "Joost Huizinga"
__version__ = "2.0 (Dec. 1 2021)"

# Constants
MAX_GEN_NOT_PROVIDED = -1
NO_LINE = 0
LINE_WIDTH = 2
FILL_ALPHA = 0.5


def def_comp_cache(): return pf.base(go.get_str("config_file")) + ".cache"


def def_box_height(): return max((len(go.get_list("input_directories")) - 1) * 0.35, 0.5)


def def_marker_step():
    if go.get_int("max_generation") > 5:
        return go.get_int("max_generation") / 5
    else:
        return None


def def_marker_offset():
    marker_step = go.get_int("marker_step")
    if marker_step == 0 or marker_step is None:
        marker_step = 1
    num_treatments = len(go.get_indices("input_directories")) + len(go.get_indices("file"))
    if num_treatments < 1:
        num_treatments = 1
    step = marker_step / num_treatments
    if step < 1:
        step = 1
    return list(range(0, marker_step, int(step)))


def def_sig_marker(): return [go.get_str("marker", index) for index in go.get_indices("marker")]


###################
#     CLASSES     #
###################

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
            print("Writing " + cache_file_name + "...")
            for i in range(len(median_array)):
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
        debug_print("raw_data", "For plot", plot_id, "added:", generation, value)
        if plot_id not in self.raw_data:
            self.raw_data[plot_id] = dict()
        if generation not in self.raw_data[plot_id]:
            self.raw_data[plot_id][generation] = list()
        self.raw_data[plot_id][generation].append(value)

    def get(self, plot_id, generation):
        return self.raw_data[plot_id][generation]

    def init_max_generation(self):
        # Read global data
        self.max_generation = go.get_int("max_generation")
        if self.max_generation == MAX_GEN_NOT_PROVIDED:
            for data in self.raw_data.values():
                generations = max(data.keys())
                debug_print("plot", "generations: " + str(generations))
                if generations > self.max_generation:
                    self.max_generation = generations


class DataSingleTreatment:
    def __init__(self, treatment):
        self.treatment = treatment
        self.raw_data = None
        self.median_and_ci = dict()
        self.stats = dict()
        self.max_generation = None

    def get_raw_data(self):
        if not self.raw_data:
            self.init_raw_data()
        return self.raw_data

    def get_stats(self, plot_id, stats):
        if plot_id not in self.stats:
            self.init_stats(plot_id, stats)
        if stats not in self.stats[plot_id]:
            self.init_stats(plot_id, stats)
        return self.stats[plot_id][stats]

    def get_median_and_ci(self, plot_id):
        print('WARNING: Method get_median_and_ci is deprecated')
        if plot_id not in self.median_and_ci:
            self.init_median_and_ci(plot_id)
        return self.median_and_ci[plot_id]

    def get_max_generation(self):
        if not self.max_generation:
            self.init_max_generation()
        return self.max_generation

    def stats_to_cache(self, stats):
        # Read global data
        to_plot = go.get_int_list("to_plot")

        for plot_id in to_plot:
            median_and_ci = self.get_stats(plot_id, stats)
            filename = self.treatment.get_cache_file_name(plot_id, stats)
            median_and_ci.to_cache(filename)

    def to_cache(self):
        print('WARNING: to_cache is deprecated')
        # Read global data
        to_plot = go.get_int_list("to_plot")

        for plot_id in to_plot:
            median_and_ci = self.get_median_and_ci(plot_id)
            median_and_ci.to_cache(self.treatment.get_cache_file_name(plot_id))

    def init_max_generation(self):
        # Read global data
        self.max_generation = go.get_int("max_generation")
        if self.max_generation == MAX_GEN_NOT_PROVIDED:
            raw_data = self.get_raw_data()
            self.max_generation = raw_data.get_max_generation()

    def init_raw_data(self):
        # Read global data
        separator = go.get_str("separator")
        to_plot = go.get_int_list("to_plot")
        y_column = go.get_int("x_column")
        one_value_per_dir = go.get_bool("one_value_per_dir")
        pool = len(go.get_list("pool", default=[])) > 0

        # Init raw data
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
                        pf.skip_header(separated_file)
                        for line in separated_file:
                            split_line = pf.get_split_line(line, separator)
                            self._add(split_line, generation)
                generation += 1
        elif pool:
            for dir_name, file_names in zip(self.treatment.dirs,
                                            self.treatment.files_per_pool):
                print("Pooling for directory: ", dir_name)
                results = []
                for file_name in file_names:
                    with open(file_name, 'r') as separated_file:
                        print("Reading raw data from " + file_name + "...")
                        pf.skip_header(separated_file)
                        generation = 0
                        for line in separated_file:
                            split_line = pf.get_split_line(line, separator)
                            result = self._parse_pool(split_line, generation)
                            # print "Value read: ", result
                            if len(results) < (generation + 1):
                                results.append(result)
                            else:
                                for i in range(len(result)):
                                    old_value = results[generation][i]
                                    new_value = result[i]
                                    if new_value > old_value:
                                        results[generation][i] = new_value
                            generation += 1
                generation = 0
                for result in results:
                    for plot_id, value in zip(to_plot, result):
                        # print "Value used:", value
                        self.raw_data.add(plot_id, generation, value)
                    generation += 1

        else:
            for file_name in self.treatment.files:
                with open(file_name, 'r') as separated_file:
                    print("Reading raw data from " + file_name + "...")
                    pf.skip_header(separated_file)
                    generation = 0
                    for line in separated_file:
                        # split_line_temp = line.split(separator)
                        split_line = pf.get_split_line(line, separator)
                        self._add(split_line, generation)
                        generation += 1

    def init_stats(self, plot_id, stats):
        # Get global data
        read_cache = go.get_bool("read_cache") and go.get_bool("read_median_ci_cache")

        if read_cache:
            try:
                self.init_stats_from_cache(plot_id, stats)
                assert plot_id in self.stats
                assert stats in self.stats[plot_id]
                return
            except IOError:
                pass
            except CacheError:
                pass
        self.init_stats_from_data(plot_id, stats)
        assert plot_id in self.stats
        assert stats in self.stats[plot_id]

    def init_median_and_ci(self, plot_id):
        print('WARNING: init_median_and_ci is deprecated')
        # Get global data
        read_cache = go.get_bool("read_cache") and go.get_bool("read_median_ci_cache")

        if read_cache:
            try:
                self.init_median_and_ci_from_cache(plot_id)
                return
            except IOError:
                pass
            except CacheError:
                pass
        self.init_median_and_ci_from_data(plot_id)

    def init_stats_from_cache(self, plot_id, stats):
        # Read global data
        step = go.get_int("step")
        x_from_file = go.get_bool("x_from_file")

        # Get the max generation for which we have data
        max_generation = self.get_max_generation()
        generations_to_plot = range(0, max_generation, step)
        data_points = len(generations_to_plot)
        cache_file_name = self.treatment.get_cache_file_name(plot_id, stats)

        # Count the number of data points we have in
        count = pf.get_nr_of_lines(cache_file_name)

        # Read the cache file
        with open(cache_file_name, 'r') as cache_file:
            print("Reading from cache file " + cache_file_name + "...")
            if plot_id not in self.stats:
                self.stats[plot_id] = dict()
            self.stats[plot_id][stats] = MedianAndCI()
            data_point_number = 0
            for line in cache_file:
                try:
                    generation = generations_to_plot[data_point_number]
                    split_line = line.split()
                    debug_print("data", "Expected generation:", generation)
                    debug_print("data", split_line)
                    if generation != int(split_line[3]) and not x_from_file:
                        raise CacheError("Step mismatch")
                    self.stats[plot_id][stats].add(int(split_line[3]),
                                                   split_line[0],
                                                   split_line[1],
                                                   split_line[2])
                    data_point_number += 1
                except IndexError:
                    break

    def init_median_and_ci_from_cache(self, plot_id):
        print('WARNING: init_median_and_ci_from_cache is deprecated')
        # Read global data
        step = go.get_int("step")
        x_from_file = go.get_bool("x_from_file")

        # Get the max generation for which we have data
        max_generation = self.get_max_generation()
        generations_to_plot = range(0, max_generation, step)
        data_points = len(generations_to_plot)
        cache_file_name = self.treatment.get_cache_file_name(plot_id)

        # Count the number of data points we have in
        count = pf.get_nr_of_lines(cache_file_name)

        # Read the cache file
        with open(cache_file_name, 'r') as cache_file:
            print("Reading from cache file " + cache_file_name + "...")
            self.median_and_ci[plot_id] = MedianAndCI()
            data_point_number = 0
            for line in cache_file:
                try:
                    generation = generations_to_plot[data_point_number]
                    split_line = line.split()
                    debug_print("data", "Expected generation:", generation)
                    debug_print("data", split_line)
                    if generation != int(split_line[3]) and not x_from_file:
                        raise CacheError("Step mismatch")
                    self.median_and_ci[plot_id].add(int(split_line[3]),
                                                    split_line[0],
                                                    split_line[1],
                                                    split_line[2])
                    data_point_number += 1
                except IndexError:
                    break

    def init_stats_from_data(self, plot_id, stats):
        # Read global data
        step = go.get_int("step")
        # stats = getStr('stats')

        write_cache = (go.get_bool("write_cache") and
                       go.get_bool("write_median_ci_cache"))
        x_from_file = go.get_bool("x_from_file")

        # Initialize empty median and ci
        if plot_id not in self.stats:
            self.stats[plot_id] = dict()
        self.stats[plot_id][stats] = MedianAndCI()
        # self.median_and_ci[plot_id] = MedianAndCI()
        max_generation = self.get_max_generation()

        if plot_id not in self.get_raw_data():
            print("Warning: no data available for plot", plot_id, "skipping.")
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

        # Calculate median and confidence intervals
        print("Calculating confidence intervals...")
        y_values = sorted(self.get_raw_data()[plot_id].keys())
        generations_to_plot = y_values[0:len(y_values):step]
        debug_print("plot", "generations_to_plot: " + str(generations_to_plot) +
                    " max generation: " + str(max_generation))
        for generation in generations_to_plot:
            raw_data = self.get_raw_data()[plot_id][generation]
            # if bootstrap:
            print("Generation: " + str(generation))
            # print("raw_data:", raw_data)
            median, ci_min, ci_max = calc_stats(raw_data, stats)
            # print("median:", median, ci_min, ci_max)
            debug_print("ci", str(median) + " " +
                        str(ci_min) + " " + str(ci_max))
            # else:
            #     median, ci_min, ci_max = calc_median_and_interquartile_range(raw_data)
            self.stats[plot_id][stats].add(generation, median, ci_min, ci_max)
        if write_cache:
            self.stats_to_cache(stats)

    def init_median_and_ci_from_data(self, plot_id):
        print('WARNING: init_median_and_ci_from_data is deprecated')

        # Read global data
        step = go.get_int("step")
        stats = go.get_str('stats')

        # Backwards compatibility with outdated bootstrap option
        bootstrap = go.get_bool("bootstrap")
        if bootstrap:
            stats = 'median_and_bootstrap_percentile'

        write_cache = (go.get_bool("write_cache") and
                       go.get_bool("write_median_ci_cache"))
        x_from_file = go.get_bool("x_from_file")

        # Initialize empty median and ci
        self.median_and_ci[plot_id] = MedianAndCI()
        max_generation = self.get_max_generation()

        if plot_id not in self.get_raw_data():
            print("Warning: no data available for plot", plot_id, "skipping.")
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

        # Calculate median and confidence intervals
        print("Calculating confidence intervals...")
        y_values = sorted(self.get_raw_data()[plot_id].keys())
        generations_to_plot = y_values[0:len(y_values):step]
        debug_print("plot", "generations_to_plot: " + str(generations_to_plot) +
                    " max generation: " + str(max_generation))
        for generation in generations_to_plot:
            raw_data = self.get_raw_data()[plot_id][generation]
            # if bootstrap:
            print("Generation: " + str(generation))
            # print("raw_data:", raw_data)
            median, ci_min, ci_max = calc_stats(raw_data, stats)
            # print("median:", median, ci_min, ci_max)
            debug_print("ci", str(median) + " " +
                        str(ci_min) + " " + str(ci_max))
            # else:
            #     median, ci_min, ci_max = calc_median_and_interquartile_range(raw_data)
            self.median_and_ci[plot_id].add(generation, median, ci_min, ci_max)
        if write_cache:
            self.to_cache()

    def _parse_pool(self, split_line, generation):
        to_plot = go.get_int_list("to_plot")
        x_values_passed = go.get_exists("x_values")
        x_values = go.get_int_list("x_values")

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
        to_plot = go.get_int_list("to_plot")
        x_from_file = go.get_bool("x_from_file")
        x_column = go.get_int("x_column")
        x_values_passed = go.get_exists("x_values")
        x_values = go.get_int_list("x_values")

        debug_print("read_values", "Split line:", split_line,
                    "plot requested:", to_plot)
        for plot_id in to_plot:
            if len(split_line) <= plot_id:
                print("Error: no data for requested column", plot_id,
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
        self.treatment_name_cache = dict()
        self.comparison_cache = None
        self.max_generation = None

    def get_treatment_index(self, treatment_name):
        if treatment_name in self.treatment_name_cache:
            return self.treatment_name_cache[treatment_name]
        else:
            for tr in self.treatment_list:
                self.treatment_name_cache[tr.get_name()] = tr.get_id()
                self.treatment_name_cache[tr.get_name_short()] = tr.get_id()
            return self.treatment_name_cache[treatment_name]

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
        # Read global data
        max_generation = go.get_int("max_generation")
        first_plot = go.get_int("to_plot")
        x_from_file = go.get_bool("x_from_file")

        treatment_data = self.get_treatment_data(treatment)
        med_ci = treatment_data.get_median_and_ci(first_plot)
        if max_generation == MAX_GEN_NOT_PROVIDED or x_from_file:
            keys = sorted(med_ci.median.keys())
            return keys[0:len(med_ci.median.keys()):go.get_int("step")]
        else:
            return range(0, len(med_ci.median) * go.get_int("step"), go.get_int("step"))

    def get_x_values_stats(self, treatment, plot_id, stats):
        # Read global data
        max_generation = go.get_int("max_generation")
        first_plot = go.get_int("to_plot")
        x_from_file = go.get_bool("x_from_file")

        treatment_data = self.get_treatment_data(treatment)
        med_ci = treatment_data.get_stats(first_plot, stats)
        if max_generation == MAX_GEN_NOT_PROVIDED or x_from_file:
            return sorted(med_ci.median.keys())
        else:
            return range(0, len(med_ci.median) * go.get_int("step"), go.get_int("step"))

    def get_comparison(self, treatment_id_1, treatment_id_2, plot_id):
        if not self.comparison_cache:
            self.init_compare()
        key = (treatment_id_1, treatment_id_2, plot_id)
        if key not in self.comparison_cache:
            print("Error: no comparison entry for values" + str(key))
            print("Cache:", self.comparison_cache)
            return []
        return self.comparison_cache[key]

    def to_cache(self):
        # Read global data
        cache_file_name = go.get_str("comparison_cache")
        stat_test_step = go.get_int("stat_test_step")

        with open(cache_file_name, 'w') as cache_file:
            print("Writing " + cache_file_name + "...")
            for entry in self.comparison_cache.items():
                key, generations = entry
                main_treatment_id, other_treatment_id, plot_id = key
                cache_file.write(str(plot_id) + " ")
                cache_file.write(str(main_treatment_id) + " ")
                cache_file.write(str(other_treatment_id) + " ")
                cache_file.write(str(stat_test_step) + " ")
                for generation in generations:
                    cache_file.write(str(generation) + " ")
                cache_file.write("\n")

    def init_max_generation(self):
        # Read global data
        self.max_generation = go.get_int("max_generation")

        # Calculate max generation if necessary
        if self.max_generation == MAX_GEN_NOT_PROVIDED:
            for treatment in self.treatment_list:
                treatment_data = self.get_treatment_data(treatment)
                if treatment_data.get_max_generation() > self.max_generation:
                    self.max_generation = treatment_data.get_max_generation()

    def init_compare(self):
        # Read global data
        read_cache = go.get_bool("read_cache") and go.get_bool("read_comparison_cache")

        self.comparison_cache = DictOfLists()
        if read_cache:
            try:
                self.init_compare_from_cache()
                return
            except IOError:
                pass
            except CacheError:
                pass
        self.init_compare_from_data()

    def init_compare_from_cache(self):
        # Read global data
        comp_cache_name = go.get_str("comparison_cache")
        stat_test_step = go.get_int("stat_test_step")

        # Actually read the cache file
        with open(comp_cache_name, 'r') as cache_file:
            print("Reading from comparison cache " + comp_cache_name + "...")
            for line in cache_file:
                numbers = line.split()
                if len(numbers) < 4:
                    raise CacheError("Entry is to short.")
                plot_id_cache = int(numbers[0])
                main_treat_id_cache = int(numbers[1])
                other_treat_id_cache = int(numbers[2])
                stat_test_step_cache = int(numbers[3])
                if stat_test_step != stat_test_step_cache:
                    raise CacheError("Cache created with different step")
                key = (main_treat_id_cache, other_treat_id_cache, plot_id_cache)
                self.comparison_cache.init_key(key)
                for i in range(4, len(numbers)):
                    self.comparison_cache.add(key, int(numbers[i]))
        self.verify_cache()

    def verify_cache(self):
        # Verify that all data is there
        plot_ids = go.get_int_list("to_plot")
        for plot_id in plot_ids:
            for compare_i in go.get_indices("comparison_main"):
                main_treat_id = go.get_str("comparison_main", compare_i)
                main_treat_i = get_treatment_index(main_treat_id, self)
                for other_treat_i in get_other_treatments(compare_i, self):
                    key = (main_treat_i, other_treat_i, plot_id)
                    if key not in self.comparison_cache:
                        raise CacheError("Cache is missing an entry.")

    def init_compare_from_data(self):
        # Get global data
        plot_ids = go.get_int_list("to_plot")
        write_cache = (go.get_bool("write_cache") and
                       go.get_bool("write_comparison_cache"))

        # Compare data for all plots and all treatments
        for plot_id in plot_ids:
            for compare_i in go.get_indices("comparison_main"):
                main_treat_id = go.get_str("comparison_main", compare_i)
                main_treat_i = get_treatment_index(main_treat_id, self)
                for other_treat_i in get_other_treatments(compare_i, self):
                    self.compare_treat(main_treat_i, other_treat_i, plot_id)
        if write_cache:
            self.to_cache()

    def compare_treat(self, main_treat_i, other_treat_i, plot_id):
        debug_print("cache", "Comparing: ", other_treat_i, " : ", main_treat_i)

        # Retrieve data
        stat_test_step = go.get_int("stat_test_step")
        p_threshold = go.get_float("p_threshold")
        main_treat = self.treatment_list[main_treat_i]
        main_data = self.get_treatment_data(main_treat).get_raw_data()
        other_treat = self.treatment_list[other_treat_i]
        other_data = self.get_treatment_data(other_treat).get_raw_data()

        # Assert that data is available
        if plot_id not in main_data:
            warn_data_avail(plot_id, main_treat)
            return
        if plot_id not in other_data:
            warn_data_avail(plot_id, other_treat)
            return
        warn_max_gen(self, main_data, other_data, plot_id)

        # Construct a key and add it to the cache
        key = (main_treat_i, other_treat_i, plot_id)
        self.comparison_cache.init_key(key)

        # Gather all generations for which we have data for both treatments
        main_gen = set(main_data[plot_id].keys())
        other_gen = set(other_data[plot_id].keys())
        generations = list(main_gen.intersection(other_gen))
        generations.sort()

        # Perform the actual statistical test
        for generation in generations[::stat_test_step]:
            data1 = main_data[plot_id][generation]
            data2 = other_data[plot_id][generation]
            p_value = mann_whitney_u(data1, data2)
            print("Generation:", generation,
                  "p-value:", p_value,
                  "mean 1:", np.mean(data1),
                  "mean 2:", np.mean(data2))
            if p_value < p_threshold:
                self.comparison_cache.add(key, generation)


######################
## HELPER FUNCTIONS ##
######################
def warn_data_avail(plot_id, treatment):
    print("Warning: no data available for plot", plot_id,
          "treatment", treatment.get_name(), ", skipping...")


def warn_max_gen(data_intr, main_data, other_data, plot_id):
    # Determine max generation for this comparison
    max_gen = data_intr.get_max_generation()
    max_gen_main = main_data.get_max_generation(plot_id)
    max_gen_other = other_data.get_max_generation(plot_id)
    max_gen_avail = min(max_gen_main, max_gen_other)
    if max_gen_avail < max_gen:
        print("Warning: data does extent until max generation: " + str(max_gen))
        print("Maximum generation available is: " + str(max_gen_avail))
        max_gen = max_gen_avail
    return max_gen


def getSigMarker(compare_to_symbol):
    sig_marker = go.get_str("sig_marker", compare_to_symbol, when_not_exist=go.RETURN_FIRST)
    try:
        matplotlib.markers.MarkerStyle(sig_marker)
    except ValueError:
        print("Warning: invalid significance marker, marker replaced with *.")
        sig_marker = "*"
    return sig_marker


def getMarker(compare_to_symbol):
    sig_marker = go.get_str("marker", compare_to_symbol)
    if sig_marker.lower() == "none":
        return None
    try:
        matplotlib.markers.MarkerStyle(sig_marker)
    except ValueError:
        print("Warning: invalid plot marker, marker replaced with *.")
        sig_marker = "*"
    return sig_marker


def getLinestyle(compare_to_symbol):
    linestyle = go.get_str("linestyle", compare_to_symbol, when_not_exist=go.RETURN_FIRST)
    if linestyle not in ['-', '--', '-.', ':']:
        print("Warning: invalid linestyle, linestyle replaced with -.")
        linestyle = "-"
    return linestyle


def getFgColor(compare_to_symbol):
    color = go.get_str("colors", compare_to_symbol)
    try:
        matplotlib.colors.colorConverter.to_rgb(color)
    except ValueError:
        print("Warning: invalid treatment color, color replaced with grey.")
        color = "#505050"
    return color


def getBgColor(compare_to_symbol):
    back_color = go.get_str("background_colors", compare_to_symbol)
    if back_color == "default":
        fore_color = go.get_str("colors", compare_to_symbol)
        back_color = tl.def_bg_color(fore_color)
    try:
        matplotlib.colors.colorConverter.to_rgb(back_color)
    except ValueError:
        print("Warning: invalid background color", back_color, ", color replaced with grey.")
        back_color = "#505050"
    return back_color


def get_other_treatments(compare_i, data_intr):
    main_treat_id = go.get_str("comparison_main", compare_i)
    main_treat_i = get_treatment_index(main_treat_id, data_intr)
    nr_of_treatments = len(data_intr.get_treatment_list())
    other_treatment_ids = go.get_str("comparison_others", compare_i, when_not_exist=go.RETURN_FIRST)
    other_treatments = parse_treatment_ids(other_treatment_ids, data_intr)
    if len(other_treatments) == 0:
        other_treatments = list(range(nr_of_treatments - 1, -1, -1))
        other_treatments.remove(main_treat_i)
    else:
        other_treatments.reverse()
    return other_treatments


######################
# PLOTTING FUNCTIONS #
######################
def create_plots(data_of_interest):
    for index in go.get_indices("to_plot"):
        create_plot(index, data_of_interest)


def draw_plot(index, data_of_interest, ax, stats):
    for treatment in data_of_interest.get_treatment_list():
        plot_treatment(index, treatment, data_of_interest, ax, stats)


def draw_inset(index, data_of_interest, ax):
    plot_id = go.get_int("to_plot", index)
    inset_stats = go.get_str('inset_stats')
    inset_x = go.get_float('inset_x')
    inset_y = go.get_float('inset_y')
    inset_w = go.get_float('inset_w')
    inset_h = go.get_float('inset_h')

    inset_area_x1 = go.get_float('inset_area_x1')
    inset_area_x2 = go.get_float('inset_area_x2')
    inset_area_y1 = go.get_float('inset_area_y1')
    inset_area_y2 = go.get_float('inset_area_y2')

    inset_labels = go.get_str('inset_labels')
    inset_ticks = go.get_str('inset_ticks')
    inset_lines_visible = go.get_str('inset_lines_visible')

    axins = ax.inset_axes([inset_x, inset_y, inset_w, inset_h])
    axins.set_xlim(inset_area_x1, inset_area_x2)
    axins.set_ylim(inset_area_y1, inset_area_y2)
    if inset_labels == 'none':
        axins.set_xticklabels('')
        axins.set_yticklabels('')
    if inset_ticks == 'none':
        axins.xaxis.set_ticks_position('none')
        axins.yaxis.set_ticks_position('none')

    rec_patch, conn_lines = ax.indicate_inset_zoom(axins)
    if inset_lines_visible == 'all':
        for conn_line in conn_lines:
            conn_line._visible = True
    elif inset_lines_visible == 'none':
        for conn_line in conn_lines:
            conn_line._visible = False

    draw_plot(plot_id, data_of_interest, axins, inset_stats)


def create_plot(index, data_of_interest):
    stats = go.get_str('stats')
    inset_stats = go.get_str('inset_stats')

    # Backwards compatibility with outdated bootstrap option
    bootstrap = go.get_bool("bootstrap")
    if bootstrap:
        stats = 'median_and_bootstrap_percentile'

    # extra_artists[plot_id] = []
    plt.figure(index)
    ax = plt.gca()
    draw_plot(index, data_of_interest, ax, stats)
    if inset_stats != '':
        draw_inset(index, data_of_interest, ax)


def plot_treatment(index, treatment, data_of_interest, ax, stats):
    # Get data
    plot_id = go.get_int("to_plot", index)
    max_generation = data_of_interest.get_max_generation()
    treatment_name = treatment.get_name()
    treatment_index = treatment.get_id()
    treatment_data = data_of_interest.get_treatment_data(treatment)
    mean_and_ci = treatment_data.get_stats(plot_id, stats)

    marker = getMarker(treatment_index)
    linestyle = getLinestyle(treatment_index)
    marker_size = go.get_float("marker_size")
    marker_offset = go.get_int("marker_offset", treatment_index)
    color = getFgColor(treatment_index)
    bg_color = getBgColor(treatment_index)

    debug_print("plot", "Max generation: " + str(max_generation))
    debug_print("plot", "Step: " + str(go.get_int("step")))

    print("For plot " + str(plot_id) + " plotting treatment: " +
          treatment.get_name())
    if len(mean_and_ci) == 0:
        print("Warning: no data available for plot", plot_id, "of treatment",
              treatment.get_name(), ", skipping.")
        return

    plot_mean = mean_and_ci.get_median_array()
    var_min = mean_and_ci.get_ci_min_array()
    var_max = mean_and_ci.get_ci_max_array()

    # Apply median filter
    plot_mean = median_filter(plot_mean, go.get_int("smoothing"))
    var_min = median_filter(var_min, go.get_int("smoothing"))
    var_max = median_filter(var_max, go.get_int("smoothing"))

    # Calculate plot markers
    data_step_x = data_of_interest.get_x_values_stats(treatment, plot_id, stats)
    debug_print("plot", "X len", len(data_step_x), "X data: ", data_step_x)
    debug_print("plot", "Y len", len(plot_mean), "Y data: ", plot_mean)
    assert (len(data_step_x) == len(plot_mean)), f"Found {len(data_step_x)} x values, but {len(plot_mean)} y values"

    if go.get_glb("marker_step")[0] is not None:
        marker_step = go.get_int("marker_step")
    else:
        marker_step = max_generation / 10
        if marker_step < 1:
            marker_step = 1
    adj_marker_step = int(marker_step / go.get_int("step"))
    adjusted_marker_offset = int(marker_offset / go.get_int("step"))

    # Debug statements
    debug_print("plot", "Marker step: " + str(marker_step) +
                " adjusted: " + str(adj_marker_step))
    debug_print("plot", "Marker offset: " + str(marker_offset) +
                " adjusted: " + str(adjusted_marker_offset))

    # Calculate markers
    # print('adjusted_marker_offset', adjusted_marker_offset)
    # print('adj_marker_step', adj_marker_step)
    plot_marker_y = plot_mean[adjusted_marker_offset:len(plot_mean):adj_marker_step]
    plot_marker_x = data_step_x[adjusted_marker_offset:len(plot_mean):adj_marker_step]

    # Debug statements
    debug_print("plot", "Plot marker X len", len(plot_marker_x),
                "X data: ", plot_marker_x)
    debug_print("plot", "Plot marker Y len", len(plot_marker_y),
                "Y data: ", plot_marker_y)
    assert (len(plot_marker_x) == len(plot_marker_y))

    # The actual median
    ax.plot(data_step_x, plot_mean, color=color, linewidth=LINE_WIDTH,
            linestyle=linestyle)

    # Fill confidence interval
    alpha = go.get_float("confidence_interval_alpha")
    ax.fill_between(data_step_x, var_min, var_max, edgecolor=bg_color,
                    facecolor=bg_color, alpha=alpha, linewidth=NO_LINE)

    if go.get_bool("plot_confidence_interval_border"):
        style = go.get_str("confidence_interval_border_style")
        width = go.get_float("confidence_interval_border_width")
        ax.plot(data_step_x, var_min, color=color, linewidth=width,
                linestyle=style)
        ax.plot(data_step_x, var_max, color=color, linewidth=width,
                linestyle=style)

    # Markers used on top of the line in the plot
    ax.plot(plot_marker_x, plot_marker_y,
            color=color,
            linewidth=NO_LINE,
            marker=marker,
            markersize=marker_size)

    # Markers used in the legend
    # To plot the legend markers, plot a point completely outside of the plot.
    ax.plot([data_step_x[0] - max_generation], [0], color=color,
            linewidth=LINE_WIDTH, linestyle=linestyle, marker=marker,
            label=treatment_name, markersize=marker_size)


def add_significance_bar(plot_config, data_intr, bar_nr):
    ROW_HEIGHT = 1.0
    HALF_ROW_HEIGHT = ROW_HEIGHT / 2.0

    i = plot_config.plot_id
    max_generation = data_intr.get_max_generation()
    min_generation = data_intr.get_min_generation()
    main_treat_id = go.get_str("comparison_main", bar_nr)
    main_treat_i = get_treatment_index(main_treat_id, data_intr)
    main_treat = data_intr.get_treatment_list()[main_treat_i]
    other_treats = get_other_treatments(bar_nr, data_intr)
    plot_id = go.get_int("to_plot", i)
    box_top = len(other_treats) * ROW_HEIGHT
    box_bot = 0

    print("  Calculating significance for plot: " + str(i))
    sig_label = go.get_str("sig_label")
    sig_label = sig_label.replace('\\n', '\n')

    if go.get_bool("sig_lbl_add_treat_name") and not go.get_bool("sig_header_show"):
        lbl = sig_label + main_treat.get_name_short()
    elif not go.get_bool("sig_header_show"):
        lbl = sig_label
    elif go.get_bool("sig_lbl_add_treat_name"):
        lbl = main_treat.get_name_short()
    else:
        lbl = ""

    ax = plt.subplot(plot_config.gridspec_dict["sig"][bar_nr])
    ax.set_xlim(0, max_generation)
    ax.get_yaxis().set_ticks([])
    ax.set_ylim(box_bot, box_top)
    if go.get_bool("sig_header_show") and bar_nr == 0:
        # Add text on the side
        dx = -(go.get_float("sig_header_x_offset") * float(max_generation))
        dy = box_top - (go.get_float("sig_header_y_offset") * float(box_top))
        an = ax.annotate(sig_label,
                         xy=(dx, dy),
                         xytext=(dx, dy),
                         annotation_clip=False,
                         verticalalignment='top',
                         horizontalalignment='right',
                         size=go.get_int("sig_header_font_size")
                         )
        plot_config.extra_artists.append(an)
    ax.set_ylabel(lbl,
                  rotation='horizontal',
                  fontsize=go.get_int("tick_font_size"),
                  horizontalalignment='right',
                  verticalalignment='center')

    # Sets the position of the p<0.05 label
    # While the y coordinate can be set directly with set_position, the x
    # coordinate passed to this method is ignored by default. So instead,
    # the labelpad is used to modify the x coordinate (and, as you may
    # expect, there is no labelpad for the y coordinate, hence the two
    # different methods for applying the offset).
    x, y = ax.get_yaxis().label.get_position()
    ax.get_yaxis().labelpad += go.get_float("comparison_offset_x")
    ax.get_yaxis().label.set_position((0, y - go.get_float("comparison_offset_y")))
    ax.tick_params(bottom=True, top=False)

    if bar_nr == (len(go.get_indices("comparison_main")) - 1):
        ax.set_xlabel(go.get_str("x_labels", i, when_not_exist=go.RETURN_FIRST))
    else:
        ax.set_xlabel("")
        ax.set_xticks([])

    odd = True
    row_center = HALF_ROW_HEIGHT
    for other_treat_i in other_treats:
        sig_marker = getSigMarker(other_treat_i)
        color = getFgColor(other_treat_i)
        back_color = getBgColor(other_treat_i)
        other_treat = data_intr.get_treatment_list()[other_treat_i]

        # Add the background box
        row_top = row_center + HALF_ROW_HEIGHT
        row_bot = row_center - HALF_ROW_HEIGHT
        box = Polygon([(min_generation, row_bot),
                       (min_generation, row_top),
                       (max_generation, row_top),
                       (max_generation, row_bot)],
                      facecolor=back_color,
                      zorder=-100)
        ax.add_patch(box)

        # Add the line separating the treatments
        ax.plot([min_generation, max_generation],
                [row_bot, row_bot],
                color='black',
                linestyle='-',
                linewidth=1.0,
                solid_capstyle="projecting")

        comp = data_intr.get_comparison(main_treat_i, other_treat_i, plot_id)
        for index in comp:
            ax.scatter(index,
                       row_center,
                       marker=sig_marker,
                       c=color,
                       s=50)

        # Determmine position for treatment labels
        lbls_x = max_generation * (1.0 + go.get_float("sig_treat_lbls_x_offset"))
        if go.get_str("sig_treat_lbls_align") == "top":
            lbls_y = row_top + go.get_float("sig_treat_lbls_y_offset")
            lbls_v_align = "top"
        elif go.get_str("sig_treat_lbls_align") == "bottom":
            lbls_y = row_bot + go.get_float("sig_treat_lbls_y_offset")
            lbls_v_align = "bottom"
        elif go.get_str("sig_treat_lbls_align") == "center":
            lbls_y = row_center + go.get_float("sig_treat_lbls_y_offset")
            lbls_v_align = "center"
        else:
            raise Exception("Invalid option for 'sig_treat_lbls_align': "
                            + go.get_str("sig_treat_lbls_align"))

        if go.get_bool("sig_treat_lbls_show"):
            if go.get_bool("sig_treat_lbls_symbols"):
                # Add symbol markers on the side
                if odd:
                    lbls_x = max_generation * (1.010 +
                                               go.get_float("sig_treat_lbls_x_offset"))
                else:
                    lbls_x = max_generation * (1.035 +
                                               go.get_float("sig_treat_lbls_x_offset"))
                    ax.plot([max_generation, lbls_x],
                            [lbls_y, lbls_y],
                            color='black',
                            linestyle='-',
                            linewidth=1.0,
                            solid_capstyle="projecting",
                            clip_on=False,
                            zorder=90)
                p = ax.scatter(lbls_x, lbls_y, marker=sig_marker, c=color,
                               s=100, clip_on=False, zorder=100)
                plot_config.extra_artists.append(p)
            else:
                # Add text on the side
                an = ax.annotate(other_treat.get_name_short(),
                                 xy=(max_generation, lbls_y),
                                 xytext=(lbls_x, lbls_y),
                                 annotation_clip=False,
                                 verticalalignment=lbls_v_align,
                                 horizontalalignment='left',
                                 rotation=go.get_float("sig_treat_lbls_rotate"),
                                 size=go.get_int("sig_treat_lbls_font_size")
                                 )
                plot_config.extra_artists.append(an)

        # End of loop operations
        odd = not odd
        row_center += ROW_HEIGHT


def plot_significance(plot_configs, data_intr):
    print("Calculating significance...")
    # for i in range(len(go.get_list("to_plot"))):
    for plot_config in plot_configs:
        for j in go.get_indices("comparison_main"):
            add_significance_bar(plot_config, data_intr, j)
    print("Calculating significance done.")


######################
### CONFIGURE PLOTS ##
######################
def setup_plots(nr_of_generations):
    """
    A setup for the different plots
    (both the main plot and the small bar at the bottom).
    """
    # If we want to plot significance indicators we have to make an additional
    # box below the plot
    if go.get_bool("sig"):
        ratios = [10]
        nr_of_comparisons = len(go.get_indices("comparison_main"))
        for i in range(nr_of_comparisons):
            ratios.append(go.get_float("comparison_height", i))
        high_level_ratios = [ratios[0], sum(ratios[1:])]
        main_plot_gridspec = gridspec.GridSpec(
            2, 1,
            height_ratios=high_level_ratios,
            hspace=go.get_float("box_margin_before")
        )
        sig_indicator_gridspec = gridspec.GridSpecFromSubplotSpec(
            nr_of_comparisons, 1,
            subplot_spec=main_plot_gridspec[1, 0],
            height_ratios=ratios[1:],
            hspace=go.get_float("box_margin_between")
        )
    else:
        main_plot_gridspec = gridspec.GridSpec(1, 1)
        sig_indicator_gridspec = None

    plot_configs = cp.setup_plots(go.get_indices("to_plot"), main_plot_gridspec)

    for plot_config in plot_configs:
        plot_config.gridspec_dict["sig"] = sig_indicator_gridspec
        ax = plot_config.subplot_dict[0]
        if go.get_bool("sig"):
            ax.tick_params(labelbottom=False)
            ax.set_xlabel("")
            ax.tick_params(axis='x', bottom='off')
        if not go.get_exists("x_axis_min"):
            ax.set_xlim(xmin=0)
        if not go.get_exists("x_axis_max"):
            ax.set_xlim(xmax=nr_of_generations)
    return plot_configs


######################
#    PARSE OPTIONS   #
######################
def parse_options(command_line_args):
    go.parse_global_options(command_line_args)
    treatment_list = tl.read_treatments()

    if len(treatment_list) < 1:
        print("No treatments provided")
        sys.exit(1)

    if len(treatment_list) == 1:
        go.set_glb("sig", [False])

    if not go.get_exists("comparison_cache"):
        go.set_glb("comparison_cache",
                   [go.get_str("output_directory") + "/comparison.cache"])

    data_intr = DataOfInterest(treatment_list)

    if not go.get_exists("marker_step"):
        go.set_glb("marker_step", [int(data_intr.get_max_generation() / 10)])

    return treatment_list, data_intr


def add_options():
    tl.add_options()
    pf.add_options()
    cp.add_options()

    # General plot settings
    go.add_option("max_generation", MAX_GEN_NOT_PROVIDED, nargs=1,
                  help_str="The maximum number of generations to plot."
                           "If not provided, the maximum will be determined from the data.")
    go.add_option("step", 1, nargs=1,
                  help_str="Step-size with which to plot the data.")
    go.add_option("stat_test_step", 1, nargs=1,
                  help_str="Step-size at which to perform statistical comparisons between "
                           "treatments.")
    go.add_option("marker_step", def_marker_step, nargs=1,
                  help_str="Step-size at which to place treatment markers.")
    go.add_option("bootstrap", False, nargs=1,
                  help_str="If true, the shaded area will be based on bootstrapped "
                           "confidence intervals. Otherwise the shaded area represents the "
                           "inter-quartile range.")
    go.add_option("stats", "median_and_interquartile_range", nargs=1,
                  help_str="The type of statistics to plot in format [central]_and_[ci]."
                           "Central options: mean, median. CI options: interquartile_range, "
                           "std_error, bootstrap_percentile, bootstrap_pivotal, bootstrap_bca, "
                           "bootstrap_pi, bootstrap_abc. Percentile and takes the "
                           "percentile of the sampled data (biased). Pivotal also subtracts "
                           "difference between the sampled and the original distribution "
                           "(unbiased, but may be wrong for certain distributions). Pi is "
                           "the scikits implementation of the percentile method. Bca is a "
                           "faster, bias-correct bootstrap method. Abc is a parametric method "
                           "meaning its faster, but it requires a smooth function to be "
                           "available.")
    go.add_option("smoothing", 1, nargs=1,
                  help_str="Applies a median window of the provided size to smooth the "
                           "line plot.")
    go.add_option("box_margin_before", 0, nargs=1, aliases=["box_sep"],
                  help_str="Space before the significance indicator boxes, "
                           "separating them from the main plot..")
    go.add_option("box_margin_between", 0, nargs=1,
                  help_str="Space between the significance indicator boxes.")
    go.add_option("marker_size", 18, nargs=1,
                  help_str="The size of the treatment markers.")
    go.add_option("one_value_per_dir", False, nargs=1,
                  help_str="If true, assumes that every file found holds a single value, "
                           "to be plotted sequentially.")

    # General inset settings
    go.add_option('inset_stats', '', nargs=1,
                  help_str="Which statistic to plot in the inset. "
                           "See the stats option for legal arguments.")
    go.add_option('inset_x', 0.5, nargs=1,
                  help_str="The x-coordinate of the left side of the inset in figure "
                           "coordinates.")
    go.add_option('inset_y', 0.5, nargs=1,
                  help_str="The y-coordinate of the bottom side of the inset in figure "
                           "coordinates.")
    go.add_option('inset_w', 0.47, nargs=1,
                  help_str="The width of the inset.")
    go.add_option('inset_h', 0.47, nargs=1,
                  help_str="The height of the inset.")
    go.add_option('inset_area_x1', 0, nargs=1,
                  help_str="The smallest x-value for the data covered in the inset "
                           "(in data coordinates).")
    go.add_option('inset_area_x2', 1, nargs=1,
                  help_str="The largest x-value for the data covered in the inset "
                           "(in data coordinates).")
    go.add_option('inset_area_y1', 0, nargs=1,
                  help_str="The smallest y-value for the data covered in the inset "
                           "(in data coordinates).")
    go.add_option('inset_area_y2', 1, nargs=1,
                  help_str="The largest y-value for the data covered in the inset "
                           "(in data coordinates).")
    go.add_option('inset_labels', 'none', nargs=1,
                  help_str="Which tick-labels to show. Current options are 'all' and "
                           "'none'.")
    go.add_option('inset_ticks', 'none', nargs=1,
                  help_str="Which ticks to show. Current options are 'all' and 'none'.")
    go.add_option('inset_lines_visible', 'all', nargs=1,
                  help_str="Which lines to show for indicating the inset area. "
                           "Current options are 'all' and 'none'.")

    # General significance bar settings
    go.add_option("comparison_offset_x", 0, nargs=1, aliases=["sig_lbl_x_offset"],
                  help_str="Allows moving the label next the significance indicator box.")
    go.add_option("comparison_offset_y", 0, nargs=1, aliases=["sig_lbl_y_offset"],
                  help_str="Allows moving the label next the significance indicator box.")
    go.add_option("sig_header_show", False, nargs=1,
                  help_str="Whether there should be a header for the significance indicator box.")
    go.add_option("sig_header_x_offset", 0, nargs=1,
                  help_str="Allows moving the header next the significance indicator box.")
    go.add_option("sig_header_y_offset", 0, nargs=1,
                  help_str="Allows moving the header next the significance indicator box.")
    go.add_option("sig_label", "p<0.05 vs ", nargs=1, aliases=["sig_lbl", "sig_header"],
                  help_str="Label next to the significance indicator box.")
    go.add_option("sig_lbl_add_treat_name", True, nargs=1,
                  help_str="Whether to add the short name of the main treatment as part "
                           "of the label next to the significance indicator box.")
    go.add_option("sig_treat_lbls_x_offset", 0.005, nargs=1,
                  help_str="Allows moving the treatment labels next to the "
                           "significance indicator box horizontally.")
    go.add_option("sig_treat_lbls_y_offset", 0, nargs=1,
                  help_str="Allows moving the treatment labels next to the "
                           "significance indicator box vertically.")
    go.add_option("sig_treat_lbls_rotate", 0, nargs=1,
                  help_str="Allows rotating the treatment labels next to the "
                           "significance indicator box.")
    go.add_option("sig_treat_lbls_symbols", False, nargs=1,
                  help_str="Plot symbols instead of names for the treatment labels next to "
                           "the significance indicator box.")
    go.add_option("sig_treat_lbls_align", "bottom", nargs=1,
                  help_str="Alignment for the treatment labels next to the significance "
                           "indicator box. Possible values are: 'top', 'bottom', and 'center'.")
    go.add_option("sig_treat_lbls_show", True, nargs=1,
                  help_str="Whether to show the treatment labels next to the significance "
                           "indicator box.")
    go.add_option("p_threshold", 0.05, nargs=1,
                  help_str="P threshold for the significance indicators.")

    # Per comparison settings
    go.add_option("comparison_main", 0, aliases=["main_treatment"],
                  help_str="Statistical comparisons are performed against this treatment.")
    go.add_option("comparison_others", "",
                  help_str="Statistical comparisons are performed against this treatment.")
    go.add_option("comparison_height", def_box_height, aliases=["box_height"],
                  help_str="The height of the box showing significance indicators.")

    # Font settings
    go.add_option("sig_treat_lbls_font_size", cp.def_tick_font_size, nargs=1,
                  help_str="Font size for the treatment labels next to "
                           "the significance indicator box.")
    go.add_option("sig_header_font_size", cp.def_tick_font_size, nargs=1,
                  help_str="Font size for the header next to the "
                           "the significance indicator box.")

    # Misc settings
    go.add_option("sig", True, nargs=1,
                  help_str="Show the significance bar underneath the plot.")
    go.add_option("plot_confidence_interval_border", False, nargs=1,
                  help_str="Whether or not the show borders at the edges of the shaded "
                           "confidence region.")
    go.add_option("confidence_interval_border_style", ":", nargs=1,
                  help_str="Line style of the confidence interval border.")
    go.add_option("confidence_interval_border_width", 1, nargs=1,
                  help_str="Line width of the confidence interval border.")
    go.add_option("confidence_interval_alpha", FILL_ALPHA, nargs=1,
                  help_str="Alpha value for the shaded region.")

    # Per plot settings
    go.add_option("to_plot", 1, aliases=["plot_column"],
                  help_str="The columns from the input files that should be plotted.")

    # Cache settings
    go.add_option("read_cache", True, nargs=1,
                  help_str="If false, script will not attempt to read data from cache.")
    go.add_option("write_cache", True, nargs=1,
                  help_str="If false, script will not write cache files.")
    go.add_option("read_median_ci_cache", True, nargs=1,
                  help_str="If false, script will not read median values from cache.")
    go.add_option("write_median_ci_cache", True, nargs=1,
                  help_str="If false, script will not write median values to cache.")
    go.add_option("read_comparison_cache", True, nargs=1,
                  help_str="If false, script will not read statistical results from cache.")
    go.add_option("write_comparison_cache", True, nargs=1,
                  help_str="If false, script will not write statistical results to cache.")
    go.add_option("comparison_cache", def_comp_cache, nargs=1,
                  help_str="Name of the cache file that holds statistical results.")

    # Per treatment settings
    go.add_option("sig_marker", def_sig_marker,
                  help_str="The marker used in the signficance indicator box.")
    go.add_option("marker_offset", def_marker_offset,
                  help_str="Offset between the markers of different treatments, so they "
                           "are not plotted on top of each other.")


def init_options():
    go.init_options("Script for creating line-plots.",
                    "[input_directories [input_directories ...]] [OPTIONS]",
                    __version__)
    add_options()


def execute_plots(command_line_args):
    treatment_list, data_of_interest = parse_options(command_line_args)
    plot_configs = setup_plots(data_of_interest.get_max_generation())

    # Plot all treatments
    create_plots(data_of_interest)

    # Plots the dots indicating significance
    if go.get_bool("sig"):
        plot_significance(plot_configs, data_of_interest)

    # Writes the plots to disk
    cp.write_plots(plot_configs)


######################
#        MAIN        #
######################
def main():
    """
    Main is split in a way that makes it easy to perform unit-test by first
    calling init_options(), then setting whatever options you want to test,
    and then calling execute_plots(CUSTOM_ARGUMENTS).
    """
    init_options()
    execute_plots(sys.argv[1:])


if __name__ == '__main__':
    main()
