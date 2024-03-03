import hashlib
import aiofiles
from logs.logger import logger


chunk_size = 1024


async def calculate_hash(file_path: str) -> str:
    sha256 = hashlib.sha256()
    try:
        async with aiofiles.open(file_path, 'rb') as f:
            while chunk := await f.read(chunk_size):
                sha256.update(chunk)
        return sha256.hexdigest()
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        return ""
