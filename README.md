# UnicodeFix

Normalizes Unicode to ASCII equivalents.

**I'm getting this out quickly as people need it. Updates will follow to polish this up more soon.**

- [UnicodeFix](#unicodefix)
  - [Installation](#installation)
  - [Usage](#usage)
  - [Shortcut for macOS](#shortcut-for-macos)
    - [To add the shortcut:](#to-add-the-shortcut)
  - [What's in This Repo:](#whats-in-this-repo)
  - [Contributing](#contributing)
  - [Support This and Other Projects I Have](#support-this-and-other-projects-i-have)
  - [Changelog](#changelog)
    - [2025-04-27](#2025-04-27)
    - [2025-04-26](#2025-04-26)
  - [License](#license)

## Installation

Clone the repository somewhere on your system. You will need to pop open a terminal window to do this.

Then copy and paste the following commands into the terminal:

```bash
git clone https://github.com/unixwzrd/UnicodeFix.git
cd UnicodeFix
bash setup.sh
```

Setup will create a virtual environment to keep your system Python clean. I also have a whole set of [Virtual Environment Utilities](https://github.com/unixwzrd/venvutil) repo  it's likely overkill for most people., but it does contain a lot of useful utilities and tools for managing Python Virtual environments using Pip and Conda, along with many other handy tools for AI and Unix.

It will also add the items needed to start the script into your `.bashrc`.

Look at the [setup.sh](setup.sh) file to see exactly what it does if you like — it's very simple.

The `.bashrc` items are necessary because I have a Shortcut you may use from the macOS context menu to run the script directly.

## Usage

```bash
(python-3.10-PA-dev) [unixwzrd@xanax: UnicodeFix]$ python bin/cleanup-text.py --help
usage: cleanup-text.py [-h] [infile ...]

Clean Unicode quirks from text.

positional arguments:
  infile                Input file(s)

options:
  -h, --help            Show this help message and exit

Example:
python bin/cleanup-text.py <input_file>
```

The output file will be named the same as the input file, but with a `.clean.txt` extension.

You can select multiple files at once.

## Shortcut for macOS

There is a "Shortcut" file in the `macOS/` directory which may be imported into the Shortcuts app.  
It will allow the script to be run as a **Quick Action** from the Finder "Right Click" menu.  
This allows selecting multiple files and scrubbing the Unicode quirks from them in bulk.

### To add the shortcut:

1. Open the "Shortcuts" app.

2. Go to `File -> Import...`

   ![Shortcuts App Menu](docs/Screenshot%202025-04-25%20at%2005.50.57.png)

3. Navigate to the `macOS` directory in this repository and select the `Strip Unicode.shortcut` file.

   ![Import Shortcut](docs/Screenshot%202025-04-25%20at%2005.51.54.png)

4. You will need to open the shortcut and change the location path of the `cleanup-text.py` script.

   ![Edit Shortcut Script Path](docs/Screenshot%202025-04-25%20at%2005.07.47.png)

5. You may have to restart Finder (use `Command+Option+Esc`, select Finder, and click "Relaunch").

6. Once setup, right-click on a file or multiple files in Finder, go to `Quick Actions`, and select `Strip Unicode`.

   ![Select Shortcut File](docs/Screenshot%202025-04-25%20at%2005.47.51.png)

   This will invoke the script on the selected files and create `.clean.txt` versions.

Strip all the Unicode quirks out of your text files right in the finder using a Quick Action!

If you know a better way for Linux or Windows users, feel free to submit a PR with your improvements.

## What's in This Repo:

- [bin/cleanup-text.py](bin/cleanup-text.py) — The script that cleans up the text.
- [bin/cleanup-text](bin/cleanup-text) — A symlink without the `.py` extension for prettier usage in scripts.
- [setup.sh](setup.sh) — A script that sets up the virtual environment.
- [LICENSE](LICENSE) — The license for the project.
- [README.md](README.md) — This file.
- [requirements.txt](requirements.txt) — The dependencies needed to run.
- [data/](data/) — Sample files full of Unicode issues for testing.
- [docs/](docs/) — Supporting documentation for the project.
- [macOS/](macOS/) — The Shortcut file for macOS users.

## Contributing

If you have suggestions, enhancements, or fixes, feel free to open an issue or pull request!  
Testing and feedback are also very welcome.

## Support This and Other Projects I Have

AI and Unix are my passions — but I need to pay the bills too.

If you find this project useful, please tell others, and consider supporting my work:

- [Patreon](https://www.patreon.com/unixwzrd)
- [Buy me a Ko-Fi](https://ko-fi.com/unixwzrd)
- [Buy me a Coffee](https://www.buymeacoffee.com/unixwzrd)

Thank you!


## Changelog

### 2025-04-27
 - bug fix for filtering STDIO pipes
 - added a shell script wrapper to source in your .bashrc, presumable with the virtual environment activated.

### 2025-04-26
- Initial release.

## License

Copyright 2025  
[unixwzrd@unixwzrd.ai](mailto:unixwzrd@unixwzrd.ai)

[MIT License](LICENSE)

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.