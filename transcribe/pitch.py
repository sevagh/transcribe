import numpy
import scipy.signal
import numba


@numba.jit(cache=True)
def _nsdf(audio_buffer):
    audio_buffer -= numpy.mean(audio_buffer)
    autocorr_f = scipy.signal.correlate(audio_buffer, audio_buffer)
    nsdf = numpy.true_divide(
        autocorr_f[int(autocorr_f.size / 2) :], autocorr_f[int(autocorr_f.size / 2)]
    )
    nsdf[nsdf == numpy.inf] = 0
    nsdf = numpy.nan_to_num(nsdf)
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
        if (nsdf[pos] > nsdf[pos - 1]) and (nsdf[pos] >= nsdf[pos + 1]):
            if cur_max_pos == 0 or nsdf[pos] > nsdf[cur_max_pos]:
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


@numba.jit(cache=True, nopython=True)
def _parabolic_interpolation(nsdf, tau):
    nsdfa, nsdfb, nsdfc = nsdf[tau - 1 : tau + 2]
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


class Mpm:
    def __init__(self, cutoff=0.97, small_cutoff=0.5, lower_pitch_cutoff=80):
        numpy.seterr(divide="ignore", invalid="ignore")
        self._max_positions = []
        self._period_estimates = []
        self._amp_estimates = []
        self.cutoff = cutoff
        self.small_cutoff = small_cutoff
        self.lower_pitch_cutoff = lower_pitch_cutoff

    def get_pitch(self, audio_buffer, sample_rate):
        self._max_positions.clear()
        self._period_estimates.clear()
        self._amp_estimates.clear()

        self._nsdf = _nsdf(audio_buffer)
        self._max_positions = _peak_picking(self._nsdf)

        highest_amplitude = float("-inf")

        for tau in self._max_positions:
            highest_amplitude = max(highest_amplitude, self._nsdf[tau])

            if self._nsdf[tau] > self.small_cutoff:
                turning_point_x, turning_point_y = _parabolic_interpolation(
                    self._nsdf, tau
                )
                self._amp_estimates.append(turning_point_y)
                self._period_estimates.append(turning_point_x)
                highest_amplitude = max(highest_amplitude, turning_point_y)

        if not self._period_estimates:
            pitch = -1
        else:
            actual_cutoff = self.cutoff * highest_amplitude

            period_index = 0
            for i in range(0, len(self._amp_estimates)):
                if self._amp_estimates[i] >= actual_cutoff:
                    period_index = i
                    break

            period = self._period_estimates[period_index]
            pitch_estimate = sample_rate / period
            if pitch_estimate > self.lower_pitch_cutoff:
                pitch = pitch_estimate
            else:
                pitch = -1

        return pitch
