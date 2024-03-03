import asyncio

from file_sync_client import FileSyncClient


def main():
    directories = [
        # r"C:\Users\dmkuz\Desktop"
        r"C:\Users\dmkuz\Desktop\ts"
    ]

    client = FileSyncClient(directories, 0)
    try:
        asyncio.run(client.start())
    except KeyboardInterrupt:
        print("Shutting down")


if __name__ == "__main__":
    main()
