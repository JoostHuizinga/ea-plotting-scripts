#!/usr/bin/env python3
import math
import sys
from typing import List, Dict
from dataclasses import dataclass
import collections
import treatment_list as tl
import parse_file as pf
import configure_plots as cp
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
import matplotlib.gridspec as gs
import global_options as go

__author__ = "Joost Huizinga"
__version__ = "1.0 (Sep. 11 2021)"


@dataclass
class Individual:
    obj1: float
    obj2: float
    fit: float
    id: int

    def __hash__(self):
        return hash((self.obj1, self.obj2))

    def __eq__(self, other):
        if not isinstance(other, Individual):
            return False
        return self.obj1 == other.obj1 and self.obj2 == other.obj2


@dataclass
class UniqueIndividual(Individual):
    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if not isinstance(other, UniqueIndividual):
            return False
        return self.id == other.id


@dataclass
class TreatmentData:
    population: Dict[int, List[Individual]]


def convert_to_unique(population):
    new_pop = []
    for indiv in population:
        new_pop.append(UniqueIndividual(indiv.obj1, indiv.obj2, indiv.fit, indiv.id))
    return new_pop


def parse_one_population_per_line(file_name):
    par_column_start = go.get_int("par_column_start")
    if go.get_exists("par_column_end"):
        par_column_end = go.get_int("par_column_end")
    else:
        par_column_end = None
    par_columns_per_indiv = go.get_int("par_columns_per_indiv")
    par_obj1_idx = go.get_int("par_obj1_idx")
    par_obj2_idx = go.get_int("par_obj2_idx")
    par_fit_idx = go.get_int("par_fit_idx")
    generations_to_plot = set()
    for index in go.get_indices("generations"):
        generations_to_plot.update(set(go.get_int_list("generations", index)))
    max_generation_to_plot = max(generations_to_plot)

    populations = collections.defaultdict(list)

    def process_line(split_line, generation):
        if generation in generations_to_plot:
            if par_column_end is None:
                _par_column_end = len(split_line)
            else:
                _par_column_end = par_column_end
            indiv_id = 0
            for j in range(par_column_start, _par_column_end, par_columns_per_indiv):
                ob1 = float(split_line[j + par_obj1_idx])
                ob2 = float(split_line[j + par_obj2_idx])
                fit = float(split_line[j + par_fit_idx])
                populations[generation].append(Individual(ob1, ob2, fit, indiv_id))
                indiv_id += 1
                if abs(ob1 * ob2 - fit) > 0.0001:
                    print("Impossible individual:", generation, j, populations[generation][-1])
            return generation >= max_generation_to_plot
        return False

    pf.read_file(file_name, process_line)
    return populations


def read_population_data(treatment_list):
    run = go.get_int("run")
    for treatment in treatment_list:
        file_name = treatment.files[run]
        treatment.data = TreatmentData(parse_one_population_per_line(file_name))


def def_file_name():
    return [f"gen_{go.get_int_list('generations', index)[0]}"
            for index in go.get_indices("generations")]


def def_title():
    result = []
    for index in go.get_indices("generations"):
        result.append([f"Generation {generation}" for generation in go.get_int_list('generations', index)])
    return result


def def_pop_marker_size():
    return go.get_float("marker_size") / 16.0


def def_legend_marker_size():
    return go.get_float("marker_size")


def parse_options():
    go.init_options("Script for creating pareto-front plots.",
                    "[input_directories [input_directories ...]] [OPTIONS]",
                    __version__)
    tl.add_options()
    pf.add_options()
    cp.add_options()

    go.set_glb("file_names", def_file_name)
    go.set_glb("titles", def_title)

    # Pareto-specific options
    go.add_option("generations", [0],
                  help_str=".")
    go.add_option("run", 0,
                  help_str=".")
    go.add_option("par_column_start", 0,
                  help_str=".")
    go.add_option("par_column_end",
                  help_str=".")
    go.add_option("par_columns_per_indiv", 3,
                  help_str=".")
    go.add_option("par_obj1_idx", 0,
                  help_str=".")
    go.add_option("par_obj2_idx", 1,
                  help_str=".")
    go.add_option("par_fit_idx", 2,
                  help_str=".")

    go.add_option("marker_size", 18, nargs=1,
                  help_str="The size of the treatment markers.")
    go.add_option("pop_marker_size", def_pop_marker_size, nargs=1,
                  help_str="The size used to plot individuals in the population.")
    go.add_option("legend_marker_size", def_legend_marker_size, nargs=1,
                  help_str="The size in the legend.")

    go.add_option("pop_alpha", 0.1, nargs=1,
                  help_str="The alpha (transparency) used to plot individuals in the population.")
    go.add_option("line_alpha", 0.5, nargs=1,
                  help_str="The alpha (transparency) of the line defining the pareto front.")
    go.add_option("line_width", 1.0, nargs=1,
                  help_str="The line width of the line defining the pareto front.")

    go.add_option("grid_columns", 3, nargs=1,
                  help_str="The maximum number of columns to add to the plot.")
    go.add_option("grid_wspace", 0.2, nargs=1,
                  help_str="Horizonal (the 'w' stands for width) distance between plots.")
    go.add_option("grid_hspace", 0.2, nargs=1,
                  help_str="Vertical (the 'h' stands for height) distance between plots.")

    go.add_option("sep_legend", False, nargs=1,
                  help_str="")
    go.add_option("legend_only", False, nargs=1,
                  help_str="")
    go.add_option("plot_pop", True, nargs=1,
                  help_str="")
    go.add_option("plot_cmoea_bins", False, nargs=1,
                  help_str="")

    go.parse_global_options(sys.argv[1:])


def get_pareto_front(population):
    sorted_pop = sorted(population, key=lambda x: x.obj1, reverse=True)
    front = [sorted_pop[0]]
    for indiv in sorted_pop[1:]:
        if indiv.obj2 > front[-1].obj2:
            if indiv.obj1 == front[-1].obj1:
                front[-1] = indiv
            else:
                front.append(indiv)
    return front


def dist(point1, point2):
    x1, y1 = point1
    x2, y2 = point2
    return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)


def get_gridspec_coordinates(index):
    return math.floor(index / go.get_int("grid_columns")), index % go.get_int("grid_columns")


def create_pareto_plot(treatment_list, plot_config, subplot_id, generation, nb_generations):
    row, column = get_gridspec_coordinates(subplot_id)
    ax = cp.init_subplot(plot_config, subplot_id, plot_config.gridspec_dict["main"][row, column])

    # Set square aspect ratio for the background
    ax.set_aspect(1.0)
    ax.apply_aspect()

    # Only show labels on the bottom and the right side
    if column != 0:
        ax.set_ylabel(None)

    last_row, last_column = get_gridspec_coordinates(nb_generations - 1)
    if not (row == last_row or (row == last_row - 1 and column > last_column)):
        ax.set_xlabel(None)

    # Plot background first (if any)
    cp.plot_background(ax)

    # Plot the entire population
    if go.get_bool("plot_pop"):
        for treatment in treatment_list:
            # print("generation:", generation, len(treatment.data.population[generation]))
            population = treatment.data.population[generation]
            for indiv in population:
                ax.scatter(
                    indiv.obj1,
                    indiv.obj2,
                    marker=treatment.marker,
                    c=treatment.color,
                    s=go.get_float("pop_marker_size"),
                    alpha=go.get_float("pop_alpha")
                )

    # Plot the pareto front
    for treatment in treatment_list:
        population = treatment.data.population[generation]
        front = get_pareto_front(population)

        if go.get_bool("plot_cmoea_bins"):
            unique_pop = convert_to_unique(population)

            hard_bin = sorted(unique_pop, key=lambda x: (x.obj2, -x.obj1), reverse=True)[0:40]
            easy_bin = sorted(unique_pop, key=lambda x: (x.obj1, -x.obj2), reverse=True)[0:40]
            easy_or_hard = set(hard_bin + easy_bin)

            combined_bin = [indiv for indiv in unique_pop if indiv not in easy_or_hard]

            print(f"{treatment.name} pareto front size: {len(front)}, of which unique: {len(set(front))}")
            comb_count = 0
            hard_count = 0
            easy_count = 0
            # for indiv in convert_to_unique(set(front)):
            for indiv in unique_pop:
                color = "#000000"
                r = "00"
                g = "00"
                b = "00"
                if indiv in combined_bin:
                    comb_count += 1
                    g = "82"
                    # color = "#008200"
                if indiv in hard_bin:
                    hard_count += 1
                    r = "82"
                    # color = "#820000"
                if indiv in easy_bin:
                    easy_count += 1
                    b = "82"
                    # color = "#000082"

                ax.scatter(
                    indiv.obj1,
                    indiv.obj2,
                    marker=treatment.marker,
                    alpha=0.5,
                    c="#" + r + g + b,
                    s=10,
                )

            print(f"comb_count: {comb_count}, hard_count: {hard_count}, easy_count: {easy_count}")
            print("combined_bin:", combined_bin)
            print("hard_bin:", hard_bin)
            print("easy_bin:", easy_bin)
        else:
            x_val = [indiv.obj1 for indiv in front]
            y_val = [indiv.obj2 for indiv in front]
            ax.plot(
                x_val,
                y_val,
                color=treatment.color,
                alpha=go.get_float("line_alpha"),
                linewidth=go.get_float("line_width"),
            )
            for indiv in [front[0], front[-1]]:
                ax.scatter(
                    indiv.obj1,
                    indiv.obj2,
                    marker=treatment.marker,
                    c=treatment.color,
                    s=go.get_float("marker_size"),
                )

    # Plot additional annotations, if any
    cp.plot_annotations(ax)


def main():
    parse_options()
    treatment_list = tl.read_treatments()
    if not go.get_bool("legend_only"):
        read_population_data(treatment_list)

    # generations = getIntList("generations")

    # Initializes global matplotlib parameters
    cp.init_params()
    for plot_id in cp.get_plot_ids():

        generations = go.get_int_list("generations", plot_id)

        num_columns = go.get_int("grid_columns")
        if len(generations) < num_columns:
            num_columns = len(generations)
        gridspec = gs.GridSpec(math.ceil(len(generations) / num_columns), num_columns)
        plot_config = cp.setup_figure(plot_id, gridspec)

        # Create the legend
        for treatment in treatment_list:
            plot_config.legend_handles.append(
                mlines.Line2D([], [],
                              marker=treatment.marker,
                              color=treatment.color,
                              markersize=go.get_float("legend_marker_size"),
                              label=treatment.name)
            )

        if not go.get_bool("legend_only"):
            plt.subplots_adjust(wspace=go.get_float("grid_wspace"), hspace=go.get_float("grid_hspace"))
            for subplot_id, generation in enumerate(generations):
                create_pareto_plot(treatment_list, plot_config, subplot_id, generation, len(generations))

            # Create color bar
            cp.create_color_bar(plot_config)

            # Write the plot to disk
            cp.write_plot(plot_config)

        if go.get_bool("sep_legend"):
            cp.export_legend(plot_config)


if __name__ == '__main__':
    main()
