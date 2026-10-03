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
