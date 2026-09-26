"""Live UI boundaries tested without downloading models or sending audio."""

from io import BytesIO
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import wave

from scripts.setup_voice_model import PARTS, MODEL, extract_required, install
from ui.voice_backend import VoiceUIError, chat_reply, decode_wav, model_ready, transcribe


def wav_bytes(seconds: float = 0.1) -> bytes:
    out = BytesIO()
    with wave.open(out, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(16_000)
        audio.writeframes(b"\x00\x00" * int(seconds * 16_000))
    return out.getvalue()


class VoiceUITests(unittest.TestCase):
    def test_audio_decode_and_length_rejection(self):
        samples = decode_wav(wav_bytes())
        self.assertEqual(samples.shape, (1600,))
        self.assertEqual(samples[0], 0.0)
        with self.assertRaisesRegex(VoiceUIError, "30"):
            decode_wav(wav_bytes(31))
        with self.assertRaises(VoiceUIError):
            decode_wav(b"not a wav")

    def test_transcript_uses_16k_audio_and_empty_is_an_error(self):
        class Recognizer:
            def create_stream(self):
                self.stream = type("Stream", (), {"result": type("Result", (), {"text": " Salut "})()})()
                self.stream.accept_waveform = lambda rate, samples: self.assert_input(rate, samples)
                return self.stream

            def assert_input(self, rate, samples):
                self.sample_rate, self.samples = rate, samples

            def decode_stream(self, stream):
                pass

        recognizer = Recognizer()
        self.assertEqual(transcribe(wav_bytes(), recognizer), "Salut")
        self.assertEqual(recognizer.sample_rate, 16_000)
        self.assertEqual(len(recognizer.samples), 1600)
        recognizer.stream.result.text = " "
        recognizer.create_stream = lambda: recognizer.stream
        with self.assertRaisesRegex(VoiceUIError, "Nu am recunoscut"):
            transcribe(wav_bytes(), recognizer)

    def test_chat_model_is_exact_and_conversation_is_bounded(self):
        calls = []

        def fake_local(path, payload, *, timeout):
            calls.append((path, payload, timeout))
            return {"message": {"content": " Răspuns local "}}

        history = [{"role": "user", "content": str(i)} for i in range(14)]
        history += [{"role": "tool", "content": "do not forward"}]
        with patch("ui.voice_backend._local_json", side_effect=fake_local):
            self.assertEqual(chat_reply(" Salut ", history, "llama3"), "Răspuns local")
            with self.assertRaises(VoiceUIError):
                chat_reply("Salut", history, "unapproved-model")
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0], "/api/chat")
        self.assertEqual(calls[0][1]["model"], "llama3")
        messages = calls[0][1]["messages"]
        self.assertEqual(messages[-1], {"role": "user", "content": "Salut"})
        self.assertNotIn("tool", {entry["role"] for entry in messages})
        self.assertEqual(len(messages), 14)

    def test_model_extraction_only_installs_expected_regular_files(self):
        archive = BytesIO()
        with tarfile.open(fileobj=archive, mode="w:bz2") as tar:
            for path in [f"{MODEL}/{part}" for part in PARTS] + ["../../untrusted.txt"]:
                contents = b"safe model file"
                member = tarfile.TarInfo(path)
                member.size = len(contents)
                tar.addfile(member, BytesIO(contents))
        archive.seek(0)
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)
            extract_required(archive, target)
            self.assertTrue(model_ready(target))
            self.assertEqual(sorted(x.name for x in target.iterdir()), sorted(PARTS))

    def test_setup_downloads_once_and_commits_complete_model_directory(self):
        archive = BytesIO()
        with tarfile.open(fileobj=archive, mode="w:bz2") as tar:
            for part in PARTS:
                contents = b"model data"
                member = tarfile.TarInfo(f"{MODEL}/{part}")
                member.size = len(contents)
                tar.addfile(member, BytesIO(contents))
        with tempfile.TemporaryDirectory() as temp:
            with patch("scripts.setup_voice_model.urllib.request.urlopen",
                       side_effect=lambda *_, **__: BytesIO(archive.getvalue())) as download:
                directory = install(root=Path(temp))
                self.assertTrue(model_ready(directory))
                self.assertEqual(install(root=Path(temp)), directory)
                download.assert_called_once()


if __name__ == "__main__":
    unittest.main()
