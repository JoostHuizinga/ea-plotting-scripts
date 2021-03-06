__author__ = 'Joost Huizinga'
__version__ = '1.8 (Jun. 27 2019)'
import sys
import os.path
import re
import shlex
import numpy as np
import scikits.bootstrap as bs
import scipy.stats as st
import subprocess as sp
import argparse as ap
import warnings
import io
import random
import quantiles

###################
#### EXCEPTIONS ###
###################
class Error(Exception):
    """Base class for exceptions in this module."""
    pass

class InputError(Error):
    """Exception raised for errors in the input.

    Attributes:
        msg  -- explanation of the error
    """

    def __init__(self, msg):
        self.msg = msg

class CacheError(Error):
    """Exception raised for errors in the input.

    Attributes:
        msg  -- explanation of the error
    """

    def __init__(self, msg):
        self.msg = msg


###################
## GLOBAL OPTIONS #
###################
global_options = {}
global_alias = {}
global_parser = ap.ArgumentParser()


def initOptions(description, usage, version):
    global_parser.version = version + "\ncreatePlotUtils.py: " + __version__
    global_parser.add_argument('-v', '--version', action='version',
                               version='%(prog)s ' + global_parser.version)
    global_parser.add_argument('-c', '--config_file', nargs='?', type=str,
                               help='Gets all options from the provided config file.')
    global_parser.add_argument("--debug", type=str, nargs='+',
                               help='Enables debug statements.')
    global_parser.add_argument("--warn_err", action='store_true',
                               help='Turns warnings into errors, so you get a stack trace.')
    global_parser.description = description
    global_parser.usage = sys.argv[0] + " " + usage
    

def addOption(name, value = [], nargs='+', aliases=[], help=""):
    if not isinstance(value, list) and not hasattr(value, '__call__'):
        value = [value]
    global_parser.add_argument("--" + name, type=str, nargs=nargs, help=help)
    global_options[name] = value
    for alias in aliases:
        global_alias[alias] = name

def addPositionalOption(name, value = [], nargs='+', help=""):
    if not isinstance(value, list) and not hasattr(value, '__call__'):
        value = [value]
    global_parser.add_argument(name, type=str, nargs=nargs, help=help)
    global_options[name] = value

def setGlb(name, value):
    global_options[name] = value

def getAny(name, index=0):
    return global_options[name][index]

def getBool(name, index=0):
    result = False

    if index < len(global_options[name]):
        if(global_options[name][index] == "False" or
           global_options[name][index] == "false" or
           global_options[name][index] == "0"):
            result = False
        elif(global_options[name][index] == "True" or
             global_options[name][index] == "true" or
             global_options[name][index] == "1"):
            result = True
        else:
            result = bool(global_options[name][index])
    return result


def getInt(name, index=0):
    result = 0
    if index < len(global_options[name]):
        result = int(global_options[name][index])
    return result


def getIntDefNone(name, index=0):
    result = None
    if index < len(global_options[name]):
        result = int(global_options[name][index])
    return result


def getFloat(name, index=0):
    result = 0.0
    if index < len(global_options[name]):
        result = float(global_options[name][index])
    return result


def getFloatDefFirst(name, index=0):
    result=None
    if len(global_options[name]) > 0:
        result = float(global_options[name][0])
    if index < len(global_options[name]):
        result = float(global_options[name][index])
    return result


def getFloatList(name):
    return list(map(float, global_options[name]))


def getFloatPair(name):
    return (getFloat(name, 0), getFloat(name, 1))


def getList(name):
    return global_options[name]


def get(name):
    return global_options[name]


def getIntList(name):
    return list(map(int, global_options[name]))


def getIntPair(name):
    return (int(global_options[name][0]), int(global_options[name][1]))


def getStr(name, index=0):
    result = "undefined-" + str(index)
    if name in global_options:
        if index < len(global_options[name]):
            result = str(global_options[name][index])
    else:
        result = None
    #print "String:", result, type(result)
    return result


def getStrDefaultEmpty(name, index=0):
    result = ""
    if name in global_options:
        if index < len(global_options[name]):
            result = str(global_options[name][index])
    else:
        result = None
    #print "String:", result, type(result)
    return result


def getStrDefaultFirst(name, index=0):
    result = "undefined-" + str(index)
    if name in global_options:
        if(index < len(global_options[name])):
            result = str(global_options[name][index])
        elif(0 < len(global_options[name])):
            result = str(global_options[name][0])
    else:
        result = None
    return result


def getExists(name, index=0):
    return index < len(global_options[name])


def readConfig(config_file_name):
    global global_options
    default_overwritten = {}
    config_file = open(config_file_name, 'r')
    for line in config_file:
        debug_print("options", "Reading line:", line)
        if line[0] == "#":
            continue
        words = shlex.split(line)
        if len(words) == 0:
            continue
        elif len(words) == 1:
            #print "Error: word \"" + str(words[0]) + "\" has no parameters"
            raise InputError("word \"" + str(words[0]) + "\" has no parameters")
        if words[0] in global_alias:
            key = global_alias[words[0]]
        else:
            key = words[0]
        if key not in default_overwritten:
            debug_print("options", "key:", key, "default:", global_options[key], "overwritting with:", words[1:]) 
            global_options[key] = words[1:]
            default_overwritten[key] = True
        else:
            debug_print("options", "key:", key, "current options:", global_options[key], "adding:", words[1:]) 
            global_options[key] += words[1:]


def parse_global_options():
    args = global_parser.parse_args()
    
    if args.warn_err:
        warnings.simplefilter("error")

    if args.debug:
        for arg in args.debug:
            debug_enabled[arg]=True

    #Retrieve values from the config file
    setGlb("config_file", [])
    if args.config_file:
        readConfig(args.config_file)
        setGlb("config_file", [args.config_file])

    #Retrieve values from the provided options, overwriting defaults and config settings
    arg_dict = vars(args)
    for option in arg_dict.items():
        key, _ = option
        if arg_dict[key]:
            value = arg_dict[key]
            if not isinstance(value, list):
                value = [value]
            setGlb(key, value)
    
    #If an option has a derived default, and the default was not overwritten, use the derived default
    for option in global_options.items():
        key, value = option
        #print("For key:", key)
        if hasattr(value, '__call__'):
            while hasattr(value, '__call__'):
                #print("Calling derived default")
                function = value
                value = function()
            if not isinstance(value, list):
                value = [value]
            setGlb(key, value)
               

###################
## Treatment List #
###################
class Treatment:
    def __init__(self, treatment_id, file_or_directory, treatment_name = "", short_name = ""):

        #Get Global data
        templates = getList("templates")
        if os.path.isfile(file_or_directory):
            self.root_directory = os.path.dirname(os.path.realpath(file_or_directory))
            self.files = [file_or_directory]
        else:
            self.root_directory = file_or_directory
            self.files = get_files(templates, file_or_directory)
        self.name = treatment_name
        self.short_name = short_name
        self.id = treatment_id

    def __str__(self):
        return str(self.root_directory) + \
            " " + str(self.name) + \
            " " + str(self.short_name) + \
            " " + str(self.id)

    def get_id(self):
        return self.id

    def get_name(self):
        return self.name

    def get_cache_file_name(self, plot_id):
        return self.root_directory + "/" + str(plot_id) + ".cache"


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

    def add_treatment(self, treatment_directory, suggested_name=None, short_name=None):
        treatment_id = len(self.treatments)
        if suggested_name and short_name:
            self.treatments.append(Treatment(treatment_id, treatment_directory, suggested_name, short_name))
        elif suggested_name:
            self.treatments.append(Treatment(treatment_id, treatment_directory, suggested_name, suggested_name))
        else:
            self.unnamed_treatment_count += 1
            name = "Unnamed " + str(self.unnamed_treatment_count)
            self.treatments.append(Treatment(treatment_id, treatment_directory, name, name))

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


###################
######## IO #######
###################
def getDirs(templates, starting_directory="."):
    currentDirectories = [starting_directory]
    for template in templates:
        nextDirectories = []
        for directory in currentDirectories:
            for filename in os.listdir(directory):
                nextDir = directory + "/" + filename
                matchFound = re.match('.*' + template + '.*', filename)
                if os.path.isdir(nextDir) and matchFound:
                    nextDirectories.append(nextDir)
        currentDirectories = nextDirectories
    return currentDirectories


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
                if os.path.isfile(path) and match and i+1 == len(templates):
                    files.append(path)
        current_directories = next_directories
    debug_print("files", "Template:", templates, "Files found:", files)
    return files


def readLogFile(filename):
    if(not(os.path.isfile(filename))):
        return

    input_file = open(filename, 'r')
    dataMatrix = []
    for line in input_file:
        line = line.strip()
        i=0
        dataArray = []
        for string in line.split():
            data=float(string)
            dataArray.append(data)
            i+=1
        dataMatrix.append(dataArray)
    return dataMatrix


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

###################
# DATA PROCESSING #
###################
def smooth(x, window_len=11, window='hanning'):
    if x.ndim != 1:
        raise ValueError("smooth only accepts 1 dimension arrays.")
    if x.size < window_len:
        raise ValueError("Input vector needs to be bigger than window size.")
    if window_len < 3:
        return x
    if not window in ['flat', 'hanning', 'hamming', 'bartlett', 'blackman']:
        raise ValueError("Window is on of 'flat', 'hanning', 'hamming', 'bartlett', 'blackman'")
    s = np.r_[2 * x[0] - x[window_len - 1::-1], x, 2 * x[-1] - x[-1:-window_len:-1]]
    if window == 'flat': #moving average
        w = np.ones(window_len, 'd')
    else:
        w = eval('numpy.' + window + '(window_len)')
    y = np.convolve(w / w.sum(), s, mode='same')
    return y[window_len:-window_len + 1]


def median_filter(x, k):
    """Apply a length-k median filter to a 1D array x.
    Boundaries are extended by repeating endpoints.
    """
    assert k % 2 == 1, "Median filter length must be odd."
    assert x.ndim == 1, "Input must be one-dimensional."
    if len(x) == 0:
        return np.zeros(0, dtype=x.dtype)
    k2 = (k - 1) // 2
    y = np.zeros((len(x), k), dtype=x.dtype)
    y[:, k2] = x
    for i in range(k2):
        j = k2 - i
        y[j:, i] = x[:-j]
        y[:j, i] = x[0]
        y[:-j, -(i + 1)] = x[j:]
        y[-j:, -(i + 1)] = x[-1]
    return np.median(y, axis=1)


def bootstrap(data, ci=0.95, n_samples=10000, statfunction=np.mean, method=''):
    stat = statfunction(data)
    if method == 'percentile' or method == 'pivotal':
        is_pivotal = method == 'pivotal'
        ci_min, ci_max = my_bootstrap(data, ci, n_samples, is_pivotal, statfunction)
    else:
        # 'pi', 'bca', or 'abc'
        try:
            ci_min, ci_max = bs.ci(data=data,
                                   statfunction=statfunction,
                                   n_samples=n_samples,
                                   method=method,
                                   alpha=1-ci)
        except IndexError:
            ci_min = stat
            ci_max = stat
    return stat, ci_min, ci_max


def my_bootstrap(data, ci=0.95, n_samples=10000, is_pivotal=True, statfunction=np.mean):
    """
    While our method is much slower, it does not throw an exception when the
    median value exists twice in the data.
    """
    statistics = np.zeros(n_samples)
    for i in range(n_samples):
        samples = []
        for j in range(len(data)):
            samples.append(random.choice(data))
        stat = statfunction(samples)
        statistics[i] = stat
    inv = float(1.0-ci)/2.0
    stat_val = statfunction(data)
    if is_pivotal:
        low = 2 * stat_val - quantiles.quantile(statistics, 1.0-inv)
        high = 2 * stat_val - quantiles.quantile(statistics, inv)
        # print(high, low, 'quantiles:',
        # quantiles.quantile(statistics, 1.0-inv),
        #       quantiles.quantile(statistics, inv), 2 * stat_val)
    else:
        high = quantiles.quantile(statistics, 1.0-inv)
        low = quantiles.quantile(statistics, inv)
#     print(statistics)
    return low, high


def calc_stats(data, stats, ci=0.95, n_samples=2000):
    if stats == 'median_and_interquartile_range':
        return calc_median_and_interquartile_range(data)
    elif stats == 'mean_and_std_error':
        return calc_mean_and_std_error(data)
    elif stats == 'median_and_bootstrap_percentile':
        return bootstrap(data, ci, n_samples, np.median, 'percentile')
    elif stats == 'median_and_bootstrap_pivotal':
        return bootstrap(data, ci, n_samples, np.median, 'pivotal')
    elif stats == 'median_and_bootstrap_bca':
        return bootstrap(data, ci, n_samples, np.median, 'bca')
    elif stats == 'median_and_bootstrap_pi':
        return bootstrap(data, ci, n_samples, np.median, 'pi')
    elif stats == 'median_and_bootstrap_abc':
        return bootstrap(data, ci, n_samples, np.median, 'abc')
    elif stats == 'mean_and_bootstrap_percentile':
        return bootstrap(data, ci, n_samples, np.mean, 'percentile')
    elif stats == 'mean_and_bootstrap_pivotal':
        return bootstrap(data, ci, n_samples, np.mean, 'pivotal')
    elif stats == 'mean_and_bootstrap_bca':
        return bootstrap(data, ci, n_samples, np.mean, 'bca')
    elif stats == 'mean_and_bootstrap_pi':
        return bootstrap(data, ci, n_samples, np.mean, 'pi')
    elif stats == 'mean_and_bootstrap_abc':
        return bootstrap(data, ci, n_samples, np.mean, 'abc')


def calc_median_and_interquartile_range(data):
    data_sorted = sorted(data)
    median = np.median(data_sorted)
    ci_min = data_sorted[int(0.25*len(data_sorted))]
    ci_max = data_sorted[int(0.75*len(data_sorted))]
    return median, ci_min, ci_max


# def calc_median_and_bootstrap(data, ci=0.95, n_samples=2000, method='pivotal'):
#     data_sorted = sorted(data)
#     median = np.median(data_sorted)
#     ci_min, ci_max = bootstrap(data=data,
#                                ci=ci,
#                                statfunction=np.median,
#                                n_samples=n_samples,
#                                method=method)
#     return median, ci_min, ci_max


def calc_mean_and_std_error(data):
    data_sorted = sorted(data)
    median = np.mean(data_sorted)
    if len(data_sorted) <= 1:
        ci_min = median
        ci_max = median
    else:
        ci_min = median - st.sem(data_sorted)
        ci_max = median + st.sem(data_sorted)
    #ci_min = data_sorted[int(0.25*len(data_sorted))]
    #ci_max = data_sorted[int(0.75*len(data_sorted))]
    return median, ci_min, ci_max


# def calc_mean_and_bootstrap(data, n_samples=2000):
#     data_sorted = sorted(data)
#     median = np.mean(data_sorted)
#     ci_min, ci_max = bootstrap(data=data,
#                                statfunction=np.mean,
#                                n_samples=n_samples)
#     # try:
#     #     ci_min, ci_max = bs.ci(data=data, statfunction=np.mean, n_samples=5000)
#     # except IndexError:
#     #     ci_min = median
#     #     ci_max = median
#     return median, ci_min, ci_max


def mann_whitney_u(data1, data2):
    try:
        _, p_value = st.mannwhitneyu(data1, data2)
    except ValueError:
        p_value = 1
    return p_value


###################
##### CLASSES #####
###################
class DictOfLists(dict):
    def init_key(self, key):
        if not super(DictOfLists, self).__contains__(key):
            super(DictOfLists, self).__setitem__(key, [])        

    def add(self, key, value):
        if not super(DictOfLists, self).__contains__(key):
            super(DictOfLists, self).__setitem__(key, [])
        super(DictOfLists, self).__getitem__(key).append(value)


class CacheException(Exception):
    pass

###################
###### DEBUG ######
###################
class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


debug_enabled = {}

def debug_print(key, *args):
    message = ""
    for arg in args:
        message += (str(arg) + " ") 
    if key in debug_enabled:
        print(bcolors.OKGREEN + str(key) + bcolors.ENDC, "|", message)


###################
####### MISC ######
###################
def dict_to_np_array(dictionary):
    data_points = len(dictionary)
    array = np.zeros(data_points)
    index = 0

    sorted_keys = sorted(dictionary.keys())
    for key in sorted_keys:
        array[index] = dictionary[key]
        index += 1
    return array


def latex_available():
    with open(os.devnull, "w") as f:
        try:
            status = sp.call(["latex","--version"], stdout=f, stderr=f)
        except OSError:
            status = 1
    if status:
        return False
    else:
        return True


def get_treatment_index(treatment_id, data_intr):
        try:
            return int(treatment_id)
        except ValueError:
            pass
        try:
            return data_intr.get_treatment_index(treatment_id)
        except KeyError:
            print("ERROR: Treatment not found: '" + treatment_id +"'")
        return None

    
def parse_treatment_ids(other_treatments, data_intr):
    if not other_treatments:
        return []
    other_treatments = other_treatments.split(",")
    resolved_treatments = []
    for treatment_id in other_treatments:
        treatment_i = get_treatment_index(treatment_id, data_intr)
        if treatment_i is not None:
            resolved_treatments.append(treatment_i)
    return resolved_treatments


def get_renderer(fig):
    if hasattr(fig.canvas, "get_renderer"):
        renderer = fig.canvas.get_renderer()
    else:
        fig.canvas.print_pdf(io.BytesIO())
        renderer = fig._cachedRenderer
    return renderer
