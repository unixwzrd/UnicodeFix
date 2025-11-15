$!/bin/bash

python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Add the script to your PATH
if [[ ! "$PATH" =~ "$PWD/bin" ]]; then
    echo "adding necessary items for Python script to run"
    echo "source $PWD/venv/bin/activate" >> ~/.bashrc
    echo "export PATH=\"$PWD/bin:\$PATH\"" >> ~/.bashrc
fi

# Source the .bashrc file to add the necessary items to the PATH
source ~/.bashrc

echo "You will need to install teh package using pip as described in the README.md file. Additional information is in the README.md file for more features of the package."
echo ""
echo "Quick Start - simply run the following command and it will install the package and make it available to use:"
echo "pip install ."
echo ""
echo "If you wish to do development, or want to use the package in your own projects, use the following command:"
echo "pip install -e ."
echo ""
echo "if you wish to use teh optional NLTK analytics, install the following optional extras for current and future NLP metrics:"
echo "pip install .[nlp]"
echo ""