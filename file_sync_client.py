import asyncio
import aiohttp
import os
from typing import Dict, List

from logs.logger import logger
from async_sha256_file_hash import calculate_hash
from file_event_handler import EventHandler, get_relative_path
import requests


class FileSyncClient:
    def __init__(self, sync_paths: List[str], mode: int = 0) -> None:
        # mode == 0: soft mode, doesnt delete files from server
        # mode == 1: hard mode, delete files from server if they are missing in client
        self.mode = mode
        self.sync_paths = sync_paths
        self.hash_table = {}

    async def start(self) -> None:
        async with aiohttp.ClientSession() as session:
            tasks = [
                # getting data from server
                asyncio.create_task(requests.get_server_data(session)),
                # indexing files on client
                asyncio.create_task(self.create_hash_table()),
            ]

            # waiting for the tasks to be completed
            result = await asyncio.gather(*tasks)
            server_hash_table = result[0] if result[0] else {}

            # waiting for client to be synchronized with server
            await self.sync_data(session, server_hash_table)

            # start watching directories and files for changes
            loop = asyncio.get_event_loop()
            handler = EventHandler(session, loop, self.sync_paths)
            await handler.start()

    async def sync_data(self, session: aiohttp.ClientSession, server_hash_table: Dict) -> None:
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
        logger.debug("Creating hash...")
        for directory in self.sync_paths:
            for root, dirs, files in os.walk(directory):
                for file in files:
                    file_path = os.path.join(root, file)
                    file_hash = await calculate_hash(str(file_path))
                    self.hash_table[file_path] = file_hash

        logger.debug(f"Hash table created!")


def get_offline_event_type(file: str, file_hash: str, server_hash_table: Dict = None) -> int | str:
    # returns old file name if name was changed, otherwise int
    if server_hash_table is None:
        server_hash_table = {}

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
