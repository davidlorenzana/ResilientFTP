# ResilientFTP

ResilientFTP is a robust Python library for handling FTP connections with automatic retry and reconnection logic. Built on top of Python's built-in `ftplib` and the powerful [Tenacity](https://tenacity.readthedocs.io/) retry library, ResilientFTP makes it easy to build resilient FTP clients that recover gracefully from transient errors and connection drops.

## Features

- **Automatic Reconnection:**
  Checks the active connection using FTP’s NOOP command and reconnects if the connection is stale.

- **Retry Logic with Exponential Backoff:**
  Uses Tenacity to automatically retry FTP operations with customizable retry counts and backoff intervals.

- **Robust Error Handling:**
  Raises clear, domain-specific exceptions (e.g., `FTPConnectionError`) for easier debugging and maintenance.

- **Context Manager Support:**
  Use the FTP handler with Python’s `with` statement for automatic connection setup and cleanup.

- **Customizable Behavior:**
  Configure the number of retries, wait strategy, and logging to suit your production needs.

## Installation

You can install ResilientFTP via pip (if published on PyPI):

```bash
pip install resilientftp
```

Alternatively, clone the repository and install locally:

```bash
git clone https://github.com/davidlorenzana/ResilientFTP.git
cd resilientftp
pip install .
```

## Usage

Below are some examples of how to use ResilientFTP.

### Basic Example

```python
from resilientftp import FTP, FTPConnectionError

# Initialize the FTP handler with your server credentials and retry settings.
ftp = FTP("ftp.example.com", user="username", password="password", retries=5)

try:
    ftp.download_file("remote/path/file.txt", "local/path/file.txt")
    print("File downloaded successfully!")
except FTPConnectionError as e:
    print(f"FTP connection error: {e}")
```

### Using Context Management

```python
from resilientftp import FTP

# Using the context manager ensures proper connection cleanup.
with FTP("ftp.example.com", user="username", password="password", retries=5) as ftp:
    ftp.download_file("remote/path/file.txt", "local/path/file.txt")
```

### Delegated FTP Commands

ResilientFTP supports delegating other FTP commands via `__getattr__`. For example:

```python
# Access underlying FTP methods with automatic retry handling.
with FTP("ftp.example.com", user="username", password="password") as ftp:
    # For example, list files in a directory:
    files = ftp.nlst()
    print(files)
```

## API Overview

### `FTP(host: str, user: Optional[str] = None, password: Optional[str] = None, retries: int = 5)`

Initializes the FTP handler with the target FTP server, credentials, and the maximum number of retry attempts.

### `download_file(remote_path: str, local_path: str, expected_md5: Optional[str] = None) -> None`

Downloads a file from the FTP server to the specified local path. If an `expected_md5` is provided, the file is verified for integrity. Retries are automatically performed on transient errors.

### `__getattr__(attr: str) -> Any`

Delegates attribute access to the underlying FTP connection, applying the same retry logic for transient errors.

### Context Manager Methods

- `__enter__()` – Establishes the FTP connection.
- `__exit__(exc_type, exc_val, exc_tb)` – Ensures the FTP connection is gracefully closed.

## Contributing

Contributions are welcome! Feel free to fork the repository, open issues, or submit pull requests. Please ensure your code adheres to [PEP 8](https://www.python.org/dev/peps/pep-0008/) standards and includes appropriate tests.

## License

ResilientFTP is released under the MIT License. See the [LICENSE](LICENSE) file for details.

## Acknowledgements

- Built on Python’s built-in `ftplib`.
- Uses [Tenacity](https://tenacity.readthedocs.io/) for robust retry handling.
