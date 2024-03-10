import asyncio
import configparser

from file_sync_client import FileSyncClient
from ssl_certificate_installer import install_ssl_certificate

config = configparser.ConfigParser()
config.read('settings.ini')

cert_path = config.get('Paths', 'cert_path')


def main():
    directories = [
        r"C:\Users\dmkuz\Desktop\gn19",
        r"C:\Users\dmkuz\Desktop\ts",
    ]

    install_ssl_certificate(cert_path)
    client = FileSyncClient(directories, 0)
    try:
        asyncio.run(client.start())
    except KeyboardInterrupt:
        print("Shutting down")


if __name__ == "__main__":
    main()
