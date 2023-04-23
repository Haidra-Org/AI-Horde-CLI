# AI Horde Command Line Interface

This repository contains python scripts which allow you to interface with the [AI Horde](https://aihorde.net) via a CLI.

## Installation

1. Git clone [this repository](https://github.com/db0/AI-Horde-CLI)
1. Make sure you have python3 installed
1. Open a git bash (or just bash in linux)
1. Download the cli requirements with `python -m pip install -r cli_requirements.txt --user`

## Usage

All `cli_requests_*.py` scripts work the same way. You simply run the script using python, and pass any command line arguments.

You can use `-h` to see the help menu for each. Example:

```
$ python cli_request_alchemy.py -h
usage: cli_request_alchemy.py [-h] [--api_key API_KEY] [-f FILENAME] [-v] [-q] [--horde HORDE]
                              [--trusted_workers] [--source_image SOURCE_IMAGE]

options:
  -h, --help            show this help message and exit
  --api_key API_KEY     The API Key to use to authenticate on the Horde. Get one in
                        https://aihorde.net/register
  -f FILENAME, --filename FILENAME
                        The filename to use to save the images. If more than 1 image is
                        generated, the number of generation will be prepended
  -v, --verbosity       The default logging level is ERROR or higher. This value increases the
                        amount of logging seen in your screen
  -q, --quiet           The default logging level is ERROR or higher. This value decreases the
                        amount of logging seen in your screen
  --horde HORDE         Use a different horde
  --trusted_workers     If true, the request will be sent only to trusted workers.
  --source_image SOURCE_IMAGE
                        A file path to an image file must be provided if one is not set in
                        cliRequestsData.
```

## CliRequestData

All CLIs also have a corresponsing `cliRequestsData_*_template.yml` file. 

To use it, copy `cliRequestsData_*_template.yml` into `cliRequestsData_*.yml` and edit its variables. 

CLI arguments will take precedence, but anything else will use the values set in `cliRequestsData_*.yml` as the defaults.
