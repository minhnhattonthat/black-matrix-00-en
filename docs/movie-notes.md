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
| BMM_002 (101 s) | opening narration | 15 cues |
| BMM_003, 011 | none (Whisper invents a stock line over music) | none |
| BMM_004 (40 s) | one line at the end | 1 cue, flagged |
| BMM_005 (149 s) | Cain and the inner voice, throughout | 40 cues |
| BMM_006 (16 s) | dream voices | 6 cues |
| BMM_007 (50 s) | four lines from 30 s | 4 cues |
| BMM_013..018 (10 s) | chapter start card, title visible 4.0-7.0 s | title cue |
| BMM_023..028 (6 s) | eyecatch, title visible 3.0-4.6 s | title cue |
| BMM_035 | logo only | none |

Transcription: faster-whisper large-v3 on CPU (no cuBLAS here), word timestamps, **VAD filter
off**. With the filter on, speech under music was dropped silently: two narration lines in
BMM_002, most of BMM_005, all of BMM_007. Without it Whisper adds stock hallucinations over
pure music (high no-speech probability; discard them by hand). `work/movie/make_cues.py`
holds the hand-corrected cues that produced `script/MOVIE/*.json`.

## Disc 2

Pristine copies live in `work/orig2/MOVIE`; `build.patch_movies(ORIG2/MOVIE, DISC2/MOVIE)` uses the
same cue files (a stream name is the same movie on either disc: 001, 002, 011, 035 are
byte-identical across discs).

| stream | speech | subtitles |
|--------|--------|-----------|
| BMM_008 (36 s) | Cain | 4 cues |
| BMM_009 / 010 (47 s) | two variants of the same scene (rule / destroy) | 5 / 3 cues; 010 may have an unheard line near 30 s |
| BMM_012, 033, 034 | none | none |
| BMM_019..022 / 029..032 | chapter 7, 8, 9 and final chapter cards | title cue |
