import os
import re
import sys
from subprocess import PIPE, Popen
from time import time
from typing import List, Optional

import requests

RELEASES_URL = 'https://api.github.com/repos/lavalink-devs/Lavalink/releases'
APPLICATION_BASE_URL = 'https://raw.githubusercontent.com/lavalink-devs/Lavalink/{}/LavalinkServer/application.yml.example'
SEMVER_REGEX = re.compile(r'(\d+)\.(\d+)(?:\.(\d+))?(?:-(\w+)(?:\.(\d+)))?')


class Release:
    def __init__(self, release_json):
        self.tag: str = release_json['tag_name']
        self.major_version: int = int(self.tag[0])
        self.prerelease: bool = release_json['prerelease']
        self.draft: bool = release_json['draft']

        assets = release_json['assets']
        jars = [asset['browser_download_url'] for asset in assets if asset['name'].endswith('.jar')]
        self.download_url: Optional[str] = jars[0] if jars else None

    def __str__(self) -> str:
        pr_str = ' [prerelease]' if self.prerelease else ''
        return '{} {}'.format(self.tag, pr_str)
    
    def __eq__(self, other):
        if not isinstance(other, Release):
            return False

        this_match = SEMVER_REGEX.match(self.tag)
        other_match = SEMVER_REGEX.match(other.tag)

        if not this_match or not other_match:
            raise ValueError('Cannot compare version strings as they do not match the regex pattern')

        this_major, this_minor, this_patch, this_tag, this_build = this_match.groups()
        other_major, other_minor, other_patch, other_tag, other_build = other_match.groups()

        this_patch = this_patch or 0
        other_patch = other_patch = 0

        this_build = this_build or 0
        other_build = other_build or 0

        return int(this_major) == int(other_major) and \
                int(this_minor) == int(other_minor) and \
                int(this_patch) == int(other_patch) and \
                int(this_build) == int(other_build)

    
    def __gt__(self, other):
        if isinstance(other, Release):
            this_match = SEMVER_REGEX.match(self.tag)
            other_match = SEMVER_REGEX.match(other.tag)

            if not this_match or not other_match:
                print(self.tag)
                print(other.tag)
                raise ValueError('Cannot compare version strings as they do not match the regex pattern')

            this_major, this_minor, this_patch, this_tag, this_build = this_match.groups()
            other_major, other_minor, other_patch, other_tag, other_build = other_match.groups()

            #  Quick and dirty workaround for versions like '3.5'. TODO: Find something better
            this_patch = this_patch or 0
            other_patch = other_patch = 0

            #  As above, but not so dirty because not all releases will have a tag or build.
            this_build = this_build or 0
            other_build = other_build or 0

            #  I'm very much aware this isn't a complete way of doing version comparison,
            #  and that there may be better ways but this should suffice for now.
            #  PRs to improve this are also welcome :)

            return int(this_major) > int(other_major) or \
                    int(this_minor) > int(other_minor) or \
                    int(this_patch) > int(other_patch) or \
                    int(this_build) > int(other_build)  #  TODO: Figure out what to do with tags.
        
        raise TypeError("'>' not supported between instances of '{}' and '{}'".format(type(self).__name__, type(other).__name__))
    
    def __ge__(self, other):
        return self.__eq__(other) or self.__gt__(other)


def display_help():
    print("""
download - Find and download specific Lavalink server versions.
    --no-overwrite  Renames an existing lavalink.jar to lavalink.old.jar
config   - Downloads a fresh application.yml.
    --fetch-dev     Fetches the latest application.yml from the development branch.
    --no-overwrite  Renames an existing application.yml to application.old.yml.
info     - Extracts version and build information from an existing Lavalink.jar.
    """.strip())


def format_bytes(length: int) -> str:
    sizes = ['B', 'KB', 'MB', 'GB', 'TB']
    unit = 0

    while length >= 1024 and unit < len(sizes) - 1:
        unit += 1
        length /= 1024

    return '%0.2f %s' % (length, sizes[unit])


def download(dl_url, path):
    res = requests.get(dl_url, stream=True, timeout=30)

    download_begin = round(time() * 1000)

    def report_progress(cur, tot):
        bar_len = 32
        progress = float(cur) / tot
        filled_len = int(round(bar_len * progress))
        percent = round(progress * 100, 2)

        elapsed = round(time() * 1000) - download_begin
        if elapsed > 0:
            correction = 1000 / elapsed
            speed = cur * correction
        else:
            speed = 0  # placeholder until we have enough data to calculate

        progress_bar = '█' * filled_len + ' ' * (bar_len - filled_len)
        sys.stdout.write('Downloading |%s| %0.1f%% (%d/%d, %s/s)\r' % (progress_bar, percent, cur, tot, format_bytes(speed)))
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


def download_jar(arguments: List[str]):  # TODO: Allow passing specific versions (4.0.0, >=4.0.0, etc)
    try:
        res = requests.get(RELEASES_URL).json()
    except requests.exceptions.JSONDecodeError:
        print('Failed to retrieve Lavalink releases')
        sys.exit(1)

    releases = list(map(Release, res))
    non_draft = [r for r in releases if not r.draft]
    suitable_releases = []

    for release in non_draft:
        if not release.download_url:
            continue

        existing = next((sr for sr in suitable_releases if sr.major_version == release.major_version), None)

        if existing and existing >= release:
            continue

        suitable_releases.append(release)

    if not suitable_releases:
        print('No suitable Lavalink releases were found.')
        sys.exit(0)  # Perhaps this should be an error, however this could also be valid (but very unlikely).

    if len(suitable_releases) > 1:
        print('There are multiple Lavalink versions to choose from.\n'
              'They have automatically been filtered based on their version, and whether they are a pre-release.\n\n'
              'Type the number of the release you would like to download.\n')

        for index, release in enumerate(suitable_releases, start=1):
            print('[{}] {}'.format(index, release))

        try:
            selected = int(input('> ')) - 1

            if not 0 <= selected <= len(suitable_releases):
                raise ValueError
        except ValueError:
            print('An incorrect selection has been made, cancelling...')
            sys.exit(1)
    else:
        selected = 0

    cwd = os.getcwd()
    selected_release = suitable_releases[selected]
    dl_url = selected_release.download_url
    dl_path = os.path.join(cwd, 'lavalink.jar')

    if '--no-overwrite' in arguments and os.path.exists(dl_path):
        os.rename(dl_path, os.path.join(cwd, 'lavalink.old.jar'))

    download(dl_url, dl_path)
    print('Downloaded {} to {}'.format(selected_release.tag, dl_path))
    sys.exit(0)


def download_config(arguments: List[str], branch: str):
    cwd = os.getcwd()
    dl_url = APPLICATION_BASE_URL.format(branch)
    dl_path = os.path.join(cwd, 'application.yml')

    if '--no-overwrite' in arguments and os.path.exists(dl_path):
        os.rename(dl_path, os.path.join(cwd, 'application.old.yml'))

    download(dl_url, dl_path)
    print('Downloaded to {}'.format(dl_path))
    sys.exit(0)


def print_info(arguments: List[str]):
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
                java_version = '8/{}'.format(java_version)

            print('Unable to display Lavalink server info.\nYour Java version is out of date. (Java {})\n\n'
                    'Java 11+ is required to run Lavalink.'.format(java_version))
            sys.exit(1)

        print(stderr)
        sys.exit(1)
    else:
        print(stdout.strip())
        sys.exit(0)


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ('--help', 'help', '?', '/help'):
        display_help()
        return

    _, action, *arguments = sys.argv
    target_branch = 'dev' if '--fetch-dev' in arguments else 'master'

    try:
        if action == 'download':
            download_jar(arguments)
        elif action == 'config':
            download_config(arguments, target_branch)
        elif action == 'info':
            print_info(arguments)
        else:
            print('Invalid argument \'{}\'. Use --help to show usage.'.format(action))
            sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == '__main__':
    main()
