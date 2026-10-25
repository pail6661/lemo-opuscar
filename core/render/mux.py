#!/usr/bin/env python3
"""Cross-platform final mux: python core/render/mux.py video.mp4 mix.wav out.mp4 [fps] [grain].

Only Python's standard library and ffmpeg/ffprobe are required. The original
output is replaced atomically after encoding and verification have succeeded.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile


class MuxError(Exception):
    """An input, decoding, encoding or verification failure."""


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                encoding="utf-8", errors="replace", check=False)
    except OSError as error:
        raise MuxError(f"cannot run {command[0]}: {error}") from error
    if result.returncode:
        detail = "\n".join(result.stderr.splitlines()[-8:])
        raise MuxError(f"{Path(command[0]).name} failed (exit {result.returncode}):\n{detail}")
    return result


def probe(path: Path, ffprobe: str) -> dict:
    result = run([ffprobe, "-v", "error", "-show_entries",
                  "stream=codec_type,duration:format=duration", "-of", "json", str(path)])
    try:
        return json.loads(result.stdout)
    except ValueError as error:
        raise MuxError(f"ffprobe returned invalid metadata for '{path}'") from error


def seconds(value: object) -> float | None:
    try:
        number = float(value)
        return number if math.isfinite(number) and number > 0 else None
    except (TypeError, ValueError):
        return None


def duration(metadata: dict, kind: str) -> float | None:
    for stream in metadata.get("streams", []):
        if stream.get("codec_type") == kind:
            value = seconds(stream.get("duration"))
            if value is not None:
                return value
    return seconds(metadata.get("format", {}).get("duration"))


def wav_header(path: Path) -> bool:
    """Reject incomplete RIFF data; return whether its data length is unknown.

ffmpeg writes 0xffffffff in WAVs sent through stdout. Those valid streamed
WAVs must not be rejected for the demuxer's fixed end-of-stream notices.
"""
    size = path.stat().st_size
    with path.open("rb") as source:
        header = source.read(12)
        if len(header) < 12 or header[:4] != b"RIFF" or header[8:12] != b"WAVE":
            return False
        offset = 12
        while offset + 8 <= size:
            source.seek(offset)
            chunk_id, length = struct.unpack("<4sI", source.read(8))
            if chunk_id == b"data":
                if length in (0, 0xFFFFFFFF):
                    return True
                if offset + 8 + length > size:
                    raise MuxError(f"the WAV file '{path}' is cut off: its header promises "
                                   "more audio than the file contains")
                return False
            offset += 8 + length + (length & 1)
    return False


ERROR_WORDS = re.compile(r"error|invalid|corrupt|header missing|overread|truncat|incomplete", re.I)
LEVEL_NUMBER = r"(?:[-+]?inf|[-+]?(?:\d+(?:\.\d*)?|\.\d+))"
STREAMED_WAV_NOTICES = re.compile(
    r"Ignoring maximum wav data size|Packet corrupt \(stream = \d+, dts = NOPTS\)|"
    r"corrupt input packet in stream \d+")


def decoding_errors(log: str, streamed_wav: bool) -> list[str]:
    errors = []
    for line in log.splitlines():
        if line.startswith("[") and ERROR_WORDS.search(line):
            if streamed_wav and STREAMED_WAV_NOTICES.search(line):
                continue
            errors.append(line)
    return errors


def decoded_duration(log: str) -> float:
    times = re.findall(r"^out_time=(\d+):(\d+):(\d+(?:\.\d+)?)$", log, re.M)
    if not times:
        raise MuxError("ffmpeg did not report a decoded audio duration")
    hours, minutes, secs = times[-1]
    value = int(hours) * 3600 + int(minutes) * 60 + float(secs)
    if value <= 0:
        raise MuxError("the audio did not decode to any samples")
    return value


def loudness_json(log: str) -> dict:
    decoder = json.JSONDecoder()
    for match in re.finditer(r"\{", log):
        try:
            data, _ = decoder.raw_decode(log[match.start():])
        except ValueError:
            continue
        if isinstance(data, dict) and "input_i" in data:
            return data
    raise MuxError("ffmpeg did not return its loudness measurement")


def note(message: str) -> None:
    print(f"mux.py: {message}", file=sys.stderr)


def mux(video: Path, audio: Path, output: Path, fps: float, grain: float,
        color: str, ffmpeg: str, ffprobe: str) -> dict[str, float]:
    for path, label in ((video, "video"), (audio, "audio")):
        if not path.is_file():
            raise MuxError(f"{label} not found: {path}")
    if output.resolve() in (video.resolve(), audio.resolve()):
        raise MuxError("output must be different from both input files")
    if not output.parent.is_dir():
        raise MuxError(f"output directory does not exist: {output.parent}")

    streamed_wav = wav_header(audio)
    audio_metadata = probe(audio, ffprobe)
    if not any(s.get("codec_type") == "audio" for s in audio_metadata.get("streams", [])):
        raise MuxError(f"no audio stream in '{audio}' (is it really the mixed audio file?)")
    video_metadata = probe(video, ffprobe)
    if not any(s.get("codec_type") == "video" for s in video_metadata.get("streams", [])):
        raise MuxError(f"no video stream in '{video}'")
    video_duration = duration(video_metadata, "video")
    if video_duration is None:
        raise MuxError(f"could not determine the video duration of '{video}'")

    # Measure actual decoded length without loudnorm. ffmpeg 6.1 reports a
    # duration about 2.9 s too short when loudnorm is present in this pass.
    decoded = run([ffmpeg, "-hide_banner", "-nostats", "-progress", "pipe:2",
                   "-i", str(audio), "-map", "0:a:0", "-vn", "-f", "null", "-"])
    decoded_seconds = decoded_duration(decoded.stderr)
    errors = decoding_errors(decoded.stderr, streamed_wav)
    if errors:
        raise MuxError(f"the audio '{audio}' is damaged; ffmpeg reported while decoding:\n"
                       + "\n".join(errors[:3]))
    claimed_seconds = duration(audio_metadata, "audio")
    if claimed_seconds is not None and "Estimating duration from bitrate" not in decoded.stderr:
        if claimed_seconds - decoded_seconds > max(claimed_seconds * .05, .15):
            raise MuxError(f"only {decoded_seconds:g} s of the {claimed_seconds:g} s that "
                           f"'{audio}' claims could be decoded: the file is damaged or cut off")
    if streamed_wav and any(STREAMED_WAV_NOTICES.search(line) for line in decoded.stderr.splitlines()):
        note("note: streamed WAV has an unknown header length; all audio decoded successfully")

    measured = run([ffmpeg, "-hide_banner", "-nostats", "-i", str(audio), "-map", "0:a:0",
                    "-vn", "-af", "loudnorm=I=-14:TP=-1.2:LRA=11:print_format=json", "-f", "null", "-"])
    errors = decoding_errors(measured.stderr, streamed_wav)
    if errors:
        raise MuxError(f"the audio '{audio}' is damaged:\n" + "\n".join(errors[:3]))
    measurement = loudness_json(measured.stderr)
    keys = ("input_i", "input_tp", "input_lra", "input_thresh", "target_offset")
    try:
        normalise = all(math.isfinite(float(measurement[key])) for key in keys)
    except (KeyError, TypeError, ValueError) as error:
        raise MuxError("ffmpeg returned an incomplete loudness measurement") from error
    if normalise:
        loudnorm = ("loudnorm=I=-14:TP=-1.2:LRA=11:"
                    f"measured_I={measurement['input_i']}:measured_TP={measurement['input_tp']}:"
                    f"measured_LRA={measurement['input_lra']}:measured_thresh={measurement['input_thresh']}:"
                    f"offset={measurement['target_offset']}:linear=true")
    else:
        # An unmeasurably short but audible file also gives -inf LUFS. Do not
        # mislabel that (or a failed measurement) as genuine silence.
        volume = run([ffmpeg, "-hide_banner", "-nostats", "-i", str(audio), "-map", "0:a:0",
                      "-vn", "-af", "volumedetect", "-f", "null", "-"])
        peaks = re.findall(r"max_volume:\s*(" + LEVEL_NUMBER + r")\s*dB", volume.stderr)
        if not peaks or float(peaks[-1]) > -70:
            raise MuxError("audio loudness could not be measured and it is not silent; "
                           "use a longer mix or fix its levels before muxing")
        loudnorm = "anull"
        note("warning: the audio is silent or quieter than -70 dB; loudness normalisation was skipped")

    if decoded_seconds < video_duration - .02:
        note(f"note: the audio ({decoded_seconds:g} s) is shorter than the video "
             f"({video_duration:g} s); padding it with silence")
    fps_text, grain_text = f"{fps:g}", f"{grain:g}"
    video_filter = f"fps={fps_text}"
    if grain:
        video_filter += f",noise=c0s={grain_text}:allf=t"
    color_args = []
    if color == "bt709":
        video_filter += (",scale=in_range=pc:out_range=tv:out_color_matrix=bt709,format=yuv420p,"
                         "setparams=range=tv:colorspace=bt709:color_primaries=bt709:color_trc=bt709")
        color_args = ["-color_range", "tv", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709"]
    else:
        video_filter += ",format=yuv420p"

    handle, temporary_name = tempfile.mkstemp(prefix=f".{output.stem}.mux-", suffix=output.suffix,
                                             dir=output.parent)
    os.close(handle)
    temporary = Path(temporary_name)
    try:
        filters = (f"[0:v:0]{video_filter}[v];[1:a:0]{loudnorm},aresample=48000,"
                   f"apad=whole_dur={video_duration:.9f}[a]")
        run([ffmpeg, "-y", "-loglevel", "error", "-i", str(video), "-i", str(audio),
             "-filter_complex", filters, "-map", "[v]", "-map", "[a]", "-c:v", "libx264",
             "-preset", "slow", "-crf", "19", "-r", fps_text, *color_args,
             "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart",
             # -t already trims the padded audio. Combining it with -shortest
             # drops the last video frame when concat timestamps make the
             # container duration a fraction of a frame shorter than N / fps.
             "-t", f"{video_duration:.9f}", str(temporary)])
        if not temporary.is_file() or not temporary.stat().st_size:
            raise MuxError(f"no output was written for '{output}'")
        finished = probe(temporary, ffprobe)
        kinds = {stream.get("codec_type") for stream in finished.get("streams", [])}
        if not {"audio", "video"}.issubset(kinds):
            raise MuxError("the finished file is missing its video or audio stream")
        finished_duration = duration(finished, "video")
        if finished_duration is None or abs(finished_duration - video_duration) > max(.15, 2 / fps):
            raise MuxError("the finished video duration differs from the input picture")
        reviewed = run([ffmpeg, "-hide_banner", "-nostats", "-i", str(temporary), "-map", "0:a:0",
                        "-vn", "-af", "ebur128=peak=true", "-f", "null", "-"])
        readings = re.findall(r"^\s+(I|LRA|Peak):\s*(" + LEVEL_NUMBER + r")", reviewed.stderr, re.M)
        levels = {key: float(value) for key, value in readings}
        if not {"I", "LRA", "Peak"}.issubset(levels):
            raise MuxError("could not verify the finished audio loudness")
        os.replace(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)

    if normalise and (not -15 <= levels["I"] <= -13 or levels["Peak"] > -1):
        note(f"warning: the film missed the target (-14 LUFS, true peak <= -1.2 dB): "
             f"measured {levels['I']:g} LUFS, peak {levels['Peak']:g} dB. "
             "Lower or tame hot peaks in the mix, then mux again")
    return levels


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path)
    parser.add_argument("audio", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("fps", nargs="?", default=24, type=float)
    parser.add_argument("grain", nargs="?", default=2, type=float)
    args = parser.parse_args(argv)
    try:
        if not math.isfinite(args.fps) or args.fps <= 0:
            raise MuxError("fps must be a positive finite number")
        if not math.isfinite(args.grain) or not 0 <= args.grain <= 100:
            raise MuxError("grain must be a finite number from 0 to 100")
        color = os.environ.get("LEMO_COLOR", "")
        if color not in ("", "bt709"):
            raise MuxError(f"LEMO_COLOR must be bt709 or unset, got '{color}'")
        ffmpeg, ffprobe = shutil.which("ffmpeg"), shutil.which("ffprobe")
        if not ffmpeg or not ffprobe:
            raise MuxError("ffmpeg and ffprobe must both be installed and on PATH")
        levels = mux(args.video, args.audio, args.output, args.fps, args.grain, color, ffmpeg, ffprobe)
        print(args.output)
        print(f"I: {levels['I']:g} LUFS\nLRA: {levels['LRA']:g} LU\nPeak: {levels['Peak']:g} dBFS")
        return 0
    except (MuxError, OSError) as error:
        note(str(error))
        return 1
    except KeyboardInterrupt:
        note("interrupted; no partial output was kept")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
