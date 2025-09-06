# Scripts

## mirror_uproject.py

Pulling or pushing Unreal project directory to dropbox.

### Arguments:

- mode: `push` or `pull`
  compulsory
- local directory: windows style path
  compulsory
- remote directory: local dropbox directory windows style path
  optional, in case it is missing it points to: "D:\Dropbox\Projects\"

### Parameters:

- force-delete: make sure tge deleted files removed on the synced side
  optional, without this the deletions are not synced
- dry-run: symulate the process and log out the differences, no modifications executed
  optional


### Examples:
- python D:\Scripts\mirror_uproject.py pull "D:\GameDev\Projects\BlackFeatherFate" --force-delete
- python D:\Scripts\mirror_uproject.py push  "D:\GameDev\Projects\BlackFeatherFate"
