# LOL Extract

This tool is about extracting the files stored in LOL's WAD files. eg.: Map11.hu_HU.wad.client

## Usage

For now in beta you have to edit the main.py in order to extract the files.
At the end of the file is a small section with the line `wad_file_name = "insert wad file name here"`. As it says, you have to write the name of the WAD file there.

The resulting files will be extracted in a folder named `extracted`.

For the tool to figure out file names, you need to have a copy of the hashfile in this directory.
You can obtain it from here: https://www.mediafire.com/file/43iitaeotgr263c/hashes.game.txt/file
