# Movie subtitles (Disc 1) — design

Burn English subtitles into the FMV streams in `MOVIE/*.STR`. The game's
text pipeline is untouched; this is a separate video path.

## Material

21 streams, all 320x240 MDEC at 15 fps with one mono 37.8 kHz XA channel,
stored by dumpsxiso as 2336-byte sectors.

| files | length | content |
|-------|--------|---------|
| BMM_001..007, 011 | 14 s .. 149 s, ~8.5 min total | story movies |
| BMM_013..018 | 10 s each | chapter title cards (Japanese title + English tagline in the image) |
| BMM_023..028, 035 | 6 s each | short clips, content to be checked |

## Scope

- Story movies: subtitle all speech.
- Chapter cards: the translated title as a subtitle; the image is not redrawn.
- Short clips: subtitle only if they hold speech or Japanese text.
- Out of scope: Disc 2 movies (same pipeline later), redrawing graphics,
  runtime text overlay.

## Text source

1. `ffmpeg -f psxstr` extracts audio (the STR is first wrapped into 2352-byte
   raw sectors: sync + header + the 2336 bytes).
2. faster-whisper (large-v3, GPU) transcribes Japanese with segment timings.
3. Claude corrects names/terms against `glossary.md` and the translated
   script, translates in the established style, and marks doubtful lines.

Cues are stored in `script/MOVIE/BMM_0NN.json`:

    {"id": "MOVIE/001/03", "start": 12.40, "end": 15.10,
     "jp": "...", "en": "...", "check": true}

`check` is optional and marks a line whose Japanese the user should verify.
Times are seconds from the start of the stream. A cue with empty `en` is not
burned.

## Rendering and insertion (`movie.py`)

- `ass(cues) -> str`: an ASS subtitle document. Style: bottom-centred, white,
  dark outline, PlayResX/Y 320x240, at most 2 lines of 42 characters (longer
  text is wrapped; a cue that needs 3 lines raises).
- `frames(cues, fps=15) -> list[range]`: frame ranges covered by cues.
- `patch(src_str, cues, dst_str)`: decode the frames in those ranges with
  ffmpeg with the ASS burned in, then `jpsxdec -replaceframes` writes them
  back into a copy of the stream. Frames outside cue ranges and all audio
  sectors stay byte-identical; file size is unchanged.
- Cache: `work/movie/cache/<name>-<sha1 of cues + source>.STR`. `build.patch()`
  copies the cached stream into the build tree, or the original when a movie
  has no translated cues.

If jPSXdec cannot index a bare 2336-byte STR, the fallback is to patch the
2352-byte wrapped copy and unwrap it; the pilot decides.

## Tools

- ffmpeg (installed), Java 8 (installed).
- jPSXdec in `tools/jpsxdec/` (downloaded release).
- `pip install faster-whisper` (transcription only; not needed to build once
  the cue files exist).

## Order of work

Pilot on BMM_001: transcribe, translate, burn, build; the user judges
readability and timing in DuckStation. Then the remaining movies, then the
chapter cards and short clips.

## Risks

- Transcription over music can be wrong or miss lines: `check` flags plus the
  user's spot-check.
- A re-encoded frame must fit its original sectors: the subtitle band may be
  soft in busy scenes; jPSXdec raises quantisation as needed and fails loudly
  if a frame cannot fit.
- Font legibility at 320x240: decided in the pilot.

## Testing

- `ass()`: timing format, wrapping at 42, 3-line cue raises, empty `en` skipped.
- `frames()`: second-to-frame rounding, merged overlapping cues.
- `patch()` with no cues returns the source bytes; a patched stream has the
  same length, identical audio sectors, and differs only in video sectors of
  frames inside cue ranges.
- `test_build` identity build unchanged (movies restored from the originals).
