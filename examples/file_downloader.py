import os
import requests
from typing import Union, List
from math import log2, floor, pow


def format_size(size_bytes):
    """
    Formats the size in bytes into a more readable format (KB, MB, etc.).

    Args:
        size_bytes (int): Size in bytes.

    Returns:
        str: Formatted size string.
    """
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = int(floor(log2(size_bytes) / 10)) if size_bytes > 0 else 0
    p = pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"


def download_files(filenames: Union[List[str], str], target_directory: str = "files"):
    """
    Downloads files from a base URL and saves them to a specified directory.

    Args:
        filenames (Union[List[str], str]): A list of filenames or a single filename to download.
        target_directory (str): The directory where the files will be saved. Defaults to "files".

    Raises:
        requests.exceptions.RequestException: If there is an issue with the HTTP request.
        OSError: If there is an issue with file or directory operations.

    Example:
        >>> download_files(['file1.txt', 'file2.txt'], target_directory='downloads')
        Downloaded downloads/file1.txt (1.02 KB)
        Downloaded downloads/file2.txt (2.04 MB)

        >>> download_files('file1.txt', target_directory='downloads')
        Downloaded downloads/file1.txt (1.02 KB)
    """
    base_url = "<some url>"

    # Ensure the target directory exists
    if not os.path.exists(target_directory):
        os.makedirs(target_directory)

    if isinstance(filenames, str):
        file_urls = {filenames: base_url + filenames}
    else:
        file_urls = {f: base_url + f for f in filenames}

    total_files = len(file_urls)
    file_paths = []
    for idx, (file_name, url) in enumerate(file_urls.items()):
        file_path = os.path.join(target_directory, file_name)
        file_paths.append(file_path)
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            readable_size = format_size(file_size)
            print(
                f"File already exists: {file_path} ({readable_size}) [{idx + 1}/{total_files}]"
            )
        else:
            try:
                response = requests.get(url)
                response.raise_for_status()  # Check if the request was successful
                with open(file_path, "wb") as file:
                    file.write(response.content)

                # Print the location and size of the downloaded file
                file_size = os.path.getsize(file_path)
                readable_size = format_size(file_size)
                print(
                    f"Downloaded {file_path} ({readable_size}) [{idx + 1}/{total_files}]"
                )

            except requests.exceptions.RequestException as e:
                print(f"Failed to download {url}: {e}")
    return file_paths
