# Tests for the optional TwelveLabs Pegasus clip selector.
#
# No-network unit tests run anywhere. A single live smoke test runs only when
# TWELVELABS_API_KEY is set, and is skipped otherwise.
#
#   python -m unittest Backend/test_twelvelabs_select.py   (from repo root)
#   python -m unittest test_twelvelabs_select               (from Backend/)

import os
import unittest
from unittest import mock

import twelvelabs_select as tl


class RerankNoNetwork(unittest.TestCase):
    def test_disabled_is_noop(self):
        urls = ["a", "b", "c"]
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(tl.rerank_clips(urls, "cats", "a script"), urls)

    def test_single_url_skips_scoring(self):
        # 0 or 1 clips: nothing to rank, returned untouched even if a key exists.
        with mock.patch.dict(os.environ, {"TWELVELABS_API_KEY": "x"}, clear=True):
            self.assertEqual(tl.rerank_clips(["only"], "s", "x"), ["only"])

    def test_reranks_by_score_and_respects_keep(self):
        with mock.patch.dict(os.environ, {"TWELVELABS_API_KEY": "x"}, clear=True), \
                mock.patch.object(tl, "_client", return_value=object()), \
                mock.patch.object(tl, "_score_clip",
                                  side_effect=lambda c, u, s, sc: {"a": 10, "b": 90, "c": 50}[u]):
            self.assertEqual(tl.rerank_clips(["a", "b", "c"], "s", "sc"), ["b", "c", "a"])
            self.assertEqual(tl.rerank_clips(["a", "b", "c"], "s", "sc", keep=2), ["b", "c"])

    def test_all_zero_scores_preserves_order(self):
        with mock.patch.dict(os.environ, {"TWELVELABS_API_KEY": "x"}, clear=True), \
                mock.patch.object(tl, "_client", return_value=object()), \
                mock.patch.object(tl, "_score_clip", return_value=0.0):
            self.assertEqual(tl.rerank_clips(["a", "b"], "s", "sc"), ["a", "b"])


@unittest.skipUnless(os.getenv("TWELVELABS_API_KEY"), "requires TWELVELABS_API_KEY")
class LiveSmoke(unittest.TestCase):
    def test_scores_a_public_clip(self):
        # Short public sample clip; Pegasus reads it server-side.
        url = "https://videos.pexels.com/video-files/3163534/3163534-sd_640_360_30fps.mp4"
        client = tl._client()
        self.assertIsNotNone(client)
        score = tl._score_clip(client, url, "ocean waves", "Calm waves roll onto the shore.")
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 100.0)


if __name__ == "__main__":
    unittest.main()
