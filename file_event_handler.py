import os

import aiohttp
from watchfiles import Change, awatch
import asyncio
from typing import List


from logs.logger import logger
import requests
from async_sha256_file_hash import calculate_hash


class EventHandler:
    def __init__(self, session: aiohttp.ClientSession, loop: asyncio.AbstractEventLoop, sync_paths: List[str]):
        self.session = session
        self.loop = loop
        self.sync_paths = sync_paths

    async def start(self):
        async for changes in awatch(*self.sync_paths):
            # unpack events
            file_events: List[List[Change | str]] = []
            for change, path in changes:
                file_events.append([change, path])

            # File was renamed. It creates 2 events: Change.deleted (3) and Change.added (1)
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

                await requests.file_name_update(self.session, old_path, old_rel_path, new_path, new_rel_path)
                # asyncio.run_coroutine_threadsafe(
                #     requests.file_name_update(self.session, old_name, new_name),
                #     loop=self.loop
                # )

            event, file_path = file_events[0]

            # file was created or updated
            if event == 1 or event == 2:
                rel_path = get_relative_path(self.sync_paths, file_path)

                file_hash = await calculate_hash(file_path)
                await requests.file_hash_update(self.session, rel_path, file_path, file_hash)
                # asyncio.run_coroutine_threadsafe(
                #     requests.file_hash_update(self.session, rel_path, file_path, file_hash),
                #     loop=self.loop
                # )
            # file was deleted
            elif event == 3:
                # send delete_file request
                relative_path = get_relative_path(self.sync_paths, file_path)
                await requests.delete_file(self.session, file_path, relative_path)
                # asyncio.run_coroutine_threadsafe(
                #     requests.delete_file(self.session, file_path, relative_path),
                #     loop=self.loop
                # )
            else:
                logger.error(f"Unexpected event: {changes}")


def get_relative_path(directories: List[str], file_path: str) -> str | None:
    # return path form watching directory to the file or None
    for path in directories:
        path = os.path.dirname(path)
        if file_path.startswith(path):
            return os.path.relpath(file_path, path)

    return None
