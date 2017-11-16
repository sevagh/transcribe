# transcribe
## transcribe music

Transcribe youtube URLs or audio files. Transcribe will chop the music up into little pieces (based on time) and detect the pitch of the raw audio data using the McLeod pitch method - [McLeod paper pdf here](http://miracle.otago.ac.nz/tartini/papers/A_Smarter_Way_to_Find_Pitch.pdf).

`./transcribe.py https://www.youtube.com/watch?v=bKS_m7JObxg`

<img src="./samples/guitar_eadgbe_out.png" width=300px>

### System dependencies

On Fedora: `sudo dnf install cairo-devel libffi-devel python3-tkinter ffmpeg ffmpeg-devel`
