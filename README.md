# UnicodeFix

Normalizes Unicode to ASCII equivalents

## Installation

Clone the repository somewhere on your system. You will need to pop up a terminal window to do this.

Then copy and paste the following commands into the command window.

```bash
git clone https://github.com/unixwzrd/UnicodeFix.git
cd UnicodeFix
bash setup.sh
```

Setup will create a virtual environment to keep your system python clean.
It will add the items needed to startup the script into your .bashrc

Look at the [setup.sh](setup.sh) file to see what it does if you like, it's very simple.

The .bashrc items are necessary because I will have a shortcut you may use from the macOS context menu to run the script shortly.

## Usage

```bash
(python-3.10-PA-dev) [unixwzrd@xanax: UnicodeFix]$ python bin/cleanup-text.py --help
usage: cleanup-text.py [-h] [-o OUTPUT] [infile]

Clean Unicode quirks from text.

positional arguments:
  infile                Input file (or use STDIN)

options:
  -h, --help            show this help message and exit
  -o OUTPUT, --output OUTPUT
                        Output file (default: STDOUT)

python bin/cleanup-text.py <input_file>
```

## Coming SOon
- macSO Shortcut

## License  
Copyright 2025 unixwzrd@unixwzrd.ai

[MIT License](LICENSE)

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.