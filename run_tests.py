import shutil
import subprocess

executable = str(shutil.which('python3.6') or shutil.which('py')).split('/')[-1]


def test_flake8():
    proc = subprocess.Popen('flake8', stdout=subprocess.PIPE)
    proc.wait()
    out = proc.stdout.read().decode()
    msg = 'OK' if not out and proc.returncode == 0 else out
    print(msg)


def test_pylint():
    proc = subprocess.Popen((f'{executable} -m pylint --max-line-length=150 --score=no '
                             '--disable=missing-docstring,wildcard-import,'
                             'attribute-defined-outside-init,too-few-public-methods,'
                             'old-style-class,import-error,invalid-name,no-init,'
                             'too-many-instance-attributes,protected-access,too-many-arguments,'
                             'too-many-public-methods,logging-format-interpolation,too-many-branches '
                             'lavalink').split(),
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    stdout, stderr = proc.communicate()
    out = stdout.decode()
    msg = 'OK' if not out and proc.returncode == 0 else out
    print(msg)


if __name__ == '__main__':
    print('-- flake8 test --')
    test_flake8()
    print('-- pylint test --')
    test_pylint()
