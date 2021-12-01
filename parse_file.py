import os
import re
from createPlotUtils import debug_print
import global_options as go


def get_dirs(templates, starting_directory="."):
    current_directories = [starting_directory]
    for template in templates:
        next_directories = []
        for directory in current_directories:
            for filename in os.listdir(directory):
                next_dir = directory + "/" + filename
                match_found = re.match('.*' + template + '.*', filename)
                if os.path.isdir(next_dir) and match_found:
                    next_directories.append(next_dir)
        current_directories = next_directories
    return current_directories


def get_files(templates, starting_directory="."):
    current_directories = [starting_directory]
    files = []
    for i, template in enumerate(templates):
        next_directories = []
        for directory in current_directories:
            for filename in os.listdir(directory):
                path = directory + "/" + filename
                match = re.match(template, filename)
                if os.path.isdir(path) and match:
                    next_directories.append(path)
                if os.path.isfile(path) and match and i + 1 == len(templates):
                    files.append(path)
        current_directories = next_directories
    debug_print("files", "Template:", templates, "Files found:", files)
    return files


def read_log_file(filename):
    if not os.path.isfile(filename):
        return

    input_file = open(filename, 'r')
    data_matrix = []
    for line in input_file:
        line = line.strip()
        i = 0
        data_array = []
        for string in line.split():
            data = float(string)
            data_array.append(data)
            i += 1
        data_matrix.append(data_array)
    return data_matrix


def get_nr_of_lines(file_name):
    count = 0
    with open(file_name, 'r') as tmp_file:
        for _ in tmp_file:
            count += 1
    return count


def is_header_line(line):
    for number in line.split():
        try:
            float(number)
        except ValueError:
            return True
    return False


def skip_header(file_handle):
    first_line = file_handle.readline()
    if not is_header_line(first_line):
        file_handle.seek(0)


def get_split_line(line, separator):
    split_line_temp = line.split(separator)
    split_line = []
    for word in split_line_temp:
        if word != "" and word != '\n':
            split_line.append(word)
    return split_line


def base(filename):
    return os.path.splitext(os.path.basename(filename))[0]


def get_generation(split_line, line_nr):
    x_from_file = go.get_bool("x_from_file")
    x_column = go.get_int("x_column")
    x_values_passed = go.get_exists("x_values")
    x_values = go.get_int_list("x_values")

    if x_from_file:
        return int(split_line[x_column])
    elif x_values_passed:
        return int(x_values[line_nr])
    else:
        return line_nr


def read_file(file_name, process_line):
    separator = go.get_str("separator")
    with open(file_name, 'r') as fh:
        print("Reading raw data from " + file_name + "...")
        skip_header(fh)
        for i, line in enumerate(fh):
            split_line = get_split_line(line, separator)
            generation = get_generation(split_line, i)
            done = process_line(split_line, generation)
            if done:
                break


def add_options():
    go.add_option("separator", " ", nargs=1,
                  help_str="The separator used for the input data.")
    go.add_option("x_from_file", False, nargs=1,
                  help_str="If true, x-values will be read from file, rather than assumed "
                           "to be from 0 to the number of data-points.")
    go.add_option("x_column", 0, nargs=1,
                  help_str="If x_from_file is true, this parameter determines which column "
                           "contains the x data.")
    go.add_option("x_values",
                  help_str="Use the provided values for the x-axis.")
