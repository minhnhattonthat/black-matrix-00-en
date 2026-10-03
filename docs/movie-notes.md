# Movie subtitle notes

## Tools

- jPSXdec 2.0: `tools/jpsxdec/jpsxdec_v2.0/jpsxdec.jar` (Java 8).
- ffmpeg reads a stream with `-f psxstr` once it is wrapped into 2352-byte raw sectors (`movie.wrap`).
- faster-whisper 1.2.1, CUDA visible to ctranslate2 (transcription only).

## Probe (BMM_003.STR, 14 s)

- jPSXdec indexes the bare 2336-byte stream as dumped by dumpsxiso: item 0 = video
  (320x240, 10 sectors per frame, header frames 1..N), item 1 = XA audio.
- `-replaceframes` patches the file in place. File size is unchanged, audio sectors are
  untouched, only the sectors of the replaced frame change.
- The `frame="N"` attribute is a 0-based index: `frame="31"` changed the frame whose STR
  header number is 32. ffmpeg's decoded frame n is therefore jPSXdec frame n, header n+1.
- jPSXdec resolves the stream name in the index and the PNG paths in the XML relative to
  the current directory: run it with cwd = the directory holding the stream.

Constants for `movie.py`: `FRAME_BASE = 0`, bare stream (no wrapping for jPSXdec).

## Content of the Disc 1 streams

| stream | speech | subtitles |
|--------|--------|-----------|
| BMM_001 (36 s) | battle lines, Pain Ring calls | 8 cues |
| BMM_002 (101 s) | opening narration | 13 cues |
| BMM_003, 004, 007, 011 | none (music; Whisper invents a line over music) | none |
| BMM_005 (149 s) | Cain / inner voice; 20-90 s is a song, not transcribed | 16 cues |
| BMM_006 (16 s) | dream voices | 7 cues, all flagged `check` |
| BMM_013..018 (10 s) | chapter start card, title visible 4.0-7.0 s | title cue |
| BMM_023..028 (6 s) | eyecatch, title visible 3.0-4.6 s | title cue |
| BMM_035 | logo only | none |

Transcription: faster-whisper large-v3 on CPU (no cuBLAS here), word timestamps, phrases cut
at pauses over 0.6 s, then corrected by hand. `work/movie/make_cues.py` holds the corrected
cues that produced `script/MOVIE/*.json`.
