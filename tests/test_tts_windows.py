"""Exercise offline Kokoro synthesis from the actual Windows library path.

Set LEMO_TEST_ASR=1 to also check the original four Chinese sample lines with
the cached Whisper small model, offline and at asr_check.py's default threshold.
"""
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import wave
import array


ROOT = Path(__file__).resolve().parents[1]
TTS = ROOT / 'core' / 'tts' / 'tts.py'
ASR = TTS.parent / 'asr_check.py'
MODELS_PRESENT = all((TTS.parent / name).is_file() for name in ('kokoro-v1.0.onnx', 'voices-v1.0.bin'))


@unittest.skipUnless(sys.platform == 'win32' and MODELS_PRESENT, 'requires Windows and the installed offline voice models')
class WindowsOfflineTtsTests(unittest.TestCase):
    def setUp(self):
        temporary_root = Path(os.environ.get('LEMO_TEST_TEMP', 'F:/tools/temp'))
        temporary_root.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix='lemo-tts-check-', dir=temporary_root)
        def cleanup():
            target, parent = Path(self.temporary.name).resolve(), temporary_root.resolve()
            self.assertEqual(target.parent, parent, 'refusing temporary cleanup outside the chosen parent')
            self.temporary.cleanup()
        self.addCleanup(cleanup)
        self.folder = Path(self.temporary.name)
        self.espeak_temp = self.folder / 'native-data'
        self.espeak_temp.mkdir()

    def invoke(self, lines):
        script = self.folder / '中文 台词.json'
        script.write_text(json.dumps(lines, ensure_ascii=False), encoding='utf-8')
        output = self.folder / '中文 配音输出'
        env = os.environ.copy()
        env['LEMO_TEST_TEMP'] = str(self.espeak_temp)
        result = subprocess.run([sys.executable, '-X', 'utf8', str(TTS), str(script), str(output)],
                                capture_output=True, text=True, encoding='utf-8', errors='replace',
                                env=env, timeout=120)
        self.assertFalse(list(self.espeak_temp.glob('lemo-espeak-*')), 'temporary native data was not cleaned up')
        return result, output

    def test_chinese_and_english_offline_wavs_are_non_silent(self):
        result, output = self.invoke([
            {'id': 'zh', 'text': '你好，这是离线语音测试。', 'lang': 'CMN'},
            {'id': 'en', 'text': 'Hello, this is an offline voice test.', 'lang': 'en-us'},
        ])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        durations = json.loads((output / 'dur.json').read_text(encoding='utf-8'))
        for name in ('zh', 'en'):
            with self.subTest(language=name), wave.open(str(output / f'{name}.wav'), 'rb') as audio:
                self.assertEqual(audio.getframerate(), 24000)
                self.assertEqual(audio.getnchannels(), 1)
                samples = array.array('h', audio.readframes(audio.getnframes()))
                self.assertGreater(len(samples) / 24000, .2)
                rms = math.sqrt(sum(float(sample) ** 2 for sample in samples) / len(samples))
                self.assertGreater(rms, 10, 'synthesis produced silence')
                self.assertAlmostEqual(durations[name], len(samples) / 24000, delta=.002)

    @unittest.skipUnless(os.environ.get('LEMO_TEST_ASR') == '1', 'set LEMO_TEST_ASR=1 with Whisper small already cached')
    def test_original_chinese_lines_match_offline_small_whisper(self):
        # These are the unchanged sample lines that espeak's Mandarin frontend
        # mispronounced. A non-silent WAV alone cannot catch that regression.
        lines = [
            {'id': 'v01', 'text': '先有一个想法。', 'voice': 'zf_xiaoxiao', 'speed': 1.0, 'lang': 'cmn'},
            {'id': 'v02', 'text': '把想法，变成画面。', 'voice': 'zf_xiaoxiao', 'speed': 1.0, 'lang': 'cmn'},
            {'id': 'v03', 'text': '让声音，跟上节奏。', 'voice': 'zf_xiaoxiao', 'speed': 1.0, 'lang': 'cmn'},
            {'id': 'v04', 'text': '最后，交付一支短片。', 'voice': 'zf_xiaoxiao', 'speed': 1.0, 'lang': 'cmn'},
        ]
        result, output = self.invoke(lines)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        env = os.environ.copy()
        env['HF_HUB_OFFLINE'] = '1'  # Never download a model from a regression test.
        result = subprocess.run(
            [sys.executable, '-X', 'utf8', str(ASR), str(self.folder / '中文 台词.json'),
             str(output), '--lang', 'zh', '--model', 'small'],
            capture_output=True, text=True, encoding='utf-8', errors='replace', env=env, timeout=180,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('mismatches: 0', result.stdout)
        for line in lines:
            self.assertRegex(result.stdout, rf'OK\s+{line["id"]}\s+\|')

    def test_chinese_with_default_english_language_is_still_rejected(self):
        result, output = self.invoke([{'id': 'wrong', 'text': '中文不能按英文读。'}])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('lang is English', result.stderr)
        self.assertFalse(output.exists())

    def test_unknown_voice_is_still_rejected(self):
        result, output = self.invoke([{'id': 'wrong', 'text': 'Hello.', 'voice': 'nonexistent_test_voice'}])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('unknown voice', result.stderr)
        self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
