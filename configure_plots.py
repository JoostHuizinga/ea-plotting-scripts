import os
import numpy as np
from typing import List, Dict, Union, Optional
import subprocess as sp
import matplotlib
import matplotlib.transforms
import matplotlib.pyplot as plt
import matplotlib.gridspec as gs
import matplotlib.transforms as tf
import matplotlib.cm as cm
from matplotlib.axes import Axes
from matplotlib.artist import Artist
from matplotlib.figure import Figure
from createPlotUtils import debug_print, get_renderer
from dataclasses import dataclass
import global_options as go
import parse_file as pf


@dataclass
class PlotConfiguration:
    plot_id: int
    fig: Figure
    gridspec_dict: Dict[str, Union[gs.GridSpec, gs.GridSpecFromSubplotSpec]]
    subplot_dict: Dict[int, Axes]
    extra_artists: List[Artist]
    legend_handles: List[Artist]


def latex_available():
    with open(os.devnull, "w") as f:
        try:
            status = sp.call(["latex", "--version"], stdout=f, stderr=f)
        except OSError:
            status = 1
    if status:
        return False
    else:
        return True


def init_params():
    # Setup the matplotlib params
    preamble = [r'\usepackage[T1]{fontenc}',
                r'\usepackage{amsmath}',
                r'\usepackage{txfonts}',
                r'\usepackage{textcomp}']
    matplotlib.rc('font', **{'family': 'sans-serif', 'sans-serif': ['Helvetica']})
    matplotlib.rc('text.latex', preamble="\n".join(preamble))
    params = {'backend': 'pdf',
              'axes.labelsize': go.get_int("font_size"),
              'font.size': go.get_int("font_size"),
              'legend.fontsize': go.get_int("legend_font_size"),
              'xtick.labelsize': go.get_int("tick_font_size"),
              'ytick.labelsize': go.get_int("tick_font_size"),
              'text.usetex': latex_available(),
              'figure.dpi': 100,
              'savefig.dpi': 100}
    matplotlib.rcParams.update(params)


def init_subplot(plot_config: PlotConfiguration, subplot_id, subplot_spec):
    fig = plt.figure(plot_config.plot_id)
    ax = fig.add_subplot(subplot_spec, label=str(subplot_id))
    ax.set_ylim(go.get_float("y_axis_min", plot_config.plot_id, when_not_exist=go.RETURN_FIRST, default=None),
                go.get_float("y_axis_max", plot_config.plot_id, when_not_exist=go.RETURN_FIRST, default=None))
    ax.set_xlim(go.get_float("x_axis_min", plot_config.plot_id, when_not_exist=go.RETURN_FIRST, default=None),
                go.get_float("x_axis_max", plot_config.plot_id, when_not_exist=go.RETURN_FIRST, default=None))
    ax.set_ylabel(go.get_str("y_labels", plot_config.plot_id, when_not_exist=go.RETURN_FIRST))
    ax.set_xlabel(go.get_str("x_labels", plot_config.plot_id, when_not_exist=go.RETURN_FIRST))
    if go.get_bool("title"):
        ax.set_title(go.get_str_list(
            "titles",
            plot_config.plot_id,
            when_not_exist=go.RETURN_FIRST
        )[subplot_id], fontsize=go.get_int("title_size"))
    if go.get_exists("x_ticks"):
        ax.set_xticks(go.get_float_list("x_ticks", plot_config.plot_id, when_not_exist=go.RETURN_FIRST))
    if go.get_exists("y_ticks"):
        ax.set_yticks(go.get_float_list("y_ticks", plot_config.plot_id, when_not_exist=go.RETURN_FIRST))
    # ax.set_aspect(1.0)
    # ax.apply_aspect()
    plot_config.subplot_dict[subplot_id] = ax
    return ax


def setup_figure(plot_id: int, gridspec: gs.GridSpec = gs.GridSpec(1, 1)) -> PlotConfiguration:
    """
    Sets up a figure based on plot id.

    By default, we assume there will only be one sub-figure, which is the main plot.

    :param plot_id: The plot id.
    :param gridspec: Gridspec layout for if the plot should contain multiple sub-figures.
    :return: Returns the plot configuration for this figure.
    """
    fig = plt.figure(plot_id, figsize=go.get_float_list("fig_size"))
    plot_config = PlotConfiguration(
        plot_id=plot_id,
        fig=fig,
        gridspec_dict={"main": gridspec},
        subplot_dict={},
        extra_artists=[],
        legend_handles=[],
    )
    return plot_config


def get_plot_ids() -> List[int]:
    """
    Currently we assume that the list of file-names holds the ground-truth on the
    number of plots we want to create.

    :return: A list of plot-ids.
    """
    return list(range(len(go.get_indices("file_names"))))


def setup_plot(plot_config: PlotConfiguration, gridspec: Optional[gs.GridSpec] = None):
    if gridspec is None:
        gridspec = plot_config.gridspec_dict["main"]
    init_subplot(plot_config, 0, gridspec[0])


def setup_plots(plot_ids: List[int] = None, gridspec=gs.GridSpec(1, 1)):
    """
    A setup for the different plots
    (both the main plot and the small bar at the bottom).
    """
    init_params()
    if plot_ids is None:
        plot_ids = [0]

    plot_configs = []
    for plot_id in plot_ids:
        plot_configs.append(setup_figure(plot_id, gridspec))

        # We assume that the first entry in the gridspec will contain the "main" plot,
        # so we initialize it with the parameters we read from the global options.
        init_subplot(plot_configs[-1], 0, gridspec[0])
    # axis = [init_subplot(plot_id, grid_spec[0]) for i, plot_id in enumerate(plot_ids)]
    return plot_configs


class ParseColumns:
    def __init__(self, columns: List[int]):
        self.data = {col: [] for col in columns}
        self.generations: List[int] = []

    def __call__(self, split_line: List[str], generation: int):
        self.generations.append(generation)
        for col in self.data:
            self.data[col].append(float(split_line[col]))


def plot_annotations(ax):
    for index in go.get_indices("line_from_file"):
        line_file = go.get_str("line_from_file", index)
        x_column = go.get_int("line_from_file_x_column", index, when_not_exist=go.RETURN_FIRST)
        y_column = go.get_int("line_from_file_y_column", index, when_not_exist=go.RETURN_FIRST)
        color = go.get_str("line_from_file_color", index, when_not_exist=go.RETURN_FIRST)
        linestyle = go.get_str("line_from_file_linestyle", index, when_not_exist=go.RETURN_FIRST)
        linewidth = go.get_float("line_from_file_linewidth", index, when_not_exist=go.RETURN_FIRST)
        column_parser = ParseColumns([x_column, y_column])
        pf.read_file(line_file, column_parser)
        ax.plot(column_parser.data[x_column],
                column_parser.data[y_column],
                color=color,
                linestyle=linestyle,
                linewidth=linewidth)


def plot_background(ax):
    """
    Draw a gradient image based on a provided function.

    :param ax: Axes The axes to draw on.
    """
    y_min = go.get_float("y_axis_min")
    y_max = go.get_float("y_axis_max")
    x_max = go.get_float("x_axis_max")
    x_min = go.get_float("x_axis_min")
    background_func = go.get_str("background")
    cmap = go.get_str("background_colormap")
    cmap_min = go.get_float("background_colormap_min")
    cmap_max = go.get_float("background_colormap_max")

    x_res = round(ax.bbox.width)
    y_res = round(ax.bbox.height)
    image = np.zeros((y_res, x_res), dtype=np.float64)
    for x in range(x_res):
        for y in range(y_res):
            x_val = (x * (x_max - x_min) / (x_res - 1))
            y_val = (y * (y_max - y_min) / (y_res - 1))
            val = eval(background_func, {}, {"x_val": x_val, "y_val": y_val})
            image[y, x] = cmap_min + (cmap_max - cmap_min) * val
    interpolation = 'nearest'
    im = ax.imshow(image, extent=(x_min, x_max, y_min, y_max),
                   interpolation=interpolation,
                   vmin=0, vmax=1, aspect="equal", origin="lower",
                   cmap=plt.get_cmap(cmap))
    return im


def create_color_bar(plot_config):
    cmap = go.get_str("color_bar_colormap")
    current_box = tf.Bbox.union([ax.get_position() for ax in plot_config.fig.axes])
    cax = plot_config.fig.add_axes([
        current_box.xmax + go.get_float("color_bar_margin"),
        current_box.ymin,
        go.get_float("color_bar_width"),
        current_box.height
    ])

    cbar = plot_config.fig.colorbar(cm.ScalarMappable(norm=None, cmap=plt.get_cmap(cmap)), cax=cax)
    cbar.set_label(
        go.get_str("color_bar_label"),
        rotation=go.get_float("color_bar_label_rotation"),
        fontsize=go.get_float("color_bar_label_font_size"),
        labelpad=go.get_float("color_bar_label_pad"),
    )


def export_legend(plot_config):
    output_dir = go.get_str("output_directory")
    ext = "." + go.get_str("type")
    out_file_path = output_dir + "/" + go.get_str("file_names", plot_config.plot_id) + "_legend" + ext

    # Create a new figure specifically for the legend
    fig = plt.figure()
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis('off')

    # Setup the legend as normal, except always in the lower left of the figure
    # and without any offset
    lgd = _setup_legend(ax, plot_config.legend_handles, "lower left", (0, 0, 1, 1))

    # Figure out the size of the legend if it would be rendered, and adjust the
    # figure accordingly
    renderer = get_renderer(fig)
    bbox = lgd.get_window_extent(renderer).transformed(fig.dpi_scale_trans.inverted())
    fig.set_size_inches(bbox.width, bbox.height)

    # Save the legend to a file
    fig.savefig(out_file_path, dpi="figure", bbox_inches=bbox)


def _setup_legend(ax, handles, legend_loc, bbox_to_anchor):
    columns = go.get_int("legend_columns")
    legend_label_spacing = go.get_float("legend_label_spacing")
    legend_column_spacing = go.get_float("legend_column_spacing")
    legend_handle_text_pad = go.get_float("legend_handle_text_pad")
    debug_print("legend", "location:", legend_loc, "columns:", columns)
    lgd = ax.legend(handles=handles,
                    loc=legend_loc, ncol=columns,
                    bbox_to_anchor=bbox_to_anchor,
                    labelspacing=legend_label_spacing,
                    columnspacing=legend_column_spacing,
                    handletextpad=legend_handle_text_pad)
    return lgd


def setup_legend(plot_config: PlotConfiguration):
    fig = plt.figure(plot_config.plot_id)
    ax = fig.get_axes()[0]
    # if getFloat("box_sep") == 0:
    #    plt.tight_layout()
    legend_loc = go.get_str("legend_loc", plot_config.plot_id, when_not_exist=go.RETURN_FIRST)
    if legend_loc != "none":
        anchor_x = go.get_float("legend_x_offset")
        anchor_y = go.get_float("legend_y_offset")
        bbox_to_anchor = (anchor_x, anchor_y, 1, 1)
        handles = None
        if len(plot_config.legend_handles) > 0:
            handles = plot_config.legend_handles
        lgd = _setup_legend(ax, handles, legend_loc, bbox_to_anchor)
        plot_config.extra_artists.append(lgd)


def write_plot(plot_config: PlotConfiguration):
    print("Writing plot " + str(plot_config.plot_id) + " ...")
    output_dir = go.get_str("output_directory")
    ext = "." + go.get_str("type")

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    setup_legend(plot_config)
    fig = plt.figure(plot_config.plot_id)

    out_file_path = output_dir + "/" + go.get_str("file_names", plot_config.plot_id) + ext
    print(f"Writing plot to: {out_file_path}")
    # Determine custom bounding box
    if go.get_str("bb") == "custom":
        fig_size = go.get_float_list("fig_size")
        renderer = get_renderer(fig)
        # bb = fig.get_window_extent(renderer)
        bb = fig.get_tightbbox(renderer)
        target_bb = matplotlib.transforms.Bbox.from_bounds(0, 0, fig_size[0], fig_size[1])
        trans2 = matplotlib.transforms.BboxTransformTo(target_bb)
        trans = fig.transFigure.inverted()
        print("Figure size:", fig_size)
        print("Original bb box:", bb.get_points())
        for artist in plot_config.extra_artists:
            other_bb = artist.get_window_extent(renderer)
            other_bb = other_bb.transformed(trans)
            other_bb = other_bb.transformed(trans2)
            print(other_bb.get_points())
            bb = matplotlib.transforms.BboxBase.union([bb, other_bb])
        target_aspect = fig_size[0] / fig_size[1]
        bb_aspect = bb.width / bb.height
        print(target_aspect, bb_aspect)
        if target_aspect < bb_aspect:
            bb = bb.expanded(1, bb_aspect / target_aspect)
        else:
            bb = bb.expanded(target_aspect / bb_aspect, 1)
        bb = bb.padded(0.2)
        print("Extended bb box:", bb.get_points())
        plt.savefig(out_file_path,
                    bbox_extra_artists=plot_config.extra_artists, bbox_inches=bb)
    elif go.get_str("bb") == "manual":
        fig_size = go.get_float_list("fig_size")
        renderer = get_renderer(fig)
        ext_width = go.get_float("bb_width")
        ext_heigth = go.get_float("bb_height")
        x_offset = go.get_float("bb_x_offset")
        y_offset = go.get_float("bb_y_offset")
        x_tight_center = go.get_float("bb_x_center_includes_labels")
        y_tight_center = go.get_float("bb_y_center_includes_labels")

        # Get the transformations that we need
        inches_to_pixels = fig.dpi_scale_trans
        pixels_to_inches = inches_to_pixels.inverted()

        # Get the bounding box of the window
        win_bb_in_pixels = fig.get_window_extent(renderer)

        # Get the bounding box of the actual figure, including labels
        fig_bb_in_inches = fig.get_tightbbox(renderer)
        fig_bb_in_pixels = fig_bb_in_inches.transformed(inches_to_pixels)

        # Get a new bounding box just as wide as the window, but with the
        # center of the figure bounding box
        new_bb_in_pixels = win_bb_in_pixels.frozen()

        if x_tight_center:
            width_ratio = win_bb_in_pixels.width / fig_bb_in_pixels.width
            new_bb_in_pixels.x0 = fig_bb_in_pixels.x0
            new_bb_in_pixels.x1 = fig_bb_in_pixels.x1
            new_bb_in_pixels = new_bb_in_pixels.expanded(width_ratio, 1)

        if y_tight_center:
            height_ratio = win_bb_in_pixels.height / fig_bb_in_pixels.height
            new_bb_in_pixels.y0 = fig_bb_in_pixels.y0
            new_bb_in_pixels.y1 = fig_bb_in_pixels.y1
            new_bb_in_pixels = new_bb_in_pixels.expanded(1, height_ratio)

        # Transform to inch space
        bb_in_inches = new_bb_in_pixels.transformed(pixels_to_inches)

        # Apply custom transformations
        bb_in_inches = bb_in_inches.expanded(
            float(ext_width) / float(fig_size[0]),
            float(ext_heigth) / float(fig_size[1]))

        bb_in_inches.y0 += y_offset
        bb_in_inches.y1 += y_offset

        bb_in_inches.x0 += x_offset
        bb_in_inches.x1 += x_offset

        plt.savefig(out_file_path,
                    bbox_extra_artists=plot_config.extra_artists,
                    bbox_inches=bb_in_inches)
    elif go.get_str("bb") == "default":
        plt.savefig(out_file_path,
                    bbox_extra_artists=plot_config.extra_artists)
    elif go.get_str("bb") == "tight":
        plt.savefig(out_file_path,
                    bbox_extra_artists=plot_config.extra_artists,
                    bbox_inches='tight')
    else:
        raise Exception("Invalid bounding box option.")
    print("Writing plot " + str(plot_config.plot_id) + " done.")


def write_plots(plot_configs: List[PlotConfiguration]):
    print("Writing plots...")
    for plot_config in plot_configs:
        write_plot(plot_config)


def def_legend_font_size(): return go.get_int("font_size") - 4


def def_title_font_size(): return go.get_int("font_size") + 4


def def_tick_font_size(): return go.get_int("font_size") - 6


def def_color_bar_label_font_size(): return go.get_float("font_size")


def def_color_bar_colormap(): return go.get_str("background_colormap")


def add_options():
    def def_output_dir():
        if go.get_exists("config_file"):
            return pf.base(go.get_str("config_file")) + "_out"
        else:
            number = 1
            name = "my_plot_" + str(number)
            while os.path.exists(name):
                number += 1
                name = "my_plot_" + str(number)
            return name

    go.add_option("output_directory", def_output_dir, nargs=1,
                  help_str="Resulting plots will be put into this directory.")
    go.add_option("type", "pdf", nargs=1,
                  help_str="The file type in which the plot will be written.")
    go.add_option("fig_size", [[8, 6]], nargs=2,
                  help_str="The size of the resulting figure.")
    go.add_option("title", True, nargs=1,
                  help_str="Show the title of the plot.")

    # Font settings
    go.add_option("font_size", 18, nargs=1,
                  help_str="The base font-size for the plot "
                           "(other font-sizes are relative to this one).")
    go.add_option("title_size", def_title_font_size, nargs=1,
                  aliases=["title_font_size"],
                  help_str="Font size for the title.")
    go.add_option("legend_font_size", def_legend_font_size, nargs=1,
                  help_str="Font size for the legend.")
    go.add_option("tick_font_size", def_tick_font_size, nargs=1,
                  help_str="Font size for the tick-labels.")

    # Per plot settings
    go.add_option("file_names", "my_plot", aliases=["plot_output"],
                  help_str="The names of the output files for each plotted column.")
    go.add_option("titles", "Unnamed plot", aliases=["plot_title"],
                  help_str="The titles for each plot.")
    go.add_option("x_labels", "Number of Generations", aliases=["plot_x_label"],
                  help_str="The x labels for each plot.")
    go.add_option("y_labels", "Value", aliases=["plot_y_label"],
                  help_str="The x labels for each plot.")
    go.add_option("legend_loc", "best", aliases=["plot_legend_loc"],
                  help_str="Legend location for each plot.")
    go.add_option("y_axis_min", aliases=["plot_y_min"],
                  help_str="The minimum value for the y axis.")
    go.add_option("y_axis_max", aliases=["plot_y_max"],
                  help_str="The maximum value for the y axis.")
    go.add_option("x_axis_max", aliases=["plot_x_max"],
                  help_str="The minimum value for the x axis.")
    go.add_option("x_axis_min", aliases=["plot_x_min"],
                  help_str="The maximum value for the x axis.")
    go.add_option("x_ticks",
                  help_str="Use the provided strings as labels for the x-ticks.")
    go.add_option("y_ticks",
                  help_str="Use the provided strings as labels for the y-ticks.")

    # Legend settings
    go.add_option("legend_columns", 1, nargs=1,
                  help_str="Number of columns for the legend.")
    go.add_option("legend_x_offset", 0, nargs=1,
                  help_str="Allows for fine movement of the legend.")
    go.add_option("legend_y_offset", 0, nargs=1,
                  help_str="Allows for fine movement of the legend.")
    go.add_option("legend_label_spacing", 0.5, nargs=1,
                  help_str="Space between legend labels.")
    go.add_option("legend_column_spacing", 2.0, nargs=1,
                  help_str="Horizontal space between legend labels.")
    go.add_option("legend_handle_text_pad", 0.8, nargs=1,
                  help_str="Horizontal space between legend labels.")

    # Bounding box settings
    go.add_option("bb", "tight", nargs=1,
                  help_str="How the bounding box of the image is determined. Options are "
                           "default (keep aspect ratio and white space), "
                           "tight (sacrifice aspect ratio to prune white space), "
                           "manual (specify the bounding box yourself),"
                           "and custom (keep aspect ratio but prune some white space).")
    go.add_option("bb_width", nargs=1,
                  help_str="The width of the bounding box, in inches.")
    go.add_option("bb_height", nargs=1,
                  help_str="The height of the bounding box, in inches.")
    go.add_option("bb_x_offset", 0, nargs=1,
                  help_str="The x offset of the bounding box, in inches.")
    go.add_option("bb_y_offset", 0, nargs=1,
                  help_str="The y offset of the bounding box, in inches.")
    go.add_option("bb_x_center_includes_labels", True, nargs=1,
                  help_str="If True, take the figure labels into account when horizontally "
                           "centering the bounding box. If false, ignore the labels when "
                           "horizontally centering.")
    go.add_option("bb_y_center_includes_labels", True, nargs=1,
                  help_str="If True, take the figure labels into account when vertically "
                           "centering the bounding box. If false, ignore the labels when "
                           "vertically centering.")

    # Annotations
    go.add_option("line_from_file", None,
                  help_str="")
    go.add_option("line_from_file_x_column", 0,
                  help_str="")
    go.add_option("line_from_file_y_column", 1,
                  help_str="")
    go.add_option("line_from_file_color", "#000000",
                  help_str="")
    go.add_option("line_from_file_linestyle", "-",
                  help_str="")
    go.add_option("line_from_file_linewidth", 1,
                  help_str="")

    # Background options
    go.add_option("background", None, nargs=1,
                  help_str="")
    go.add_option("background_colormap", "Greys", nargs=1,
                  help_str="'Accent', 'Accent_r', 'Blues', 'Blues_r', 'BrBG', 'BrBG_r', "
                           "'BuGn', 'BuGn_r', 'BuPu', 'BuPu_r', 'CMRmap', 'CMRmap_r', "
                           "'Dark2', 'Dark2_r', 'GnBu', 'GnBu_r', 'Greens', 'Greens_r', "
                           "'Greys', 'Greys_r', 'OrRd', 'OrRd_r', 'Oranges', 'Oranges_r', "
                           "'PRGn', 'PRGn_r', 'Paired', 'Paired_r', 'Pastel1', 'Pastel1_r', "
                           "'Pastel2', 'Pastel2_r', 'PiYG', 'PiYG_r', 'PuBu', 'PuBuGn', "
                           "'PuBuGn_r', 'PuBu_r', 'PuOr', 'PuOr_r', 'PuRd', 'PuRd_r', "
                           "'Purples', 'Purples_r', 'RdBu', 'RdBu_r', 'RdGy', 'RdGy_r', "
                           "'RdPu', 'RdPu_r', 'RdYlBu', 'RdYlBu_r', 'RdYlGn', 'RdYlGn_r', "
                           "'Reds', 'Reds_r', 'Set1', 'Set1_r', 'Set2', 'Set2_r', 'Set3', "
                           "'Set3_r', 'Spectral', 'Spectral_r', 'Wistia', 'Wistia_r', 'YlGn', "
                           "'YlGnBu', 'YlGnBu_r', 'YlGn_r', 'YlOrBr', 'YlOrBr_r', 'YlOrRd', "
                           "'YlOrRd_r', 'afmhot', 'afmhot_r', 'autumn', 'autumn_r', 'binary', "
                           "'binary_r', 'bone', 'bone_r', 'brg', 'brg_r', 'bwr', 'bwr_r', "
                           "'cividis', 'cividis_r', 'cool', 'cool_r', 'coolwarm', 'coolwarm_r', "
                           "'copper', 'copper_r', 'cubehelix', 'cubehelix_r', 'flag', 'flag_r', "
                           "'gist_earth', 'gist_earth_r', 'gist_gray', 'gist_gray_r', 'gist_heat', "
                           "'gist_heat_r', 'gist_ncar', 'gist_ncar_r', 'gist_rainbow', 'gist_rainbow_r', "
                           "'gist_stern', 'gist_stern_r', 'gist_yarg', 'gist_yarg_r', "
                           "'gnuplot', 'gnuplot2', 'gnuplot2_r', 'gnuplot_r', 'gray', "
                           "'gray_r', 'hot', 'hot_r', 'hsv', 'hsv_r', 'inferno', 'inferno_r', "
                           "'jet', 'jet_r', 'magma', 'magma_r', 'nipy_spectral', 'nipy_spectral_r', "
                           "'ocean', 'ocean_r', 'pink', 'pink_r', 'plasma', 'plasma_r', 'prism', "
                           "'prism_r', 'rainbow', 'rainbow_r', 'seismic', 'seismic_r', 'spring', "
                           "'spring_r', 'summer', 'summer_r', 'tab10', 'tab10_r', 'tab20', 'tab20_r', "
                           "'tab20b', 'tab20b_r', 'tab20c', 'tab20c_r', 'terrain', 'terrain_r', 'turbo', "
                           "'turbo_r', 'twilight', 'twilight_r', 'twilight_shifted', 'twilight_shifted_r', "
                           "'viridis', 'viridis_r', 'winter', 'winter_r'")
    go.add_option("background_colormap_min", 0.0, nargs=1,
                  help_str="")
    go.add_option("background_colormap_max", 1.0, nargs=1,
                  help_str="")

    # Color bar options
    go.add_option("color_bar_colormap", "Greys", nargs=1,
                  help_str="The colormap used for the color bar.")
    go.add_option("color_bar_margin", 0.005, nargs=1,
                  help_str="The distance between the main plot and the color bar in a "
                           "percentage of the overall figure.")
    go.add_option("color_bar_width", 0.015, nargs=1,
                  help_str="The width of the color bar as a percentage of the overall figure.")
    go.add_option("color_bar_label", "", nargs=1,
                  help_str="The label next to the color bar.")
    go.add_option("color_bar_label_rotation", 0, nargs=1,
                  help_str="The width of the color bar as a percentage of the overall figure.")
    go.add_option("color_bar_label_font_size", def_color_bar_label_font_size, nargs=1,
                  help_str="The font size of the color bar label.")
    go.add_option("color_bar_label_pad", 0, nargs=1,
                  help_str="The padding (x-offset of the color bar label.")
