from pandoc.types import Str, Space, LineBreak

from n2y.rich_text import RichText


def test_plain_text_to_pandoc_basic():
    pandoc_ast = RichText.plain_text_to_pandoc("hello world")
    assert pandoc_ast == [Str("hello"), Space(), Str("world")]


def test_plain_text_to_pandoc_spaces_before():
    pandoc_ast = RichText.plain_text_to_pandoc("  hello")
    assert pandoc_ast == [Space(), Space(), Str("hello")]


def test_plain_text_to_pandoc_spaces_after():
    pandoc_ast = RichText.plain_text_to_pandoc("hello ")
    assert pandoc_ast == [Str("hello"), Space()]


def test_plain_text_to_pandoc_spaces_after_newline():
    pandoc_ast = RichText.plain_text_to_pandoc("hello\n  world")
    assert pandoc_ast == [Str("hello"), LineBreak(), Space(), Space(), Str("world")]
