import json
import os
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SCRIPTS_DIR = os.path.join(os.path.dirname(_HERE), "scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from sponsor_check import (  # noqa: E402
    check,
    detect,
    excerpt,
    main,
    parse_post,
    run,
    to_mobile_url,
)

_FIXTURES_DIR = os.path.join(_HERE, "fixtures")


def _load_fixture(name: str) -> str:
    path = os.path.join(_FIXTURES_DIR, name)
    with open(path, encoding="utf-8") as f:
        return f.read()


def _positions(evidence):
    return [item["position"] for item in evidence]


class ParsePostTests(unittest.TestCase):
    def test_parse_se_editor(self):
        html = _load_fixture("sponsored_bottom.html")
        post = parse_post(html)
        self.assertEqual(post["title"], "동네 카페 다녀온 후기")
        self.assertTrue(post["date"])
        self.assertIn("오늘은 동네에 새로 생긴 카페를 다녀왔어요.", post["text"])

    def test_parse_old_editor(self):
        html = _load_fixture("plain.html")
        post = parse_post(html)
        self.assertTrue(post["text"].strip())

    def test_unclosed_tag_inside_root_does_not_leak_content_after_root_closes(self):
        # A stray, never-closed <span> inside the body root must not desync
        # root tracking: the root's own </div> still has to close it, and
        # anything after that </div> must not be treated as body content.
        html = (
            '<div class="se-main-container">'
            "<p>첫 문단입니다 <span>닫히지 않은 span 태그 이후 내용</p>"
            '<a href="https://example.com/inside">inside-link</a>'
            "</div>"
            "<p>루트가 닫힌 뒤에 나오는 바깥 문단입니다.</p>"
            '<a href="https://example.com/outside">outside-link</a>'
        )
        post = parse_post(html)  # must not raise
        self.assertIn("첫 문단입니다", post["text"])
        self.assertNotIn("바깥 문단", post["text"])
        self.assertIn("https://example.com/inside", post["links"])
        self.assertNotIn("https://example.com/outside", post["links"])

    def test_old_editor_minified_splits_paragraphs_and_excerpt_finds_middle(self):
        # No literal newlines between <p> tags — paragraph splitting must
        # come from the block-tag boundaries, not from whitespace in markup.
        html = (
            '<div id="viewTypeSelector">'
            "<p>첫 번째 문단입니다.</p>"
            "<p>단점은 주차 공간이 좁다는 점이었습니다.</p>"
            "<p>마지막 문단입니다.</p>"
            "</div>"
        )
        post = parse_post(html)
        paragraphs = post["text"].split("\n")
        self.assertEqual(
            paragraphs,
            [
                "첫 번째 문단입니다.",
                "단점은 주차 공간이 좁다는 점이었습니다.",
                "마지막 문단입니다.",
            ],
        )
        result = excerpt(post["text"])
        self.assertIn("단점은 주차 공간이 좁다는 점이었습니다.", result)


class DetectTests(unittest.TestCase):
    def test_sponsored_bottom(self):
        post = parse_post(_load_fixture("sponsored_bottom.html"))
        verdict, evidence = detect(post)
        self.assertEqual(verdict, "협찬")
        self.assertIn("맨 아래", _positions(evidence))

    def test_sponsored_top(self):
        post = parse_post(_load_fixture("sponsored_top.html"))
        verdict, evidence = detect(post)
        self.assertEqual(verdict, "협찬")
        self.assertIn("맨 위", _positions(evidence))

    def test_banner_image_domain_detected(self):
        post = parse_post(_load_fixture("banner_only.html"))
        verdict, evidence = detect(post)
        self.assertEqual(verdict, "협찬")
        self.assertIn("링크/이미지", _positions(evidence))

    def test_plain_is_none(self):
        post = parse_post(_load_fixture("plain.html"))
        verdict, evidence = detect(post)
        self.assertEqual(verdict, "없음")
        self.assertEqual(evidence, [])

    def test_negated_disclosure_is_not_sponsored(self):
        post = parse_post(_load_fixture("negated.html"))
        verdict, _evidence = detect(post)
        self.assertEqual(verdict, "없음")

    def test_plain_word_gwanggo_mid_text_not_flagged(self):
        filler = "맛도 향도 괜찮았고 가격도 적당한 편이었습니다. " * 20
        text = filler + "광고에서 보던 그 맛이 그대로 느껴져서 신기했습니다. " + filler
        post = {"title": "t", "date": "d", "text": text, "links": [], "images": []}
        verdict, evidence = detect(post)
        self.assertEqual(verdict, "없음")
        self.assertEqual(evidence, [])

    def test_mixed_naedon_flags_both(self):
        post = parse_post(_load_fixture("mixed_naedon.html"))
        verdict, evidence = detect(post)
        self.assertEqual(verdict, "협찬")
        self.assertIn(
            "내돈내산 표기와 협찬 표시가 함께 있음",
            [item["signal"] for item in evidence],
        )

    def test_repeated_phone_is_suspect(self):
        text = (
            "맛있는 식당이라 추천하고 싶어요. 예약 문의는 010-1234-5678 로 주세요. "
            + "궁금하신 분들은 010-1234-5678 로 연락 주시면 안내해드립니다."
        )
        post = {"title": "t", "date": "d", "text": text, "links": [], "images": []}
        verdict, evidence = detect(post)
        self.assertEqual(verdict, "의심")
        self.assertTrue(evidence)


class ExcerptTests(unittest.TestCase):
    def test_excerpt_keeps_tail_and_proscons(self):
        filler = "오늘 다녀온 곳은 분위기가 평범했고 특별한 점은 없었습니다. " * 150
        middle_sentence = "단점은 주차 공간이 좁다는 점이었습니다."
        tail_sentence = "이 문장은 끝부분에만 등장하는 고유한 마지막 문장입니다."
        text = filler + "\n" + middle_sentence + "\n" + filler + "\n" + tail_sentence
        self.assertGreaterEqual(len(text), 10000)  # the 10,000-char scale the brief asks for

        result = excerpt(text, limit=3000)
        self.assertIn(middle_sentence, result)
        self.assertIn(tail_sentence, result)
        self.assertLessEqual(len(result), 3000)


class ToMobileUrlTests(unittest.TestCase):
    def test_to_mobile_url_variants(self):
        expected = "https://m.blog.naver.com/PostView.naver?blogId=myid&logNo=12345"
        variants = [
            "https://blog.naver.com/myid/12345",
            "http://blog.naver.com/myid/12345",
            "https://m.blog.naver.com/myid/12345",
            "https://blog.naver.com/myid/12345?from=search&extra=1",
            "https://m.blog.naver.com/PostView.naver?blogId=myid&logNo=12345",
            "https://blog.naver.com/PostView.naver?blogId=myid&logNo=12345&redirect=Dlog",
        ]
        for url in variants:
            with self.subTest(url=url):
                self.assertEqual(to_mobile_url(url), expected)

        self.assertIsNone(to_mobile_url("https://cafe.naver.com/x/1"))


class CheckTests(unittest.TestCase):
    def test_non_blog_url_reported_not_raised(self):
        result = check("https://cafe.naver.com/x/1")
        self.assertEqual(result["verdict"], "읽기실패")
        self.assertEqual(result["error"], "네이버 블로그 주소가 아님")

    def test_check_success_returns_verdict_from_fetched_html(self):
        html = _load_fixture("sponsored_bottom.html")

        def stub_fetch(_url: str) -> str:
            return html

        result = check("https://blog.naver.com/myid/12345", fetch=stub_fetch)
        self.assertEqual(result["verdict"], "협찬")
        self.assertEqual(result["title"], "동네 카페 다녀온 후기")
        self.assertNotIn("error", result)


class RunTests(unittest.TestCase):
    def test_fetch_failure_continues(self):
        html = _load_fixture("sponsored_bottom.html")

        def flaky_fetch(url: str) -> str:
            if "bad" in url:
                raise OSError("boom")
            return html

        results = run(
            [
                "https://blog.naver.com/bad/1",
                "https://blog.naver.com/myid/12345",
            ],
            fetch=flaky_fetch,
        )
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["verdict"], "읽기실패")
        self.assertEqual(results[1]["verdict"], "협찬")

    def test_max_posts_cap(self):
        html = _load_fixture("plain.html")

        def stub_fetch(_url: str) -> str:
            return html

        urls = [f"https://blog.naver.com/myid/{i}" for i in range(35)]
        results = run(urls, fetch=stub_fetch)
        self.assertEqual(len(results), 30)


class CliTests(unittest.TestCase):
    def test_cli_json_output(self):
        html = _load_fixture("sponsored_bottom.html")

        def stub_fetch(_url: str) -> str:
            return html

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write("https://blog.naver.com/myid/12345\n")
            tmpfile = f.name

        try:
            output = main(["--input", tmpfile], fetch=stub_fetch)
        finally:
            os.unlink(tmpfile)

        parsed = json.loads(output)
        self.assertEqual(len(parsed), 1)
        self.assertNotIn("\\u", output)
        self.assertIn("협찬", output)


if __name__ == "__main__":
    unittest.main()
