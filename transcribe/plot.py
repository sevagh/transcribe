import os
import time
import matplotlib.pylab
import matplotlib.pyplot


class Plotter(object):
    def __init__(self):
        [x.switch_backend("cairo") for x in [matplotlib.pylab, matplotlib.pyplot]]
        self.font = {"fontname": "DejaVu Sans"}

    def plot_transcription_result(self, name, data_dict, all_notes):
        items = [(float(timestamp), val) for timestamp, val in data_dict.items()]
        timestamps, notes = zip(*items)
        pitches = [all_notes[x] for x in notes]
        matplotlib.pyplot.figure()
        matplotlib.pyplot.scatter(timestamps, pitches)
        matplotlib.pyplot.yticks(pitches, notes)
        matplotlib.pyplot.title(os.path.basename(os.path.normpath(name)), **self.font)
        matplotlib.pyplot.xlabel("time (ms)", **self.font)
        matplotlib.pyplot.ylabel("note", rotation=0, labelpad=15, **self.font)
        filename = "{0}-{1}.png".format(name, time.strftime("%y%m%d%H%M%s"))
        matplotlib.pylab.savefig(filename)
        return filename
