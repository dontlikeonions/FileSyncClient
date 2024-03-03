import asyncio
import sys

import aiohttp
import json
import configparser

from typing import Dict

from logs.logger import logger


config = configparser.ConfigParser()
config.read('settings.ini')

SERVER_IP = config.get('Server', 'ip')
DEFAULT_PORT = config.get('Server', 'port')
URL = "https://{0}:{1}".format(SERVER_IP, str(DEFAULT_PORT))

REQUEST_TIMEOUT = config.getint('Timeouts', 'request_timeout')
timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)


def create_payload(file_path: str, new_rel_path: str = None,
                   old_path: str = None, old_rel_path: str = None,
                   file_hash: str = None) -> Dict:
    payload = {'file_path': file_path,
               'relative_path': new_rel_path,
               'old_path': old_path,
               'old_relative_path': old_rel_path,
               'file_hash': file_hash,
               }
    return payload


async def get_server_data(session: aiohttp.ClientSession) -> Dict:
    logger.debug("Getting server data")

    try:
        async with session.get(URL + '/get_data', timeout=timeout) as response:
            text = await response.text()
            data = json.loads(text)
            logger.debug(f"Received file data from server: {data}")
            return data
    except asyncio.TimeoutError:
        logger.error(f"Timeout error: Unable to get data from server for {REQUEST_TIMEOUT} seconds")
    except aiohttp.client_exceptions.ClientConnectorError as e:
        logger.error(e)
        print(f"Cannot connect to host {SERVER_IP}:{DEFAULT_PORT} Try to reload the app")
        sys.exit()
    finally:
        return {}


async def file_hash_update(session: aiohttp.ClientSession, relative_path: str, file_path: str, file_hash: str) -> None:
    logger.debug(f"Updating file: {file_path}")

    payload = create_payload(file_path, relative_path, file_hash=file_hash)

    with open(file_path, 'rb') as file:
        file_data = file.read()
        data = aiohttp.FormData()
        data.add_field("file", file_data, filename=file_path)
        data.add_field("payload", json.dumps(payload))

        try:
            async with session.post(URL + '/file_hash_update', data=data, timeout=timeout) as response:
                response_text = await response.text()
                logger.debug(f"File {file_path} updated, response: {response_text}")
        except asyncio.TimeoutError:
            logger.error(f"Timeout error: Unable to update file data '{file_path}' for {REQUEST_TIMEOUT} seconds")
        except aiohttp.client_exceptions.ClientConnectorError as e:
            logger.error(e)
            print(f"Cannot connect to host {SERVER_IP}:{DEFAULT_PORT} Try to reload the app")
            sys.exit()


async def file_name_update(session: aiohttp.ClientSession,
                           old_path: str, old_rel_path: str,
                           new_path: str, new_rel_path: str) -> None:
    logger.debug(f"Updating file name: Old name: '{old_path}', New name: '{new_path}'")

    payload = create_payload(new_path, new_rel_path, old_path, old_rel_path)

    try:
        async with session.post(URL + '/file_name_update', json=payload, timeout=timeout) as response:
            response_text = await response.text()
            logger.debug(f"Updating file name '{new_path}', response: {response_text}")
    except asyncio.TimeoutError:
        logger.error(f"Timeout error: Unable to update file name '{new_path}' for {REQUEST_TIMEOUT} seconds")
    except aiohttp.client_exceptions.ClientConnectorError as e:
        logger.error(e)
        print(f"Cannot connect to host {SERVER_IP}:{DEFAULT_PORT} Try to reload the app")
        sys.exit()


async def delete_file(session: aiohttp.ClientSession, file_path: str, relative_path: str) -> None:
    logger.error(f"Removing file: {file_path}")

    payload = create_payload(file_path, relative_path)

    try:
        async with session.delete(URL + '/delete_file', json=payload, timeout=timeout) as response:
            response_text = await response.text()
            logger.debug(f"Deleting file: '{file_path}', response: {response_text}")
    except asyncio.TimeoutError:
        logger.error(f"Timeout error: Unable to delete '{file_path}' for {REQUEST_TIMEOUT} seconds")
    except aiohttp.client_exceptions.ClientConnectorError as e:
        logger.error(e)
        print(f"Cannot connect to host {SERVER_IP}:{DEFAULT_PORT} Try to reload the app")
        sys.exit()
