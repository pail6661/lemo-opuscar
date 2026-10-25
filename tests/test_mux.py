"""Real ffmpeg smoke/regression tests for the cross-platform final mux."""
import array
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
MUX = ROOT / "core" / "render" / "mux.py"


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg and ffprobe are required")
class MuxTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix=".mux-test-", dir=ROOT / "tests")
        cls.folder = Path(cls.temp.name) / "中文 含空格视频"
        cls.folder.mkdir()
        cls.video = cls.folder / "原始 画面.mp4"
        cls.command(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
                     "testsrc2=size=96x64:rate=12:duration=1.5", "-c:v", "libx264",
                     "-pix_fmt", "yuv420p", str(cls.video)])
        cls.normal = cls.audio("正常 混音.wav", 1.5)
        cls.short = cls.audio("短音频.wav", .5)
        cls.long = cls.audio("长音频.wav", 3)
        cls.silent = cls.audio("真静音.wav", 1.5, silent=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    @staticmethod
    def command(command):
        return subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              check=True).stdout

    @classmethod
    def audio(cls, name, length, silent=False):
        path = cls.folder / name
        source = "anullsrc=r=48000:cl=mono" if silent else "sine=frequency=700:sample_rate=48000"
        cls.command(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", source,
                     "-t", str(length), "-c:a", "pcm_s16le", str(path)])
        return path

    def invoke(self, audio=None, name=None, color="", grain="0", video=None):
        output = self.folder / (name or f"{self._testMethodName} 成品.mp4")
        env = os.environ.copy()
        env["LEMO_COLOR"] = color
        result = subprocess.run([sys.executable, "-X", "utf8", str(MUX), str(video or self.video),
                                 str(audio or self.normal), str(output), "12", grain],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                encoding="utf-8", errors="replace", env=env)
        self.assertFalse(list(self.folder.glob(f".{output.stem}.mux-*")), "partial mux files were left behind")
        return result, output

    def inspect(self, output):
        return json.loads(self.command(["ffprobe", "-v", "error", "-show_streams", "-show_format",
                                        "-of", "json", str(output)]))

    def assert_film(self, result, output):
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(output.is_file())
        info = self.inspect(output)
        self.assertEqual({s["codec_type"] for s in info["streams"]}, {"video", "audio"})
        self.assertAlmostEqual(float(info["format"]["duration"]), 1.5, delta=.12)
        self.assertIn("I:", result.stdout)
        return info

    def test_normal_audio_and_unicode_paths(self):
        result, output = self.invoke()
        self.assert_film(result, output)
        loudness = float(re.search(r"^I: ([-\d.]+)", result.stdout, re.M).group(1))
        peak = float(re.search(r"^Peak: ([-\d.]+)", result.stdout, re.M).group(1))
        self.assertAlmostEqual(loudness, -14, delta=1)
        self.assertLessEqual(peak, -1)

    def test_fractional_container_duration_preserves_the_actual_last_frame(self):
        # Parallel-render concatenation can shift later PTS by a few ticks:
        # 18 real frames at 12 fps, but the container says 1.499674 s. Combining
        # -t with -shortest used to remove the final frame in this case.
        source = self.folder / "亚帧 时长.mp4"
        self.command(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
                      "testsrc2=size=96x64:rate=12:duration=1.5", "-vf",
                      "drawbox=color=red:t=fill:enable=eq(n\\,17),settb=1/12288,setpts=PTS-4*gte(N\\,9)",
                      "-fps_mode", "passthrough", "-enc_time_base", "filter", "-c:v", "libx264",
                      "-pix_fmt", "yuv420p", str(source)])
        original = self.inspect(source)
        original_video = next(s for s in original["streams"] if s["codec_type"] == "video")
        self.assertEqual(int(original_video["nb_frames"]), 18)
        self.assertLess(float(original_video["duration"]), 1.5)
        result, output = self.invoke(video=source)
        self.assert_film(result, output)
        counted = json.loads(self.command(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
                                           "-show_entries", "stream=nb_read_frames,duration", "-of", "json", str(output)]))
        self.assertEqual(int(counted["streams"][0]["nb_read_frames"]), 18)
        self.assertAlmostEqual(float(counted["streams"][0]["duration"]), 1.5, places=6)
        # The last source frame is red; preserving its pixels rules out fixing
        # the count by duplicating the preceding frame.
        last = self.command(["ffmpeg", "-v", "error", "-i", str(output), "-vf", "select=eq(n\\,17)",
                             "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"])
        self.assertEqual(len(last), 96 * 64 * 3)
        self.assertGreater(sum(last[0::3]) / (96 * 64), 200)
        self.assertLess(sum(last[1::3]) / (96 * 64), 30)

    def test_short_audio_is_padded_with_silence(self):
        result, output = self.invoke(self.short)
        self.assert_film(result, output)
        self.assertIn("padding it with silence", result.stderr)
        samples = array.array("h", self.command(["ffmpeg", "-v", "error", "-ss", "1.1", "-i", str(output),
                                                "-t", "0.25", "-vn", "-f", "s16le", "-ac", "1", "-"]))
        self.assertGreater(len(samples), 100)
        rms = math.sqrt(sum(sample * sample for sample in samples) / len(samples))
        self.assertLess(rms, 5, "the padded tail is not silent")

    def test_long_audio_is_cut_to_picture_duration(self):
        self.assert_film(*self.invoke(self.long))

    def test_true_silence_is_accepted(self):
        result, output = self.invoke(self.silent)
        self.assert_film(result, output)
        self.assertIn("silent", result.stderr)

    def test_short_audible_clip_is_not_mislabelled_as_silence(self):
        audible = self.audio("过短 但有声音.wav", .1)
        result, output = self.invoke(audible)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not silent", result.stderr)
        self.assertFalse(output.exists())

    def test_truncated_wav_is_rejected_without_output(self):
        truncated = self.folder / "损坏 WAV.wav"
        data = self.normal.read_bytes()
        truncated.write_bytes(data[:len(data) // 2])
        result, output = self.invoke(truncated)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("cut off", result.stderr)
        self.assertFalse(output.exists())

    def test_non_audio_is_rejected_without_output(self):
        result, output = self.invoke(self.video)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("no audio stream", result.stderr)
        self.assertFalse(output.exists())

    def test_streamed_wav_placeholder_is_accepted(self):
        streamed = self.folder / "流式 WAV.wav"
        streamed.write_bytes(self.command(["ffmpeg", "-v", "error", "-i", str(self.normal),
                                           "-f", "wav", "-"]))
        self.assert_film(*self.invoke(streamed))

    def test_bt709_color_tags(self):
        info = self.assert_film(*self.invoke(color="bt709", grain="1"))
        video = next(s for s in info["streams"] if s["codec_type"] == "video")
        self.assertEqual(video["color_space"], "bt709")
        self.assertEqual(video["color_range"], "tv")

    def test_failed_encode_preserves_existing_output_and_cleans_temporary(self):
        output = self.folder / "保留 原始文件.invalid"
        output.write_bytes(b"keep this existing file")
        result, actual = self.invoke(name=output.name)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(actual.read_bytes(), b"keep this existing file")

    def test_bad_configuration_is_rejected(self):
        result, output = self.invoke(color="invalid")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("LEMO_COLOR", result.stderr)
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
