import ftplib
import os
import time
import logging
import hashlib
from typing import Optional, Any
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, before_sleep_log

logger = logging.getLogger(__name__)

class FTPConnectionError(Exception):
    """Custom exception to indicate FTP connection errors."""
    pass

class FTP:
    """
    A robust FTP handler class for connecting to an FTP server,
    downloading files with retries, MD5 verification, and context management.
    """

    def __init__(
        self,
        host: str,
        user: Optional[str] = None,
        password: Optional[str] = None,
        retries: int = 5,
    ) -> None:
        """
        Initialize the FTPHandler with server credentials and retry settings.

        :param host: FTP server host.
        :param user: Username for authentication (optional).
        :param password: Password for authentication (optional).
        :param retries: Number of retry attempts for operations.
        """
        self.host: str = host
        self.user: Optional[str] = user
        self.password: Optional[str] = password
        self.retries: int = retries
        self.ftp: Optional[ftplib.FTP] = None

    def _connect(self) -> None:
        """
        Establish an FTP connection and perform login using Tenacity’s retry mechanism.
        This method first checks if an existing connection is active (via a NOOP command).
        If not active or if an error occurs, it attempts to reconnect with retries.
        """
        # Check if there's already an active connection.
        if self.ftp is not None and self.ftp.sock:
            try:
                # Send a NOOP command to validate the connection.
                self.ftp.voidcmd("NOOP")
                return
            except ftplib.all_errors as e:
                logger.warning(f"Existing FTP connection appears stale: {e}. Reconnecting...")
                self._disconnect()

        # Define a callback to be invoked before sleeping between retry attempts.
        def before_sleep(retry_state):
            logger.debug(
                f"Retrying connection: attempt {retry_state.attempt_number}/{self.retries} "
                f"failed due to {retry_state.outcome.exception()}"
            )
            # Disconnect to ensure a fresh connection attempt.
            self._disconnect()

        def do_connect():
            # Create a new FTP connection.
            self.ftp = ftplib.FTP(self.host, timeout=30)
            if self.user and self.password:
                self.ftp.login(self.user, self.password)
            else:
                self.ftp.login()  # Anonymous login
            logger.info("FTP connection established.")

        # Wrap the connection logic with Tenacity’s retry decorator using the dynamic self.retries.
        decorated_connect = retry(
            stop=stop_after_attempt(self.retries),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type(ftplib.all_errors),
            reraise=True,
            before_sleep=before_sleep
        )(do_connect)

        try:
            decorated_connect()
        except ftplib.all_errors as e:
            logger.error(f"Failed to connect to FTP server after {self.retries} attempts: {e}")
            self._disconnect()
            raise FTPConnectionError(f"Unable to connect to FTP server {self.host}") from e

    def _disconnect(self) -> None:
        """
        Close the FTP connection gracefully.
        """
        if self.ftp is not None:
            try:
                self.ftp.quit()
                logger.info("FTP connection closed gracefully.")
            except ftplib.all_errors as e:
                logger.warning(f"Error during FTP disconnect: {e}")
            finally:
                self.ftp = None

    def _verify_md5(self, file_path: str, expected_md5: str) -> bool:
        """
        Verify the MD5 checksum of a downloaded file.

        :param file_path: Local file path.
        :param expected_md5: Expected MD5 hash string.
        :return: True if checksum matches; False otherwise.
        """
        hasher = hashlib.md5()
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)
            computed_md5 = hasher.hexdigest()
            return computed_md5 == expected_md5
        except Exception as e:
            logger.error(f"Failed to compute MD5 for {file_path}: {e}")
            return False

    def download_file(self, remote_path: str, local_path: str, expected_md5: Optional[str] = None) -> None:
        """
        Download a file from the FTP server with retry logic and optional MD5 verification.

        :param remote_path: Path of the file on the FTP server.
        :param local_path: Local path to save the file.
        :param expected_md5: Optional MD5 hash to verify the file integrity.
        :raises FTPConnectionError: If the download fails after all retries.
        """
        if os.path.exists(local_path):
            logger.info(f"Skipping download; local file '{local_path}' already exists.")
            return

        logger.info(f"Starting download of '{remote_path}' to '{local_path}'")

        def do_download():
            self._connect()
            self.ftp.sendcmd("TYPE I")  # Ensure binary mode
            with open(local_path, 'wb') as fp:
                self.ftp.retrbinary(f"RETR {remote_path}", fp.write)
            if expected_md5 and not self._verify_md5(local_path, expected_md5):
                logger.error(f"MD5 checksum mismatch for '{local_path}'.")
                if os.path.exists(local_path):
                    os.remove(local_path)
                raise ValueError("MD5 checksum mismatch")
            logger.info(f"Successfully downloaded '{remote_path}' to '{local_path}'.")

        # Apply the Tenacity retry decorator dynamically using self.retries.
        decorated_download = retry(
            stop=stop_after_attempt(self.retries),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type((ftplib.error_temp, EOFError, ConnectionResetError)),
            reraise=True,
            before_sleep=lambda retry_state: self._disconnect()
        )(do_download)

        try:
            decorated_download()
        except Exception as e:
            logger.error(f"Failed to download '{remote_path}' after {self.retries} attempts: {e}")
            if os.path.exists(local_path):
                try:
                    os.remove(local_path)
                    logger.info(f"Removed incomplete file '{local_path}'.")
                except Exception as cleanup_error:
                    logger.error(f"Failed to remove incomplete file '{local_path}': {cleanup_error}")
            raise FTPConnectionError(f"Failed to download '{remote_path}' after {self.retries} attempts.") from e

    def __getattr__(self, attr: str) -> Any:
        """
        Delegate attribute access to the underlying ftplib.FTP instance with retry logic.
        """
        def do_getattr():
            # Ensure connection before attempting to retrieve attribute.
            self._connect()
            return getattr(self.ftp, attr)

        # Decorate the inner function using self.retries dynamically.
        decorated_getattr = retry(
            stop=stop_after_attempt(self.retries),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type((ftplib.error_temp, EOFError, ConnectionResetError)),
            reraise=True,
            # Before each sleep, disconnect to clean up the state.
            before_sleep=lambda retry_state: self._disconnect()
        )(do_getattr)

        try:
            return decorated_getattr()
        except Exception as e:
            logger.error(f"FTP command '{attr}' failed after {self.retries} attempts: {e}")
            raise FTPConnectionError(f"FTP command '{attr}' failed after {self.retries} attempts.") from e

    def __enter__(self) -> "FTPHandler":
        """
        Enable use of 'with' context for automatic connection management.
        """
        self._connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Ensure the FTP connection is closed when exiting the context.
        """
        self._disconnect()

# Example usage:
if __name__ == "__main__":
    # Replace with actual FTP server details
    FTP_HOST = "ftp.example.com"
    FTP_USER = "username"
    FTP_PASSWORD = "password"
    REMOTE_FILE = "path/to/remote/file.txt"
    LOCAL_FILE = "file.txt"
    EXPECTED_MD5 = "d41d8cd98f00b204e9800998ecf8427e"  # Replace with the actual MD5 hash if needed

    try:
        # Using context management to ensure proper connection cleanup.
        with FTP(FTP_HOST, FTP_USER, FTP_PASSWORD) as ftp_handler:
            ftp_handler.download_file(REMOTE_FILE, LOCAL_FILE, EXPECTED_MD5)
    except Exception as e:
        logger.error(f"An error occurred: {e}")
