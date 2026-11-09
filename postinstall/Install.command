#!/bin/bash
# Double-click in Finder. Asks for your password, then runs the post-install.
cd "$(dirname "$0")"
sudo /usr/bin/python install.py "$@"
echo
read -n 1 -s -p "Press any key to close this window."
