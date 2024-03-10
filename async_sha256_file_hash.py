import hashlib
from pathlib import Path

import aiofiles
from logs.logger import logger


async def calculate_hash(file_path: str | Path, chunk_size: int = 1024) -> str:
    """
    Asynchronously calculate the SHA256 hash of a file

    Returns:
        str: A hexadecimal string representing the SHA256 hash digest of the file
    """
    sha256 = hashlib.sha256()
    try:
        async with aiofiles.open(file_path, 'rb') as f:
            while chunk := await f.read(chunk_size):
                sha256.update(chunk)
        return sha256.hexdigest()
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        return ""
