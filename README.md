# UnicodeFix

Normalizes Unicode to ASCII equivalents

## Installation

I would recommend setting up a virtual environment so when you install the requirements it doesn't mess with your system python.

```bash
git clone https://github.com/unixwzrd/UnicodeFix.git
cd UnicodeFix
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

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

## License  
Copyright 2025 unixwzrd@unixwzrd.ai

[MIT License](LICENSE)

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.