import urllib.request
import urllib.error
import json
from . import __version__

def check_for_updates():
    """
    Checks for updates from the upstream GitHub repository.
    Returns:
        tuple: (is_update_available, latest_version, current_version)
    """
    repo_url = "https://api.github.com/repos/amanasci/DecidRX_py/releases/latest"
    try:
        with urllib.request.urlopen(repo_url) as response:
            if response.status == 200:
                data = json.loads(response.read().decode())
                latest_version = data.get("tag_name")
                if latest_version:
                    # Remove 'v' prefix if present for comparison
                    clean_latest = latest_version.lstrip("v")
                    clean_current = __version__.lstrip("v")
                    
                    if clean_latest > clean_current:
                        return True, latest_version, __version__
                    else:
                        return False, latest_version, __version__
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None, "No releases found on upstream repository", __version__
        return None, f"HTTP Error {e.code}: {e.reason}", __version__
    except Exception as e:
        return None, str(e), __version__
    
    return None, "Unknown error", __version__
