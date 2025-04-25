$!/bin/bash

python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
chmod +x bin/cleanup-text.py

# Add the script to your PATH
if [[ ! "$PATH" =~ "$PWD/bin" ]]; then
    echo "adding necessary items for Python script to run"
    echo "source $PWD/venv/bin/activate" >> ~/.bashrc
    echo "export PATH=\"$PWD/bin:\$PATH\"" >> ~/.bashrc
fi