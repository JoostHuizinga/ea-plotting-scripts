
import sys
import os.path
import re

import numpy as np
import scikits.bootstrap as bs
import scipy.stats as st


import io
import random
import quantiles
from enum import Enum



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


class CacheException(Exception):
    pass



               

###################
## Treatment List #
###################


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
                                   method='bca',
                                   alpha=1-ci)
        except IndexError:
            ci_min = stat
            ci_max = stat
    return stat, ci_min, ci_max


def my_bootstrap(data, ci=0.95, n_samples=10000, is_pivotal=True, statfunction=np.mean):
    """
    While our method is much slower, it does not throw an exception when the
    median value exists twice in the data.

    To recap, let "f" be the true probability distribution from which we have drawn our data.
    - "statfunction" or "T" is the parameter of "f" that we want to estimate, such as its mean.
    - "true_stat_val" or "\\theta" is the true value of our statistics when calculated over "f": \theta = statfunction(f)
    - Then "data" or "X" is a sample from that distribution.
    - "stat_val" or "\\theta\\hat" is an approximation of the "statfunction" obtained by calculating it
      over our sample of data instead: statfunction(data) ~= statfunction(f).
    - Because "stat_val" is an estimate obtained by sampling, it will have a distribution as well.
      If we would resample "data" and recalculate "stat_val" a 1,000 times, we would get 1,000 different
      values.
    - "f\\hat_n" is what you get when you interpret "data" as a distribution you can sample from.
      The underlying idea of bootstrapping is that "f\\hat_n" will behave like "f", but is much easier
      to sample from.
    - "bootstrap_stat_val" or "\\theta\\hat^star_1" is a new estimate of "stat_val", calculated by sampling from "f\\hat_n" and
      applying "statfunction" over that sample, called a bootstrap sample.
    - "statistics" or "M" is a list of "n_samples" (or "m") sampled statistics.

    The pivot confidence interval argues that the behavior of "true_stat_val - stat_val" is roughly the same as
    the behavior of "stat_val - bootstrap_stat_val".

    So, we say that, with 95% confidence, any bootstrap_stat_val value will be:
    * bootstrap_stat_values[0.025] <= bootstrap_stat_val <= bootstrap_stat_values[0.975]

    We can subtract "stat_val" from all terms without changing the meaning:
    * bootstrap_stat_values[0.025] - stat_val <= bootstrap_stat_val - stat_val <= bootstrap_stat_values[0.975] - stat_val

    We can flip the order and the "smaller than" signs to "greater than" signs:
    * stat_val - bootstrap_stat_values[0.025] >= stat_val - bootstrap_stat_val >= stat_val - bootstrap_stat_values[0.975]

    Now we replace "stat_val - bootstrap_stat_val" with "true_stat_val - stat_val", the thing we actually care about:
    * stat_val - bootstrap_stat_values[0.025] >= true_stat_val - stat_val >= stat_val - bootstrap_stat_values[0.975]

    Finally, we add "stat_val" to all terms:
    * 2 * stat_val - bootstrap_stat_values[0.025] >= true_stat_val >= 2 * stat_val - bootstrap_stat_values[0.975]

    Meaning this is low:
    low = 2 * stat_val - bootstrap_stat_values[0.975]

    And this is high:
    high = 2 * stat_val - bootstrap_stat_values[0.025]
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
        _, p_value = st.mannwhitneyu(data1, data2, alternative="two-sided")
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
