#!/bin/bash

cd ..
rsync -av chromabot2 roger@llynmir.net:. --exclude chromabot2/venv --exclude run
