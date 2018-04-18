#!/usr/bin/env bash

command -v "youtube-dl" 2>&1 >/dev/null || (>&2 echo "youtube-dl missing" && exit 1)

if [ -z "${1}" ]; then
	echo "downloader.sh <youtube_url>" >&2
	exit 1
fi

youtube-dl "${1}" -x --audio-format 'm4a'
