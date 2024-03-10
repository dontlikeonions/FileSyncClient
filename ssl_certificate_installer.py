import sys
import platform


def install_ssl_certificate(certificate_path: str) -> None:
    os = platform.system()
    match os:
        case 'Windows':
            install_ssl_certificate_win(certificate_path)
        case 'Linux':
            install_ssl_certificate_linux(certificate_path)
        case default:
            print("Unknown operating system")
            sys.exit()


def install_ssl_certificate_linux(certificate_path: str) -> None:
    """
    Install an SSL certificate to the root store on Linux.

    Args:
        certificate_path (str): Path to the SSL certificate file.

    This function reads the contents of the certificate file and installs it to the
    root certificate store on a Linux system.

    Note:
        This function assumes the use of the `update-ca-certificates` command, which is
        commonly available on Debian-based distributions. This may need adjustments
        for other Linux distributions.

    Example:
        install_ssl_certificate_linux('/path/to/certificate.crt')
    """
    import shutil
    import subprocess

    # copy the certificate to the appropriate directory
    cert_fir = '/usr/local/share/ca-certificates/'
    shutil.copy(certificate_path, cert_fir)

    # update the CA certificates store
    subprocess.run(['update-ca-certificates'], check=True)


def install_ssl_certificate_win(certificate_path) -> None:
    """
    Install an SSL certificate to the root store on Windows.

    Args:
        certificate_path (str): Path to the SSL certificate file.

    This function reads the contents of the certificate file, decodes it, and installs
    it to the root certificate store on a Windows system.

    Note:
        This function is specific to Windows and relies on the `win32crypt` library.

    Example:
        install_ssl_certificate('path/to/certificate.crt')
    """
    import win32crypt
    import win32cryptcon

    with open(certificate_path, 'r') as cert_file:
        cert_str = cert_file.read()

    # decoding certificate
    cert_byte = win32crypt.CryptStringToBinary(cert_str, win32cryptcon.CRYPT_STRING_BASE64HEADER)[0]

    # opening root store
    store = win32crypt.CertOpenStore(
        win32cryptcon.CERT_STORE_PROV_SYSTEM,
        0,
        None,
        win32cryptcon.CERT_SYSTEM_STORE_LOCAL_MACHINE,
        "ROOT"
    )

    try:
        # installing certificate
        store.CertAddEncodedCertificateToStore(
            win32cryptcon.X509_ASN_ENCODING,
            cert_byte,
            win32cryptcon.CERT_STORE_ADD_REPLACE_EXISTING)
    finally:
        # closing opened store
        store.CertCloseStore(win32cryptcon.CERT_CLOSE_STORE_FORCE_FLAG)
