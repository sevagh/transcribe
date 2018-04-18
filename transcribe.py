#!/usr/bin/env python3

import sys
from tempfile import TemporaryDirectory
from transcribe.music import SongSplitter
from transcribe.pitch import Mpm
from transcribe.plot import Plotter


if __name__ == '__main__':
    with TemporaryDirectory() as tempdir:
        try:
            song = SongSplitter(sys.argv[1])
            song.set_pitch_detector(Mpm())
            song.set_plotter(Plotter())
            song.plot_transcription()
        except IndexError:
            print('Rerun with file path as first arg', file=sys.stderr)
