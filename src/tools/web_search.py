#
#  Copyright (c) 2026
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import httpx
import logging
import requests
from requests.exceptions import HTTPError, ConnectionError, Timeout, RequestException
from typing import Optional, Dict, Any, Union
from src.tools.base import tool_with_interrupt

logger = logging.getLogger(__name__)

""""
Example:
>> >  # Basic usage with a dictionary
>> > payload = {'key1': 'value1', 'key2': 'value2'}
>> > content = get_url_content("https://httpbin.org/get", params=payload)

>> >  # Usage with a list of tuples (useful for duplicate keys)
>> > payload = [('tags', 'python'), ('tags', 'requests')]
>> > content = get_url_content("https://httpbin.org/get", params=payload)
"""


@tool_with_interrupt
def get_url_content(url: str, params: Optional[Dict[str, str] | list] = None, timeout: int = 10) -> Optional[str]:
    """
    Fetches the raw text content from a specified URL with error handling.

    Args:
        url: The destination URL to send the GET request to. Example "https://api.example.com/v1/data"

        params: Query string parameters to be appended to the URL.
            - If a dictionary is provided, keys with None values will not be added.
            Example: {search: python, page: 2} -> ?search=python&page=2
            - If a list of tuples is provided:
             Example: [(topic, python), (topic, requests)] -> ?topic=python&topic=requests

        timeout: Time to wait. Set it appropriately based on traffic request to server based on exception.
    Returns:
        Optional[str]: The decoded text content of the response if successful.
            Returns None if any exception occurs during the process.
    """
    try:
        # 10 second timeout for the initial connection and the reading of data
        response = requests.get(url, params=params, timeout=timeout)

        # Triggers HTTPError for 4xx or 5xx status codes
        response.raise_for_status()

        return response.text

    except HTTPError as http_err:
        logger.error(f"HTTP error occurred: {http_err}")
    except ConnectionError as conn_err:
        logger.error(f"Connection error: {conn_err}")
    except Timeout as timeout_err:
        logger.error(f"Timeout error: {timeout_err}")
    except RequestException as req_err:
        logger.error(f"General Request error: {req_err}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")

    return None
