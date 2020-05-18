#!/bin/bash

if [[ ! $TRAVIS ]]; then
    echo "This script is made for travis-ci.org! It cannot run without \$TRAVIS."
    exit 1
fi

# Install python packages
pip install -r dev-requirements.txt

# Run SSH service, configure automatic access to localhost.
sudo start ssh
ssh-keygen -t rsa -f ~/.ssh/id_rsa -N "" -q
cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys
ssh-keyscan -t rsa localhost >> ~/.ssh/known_hosts