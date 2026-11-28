import os
def load():
    return open(os.path.join('/opt', 'ci-data', 'fixtures.json')).read()
