"""Markdown (GFM) output of txt2tags3_mod: constructs that used to come out broken."""

import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def convert(body, *args, target="md"):
    src = "\n\n\n" + body  # 3 empty header lines
    r = subprocess.run(
        [sys.executable, "-W", "ignore", "-m", "txt2tags3_mod", "-t", target,
         "-H", "-o", "-", *args, "-"],
        input=src.encode(), capture_output=True, cwd=REPO, check=True,
    )
    return r.stdout.decode()


def test_toc_macro_without_toc_option_leaves_no_placeholder():
    for target in ("md", "html", "tex"):
        assert "vvvTOCvvv" not in convert("%%toc\n\n= A =\n", target=target)


def test_toc_macro_with_toc_option_is_expanded_in_place():
    out = convert("intro\n\n%%toc\n\n= A =\n== B ==\n", "--toc")
    assert "vvvTOCvvv" not in out
    assert out.index("* [A](#a)") > out.index("intro")


def test_header_is_a_heading_then_author_and_date():
    r = subprocess.run(
        [sys.executable, "-W", "ignore", "-m", "txt2tags3_mod", "-t", "md", "-o", "-", "-"],
        input=b"Title\nAuthor\n2026-01-01\n\ntext\n", capture_output=True, cwd=REPO, check=True,
    )
    out = r.stdout.decode()
    assert out.startswith("# Title\n")
    assert "Author  \n2026-01-01" in out


def test_nested_lists_are_indented():
    out = convert("- a\n - b\n  - c\n\n\n+ n\n + m\n")
    assert "* a\n    * b\n        * c" in out
    assert "1. n\n    1. m" in out


def test_list_item_paragraphs_stay_in_the_item():
    out = convert("- a\n\n  more a\n\n- b\n")
    assert "* a\n\n  more a\n" in out


def test_definition_list_terms_are_bold():
    out = convert(": Term\n def one\n def two\n")
    assert "**Term**  \ndef one\ndef two" in out


def test_table_has_header_separator_per_column_and_alignment():
    out = convert("|| a | b | c\n|  r | c  | l\n")
    assert "|---|---|---|" in out or "|---:|" in out
    out = convert("||  a |  b  | c \n| 1 | 2 | 3 |\n")
    assert out.count("---") + out.count(":---:") >= 3


def test_table_without_header_gets_an_empty_one():
    out = convert("| x | y |\n| z | w |\n")
    assert out.lstrip().startswith("|  |  |\n|---|---|")


def test_special_characters_are_escaped():
    out = convert("2*3*4 and a < b\n\n1. not a list\n# not a title\n> not a quote\n")
    assert "2\\*3\\*4" in out
    assert "\\<" in out
    assert "1\\. not a list" in out
    assert "\\# not a title" in out
    assert "\\> not a quote" in out


def test_marks_and_inline_code_are_not_escaped():
    out = convert("**bold** //it// ``a*b_c<d``\n")
    assert "**bold** *it* `a*b_c<d`" in out


def test_blocks_are_separated_by_blank_lines():
    out = convert("\tquote\n\n```\ncode\n```\n\ntext\n")
    assert "> quote\n\n```\ncode\n```\n\ntext" in out


def test_verbatim_fence_is_longer_than_its_content():
    out = convert("```\na ``` b\n```\n")
    assert "````\na ``` b\n````" in out


def test_verbatim_after_a_list_is_not_part_of_the_item():
    out = convert("- one\n\n\n```\ncode\n```\n")
    assert "* one\n\n```\ncode\n```" in out


def test_toc_links_use_github_anchors():
    out = convert("= Intro =\n== Sub Title ==\n= Intro =\n", "--toc")
    assert "* [Intro](#intro)\n    * [Sub Title](#sub-title)\n* [Intro](#intro-1)" in out


def test_paragraph_lines_are_stripped():
    assert convert("   one  \n  two   \n") .strip() == "one\ntwo"


def test_email_link_has_a_target():
    assert "[me](mailto:a@b.org)" in convert("[me a@b.org]\n")


def test_blank_lines_are_normalized():
    out = convert("a\n\n\n\nb\n")
    assert out == "a\n\nb\n"
