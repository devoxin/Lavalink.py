"""
MIT License

Copyright (c) 2017-present Devoxin

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
import os
import re
import sys
import traceback
from subprocess import PIPE, Popen
from time import time
from typing import Optional, Sequence

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
        return f'{self.tag} {"[prerelease]" if self.prerelease else ""}'

    def __eq__(self, other):
        if not isinstance(other, Release):
            return False

        this_match = SEMVER_REGEX.match(self.tag)
        other_match = SEMVER_REGEX.match(other.tag)

        if not this_match or not other_match:
            raise ValueError('Cannot compare version strings as they do not match the regex pattern')

        this_major, this_minor, this_patch, _, this_build = this_match.groups()
        this_version = (int(this_major), int(this_minor), int(this_patch or 0), int(this_build or 0))

        other_major, other_minor, other_patch, _, other_build = other_match.groups()
        other_version = (int(other_major), int(other_minor), int(other_patch or 0), int(other_build or 0))

        return this_version == other_version

    def __lt__(self, other):
        this_match = SEMVER_REGEX.match(self.tag)

        if not this_match:
            raise ValueError('Cannot compare version strings as they do not match the regex pattern')

        this_major, this_minor, this_patch, _, this_build = this_match.groups()
        this_version = (int(this_major), int(this_minor), int(this_patch or 0), int(this_build or 0))

        if isinstance(other, str):
            parts = list(map(int, other.split('.')))

            if len(parts) == 1:
                other_version = (parts[0], 0, 0, 0)
            elif len(parts) == 2:
                other_version = (parts[0], parts[1], 0, 0)
            elif len(parts) == 3:
                other_version = (parts[0], parts[1], parts[2], 0)
            else:
                raise ValueError('Cannot compare version string with more fields than major.minor.patch')
        elif isinstance(other, Release):
            other_match = SEMVER_REGEX.match(other.tag)

            if not this_match or not other_match:
                raise ValueError('Cannot compare version strings as they do not match the regex pattern')

            other_major, other_minor, other_patch, _, other_build = other_match.groups()
            other_version = (int(other_major), int(other_minor), int(other_patch or 0), int(other_build or 0))
        else:
            raise TypeError(f'"<" not supported between instances of "{type(self).__name__}" and "{type(other).__name__}"')

        return this_version < other_version

    def __gt__(self, other):
        this_match = SEMVER_REGEX.match(self.tag)

        if not this_match:
            raise ValueError('Cannot compare version strings as they do not match the regex pattern')

        this_major, this_minor, this_patch, _, this_build = this_match.groups()
        this_version = (int(this_major), int(this_minor), int(this_patch or 0), int(this_build or 0))

        if isinstance(other, str):
            parts = list(map(int, other.split('.')))

            if len(parts) == 1:
                other_version = (parts[0], 0, 0, 0)
            elif len(parts) == 2:
                other_version = (parts[0], parts[1], 0, 0)
            elif len(parts) == 3:
                other_version = (parts[0], parts[1], parts[2], 0)
            else:
                raise ValueError('Cannot compare version string with more fields than major.minor.patch')
        elif isinstance(other, Release):
            other_match = SEMVER_REGEX.match(other.tag)

            if not this_match or not other_match:
                raise ValueError('Cannot compare version strings as they do not match the regex pattern')

            other_major, other_minor, other_patch, _, other_build = other_match.groups()
            other_version = (int(other_major), int(other_minor), int(other_patch or 0), int(other_build or 0))
        else:
            raise TypeError(f'">" not supported between instances of "{type(self).__name__}" and "{type(other).__name__}"')

        return this_version > other_version

    def __ge__(self, other):
        return self.__eq__(other) or self.__gt__(other)

    def __le__(self, other):
        return self.__eq__(other) or self.__lt__(other)


def display_help():
    print("""
download - Find and download specific Lavalink server versions.
    --no-overwrite  Renames an existing lavalink.jar to lavalink.old.jar
config   - Downloads a fresh application.yml.
    --fetch-dev     Fetches the latest application.yml from the development branch.
    --no-overwrite  Renames an existing application.yml to application.old.yml.
info     - Extracts version and build information from an existing Lavalink.jar.
    """.strip(), file=sys.stdout)


def format_bytes(length: float) -> str:
    sizes = ['B', 'KB', 'MB', 'GB', 'TB']
    unit = 0

    while length >= 1024 and unit < len(sizes) - 1:
        unit += 1
        length /= 1024

    return f'{length:.2f} {sizes[unit]}'


def download(dl_url, path):
    res = requests.get(dl_url, stream=True, timeout=15)

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
        sys.stdout.write(f'Downloading |{progress_bar}| {percent:.1f}% ({cur}/{tot}, {format_bytes(speed)}/s)\r')
        sys.stdout.flush()

        if cur >= tot:
            sys.stdout.write('\n')

    def read_chunk(out, chunk_size=8192):
        total_bytes = int(res.headers['Content-Length'].strip())
        current_bytes = 0

        for chunk in res.iter_content(chunk_size):
            out.write(chunk)
            current_bytes += len(chunk)
            report_progress(min(current_bytes, total_bytes), total_bytes)

    with open(path, 'wb') as out:
        read_chunk(out)


def select_release_unattended(non_draft: Sequence[Release], version_selector: str) -> Release:
    matcher = SEMVER_REGEX.match(version_selector)

    if matcher:
        def exact_version(release: Release):
            return release.tag == version_selector

        predicate = exact_version
    elif version_selector.startswith('>='):
        def gte(release: Release):
            return release >= version_selector[2:]

        predicate = gte
    elif version_selector.startswith('<='):
        def lte(release: Release):
            return release.tag <= version_selector[2:]

        predicate = lte
    elif version_selector.startswith('>'):
        def gt(release: Release):  # pylint: disable=C0103
            return release > version_selector[1:]

        predicate = gt
    elif version_selector.startswith('<'):
        def lte(release: Release):
            return release.tag < version_selector[1:]

        predicate = lte
    elif version_selector.startswith('~='):
        minimum = version_selector[2:]
        major, minor, _ = minimum.split('.')
        maximum = f'{major}.{int(minor) + 1}.0'

        def compatible(release: Release):
            return minimum <= release < maximum

        predicate = compatible
    else:
        # TODO: Support multiple version specifiers (e.g. >=3.7.0,<4.0.0)
        raise ValueError('Unsupported version selector')

    selected_release = next((release for release in non_draft if predicate(release)), None)

    if not selected_release:
        print('Couldn\'t find a suitable release with the provided version selector.', file=sys.stderr)
        sys.exit(1)

    print(f'Release selected: {selected_release.tag}', file=sys.stdout)

    return selected_release


def select_release(non_draft: Sequence[Release]) -> Release:
    suitable_releases = []

    for release in non_draft:
        if not release.download_url:
            continue

        newest: Optional[Release] = next((sr for sr in suitable_releases if sr.major_version == release.major_version), None)

        if newest:
            if newest > release:  # GitHub gives newest->oldest releases, so it could be that we iterate over a pre-release before a release.
                if newest.prerelease and not release.prerelease:  # If that is the case, we check the version against the current non-prerelease
                    current_non_prerelease: Optional[Release] = next((sr for sr in suitable_releases if sr.major_version == release.major_version
                                                                      and not sr.prerelease), None)

                    if current_non_prerelease and current_non_prerelease > release:
                        continue
                else:
                    continue

        suitable_releases.append(release)

    if not suitable_releases:
        print('No suitable Lavalink releases were found.', file=sys.stdout)
        sys.exit(0)  # Perhaps this should be an error, however this could also be valid (but very unlikely).

    if len(suitable_releases) > 1:
        print('There are multiple Lavalink versions to choose from.\n'
              'They have automatically been filtered based on their version, and whether they are a pre-release.\n\n'
              'Type the number of the release you would like to download.\n', file=sys.stdout)

        for index, release in enumerate(suitable_releases, start=1):
            print(f'[{index}] {release}', file=sys.stdout)

        try:
            selected = int(input('> ')) - 1

            if not 0 <= selected <= len(suitable_releases):
                raise ValueError
        except ValueError:
            print('An incorrect selection has been made, cancelling...', file=sys.stderr)
            sys.exit(1)
    else:
        selected = 0

    return suitable_releases[selected]


def download_jar(arguments: Sequence[str]):
    try:
        res = requests.get(RELEASES_URL, timeout=15).json()
    except requests.exceptions.JSONDecodeError:
        print('Failed to retrieve Lavalink releases', file=sys.stderr)
        sys.exit(1)

    releases = list(map(Release, res))
    non_draft = [r for r in releases if not r.draft]

    if arguments:
        try:
            release = select_release_unattended(non_draft, arguments[0])
        except ValueError:
            traceback.print_exc(file=sys.stderr)
            sys.exit(1)
    else:
        release = select_release(non_draft)

    cwd = os.getcwd()
    dl_url = release.download_url
    dl_path = os.path.join(cwd, 'lavalink.jar')

    if '--no-overwrite' in arguments and os.path.exists(dl_path):
        os.rename(dl_path, os.path.join(cwd, 'lavalink.old.jar'))

    download(dl_url, dl_path)
    print(f'Downloaded {release.tag} to {dl_path}', file=sys.stdout)
    sys.exit(0)


def download_config(arguments: Sequence[str], branch: str):
    cwd = os.getcwd()
    dl_url = APPLICATION_BASE_URL.format(branch)
    dl_path = os.path.join(cwd, 'application.yml')

    if '--no-overwrite' in arguments and os.path.exists(dl_path):
        os.rename(dl_path, os.path.join(cwd, 'application.old.yml'))

    download(dl_url, dl_path)
    print(f'Downloaded to {dl_path}', file=sys.stdout)
    sys.exit(0)


def print_info(arguments: Sequence[str]):
    check_names = ['lavalink.jar', 'Lavalink.jar', 'LAVALINK.JAR']

    if arguments:
        check_names.extend([arguments[0]])

    file_name = next((fn for fn in check_names if os.path.exists(fn)), None)

    if not file_name:
        print('Unable to display Lavalink server info: No Lavalink file found.', file=sys.stderr)
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

            print(f'Unable to display Lavalink server info.\nYour Java version is out of date. (Java {java_version})\n\n'
                  'Java 11+ is required to run Lavalink.', file=sys.stderr)
            sys.exit(1)

        print(stderr, file=sys.stderr)
        sys.exit(1)
    else:
        print(stdout.strip(), file=sys.stdout)
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
            print(f'Invalid argument \'{action}\'. Use --help to show usage.', file=sys.stderr)
            sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(2)  # CTRL-C = SIGINT = 2


if __name__ == '__main__':
    main()
