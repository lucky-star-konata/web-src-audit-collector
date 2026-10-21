#!/bin/bash
# Clean all downloaded source code
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "${SCRIPT_DIR}")"
SRC_DIR="${ROOT_DIR}/source_code"

if [ ! -d "${SRC_DIR}" ];then
    echo "[!] ${SRC_DIR} not found, nothing to clean."
    exit 0
fi

read -r -p "Confirm delete all source files in source_code ? (y/N) " ans
if [ "${ans}" = "y" ];then
    rm -rf "${SRC_DIR:?}"/*
    echo "Source folder cleared."
else
    echo "Clean cancelled."
fi
