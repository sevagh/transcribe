#!/usr/bin/env python3

import numpy as np
import json
import os
from collections import OrderedDict
from tempfile import TemporaryDirectory
from urllib.request import urlopen
import time
import numpy
import pafy
from pydub import AudioSegment
from pydub.utils import get_array_type
import matplotlib.pylab as plb
import matplotlib.pyplot as plt
import sys
import numba

[x.switch_backend('cairo') for x in [plb, plt]]
np.seterr(divide='ignore', invalid='ignore')

MS_INCREMENT = 100
CUTOFF = 0.97
SMALL_CUTOFF = 0.5
LOWER_PITCH_CUTOFF = 80


def plot_transcription_result(name, data_dict, all_notes):
    font = {'fontname': 'Helvetica Neue'}
    items = [(float(timestamp), val) for timestamp, val in data_dict.items()]
    timestamps, notes = zip(*items)
    pitches = [all_notes[x] for x in notes]
    plt.figure()
    plt.scatter(timestamps, pitches)
    plt.axes().set_yticks(pitches)
    plt.axes().set_yticklabels(notes)
    plt.title(os.path.basename(os.path.normpath(name)), **font)
    plt.xlabel('time (ms)', **font)
    plt.ylabel('note', rotation=0, labelpad=15, **font)
    plb.savefig('{0}.png'.format(time.strftime('%y%m%d%H%M%s')))


def transcribe(path):
    with TemporaryDirectory() as tempdir:
        if path[:3] == 'file':
            _IteratorMedia(urlopen(path)).plot_transcription()
        else:
            p = pafy.new(path)
            file = p.getbestaudio(preftype='m4a').download(
                    filepath=os.path.join(p.title, tempdir))
            _IteratorMedia(file).plot_transcription()


class _IteratorMedia:
    all_notes = json.loads(open('./notemap.json').read())

    def __init__(self, file):
        self.filename = os.path.splitext(os.path.basename(file))[0]
        sound = AudioSegment.from_file(file=file,
                                       format=file.split(
                                           '.')[1]).set_channels(1)
        self.sound_raw = np.frombuffer(
                sound._data,
                dtype=get_array_type(
                    sound.sample_width * 8)).astype(
                            np.float64, copy=False)
        self.sound_raw.setflags(write=1)

        self.raw_length = len(self.sound_raw)
        self.raw_increment = int(MS_INCREMENT *
                                 (len(self.sound_raw) /
                                  sound.duration_seconds / 1000))
        self.sample_rate = sound.frame_rate
        self.mpm = Mpm()

    def _iterate(self):
        tstamp = 0
        left_limit = 0
        while left_limit < self.raw_length:
            yield self.sound_raw[left_limit:min(
                left_limit + self.raw_increment, self.raw_length - 1)], tstamp
            left_limit += self.raw_increment
            tstamp += MS_INCREMENT

    def plot_transcription(self):
        data = OrderedDict()
        for sound_chunk, tstamp in self._iterate():
            note = _get_note_name_from_pitch(
                self.mpm.get_pitch(sound_chunk,
                                   self.sample_rate), _IteratorMedia.all_notes)
            if note is not None:
                data[tstamp] = note
        plot_transcription_result(self.filename, data,
                                  _IteratorMedia.all_notes)


def _get_note_name_from_pitch(pitch, all_notes):
    idx = numpy.abs(numpy.array(list(all_notes.values())) - pitch).argmin()
    return list(all_notes.keys())[idx] if pitch != -1 else None


@numba.jit(cache=True)
def _nsdf(audio_buffer):
    audio_buffer -= np.mean(audio_buffer)
    autocorr_f = np.correlate(audio_buffer, audio_buffer, mode='full')
    nsdf = np.true_divide(autocorr_f[int(autocorr_f.size/2):],
                          autocorr_f[int(autocorr_f.size/2)])
    nsdf[nsdf == np.inf] = 0
    nsdf = np.nan_to_num(nsdf)
    return nsdf


@numba.jit(cache=True, nopython=True)
def _peak_picking(nsdf):
    pos = 0
    cur_max_pos = 0

    length_nsdf = len(nsdf)

    while (pos < (length_nsdf - 1) / 3) and (nsdf[pos] > 0):
        pos += 1

    while (pos < length_nsdf - 1) and (nsdf[pos] <= 0.0):
        pos += 1

    if pos == 0:
        pos = 1

    max_positions = []
    while pos < length_nsdf - 1:
        if (nsdf[pos] > nsdf[pos - 1]) and (
                nsdf[pos] >= nsdf[pos + 1]):
            if cur_max_pos == 0 or\
               nsdf[pos] > nsdf[cur_max_pos]:
                cur_max_pos = pos
            elif nsdf[pos] > nsdf[cur_max_pos]:
                cur_max_pos = pos

        pos += 1
        if pos < length_nsdf - 1 and nsdf[pos] <= 0:
            if cur_max_pos > 0:
                max_positions.append(cur_max_pos)
                cur_max_pos = 0
            while pos < length_nsdf - 1 and nsdf[pos] <= 0:
                pos += 1

    if cur_max_pos > 0:
        max_positions.append(cur_max_pos)
    return max_positions


class Mpm:
    def __init__(self):
        self._max_positions = []
        self._period_estimates = []
        self._amp_estimates = []

    def get_pitch(self, audio_buffer, sample_rate):
        self._max_positions.clear()
        self._period_estimates.clear()
        self._amp_estimates.clear()

        self._nsdf = _nsdf(audio_buffer)
        self._max_positions = _peak_picking(self._nsdf)

        highest_amplitude = float('-inf')

        for tau in self._max_positions:
            highest_amplitude = max(highest_amplitude, self._nsdf[tau])

            if self._nsdf[tau] > SMALL_CUTOFF:
                def _parabolic_interpolation(nsdf, tau):
                    nsdfa, nsdfb, nsdfc = nsdf[tau - 1:tau + 2]
                    b_value = tau
                    bottom = nsdfc + nsdfa - 2 * nsdfb
                    if bottom == 0.0:
                        turning_point_x = b_value
                        turning_point_y = nsdfb
                    else:
                        delta = nsdfa - nsdfc
                        turning_point_x = b_value + delta / (2 * bottom)
                        turning_point_y = nsdfb - delta * delta / (8 * bottom)
                    return turning_point_x, turning_point_y
                turning_point_x, turning_point_y = _parabolic_interpolation(
                    self._nsdf, tau)
                self._amp_estimates.append(turning_point_y)
                self._period_estimates.append(turning_point_x)
                highest_amplitude = max(highest_amplitude, turning_point_y)

        if not self._period_estimates:
            pitch = -1
        else:
            actual_cutoff = CUTOFF * highest_amplitude

            period_index = 0
            for i in range(0, len(self._amp_estimates)):
                if self._amp_estimates[i] >= actual_cutoff:
                    period_index = i
                    break

            period = self._period_estimates[period_index]
            pitch_estimate = sample_rate / period
            if pitch_estimate > LOWER_PITCH_CUTOFF:
                pitch = pitch_estimate
            else:
                pitch = -1

        return pitch


if __name__ == '__main__':
    try:
        transcribe(sys.argv[1])
    except IndexError:
        print('Rerun with url as first arg', file=sys.stderr)
