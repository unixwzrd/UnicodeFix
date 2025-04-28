# UnicodeFix

UnicodeFix normalizes problematic Unicode artifacts into clean ASCII equivalents.

This project was created to address the increasing frequency of invisible and typographic Unicode characters causing issues in code, configuration files, AI detection, and document processing.

**This is an early release. Further polishing and enhancements will follow.**

- [UnicodeFix](#unicodefix)
  - [Installation](#installation)
  - [Usage](#usage)
    - [Pipe / Filter (STDIN to STDOUT)](#pipe--filter-stdin-to-stdout)
    - [Using in vi/vim/macvim](#using-in-vivimmacvim)
  - [Shortcut for macOS](#shortcut-for-macos)
    - [To add the Shortcut:](#to-add-the-shortcut)
  - [What's in This Repository](#whats-in-this-repository)
  - [Contributing](#contributing)
  - [Support This and Other Projects](#support-this-and-other-projects)
  - [Changelog](#changelog)
    - [2025-04-27](#2025-04-27)
    - [2025-04-26](#2025-04-26)
  - [License](#license)

## Installation

Clone the repository and run the setup script:

```bash
git clone https://github.com/unixwzrd/UnicodeFix.git
cd UnicodeFix
bash setup.sh
```

The \`setup.sh\` script:

- Creates a dedicated Python virtual environment
- Installs required dependencies
- Adds startup configuration to your \`.bashrc\` for easier usage

You can review [setup.sh](setup.sh) to see exactly what is modified.

I also maintain a broader toolset for virtual environment management here: [VenvUtil](https://github.com/unixwzrd/venvutil), which may be of interest for more advanced users.

## Usage

Once installed and activated:

```bash
(python-3.10-PA-dev) [unixwzrd@xanax: UnicodeFix]$ python bin/cleanup-text.py --help
usage: cleanup-text.py [-h] [infile ...]

Clean Unicode quirks from text.

positional arguments:
  infile                Input file(s)

options:
  -h, --help            Show this help message and exit
```

### Pipe / Filter (STDIN to STDOUT)

UnicodeFix can operate as a standard UNIX pipe:

```bash
cat file.txt | cleanup-text > cleaned.txt
```

If no input file arguments are given, it automatically reads from standard input and writes to standard output.

### Using in vi/vim/macvim

You can run UnicodeFix as a filter within vi/vim/macvim:

```vim
:%!cleanup-text
```

This command rewrites the entire buffer with cleaned text.

**Note**:
- Ensure your virtual environment is activated before launching your editor, or
- Use a shell wrapper that sources your \`.bashrc\` and activates the environment automatically.

Depending on how you manage virtual environments, you may need to adjust your editor’s shell invocation settings.

## Shortcut for macOS

UnicodeFix includes a macOS Shortcut for direct Finder integration.

You can right-click one or more files and select a Quick Action to clean Unicode quirks without opening a terminal.

### To add the Shortcut:

1. Open the **Shortcuts** app.
2. Navigate to \`File -> Import\`.

   ![Shortcuts App Menu](docs/Screenshot%202025-04-25%20at%2005.50.57.png)

3. Select the Shortcut file located in \`macOS/Strip Unicode.shortcut\`.

   ![Import Shortcut](docs/Screenshot%202025-04-25%20at%2005.51.54.png)

4. Edit the Shortcut to point to your local installation of \`cleanup-text.py\`.

   ![Edit Shortcut Script Path](docs/Screenshot%202025-04-25%20at%2005.07.47.png)

5. You may need to relaunch Finder (\`Command+Option+Esc\` → Select Finder → Relaunch).

6. After setup, right-click selected files, choose \`Quick Actions\`, and select \`Strip Unicode\`.

   ![Select Shortcut File](docs/Screenshot%202025-04-25%20at%2005.47.51.png)

## What's in This Repository

- [bin/cleanup-text.py](bin/cleanup-text.py) — Main cleaning script
- [bin/cleanup-text](bin/cleanup-text) — Symlink for command-line usage
- [setup.sh](setup.sh) — Virtual environment setup script
- [requirements.txt](requirements.txt) — Python dependencies
- [macOS/](macOS/) — macOS Shortcut for Finder integration
- [data/](data/) — Example test files with Unicode artifacts
- [docs/](docs/) — Documentation and screenshots
- [LICENSE](LICENSE) — License information
- [README.md](README.md) — This file

## Contributing

Feedback, testing, bug reports, and pull requests are welcome.

If you find a better integration path for Linux or Windows platforms, feel free to open an issue or contribute a patch.

## Support This and Other Projects

If you find UnicodeFix or my other projects valuable, please consider supporting continued development:

- [Patreon](https://www.patreon.com/unixwzrd)
- [Ko-Fi](https://ko-fi.com/unixwzrd)
- [Buy Me a Coffee](https://www.buymeacoffee.com/unixwzrd)

Thank you for your support.

## Changelog

### 2025-04-27
- Fixed behavior when processing STDIN pipes
- Added trailing whitespace and blank line normalization
- Added shell script wrapper for easier activation from editors

### 2025-04-26
- Initial release

## License

Copyright 2025  
[unixwzrd@unixwzrd.ai](mailto:unixwzrd@unixwzrd.ai)

[MIT License](LICENSE)

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.