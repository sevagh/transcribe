Speeding up numpy-based pitch detection with numba and scipy
============================================================

[2018-04-14] Profiling and optimization to make a numpy.correlate-based music transcriber faster
------------------------------------------------------------------------------------------------

# Motivation

An almost 3-year follow up to [this post](./snac.md).

I have relatively old [Python code](https://github.com/sevagh/transcribe) that attempts to transcribe music with the McLeod Pitch Method, which is based on autocorrelation via [`numpy.correlate`](https://docs.scipy.org/doc/numpy/reference/generated/numpy.correlate.html).

My goals are to modernize the code, improve its performance, and learn something deeper about Python and its scientific ecosystem.

## Conda

In discussing Numba on [their gitter](gitter.im/numba/numba), I was told that the dev build of Numba had support for `numpy.correlate` and to use Conda to install it. I was aware of the Conda project but I had never actually used it yet.

I [converted my project](https://github.com/sevagh/transcribe/tree/4120b9cdc46097fa71ab25e44d71385d9e72bf82) from pip-based to conda-based and after some sticky moments of the conversion (including splitting my pip requirements.txt into one list for Conda and one for pip) it felt better than the primitive way I was invoking regular virtualenvs.

We can see from the Numba commits that the [release 0.38](https://github.com/numba/numba/commit/a0390f660c7e78e144237d737f2089c9f0d77f0b) is the one which contains the `np.correlate` support, and to install this with Conda from the Numba dev channel is easy:

```shell
$ conda install -c numba numba=0.38 -f
```

# Profiling

Profiler annotation output from profilehooks:

```
ncalls  tottime  percall  cumtime  percall filename:lineno(function)
1    0.007    0.007    7.037    7.037 transcribe.py:80(plot_transcription)
601    0.043    0.000    5.011    0.008 transcribe.py:104(get_pitch)
601    0.090    0.000    2.991    0.005 transcribe.py:109(_nsdf)
601    0.003    0.000    2.727    0.005 numeric.py:873(correlate)
601    2.721    0.005    2.721    0.005 {built-in method numpy.core.multiarray.correlate2}
1    0.000    0.000    1.972    1.972 transcribe.py:29(plot_transcription_result)
601    1.932    0.003    1.938    0.003 transcribe.py:167(_peak_picking)
```

It looks like I can make big wins by improving the call to numpy `correlate` and my own method `_peak_picking`.

Hyperfine time benchmark:

```
$ hyperfine --min-runs 10 './transcribe.py https://www.youtube.com/watch?v=bKS_m7JObxg'
Benchmark #1: ./transcribe.py https://www.youtube.com/watch?v=bKS_m7JObxg

  Time (mean ± σ):     13.487 s ±  1.844 s    [User: 8.672 s, System: 0.710 s]

  Range (min … max):   10.477 s … 16.439 s
```

# Numba

## Without numpy in `_peak_picking`

The method I first chose to annotate with numba's jit annotation is `_peak_picking()`, which isn't leveraging numpy.

It's the only code that took any significant CPU time outside of the final plotting phase (not too important) and numpy's correlation.

Let's check the timing improvements:

* jit(cache=True)

```shell
$ hyperfine --min-runs 10 './transcribe.py https://www.youtube.com/watch?v=bKS_m7JObxg' -w 3
Benchmark #1: ./transcribe.py https://www.youtube.com/watch?v=bKS_m7JObxg

  Time (mean ± σ):     12.624 s ±  0.988 s    [User: 12.085 s, System: 0.501 s]

  Range (min … max):   10.811 s … 14.200 s
```
Less than a second saved from the mean time.

* jit(cache=True, nopython=True)

When first running nopython=True, numba gave the following warning:

```
File "transcribe.py", line 169:
    def _peak_picking(self):
        pos = 0
        ^

This error may have been caused by the following argument(s):
- argument 0: cannot determine Numba type of <class '__main__.Mpm'>
```

Because `_peak_picking` is a class method, that blocks Numba from proceeding. I rewrote it to receive the autocorrelated array as an argument, instead of via `self`.

Hyperfine results:

```
$ hyperfine --min-runs 10 './transcribe.py https://www.youtube.com/watch?v=bKS_m7JObxg' -w 3
Benchmark #1: ./transcribe.py https://www.youtube.com/watch?v=bKS_m7JObxg

  Time (mean ± σ):     10.263 s ±  1.138 s    [User: 7.965 s, System: 0.359 s]

  Range (min … max):    8.868 s … 12.665 s
```

Shaved off an additional 2s!

* jit(cache=True, nopython=True, parallel=True)

Parallel made no additional difference. I assume that means this code is unparallelizable.

## With numpy in `_nsdf`

The next thing we'll tackle is the loop that contains the call to `numpy.correlate`. Now to clear things up, the support for `numpy.correlate` in Numba's latest dev build is only for `mode='valid'`, the default mode of correlate.

For the McLeod Pitch Method to work correctly we need `mode='full'`. What this ultimately means is that the `nopython` mode of numba's jit will not work.

In this case we're annotating the method which contains the call to `numpy.correlate`, `_nsdf()`.

* jit(cache=True)

No additional time saved.

* jit(cache=True, nopython=True)

Just to prove to ourselves that this doesn't work (yet):

```
Invalid usage of Function(<function correlate at 0x7f027759ee18>) with parameters (array(float64, 1d, C), array(float64, 1d, C), mode=const('full'))
 * parameterized
In definition 0:
    TypeError: _np_correlate() got an unexpected keyword argument 'mode'
    raised from /home/sevagh/miniconda3/envs/transcribe-venv/lib/python3.6/site-packages/numba/typing/templates.py:309
[1] During: resolving callee type: Function(<function correlate at 0x7f027759ee18>)
[2] During: typing of call at ./transcribe.py (102)


File "transcribe.py", line 102:
def _nsdf(audio_buffer):
    <source elided>
    audio_buffer -= np.mean(audio_buffer)
    autocorr_f = np.correlate(audio_buffer, audio_buffer, mode='full')
    ^
```

* Correlation vs. convolution

There's also `np.convolve`, and I don't remember enough of my formal signal processing education.

If somehow I could get a correlation from a convolution, I'd be able to use `nopython=True` with `np.convolve(_, _, mode='full')`.

Since my data is positive and real, I had an inkling that the convolution and correlation might be similar, but when I tried to replace the correlate call with convolve, the output data was completely incorrect.

## Without numpy in `_nsdf`

If you read the original blog post ([another link](../snac)), you'd see that the thing I was celebrating was improving over my own correlation implementation with Numpy's correlate.

Let's go back to that old code and see if Numba's jit settings can make it beat `numpy.correlate`.

Code side by side. Numpy:

```python
def _nsdf(audio_buffer):
    audio_buffer -= np.mean(audio_buffer)
    autocorr_f_valid = np.correlate(audio_buffer, audio_buffer, mode='valid    ')
    autocorr_f = np.correlate(audio_buffer, audio_buffer, mode='full')
    print('Valid val: {0}'.format(autocorr_f_valid))
    nsdf = np.true_divide(autocorr_f[int(autocorr_f.size/2):],
                          autocorr_f[int(autocorr_f.size/2)])
    nsdf[nsdf == np.inf] = 0
    nsdf = np.nan_to_num(nsdf)
    return nsdf
```

No numpy:

```python
def _nsdf(audio_buffer):
    length_audio_buffer = len(audio_buffer)
    median = np.median(np.array(audio_buffer))
    nsdf = [0.0] * length_audio_buffer
    for tau in range(0, length_audio_buffer):
        acf = 0
        divisor_m = 0
        for i in range(0, length_audio_buffer - tau):
            acf += (audio_buffer[i]-median) * (audio_buffer[i + tau]-median    )
            divisor_m += (audio_buffer[i]-median) * (audio_buffer[i]-median    ) + (audio_buffer[i + tau]-median) * (audio_buffer[i + tau]-median)
        if divisor_m != 0:
            nsdf[tau] = 2 * acf / divisor_m
    return nsdf
```


Indeed the performance is slow as all hell, and single-threaded to boot. This makes me wonder if `nopython=True,parallel=True` in Numba is going to have a huge impact.

Ultimately, the execution time is so slow (60s+) that I get bored of waiting and cancel the benchmark.

## Scipy

First, I removed the youtube-dl components of the program to just accept a filesystem path to transcribe. Baseline benchmark:

```
$ hyperfine --min-runs 10 './transcribe.py /home/sevagh/repos/transcribe/"Guitar Tuning Standard EADGBE-bKS_m7JObxg.m4a"' -w 1
Benchmark #1: ./transcribe.py /home/sevagh/repos/transcribe/"Guitar Tuning Standard EADGBE-bKS_m7JObxg.m4a"

  Time (mean ± σ):      6.803 s ±  0.131 s    [User: 10.412 s, System: 0.434 s]

  Range (min … max):    6.672 s …  7.070 s
```

~7s, compared to yesterday's ~10s, gained from stripping out the download of the file.

After replacing `numpy.correlate` with `scipy.correlate`, the time is reduced down to ~3s:

```
$ hyperfine --min-runs 10 './transcribe.py /home/sevagh/repos/transcribe/"Guitar Tuning Standard EADGBE-bKS_m7JObxg.m4a"' -w 1 --capture-output
Benchmark #1: ./transcribe.py /home/sevagh/repos/transcribe/"Guitar Tuning Standard EADGBE-bKS_m7JObxg.m4a"

  Time (mean ± σ):      3.073 s ±  0.586 s    [User: 2.758 s, System: 0.205 s]

  Range (min … max):    2.460 s …  4.191 s
```

# Conclusion

Trust in the big Python science projects (numpy, scipy, numba) and use their features properly. Also, Conda is cool.
