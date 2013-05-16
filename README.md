gdrivesync
==========

A simple python tools to sync files in a local directory to Google Drive directory.

##usage
Please register a Google api key for access Drive API, and

    python -c gdrivesync.py config_file.json [dir_name1[, dir_name2[, ...]]]
    
The confie_file.json should be a json file like

    {"client_secret": "YOUR_CLIENT_SECRET",
     "client_id": "YOUR_CLIENT_ID"}
    
Each of dir_name* is a local directory to sync, for specify the sync beheavior, there should be a _.gdrivesync_ file contained in the directory. For example:

    {"exclude": [".gdrivesync"],
     "include": ["*.txt", "*.md"],
     "remote_dir": "gdrive-sync",
     "remote_id": "GOOGLE_DRIVE_FOLDER_ID"}
     
The meanning of keys in .gdrivesync files are:

+ __remote\_id__ The id of your target folder in google drive, your files will be sync to this folder.
+ __remote\_dir__ If no _remote\_id_ provided, the tools will try find the id of this folder in your google drive.
+ __include__ If provided, only files matched specified patterns will be synced.
+ __exclude__ If provided, files matched specified patterns will be removed. Note that the tools will adopt _include_ first, _exclude_ after.
