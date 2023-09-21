from utils.download import DL_STATUS, download_file
from utils.upload import upload_file_to_channel
import re
import requests

def getFilename_fromCd(cd):
    if not cd:
        return None
        fname = re.findall('filename=(.+)', cd)
    if len(fname) == 0:
        return None
    return fname[0]
async def start_remote_upload(session, hash, url):
    ext = await download_file(session, hash, url)
    r = requests.get(url, allow_redirects=True)
    orgname = getFilename_fromCd(r.headers.get('content-disposition'))
    if ext:
        await upload_file_to_channel(hash, hash + "." + ext, ext,orgname)
