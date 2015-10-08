"""Integration with Google Cloud Storage.

"""
import os
import requests

# Root URL to use for our queries.
GCS = "https://www.googleapis.com/storage/v1/"

DEFAULT_BUCKET = "llvm-build-artifacts"

BUCKET = os.getenv("BUCKET", DEFAULT_BUCKET)


def fetch_builders():
    """Each build kind is stored as a folder in the GCS bucket.
    List all the folders in the bucket, which is our list of possible
    compilers.
    """
    params = {'delimiter': "/", 'fields': "prefixes"}
    r = requests.get(GCS + "b/" + BUCKET + "/o", params=params)
    r.raise_for_status()
    reply_data = r.json()
    folders = reply_data['prefixes']
    no_slashes = [x.replace("/", "") for x in folders]
    return no_slashes


def fetch_builds(project):
    """Given a builder name, get the list of all the files stored for that
    builder.
    """
    assert project is not None
    params = {'delimiter': "/",
              "fields": "kind,items(name, mediaLink)",
              'prefix': project + "/"}
    r = requests.get(GCS + "b/" + BUCKET + "/o", params=params)
    r.raise_for_status()
    reply_data = r.json()
    return reply_data

#  Dunno what this could be moved up to?
CHUNK_SIZE = 5124288


def get_compiler(url, filename):
    """Get the compiler at the url, and save to filename."""
    r = requests.get(url)
    r.raise_for_status()
    with open(filename, 'wb') as fd:
        for chunk in r.iter_content(CHUNK_SIZE):
            fd.write(chunk)
    return filename
