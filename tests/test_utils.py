import pytest
from utils import sanitize_filename, safe_join


def test_sanitize_basic():
    name = 'My:Unsafe/File*Name?.mp4'
    safe = sanitize_filename(name)
    assert ':' not in safe
    assert '/' not in safe
    assert '*' not in safe
    assert '?' not in safe
    assert len(safe) > 0


def test_sanitize_unicode_and_truncation():
    long_name = '测试' * 200
    safe = sanitize_filename(long_name, max_length=50)
    assert len(safe) <= 50
    assert safe != ''


def test_sanitize_empty_replacement_does_not_crash():
    # Empty replacement should not crash; underscores remain since no collapse happens
    safe = sanitize_filename('foo___bar', replacement='')
    assert safe == 'foo___bar'
    assert safe != ''


def test_safe_join_raises_on_traversal():
    import os
    base = os.path.join('tmp', 'base')
    with pytest.raises(ValueError):
        safe_join(base, os.path.join('..', 'etc', 'passwd'))
