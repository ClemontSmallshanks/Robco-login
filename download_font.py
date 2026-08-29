import urllib.request
import zipfile
import os

url = 'https://fonts.google.com/download?family=Share+Tech+Mono'
zip_path = '/tmp/share_tech_mono.zip'
extract_path = '/home/regi/Desktop/Fallout login/robco-greeter/app/assets/fonts'

os.makedirs(extract_path, exist_ok=True)
print('Downloading...')
urllib.request.urlretrieve(url, zip_path)
print('Extracting...')
with zipfile.ZipFile(zip_path, 'r') as zip_ref:
    zip_ref.extractall(extract_path)
print('Done!')
