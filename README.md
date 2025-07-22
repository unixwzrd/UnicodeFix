# UnicodeFix

![UnicodeFix Hero Image](docs/controlling-unicode.png)

- [UnicodeFix](#unicodefix)
    - [**Finally - a tool that blasts AI fingerprints, torches those infuriating smart quotes, and leaves your code \& docs squeaky clean for real humans.**](#finally---a-tool-that-blasts-ai-fingerprints-torches-those-infuriating-smart-quotes-and-leaves-your-code--docs-squeaky-clean-for-real-humans)
  - [Why Is This Happening?](#why-is-this-happening)
  - [Installation](#installation)
  - [Usage](#usage)
  - [Brief Examples](#brief-examples)
    - [Pipe / Filter (STDIN to STDOUT)](#pipe--filter-stdin-to-stdout)
    - [Batch Clean](#batch-clean)
    - [In-Place (Safe) Clean](#in-place-safe-clean)
    - [Preserve Temp File for Backup](#preserve-temp-file-for-backup)
    - [Using in vi/vim/macvim](#using-in-vivimmacvim)
  - [What's New / What's Cool](#whats-new--whats-cool)
  - [Shortcut for macOS](#shortcut-for-macos)
    - [To add the Shortcut:](#to-add-the-shortcut)
  - [What's in This Repository](#whats-in-this-repository)
  - [Testing and CI/CD](#testing-and-cicd)
  - [Contributing](#contributing)
  - [Support This and Other Projects](#support-this-and-other-projects)
  - [Changelog](#changelog)
  - [License](#license)

---

### **Finally - a tool that blasts AI fingerprints, torches those infuriating smart quotes, and leaves your code & docs squeaky clean for real humans.**

Ever open up a file and instantly know it came from ChatGPT, Copilot, or one of their AI cousins? (Yeah, so can everyone else now.)
UnicodeFix vaporizes all the weird dashes, curly quotes, invisible space ninjas, and digital "tells" that out you as an AI user - or just make your stuff fail linters and code reviews.

**Whether you're a student, a dev, or an open-source rebel: this is your "eraser for AI breadcrumbs."**

_Yes, it helps students cheat on their homework._
It also makes blog posts and AI-proofed emails look like you sweated over every character.
Nearly a thousand people have grabbed it. Nobody's bought me a coffee yet, but hey… there's a first time for everything.

---

## Why Is This Happening?

Some folks think all this Unicode cruft is a side-effect of generative AI's training data. Others believe it's a deliberate move - baked-in "watermarks" to ID machine-generated text. Either way: these artifacts leave a trail. UnicodeFix wipes it.

---

## Installation

Clone the repository and run the setup script:

```
git clone https://github.com/unixwzrd/UnicodeFix.git
cd UnicodeFix
bash setup.sh
```

The `setup.sh` script:
- Creates a Python virtual environment just for UnicodeFix
- Installs dependencies
- Adds handy startup config to your `.bashrc` for one-command usage

See [setup.sh](setup.sh) for the nitty-gritty.

For serious environment nerds: [VenvUtil](https://github.com/unixwzrd/venvutil) is my full-featured Python env toolkit.

---

## Usage

Once installed and activated:

```
(python-3.10-PA-dev) [unixwzrd@xanax: UnicodeFix]$ cleanup-text --help

usage: cleanup-text [-h] [-i] [-o OUTPUT] [-t] [-p] [-n] [infile ...]

Clean Unicode quirks from text. If no input files are given, reads from STDIN and writes to STDOUT (filter mode). If input files are given, creates cleaned files with .clean before the extension (e.g., foo.txt -> foo.clean.txt). Use -o - to force output to STDOUT for all input files, or -o <file> to specify a single output file
(only with one input file).

positional arguments:
  infile                Input file(s)

options:
  -h, --help            show this help message and exit
  -i, --invisible       Preserve invisible Unicode characters (zero-width, non-breaking, etc.)
  -o OUTPUT, --output OUTPUT
                        Output file name, or '-' for STDOUT. Only valid with one input file, or use '-' for STDOUT with multiple files.
  -t, --temp            In-place cleaning: Move each input file to .tmp, clean it, write cleaned output to original name, and delete .tmp after success.
  -p, --preserve-tmp    With -t, preserve the .tmp file after cleaning (do not delete it). Useful for backup or manual recovery.
  -n, --no-newline      Do not add a newline at the end of the output file (suppress final newline).
```

## Brief Examples

### Pipe / Filter (STDIN to STDOUT)
```
cat file.txt | cleanup-text > cleaned.txt
```

### Batch Clean
```
cleanup-text *.txt
```

### In-Place (Safe) Clean
```
cleanup-text -t myfile.txt
```

### Preserve Temp File for Backup
```
cleanup-text -t -p myfile.txt
```

### Using in vi/vim/macvim

```
:%!cleanup-text
```

You can run it from Vim, VS Code in Vim mode, or as a pre-commit. Use it for email, blog posts, whatever. Ignore the naysayers - this is *real-world convenience.*

See [cleanup-text.md](docs/cleanup-text.md) for deeper dives and arcane options.

- **Make sure your Python environment is activated** before launching your editor, or wrap it in a shell script that does it for you.
- Adjust your editor's shell settings as needed for best results.

---

## What's New / What's Cool

- **Vaporizes invisible Unicode (unless you tell it not to)**
- **Normalizes EM/EN dashes to true ASCII - no more AI " - " nonsense**
- **Wipes AI "tells," watermarks, and digital fingerprints**
- **Fixes trailing whitespace, normalizes newlines, burns the digital junk**
- **Portable (Python 3.7+), cross-platform**
- **Integrated macOS Shortcut for right-click cleaning in Finder**
- **Can be used in CI/CD - but also by normal humans, not just pipeline freaks**

> *Fun fact*: Even Python will execute code with "curly quotes." Your IDE, email client, and browser all sneak these in. UnicodeFix hunts them down and torches them.

---

## Shortcut for macOS

UnicodeFix ships with a macOS Shortcut for direct Finder integration.

Right-click files, pick a Quick Action, and - bam - no terminal required.

### To add the Shortcut:

1. Open the **Shortcuts** app.
2. Choose `File -> Import`.
   ![Shortcuts App Menu](docs/Screenshot%202025-04-25%20at%2005.50.57.png)
3. Select the Shortcut in `macOS/Strip Unicode.shortcut`.
   ![Import Shortcut](docs/Screenshot%202025-04-25%20at%2005.51.54.png)
4. Edit it to point to your local `cleanup-text.py`.
   ![Edit Shortcut Script Path](docs/Screenshot%202025-04-25%20at%2005.07.47.png)
5. Relaunch Finder (`Cmd+Opt+Esc` → select Finder → Relaunch) if needed.
6. After setup, right-click files, choose `Quick Actions`, select `Strip Unicode`.
   ![Select Shortcut File](docs/Screenshot%202025-04-25%20at%2005.47.51.png)

---

## What's in This Repository

- [bin/cleanup-text.py](bin/cleanup-text.py) - Main cleaning script
- [bin/cleanup-text](bin/cleanup-text) - Symlink for CLI usage
- [setup.sh](setup.sh) - Easy setup and env configuration
- [requirements.txt](requirements.txt) - Python dependencies
- [macOS/](macOS/) - Shortcuts, scripts for Finder
- [data/](data/) - Example test files
- [test/](test/) - Automated test suite for all features/edge cases
- [docs/](docs/) - Documentation and screenshots
- [LICENSE](LICENSE)
- [README.md](README.md) - This file

---

## Testing and CI/CD

UnicodeFix comes with a full, automated test suite:

- Runs every feature & scenario on files in `data/`
- Outputs to `test_output/` (by scenario, with diffs and word counts)
- Clean up with: `./test/test_all.sh clean`
- Plug into your CI/CD pipeline or just use as a "paranoia check" before shipping anything

**Pro tip:** Run the tests before you merge, publish, or email a "final" version.

See [docs/test-suite.md](docs/test-suite.md) for the deep dive.

---

## Contributing

Feedback, bug reports, and patches welcome.

If you've got a better integration path for your favorite platform, let's make it happen.
Pull requests with attitude, creativity, and clean diffs appreciated.

---

## Support This and Other Projects

If UnicodeFix (or my other projects) saved your bacon or made you smile,
please consider fueling my caffeine habit and indie dev obsession:

- [Patreon](https://patreon.com/unixwzrd)
- [Ko-Fi](https://ko-fi.com/unixwzrd)
- [Buy Me a Coffee](https://buymeacoffee.com/unixwzrd)

One coffee = one more tool released to the wild.

Thank you for keeping solo development alive!

---

## Changelog

**See [CHANGELOG.md](CHANGELOG.md) for the latest drop.**

---

## License

Copyright 2025
[unixwzrd@unixwzrd.ai](mailto:unixwzrd@unixwzrd.ai)

[MIT License](LICENSE)

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.