# EA Plotting Scripts
A set of plotting scripts specifically designed to the plot the results of evolutionary algorithm experiments.

# Usage
While the package includes many different scripts for different scenarios, the most common script you probably want to run 
is createPlots.py. With the default behavior of createPlots.py you need to provide at least one argument. If the argument is a
file, createPlots.py assumes that you wish to plot the data of this file. When plotting a file, createPlots.py assumes
your data is organized in columns, with the first column containing the generation number, and the second column containing
the value (e.g. performance) at that generation. When the argument is a directory, createPlots.py will assume that each file
in that directory holds data you want to plot, and that all files belong to the same treatment. The script will read all files,
calculate the median at each generation across all files, and then plot that median with its associated interquartile range.
If multiple directories are provided, each directory will be considered as a separate treatment, and thus a different median
will be plotted for each directory provided. In addition, the plotting script will calculate statistical signficance 
(Mann-Withney U) between the first treatment and the other treatments at each generation, and it will plot the results of these
tests as symbols below the plot.

