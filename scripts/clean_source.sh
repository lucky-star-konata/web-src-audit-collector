#!/bin/bash
# Clean all downloaded source code
read -p "Confirm delete all source files in source_code ? (y/N) " ans
if [ "$ans" = "y" ];then
    rm -rf ./source_code/*
    echo "Source folder cleared."
else
    echo "Clean cancelled."
fi
