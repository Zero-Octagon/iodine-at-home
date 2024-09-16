import core.settings as settings
from alist import AlistClient, AlistFileSystem

class Alist:
    def __init__(self, url: str, username: str, password: str):
        self.client = AlistClient(url, username, password)
    
alist = Alist(settings.ALIST_URL, settings.ALIST_USERNAME, settings.ALIST_PASSWORD)