"""A flush-left title ends an open list; --legacy restores the old behaviour."""

import os
import subprocess
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def html(body, *args):
    src = "\n\n\n" + body  # 3 empty header lines
    r = subprocess.run(
        [sys.executable, "-W", "ignore", "-m", "txt2tags3_mod", "-t", "html",
         "-H", "-o", "-", *args, "-"],
        input=src.encode(), capture_output=True, cwd=REPO, check=True,
    )
    return r.stdout.decode()


@pytest.mark.parametrize("sep", ["\n\n", "\n \n", "\n"])
def test_title_closes_list(sep):
    out = html("- item\n  suite" + sep + "== Titre ==\n\ntexte\n")
    assert "<H2>Titre</H2>" in out
    assert "== Titre ==" not in out
    assert out.index("</UL>") < out.index("<H2>")
    assert "<P></P>\n</UL>" not in out


def test_numtitle_closes_list():
    assert "<H1>1. T</H1>" in html("- a\n\n+ T +\n")


def test_legacy_swallows_title():
    assert "== Titre ==" in html("- item\n\n== Titre ==\n\ntexte\n", "--legacy")


def test_spaced_items_stay_one_list():
    assert html("- a\n\n- b\n").count("<UL>") == 1


def test_multi_paragraph_item_unchanged():
    out = html("- a\n\n  more a\n")
    assert "  more a" in out and out.count("<UL>") == 1


def test_indented_title_stays_in_item():
    assert "<H2>" not in html("- a\n\n  == x ==\n")
