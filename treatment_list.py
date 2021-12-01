from typing import List
import collections
import os
import sys
import parse_file as pf
import matplotlib.colors
import global_options as go
import hashlib
import struct
from createPlotUtils import debug_print


def hash_list_of_strings(strings: List[str]):
    new_hash = hashlib.sha1()
    for s in strings:
        new_hash.update(struct.pack("I", len(s)))
        new_hash.update(s.encode())
    return new_hash.hexdigest()


def create_prefix(root_directory, files):
    # We keep the shared parts of the provided paths human readable, but
    # to increase the chance that each new combination of files will get
    # a unique cache file name, we hash the rest.
    key_dict = collections.defaultdict(list)
    root_path_list = root_directory.split(os.path.sep)
    for file in files:
        path_list = file.split(os.path.sep)
        for i, path in enumerate(path_list[len(root_path_list):]):
            key_dict[i].append(path)
    prefix = ""
    hash_part = []
    for path_section_names in key_dict.values():
        if all([path_section_names[0] == name for name in path_section_names]):
            if len(prefix) != 0:
                prefix += "_"
            prefix += path_section_names[0]
        else:
            hash_part += path_section_names
    if len(hash_part) != 0:
        if len(prefix) != 0:
            prefix = "_" + prefix
        prefix = hash_list_of_strings(hash_part)[:16] + prefix
    return prefix


class Treatment:
    def __init__(self,
                 treatment_id=None,
                 files_or_directories=None,
                 treatment_name=None,
                 short_name=None,
                 color=None,
                 background_color=None,
                 marker=None,
                 linestyle=None,
                 ):

        # Get Global data
        self.templates = go.get_list("templates", default=[])
        self.pool = go.get_str_list("pool", default=[])
        self.dirs = []
        self.files = []
        self.parts = []

        if len(self.pool) > 0:
            debug_print("files", "Pooling:", self.pool)
            for directory in files_or_directories:
                # self.root_directory = directory
                dirs_current_pool = pf.get_dirs(self.pool, directory)
                self.dirs += dirs_current_pool
                # self.files = []
                self.files_per_pool = []
                for pool_dir in self.dirs:
                    files = pf.get_files(self.templates, pool_dir)
                    self.files += files
                    self.files_per_pool.append(files)
                # self.cache_file_name_prefix = (self.root_directory + "/ch_" +
                #                                self.templates[-1] + "_")

        for file_or_directory in files_or_directories:
            if os.path.isfile(file_or_directory):
                debug_print("files", "Retrieving file:", file_or_directory)
                self.files.append(file_or_directory)
                self.parts.append([file_or_directory])
            else:
                debug_print("files", "Retrieving files from directory:", file_or_directory,
                            "with template:", self.templates)
                files = pf.get_files(self.templates, file_or_directory)
                self.files += files
                self.parts.append(files)
            # self.root_directory = None
            # self.cache_file_name_prefix = "unknown_"
        if len(self.files) != 0:
            self.files = [os.path.normpath(os.path.realpath(file)) for file in self.files]
            self.root_directory = os.path.commonpath(self.files)
            if os.path.isfile(self.root_directory):
                self.root_directory = os.path.dirname(self.root_directory)
            # self.root_directory = os.path.dirname(os.path.realpath(self.files[0]))
            # for file in self.files[1:]:
            #     potential_root = os.path.dirname(os.path.realpath(file))
            #     while potential_root != self.root_directory:
            #         self.root_directory = os.path.dirname(self.root_directory)
            #         potential_root = os.path.dirname(potential_root)
            prefix = create_prefix(self.root_directory, self.files)
        else:
            debug_print("files", "No files found.")
            self.root_directory = ""
            prefix = ""
        self.cache_file_name_prefix = "ch_" + prefix + "_"
        self.name = treatment_name
        self.short_name = short_name
        self.id = treatment_id
        self.color = color
        self.background_color = background_color
        self.marker = marker
        self.linestyle = linestyle
        self.data = None
        debug_print("files", "root directory:", self.root_directory)
        debug_print("files", "cache file prefix:", self.cache_file_name_prefix)

    def __repr__(self):
        return "Treatment(id=" + str(self.id) + "," + \
               " dir=\"" + str(self.root_directory) + "\"," \
                                                      " name=\"" + str(self.name) + "\"," + \
               " short_name=\"" + str(self.short_name) + "\")" + \
               " color=\"" + str(self.color) + "\")" + \
               " background_color=\"" + str(self.background_color) + "\")" + \
               " marker=\"" + str(self.marker) + "\")" + \
               " linestyle=\"" + str(self.linestyle) + "\")"

    def get_id(self):
        return self.id

    def get_name(self):
        return self.name

    def get_name_short(self):
        return self.short_name

    # def add_dir(self, directory):
    #     self.parts.append(pf.get_files(self.templates, directory))

    # def get_cache_file_name(self, plot_id):
    #     return self.root_directory + "/" + str(plot_id) + ".cache"

    def get_cache_file_name(self, plot_id, stats=''):
        # if stats == '':
        #     return self.root_directory + "/" + self.cache_file_name_prefix + str(plot_id) + ".cache"
        return self.root_directory + "/" + self.cache_file_name_prefix + stats + '_' + str(plot_id) + ".cache"

    def get_background_color(self):
        back_color = self.background_color
        if back_color == "default":
            back_color = def_bg_color(self.color)
        try:
            matplotlib.colors.colorConverter.to_rgb(back_color)
        except ValueError:
            print("Warning: invalid background color", back_color, ", color replaced with grey.")
            back_color = "#505050"
        return back_color


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
        return "TreatmentList(" + str(self.treatments) + ")"

    def add_treatment(self, treatment):
        treatment.id = len(self.treatments)
        if not treatment.name:
            self.unnamed_treatment_count += 1
            treatment.name = "Unnamed " + str(self.unnamed_treatment_count)
        if not treatment.short_name:
            treatment.short_name = treatment.name
        self.treatments.append(treatment)

    def fill_from_global_options(self):
        assert not (go.get_exists("input_directories") and go.get_exists("file"))
        if go.get_exists("input_directories"):
            dir_key = "input_directories"
        else:
            dir_key = "file"
        root_dir = go.get_str("treatment_root_dir")
        for index in go.get_indices(dir_key):
            files_or_directories = [os.path.join(root_dir, file_or_directory)
                                    for file_or_directory in go.get_str_list(dir_key, index)]
            # file_or_directory = os.path.join(root_dir, file_or_directory)
            self.add_treatment(Treatment(
                files_or_directories=files_or_directories,
                treatment_name=go.get_str("treatment_names", index),
                short_name=go.get_str("treatment_names_short", index),
                color=go.get_str("colors", index),
                background_color=go.get_str("background_colors", index),
                marker=go.get_str("marker", index),
                linestyle=go.get_str("linestyle", index),
            ))

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


def read_treatments():
    treatment_list = TreatmentList()
    treatment_list.fill_from_global_options()
    # root_dir = getStr("treatment_root_dir")
    # for i in range(len(getList("input_directories"))):
    #     input_dir = os.path.join(root_dir, getStr("input_directories", i))
    #     if not getBool("one_value_per_dir") or len(treatment_list) == 0:
    #         treatment_list.add_treatment(input_dir,
    #                                      getStr("treatment_names", i),
    #                                      getStr("treatment_names_short", i))
    #     else:
    #         treatment_list[0].add_dir(input_dir)
    #
    # for i in range(len(getList("file"))):
    #     treatment_list.add_treatment(getStr("file", i),
    #                                  getStr("treatment_names", i),
    #                                  getStr("treatment_names_short", i))

    if len(treatment_list) < 1:
        print("No treatments provided")
        sys.exit(1)

    return treatment_list


def def_treatment_names():
    key = "file"
    if len(go.get_indices("input_directories")) > 0:
        key = "input_directories"
    return [os.path.basename(go.get_str_list(key, index)[0]) for index in go.get_indices(key)]


def def_treatment_names_short():
    return go.get_list("treatment_names")


def def_treatment_root_dir():
    if len(go.get_list("config_file", default=[])) == 0:
        return ""
    else:
        return os.path.dirname(os.path.realpath(go.get_str("config_file")))


def def_bg_color(color: str):
    byte = ""
    new_color = "#"
    for char in color:
        if char == '#':
            continue
        byte += char
        if len(byte) == 2:
            byte_as_int = int(byte, 16)
            new_value = min(byte_as_int + 128, 255)
            new_value_as_string = "%x" % new_value
            new_color += new_value_as_string
            byte = ""
    return new_color


def def_background_colors():
    return [def_bg_color(go.get_str("colors", index)) for index in go.get_indices("colors")]


def add_options():
    """
    There are two methods for adding treatments: the positional "file" argument
    and the named "treatment_dir" argument. The "file" argument is intended for
    quick plotting by providing a list of files or directories, where every
    file or directory will be considered as a separate treatment. The
    "treatment_dir" method is intended to be used for configuration files, and
    will create one treatment per provided directory, unless the
    "one_value_per_dir" is provided.

    The "file" method:
    - file: The positional "file" argument can specify both files and directories, and
      the code will create one treatment for each file (i.e. directory or file)
      provided.

    The "treatment_dir" method:
    - treatment_dir: The directory from which the data for this treatment will
      come from.
    - one_value_per_dir: if True, the code will only add one treatment, and
      add all provided.

    Options for both methods:
    - treatment_names (optional): The name of this treatment to be used in e.g.
      a legend.
    - treatment_names_short (optional): A shorted name for the treatment for
      cases where the full name may not fit.
    - templates: the template that determines how to obtain the files for each
      of the provided treatment directories.

    :return:
    """
    go.add_positional_option("file", nargs="*",
                             help_str="Files or directories from which to read the data.")

    go.add_option("input_directories", aliases=["treatment_dir"],
                  help_str="Directories containing the files for each specific treatment.")
    # addOption("one_value_per_dir", False, nargs=1,
    #           help="If true, assumes that every file found holds a single value, "
    #                "to be plotted sequentially.")
    go.add_option("pool",
                  help_str="Pool the results in this directory together by taking the "
                           "maximum. Accepts regular expressions.")
    go.add_option("templates", ".*",
                  help_str="Directories to traverse to find files to plot. "
                           "Accepts regular expressions.")
    go.add_option("treatment_root_dir", def_treatment_root_dir,
                  help_str="Treatment directories and files are assumed to be relative"
                           "to this directory.")
    go.add_option("treatment_names", def_treatment_names, aliases=["treatment_name"],
                  help_str="The names of each treatment, used for the legend.")
    go.add_option("treatment_names_short", def_treatment_names_short,
                  aliases=["treatment_name_short"],
                  help_str="A short name for each treatment, used when the regular name "
                           "does not fit.")
    go.add_option("colors",
                  ["#000082", "#008200", "#820000", "#008282", "#828200", "#820082"],
                  aliases=["treatment_color"],
                  help_str="The color for each treatment.")
    go.add_option("background_colors", def_background_colors,
                  aliases=["treatment_bgcolor"],
                  help_str="The color of the shaded region, for each treatment.")
    go.add_option("marker",
                  ["o", "^", "v", "<", ">", "*"],
                  aliases=["treatment_marker"],
                  help_str="The marker used for each treatment.")
    go.add_option("linestyle",
                  ["-"],
                  aliases=["treatment_linestyle"],
                  help_str="The marker used for each treatment.")
