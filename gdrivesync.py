'''
gdrivesync

Sync files in local directory to a Google Drive directory.
'''
import httplib2
import json
import fnmatch
import sys
import os
import getopt
import logging
from apiclient.discovery import build
from apiclient.http import MediaIoBaseUpload
from oauth2client.client import OAuth2WebServerFlow,  OAuth2Credentials

logging.basicConfig(level=logging.INFO)


class GoogleCredentials(object):
    def __init__(self, config_file):
        self.config_file = config_file
        self.config = {}

    def _load_credentials(self):
        self.config = json.loads(open(self.config_file).read())

    def _save_credentials(self):
        fd = open(self.config_file, 'w')
        fd.write(json.dumps(self.config))

    def _get_credentials(self):
        OAUTH_SCOPE = 'https://www.googleapis.com/auth/drive'
        REDIRECT_URI = 'http://localhost'

        flow = OAuth2WebServerFlow(self.config['client_id'],
                                   self.config['client_secret'],
                                   OAUTH_SCOPE,
                                   REDIRECT_URI)
        authorize_url = flow.step1_get_authorize_url()
        print 'Go to the following link in your browser: ' + authorize_url
        code = raw_input('Enter verification code: ').strip()
        credentials = flow.step2_exchange(code)
        return credentials

    def get_service(self):
        self._load_credentials()

        if not self.config.get('credentials'):
            logging.info("Credentials not found, begin the Oauth process.")
            credentials = self._get_credentials()
            self.config['credentials'] = credentials.to_json()
            self._save_credentials()
        else:
            credentials_json = self.config.get('credentials')
            credentials = OAuth2Credentials.from_json(credentials_json)

        # Create an httplib2.Http object and authorize it with our credentials
        http = httplib2.Http()
        http = credentials.authorize(http)

        drive_service = build('drive', 'v2', http=http)

        return drive_service


def match_any(name, patterns):
    '''
    Check if the name match any patterns.
    '''
    for pattern in patterns:
        if fnmatch.fnmatch(name, pattern):
            return True
    return False


def walk_files(root_path='.', patterns_include=None, patterns_exclude=None):
    '''
    A wrapper of os.walk(). If patterns_include is provided, only files matched
    any of patterns_include are returned; if patterns_exclude is provided,
    files matched any of patterns_exclude are removed from the results.
    The function will first evaluate patterns_include, then patterns_exclude.
    '''
    result = []
    if not root_path.endswith('/'):
        root_path += '/'
    for path, __, names in os.walk(root_path):
        prefix = path[len(root_path):]
        files = []
        for name in names:
            fullname = (prefix + '/' + name) if prefix else name
            if patterns_include and\
                     (not match_any(fullname, patterns_include)):
                continue
            if patterns_exclude and match_any(fullname, patterns_exclude):
                continue
            files.append(name)
        if files:
            result.append([prefix, files])
    return result


class GDriveSync(object):
    def __init__(self, service, target):
        '''
        :param service: The service of get_service by GoogleCredentials.
        :param target: The target folder to sync.
        '''
        self.service = service
        self.target = target

    def get_config(self):
        if not self.target.endswith('/'):
            self.target += '/'
        content = open('%s.gdrivesync' % self.target).read()
        self.config = json.loads(content)

    def get_directory(self, title, parent_id):
        '''
        Get the file object with title and parent_id.
        If not found, a None object will be returned.
        '''
        q = 'title = "%s" and "%s" in parents' % (title, parent_id)
        q += ' and trashed = false'
        q += ' and mimeType = "application/vnd.google-apps.folder"'
        r = self.service.files().list(q=q).execute()  # use the first matched
        if r['items']:
            r = r['items'][0]
        else:
            r = None
        return r

    def create_folder(self, title, parent_id):
        '''
        Create a folder with title under a parnet folder with parent_id.
        '''
        params = {'title': title,
                  'parents': [{'id': parent_id}],
                  'mimeType': 'application/vnd.google-apps.folder'}
        r = self.service.files().insert(body=params).execute()
        return r

    def recursive_path(self, path, root='root', ensure_path=False):
        '''
        Recursivly locate the path.
        :param path: The spcified path,
               heading and tailing '/' will be ignored.
        :param root: The parent folder id of path, default 'root'.
        :param ensure_path: If True, the not found folder will be created.
        '''
        directories = [i for i in path.strip().split('/') if i]
        parent_id = root
        r = None
        for directory in directories:
            r = self.get_directory(directory, parent_id)
            if r:
                parent_id = r['id']
            elif ensure_path:
                r = self.create_folder(directory, parent_id)
                parent_id = r['id']
            else:
                raise Exception("Folder %s not found." % directory)
        if r:
            return r
        else:
            return None

    def insert_file(self, root_path, path, title, parent_id):
        '''
        Insert a file to google drive.
        '''
        if not root_path.endswith('/'):
            root_path += '/'
        filename = root_path + path + '/' + title
        logging.info("Inserting %s to folder %s." % (filename, parent_id))
        media_body = MediaIoBaseUpload(open(filename),
                                       'text/plain',
                                       resumable=True)
        body = {
            'title': title,
            'description': title,
            'mimeType': 'text/plain',
            'parents': [{'id': parent_id}],
            'indexableText.text': open(filename).read()}
        file = self.service.files().insert(body=body,
                                           media_body=media_body).execute()
        return file

    def update_file(self, file_obj, root_path, path, title, parent_id):
        '''
        Update a file to google drive.
        '''
        if not root_path.endswith('/'):
            root_path += '/'
        filename = root_path + path + '/' + title
        logging.info("Updating %s to folder %s." % (filename, parent_id))
        media_body = MediaIoBaseUpload(open(filename),
                                       'text/plain',
                                       resumable=True)
        body = {'title': title,
                'description': title,
                'mimeType': 'text/plain',
                'indexableText.text': open(filename).read()}
        file = self.service.files().update(body=body,
                                           media_body=media_body,
                                           fileId=file_obj['id'],
                                           newRevision=True).execute()
        return file

    def get_file(self, title, parent_id):
        '''
        Get the file object named title in folder parent_id.
        '''
        q = 'title = "%s" and "%s" in parents' % (title, parent_id)
        q += ' and trashed = false'
        q += '  and mimeType != "application/vnd.google-apps.folder"'
        r = self.service.files().list(q=q).execute()
        if r['items']:
            r = r['items'][0]
        else:
            r = None
        return r

    def upload_files(self, root_path, files, root_id):
        '''
        Upload files located in root_path to folder root_id on
        Google Drive.
        '''
        for prefix, names in files:
            if prefix:
                path_obj = self.recursive_path(prefix,
                                               root=root_id,
                                               ensure_path=True)
                parent_id = path_obj['id']
            else:
                parent_id = root_id
            for name in names:
                file_obj = self.get_file(name, parent_id)
                if file_obj:
                    self.update_file(file_obj,
                                     root_path,
                                     prefix,
                                     name,
                                     parent_id)
                else:
                    self.insert_file(root_path, prefix, name, parent_id)

    def run(self):
        self.get_config()
        files = walk_files(root_path=self.target,
                           patterns_include=self.config.get('include'),
                           patterns_exclude=self.config.get('exclude'))
        remote_id = self.config.get('remote_id')
        if remote_id is None:
            if self.config.get('remote_dir'):
                path_obj = self.recursive_path(self.config.get('remote_dir'))
                if path_obj:
                    remote_id = path_obj['id']
        if remote_id is None:
            raise Exception("Remote path or id not existed.")
        self.upload_files(self.target, files, remote_id)


def main():
    opts, args = getopt.gnu_getopt(sys.argv[1:], 'c:')
    opts = dict(opts)
    config_file = 'config.json' if not '-c' in opts else opts['-c']
    gc = GoogleCredentials(config_file)
    service = gc.get_service()
    for arg in args:
        GDriveSync(service, arg).run()


if __name__ == '__main__':
    main()
