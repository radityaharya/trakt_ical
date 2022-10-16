import hashlib
import requests


def generate_color_code_from_string(string):
    """
    It takes a string, converts it to a byte string, hashes it, and returns the first six characters of
    the hash as a hexadecimal string

    Args:
      string: The string to generate the color code from.

    Returns:
      A hexadecimal color code.
    """
    return "#" + hashlib.md5(string.encode()).hexdigest()[:6]


def upload_to_s3(endpoint, file_path, x_api_key, file_name):
    """
    It uploads a file to an S3 bucket

    Args:
      endpoint: The endpoint of the S3 bucket.
      file_path: The path to the file you want to upload.
      x_api_key: The API key for the S3 bucket.
      file_name: The name of the file you want to upload to S3.

    Returns:
      The text of the response.
    """
    r = requests.put(
        endpoint + "/" + file_name,
        data=open(file_path, "rb"),
        headers={"x-api-key": x_api_key},
    )
    return r.text
