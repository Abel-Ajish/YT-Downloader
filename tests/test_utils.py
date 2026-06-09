from utils import sanitize_filename


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
