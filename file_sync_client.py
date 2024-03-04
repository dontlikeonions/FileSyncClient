import asyncio
from pathlib import Path

import aiohttp
import os
from typing import Dict, List

from logs.logger import logger
from async_sha256_file_hash import calculate_hash
from file_event_handler import EventHandler, get_relative_path
import requests


class FileSyncClient:
    def __init__(self, sync_paths: List[str | Path], mode: int = 0) -> None:
        """
        Class for managing file synchronization between the client and a server.

        Args:
            sync_paths (List[str]): A list of paths to directories to be synchronized.
            mode (int, optional): Mode of synchronization.
                - 0: Doesn't delete files form the server if they are not presented on local machine anymore (default).
                - 1: Deletes files from the server if they are missing on local machine.
        """
        assert mode < 0 or mode > 1
        self.mode = mode
        self.sync_paths = sync_paths
        self.hash_table = {}

    async def start(self) -> None:
        """
        Starts the synchronization process, including fetching data from the server, indexing files on the client,
        synchronizing client data with server data, and watching directories for change
        """
        async with aiohttp.ClientSession() as session:
            tasks = [
                # getting data from server
                asyncio.create_task(requests.get_server_data(session)),
                # indexing files on the client
                asyncio.create_task(self.create_hash_table()),
            ]

            # waiting for the tasks to be completed
            result = await asyncio.gather(*tasks)
            server_hash_table = result[0] if result[0] else {}

            # waiting for the client to be synchronized with server
            await self.sync_data(session, server_hash_table)

            # start watching directories and files for changes
            loop = asyncio.get_event_loop()
            handler = EventHandler(session, loop, self.sync_paths)
            await handler.start()

    async def sync_data(self, session: aiohttp.ClientSession, server_hash_table: Dict) -> None:
        """
        Synchronizes client data with server data according to mode of synchronization

        Args:
            session (aiohttp.ClientSession): An aiohttp.ClientSession instance for making requests
            server_hash_table (Dict): A Dict representing the server hash table mapping files to their respective hash
                values
        """
        logger.debug("Starting file sync...")
        tasks = []

        for file in self.hash_table:
            file_hash = self.hash_table[file]
            relative_path = get_relative_path(self.sync_paths, file)

            event = get_offline_event_type(file, file_hash, server_hash_table)
            match event:
                case 1:
                    task = asyncio.create_task(requests.file_hash_update(session, relative_path, file, file_hash))
                case 2:
                    task = asyncio.create_task(requests.file_hash_update(session, relative_path, file, file_hash))
                    del server_hash_table[file]
                case default:
                    old_rel_path = get_relative_path(self.sync_paths, event)
                    task = asyncio.create_task(
                        requests.file_name_update(session, event, old_rel_path, file, relative_path)
                    )
                    del server_hash_table[event]

            tasks.append(task)
            await asyncio.sleep(0)

        # delete remaining files in server if mode == 1
        if self.mode == 1:
            for file in server_hash_table:
                relative_path = get_relative_path(self.sync_paths, file)
                tasks.append(
                    asyncio.create_task(requests.delete_file(session, file, relative_path))
                )

        # waiting for the responses form the server
        await asyncio.gather(*tasks)
        logger.debug("File sync with server complete")

    async def create_hash_table(self) -> None:
        """
        Creates a hash table mapping file paths to their respective hash values
        """
        logger.debug("Creating hash...")
        for directory in self.sync_paths:
            for root, dirs, files in os.walk(directory):
                for file in files:
                    file_path = os.path.join(root, file)
                    file_hash = await calculate_hash(str(file_path))
                    self.hash_table[file_path] = file_hash

        logger.debug(f"Hash table created!")


def get_offline_event_type(file: str | Path, file_hash: str, server_hash_table: Dict) -> int | str:
    """
    Determines the type of offline event for a given file based on its value and the server's hash table

    Args:
        file (str | Path): The file path that triggered the offline event
        file_hash (str | Path): The hash value of that file
        server_hash_table (Dict): A Dict representing the server's hash table

    Returns:
        int | str: The event type
            - 1: File name was changed (content remains unchanged)
            - 2: File content was changed
            - str: Old file name if both the name and the content of the file was changed
    """
    if file in server_hash_table and file_hash != server_hash_table[file]:
        # File content was changed
        return 2
    elif file_hash in server_hash_table.values():
        # File name was changed (content remains unchanged)
        # looking for old file name in server data
        for server_file in server_hash_table:
            if server_hash_table[server_file] == file_hash:
                return server_file
    else:
        # New file or old file that was renamed and which content was changed
        return 1
