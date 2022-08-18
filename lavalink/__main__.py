import os
import re
import sys
from subprocess import PIPE, Popen

import requests

LAVALINK_BASE_URL = 'https://ci.fredboat.com/repository/download/Lavalink_Build/.lastSuccessful/Lavalink.jar?guest=1&branch=refs/heads/{}'
APPLICATION_BASE_URL = 'https://raw.githubusercontent.com/freyacodes/Lavalink/{}/LavalinkServer/application.yml.example'


def display_help():
    print("""
download - Downloads the latest (stable) Lavalink jar.
    --fetch-dev     Fetches the latest Lavalink development jar.
    --no-overwrite  Renames an existing lavalink.jar to lavalink.old.jar
config   - Downloads a fresh application.yml.
    --fetch-dev     Fetches the latest application.yml from the development branch.
    --no-overwrite  Renames an existing application.yml to application.old.yml.
info     - Extracts version and build information from an existing Lavalink.jar.
    """.strip())


def download(dl_url, path):
    res = requests.get(dl_url, stream=True)

    def report_progress(cur, tot):
        bar_len = 32
        progress = float(cur) / tot
        filled_len = int(round(bar_len * progress))
        percent = round(progress * 100, 2)

        progress_bar = '█' * filled_len + ' ' * (bar_len - filled_len)
        sys.stdout.write('Downloading |%s| %0.2f%% (%d/%d)\r' % (progress_bar, percent, cur, tot))
        sys.stdout.flush()

        if cur >= tot:
            sys.stdout.write('\n')

    def read_chunk(f, chunk_size=8192):
        total_bytes = int(res.headers['Content-Length'].strip())
        current_bytes = 0

        for chunk in res.iter_content(chunk_size):
            f.write(chunk)
            current_bytes += len(chunk)
            report_progress(min(current_bytes, total_bytes), total_bytes)

    with open(path, 'wb') as f:
        read_chunk(f)


def main():  # pylint: disable=too-many-locals,too-many-statements
    if len(sys.argv) < 2 or sys.argv[1] == '--help' or sys.argv[1] == 'help' or sys.argv[1] == '?':
        display_help()
        return

    cwd = os.getcwd()
    _, action, *arguments = sys.argv

    if action == 'download':
        target_branch = 'dev' if '--fetch-dev' in arguments else 'master'
        dl_url = LAVALINK_BASE_URL.format(target_branch)
        dl_path = os.path.join(cwd, 'lavalink.jar')

        if '--no-overwrite' in arguments and os.path.exists(dl_path):
            os.rename(dl_path, os.path.join(cwd, 'lavalink.old.jar'))

        download(dl_url, dl_path)
        print('Downloaded to {}'.format(dl_path))
        sys.exit(0)
    elif action == 'config':
        target_branch = 'dev' if '--fetch-dev' in arguments else 'master'
        dl_url = APPLICATION_BASE_URL.format(target_branch)
        dl_path = os.path.join(cwd, 'application.yml')

        if '--no-overwrite' in arguments and os.path.exists(dl_path):
            os.rename(dl_path, os.path.join(cwd, 'application.old.yml'))

        download(dl_url, dl_path)
        print('Downloaded to {}'.format(dl_path))
        sys.exit(0)
    elif action == 'info':
        check_names = ['lavalink.jar', 'Lavalink.jar', 'LAVALINK.JAR']

        if arguments:
            check_names.extend([arguments[0]])

        file_name = next((fn for fn in check_names if os.path.exists(fn)), None)

        if not file_name:
            print('Unable to display Lavalink server info: No Lavalink file found.')
            sys.exit(1)

        proc = Popen(['java', '-jar', file_name, '--version'], stdout=PIPE, stderr=PIPE, text=True)
        stdout, stderr = proc.communicate()

        if stderr:
            if 'UnsupportedClassVersionError' in stderr:
                java_proc = Popen(['java', '-version'], stdout=PIPE, stderr=PIPE, text=True)
                j_stdout, j_stderr = java_proc.communicate()
                j_ver = re.search(r'java version "([\d._]*)"', j_stdout or j_stderr)
                java_version = j_ver.group(1) if j_ver else 'UNKNOWN'

                if java_version.startswith('1.8'):
                    java_version = f'8/{java_version}'

                print('Unable to display Lavalink server info.\nYour Java version is out of date. (Java {})\n\n'
                      'Java 11+ is required to run Lavalink.'.format(java_version))
                sys.exit(1)

            print(stderr)
            sys.exit(1)
        else:
            print(stdout.strip())
            sys.exit(0)
    else:
        print('Invalid argument \'{}\'. Use --help to show usage.'.format(action))
        sys.exit(1)


if __name__ == '__main__':
    main()
