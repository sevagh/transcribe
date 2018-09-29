## transcribe music

Transcribe will chop the music up into time slices and detect the pitch of the raw audio data of each slice using the [McLeod pitch method](http://miracle.otago.ac.nz/tartini/papers/A_Smarter_Way_to_Find_Pitch.pdf).

```
(transcribe-venv) sevagh:transcribe $ ./transcribe.py \
	/home/sevagh/repos/transcribe/'Guitar Tuning Standard EADGBE-bKS_m7JObxg.m4a'
```

<img src="./.github/guitar_eadgbe_out.png" width=300px>

### System dependencies

This project uses Conda for development. On Fedora: `sudo dnf install cairo-devel libffi-devel python3-tkinter ffmpeg ffmpeg-devel`

#### xar

Additional system dependencies for playing around with https://github.com/facebookincubator/xar: `sudo dnf install squashfs-tools squashfuse`

### Additional reading

* [Speeding up real-time pitch detection with FFT autocorrelation](./doc/snac.md)
* [Speeding up numpy-based pitch detection with numba and scipy](./doc/snac2.md)
* [Packaging Python code with XAR](./doc/xar.md)
