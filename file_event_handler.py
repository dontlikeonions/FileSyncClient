import os
from pathlib import Path

import aiohttp
from watchfiles import Change, awatch
import asyncio
from typing import List


from logs.logger import logger
import requests
from async_sha256_file_hash import calculate_hash


class EventHandler:
    def __init__(self, session: aiohttp.ClientSession, loop: asyncio.AbstractEventLoop, sync_paths: List[str | Path]):
        """
        Class for handling file change events and sending them to the server
        Args:
            session (aiohttp.ClientSession): An aiohttp.ClientSession instance for making requests
            loop (asyncio.AbstractEventLoop): The asyncio event loop where the class is running
            sync_paths (List[str | Path]): List of paths to be watched for file changes
        """
        self.session = session
        self.loop = loop
        self.sync_paths = sync_paths

    async def start(self) -> None:
        """
        Asynchronously starts watching the file changes in the specified sync_paths.
        When a change is detected triggers a corresponding request to the server
        """
        async for changes in awatch(*self.sync_paths):
            # unpack events
            file_events: List[List[Change | str]] = []
            for change, path in changes:
                file_events.append([change, path])

            # file was renamed. It creates 2 events: Change.deleted (3) and Change.added (1)
            if len(file_events) > 1:
                # Events can be in any order
                if file_events[0][0] == 3:
                    old_path = file_events[0][1]
                    new_path = file_events[1][1]
                else:
                    old_path = file_events[1][1]
                    new_path = file_events[0][1]

                old_rel_path = get_relative_path(self.sync_paths, old_path)
                new_rel_path = get_relative_path(self.sync_paths, new_path)

                asyncio.run_coroutine_threadsafe(
                    requests.file_name_update(self.session, old_path, old_rel_path, new_path, new_rel_path),
                    loop=self.loop
                )
            else:
                event, file_path = file_events[0]

                # file was created or updated
                if event == 1 or event == 2:
                    rel_path = get_relative_path(self.sync_paths, file_path)
                    asyncio.run_coroutine_threadsafe(
                        self.prepare_hash_update(file_path, rel_path),
                        loop=self.loop
                    )
                # file was deleted
                elif event == 3:
                    # send delete_file request
                    relative_path = get_relative_path(self.sync_paths, file_path)
                    asyncio.run_coroutine_threadsafe(
                        requests.delete_file(self.session, file_path, relative_path),
                        loop=self.loop
                    )
                else:
                    logger.error(f"Unexpected event: {changes}")

    async def prepare_hash_update(self, file_path: str | Path, rel_path: str | Path) -> None:
        """
        Calculates the hash of the file and sends a request

        Args:
            file_path (str | Path): The path of the file
            rel_path (str | Path): The relative path of the file within the watching directory
        """
        file_hash = await calculate_hash(file_path)
        asyncio.run_coroutine_threadsafe(
            requests.file_hash_update(self.session, rel_path, file_path, file_hash),
            loop=self.loop
        )


def get_relative_path(directories: List[str | Path], file_path: str | Path) -> str | None:
    """
    Look for a relative path in given List of directories and return the relative path of the file within the directory
    or None if not found

    Args:
        directories (List[str]): List of directories to look for file
        file_path (str | Path): The path of the file

    Return:
        str | None: The relative path of the file within the directory
    """
    for path in directories:
        path = os.path.dirname(path)
        if file_path.startswith(path):
            return os.path.relpath(file_path, path)

    return None
