import sys
from io import StringIO

import pylint.lint as pylint
from flake8.api import legacy
from pylint.reporters import text


def test_flake8():
    style_guide = legacy.get_style_guide()
    report = style_guide.check_files(['lavalink'])
    statistics = report.get_statistics('E')
    failed = bool(statistics)

    if not failed:
        print('OK')


def test_pylint():
    stdout = StringIO()
    reporter = text.TextReporter(stdout)
    opts = ['--max-line-length=150', '--score=no', '--disable=missing-docstring, wildcard-import, '
                                                   'attribute-defined-outside-init, too-few-public-methods, '
                                                   'old-style-class,import-error,invalid-name,no-init,'
                                                   'too-many-instance-attributes,protected-access,too-many-arguments,'
                                                   'too-many-public-methods,logging-format-interpolation,'
                                                   'too-many-branches', 'lavalink']
    pylint.Run(opts, reporter=reporter, do_exit=False)
    out = reporter.out.getvalue()

    failed = bool(out)
    msg = 'OK' if not failed else out
    print(msg)

    return failed


if __name__ == '__main__':
    print('-- flake8 test --')
    flake_failed = test_flake8()
    print('-- pylint test --')
    pylint_failed = test_pylint()

    if flake_failed or pylint_failed:
        sys.exit(1)
