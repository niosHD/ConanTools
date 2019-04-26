#!/usr/bin/env bash

baseDir=$(dirname `readlink -f -- $0`)

cd "${baseDir}"
python3 setup.py sdist bdist_wheel
python3 -m twine upload -u nioshd -p "$PYPI_PASSWORD" dist/*
