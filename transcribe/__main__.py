import sys
from tempfile import TemporaryDirectory
from .music import SongSplitter
from .pitch import Mpm
from .plot import Plotter


def main():
    with TemporaryDirectory() as tempdir:
        try:
            song = SongSplitter(sys.argv[1])
            song.set_pitch_detector(Mpm())
            song.set_plotter(Plotter())
            retfile = song.plot_transcription()
            print("Plotted transcription result to '{0}'".format(retfile))
        except IndexError:
            print("Rerun with file path as first arg", file=sys.stderr)


if __name__ == "__main__":
    main()
