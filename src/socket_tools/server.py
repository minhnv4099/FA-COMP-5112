#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import json
import logging
import threading
import socket
import time
import traceback
from typing import Optional
from typing_extensions import Self
from abc import ABC, ABCMeta, abstractmethod

from datetime import datetime
from contextlib import contextmanager, suppress

SERVER_NAME = "File System Socket Server"
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(SERVER_NAME)

SERVER = {
    "name": "Socket Tolls",
    "author": "minhnv14099",
    "version": "0.0.1"
}


class BaseToolServer:
    host: str
    """Host address."""
    port: int
    """Port to listen."""
    name: str
    """Name."""
    running: bool
    """Is running?."""
    _socket: Optional[socket.socket]
    """The socket for server and client to communicate."""
    server_thread: Optional[threading.Thread]
    """The sole thread run server loop."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 9999,
        name: Optional[str] = None,
    ):
        super().__init__()

        self.host = host
        self.port = port
        self.name = name or SERVER_NAME

        self.running = False
        self._socket = None
        self.server_thread = None

    def start(self):
        if self.running:
            logger.info(f"Server {self.name!r} is already running.")
            return None

        self.running = True

        try:
            self._socket = socket.socket(
                family=socket.AF_INET,
                type=socket.SOCK_STREAM
            )
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._socket.bind((self.host, self.port))
            self._socket.listen(1)

            self.server_thread = threading.Thread(
                target=self._server_loop,
                daemon=True,
                name=self.name,
                args=(),
                kwargs={}
            )
            self.server_thread.start()

            logger.info(f"{self.name!r} server stated on '{self.host}:{self.port}'.")
        except Exception as e:
            logger.info(f"Failed to start {self.name!r} server: {str(e)}")

        return None

    def stop(self):
        self.running = False

        # Try close socket
        if self._socket:
            try:
                self._socket.close()
            except:
                pass

            self._socket = None

        if self.server_thread:
            try:
                if self.server_thread.is_alive():
                    self.server_thread.join(timeout=1.0)
            except:
                pass
            self.server_thread = None

        logger.info(f"{self.name!r} server is stopped.")

    def _server_loop(self, *args, **kwargs):
        """Main server loop operating in a separate thread."""
        logger.info("Server thread started.")
        self._socket.settimeout(1.0)

        while self.running:
            try:
                try:
                    client, address = self._socket.accept()
                    logger.info(f"Connect to client: '{address[0]}:{address[1]}'")

                    client_thread: threading.Thread = threading.Thread(
                        target=self._handle_client,
                        daemon=True,
                        args=(client,),
                        kwargs={}
                    )
                    client_thread.start()
                except socket.timeout:
                    logger.debug(f"It seems timeout issues. Try again.")
                    continue
                except Exception as e:
                    logger.error(f"Error accepting connection: {str(e)}")
                    logger.info(f"Pause a bit and try again.")
                    time.sleep(0.5)
            except Exception as e:
                logger.debug(f"Error in server loop: {str(e)}")
                if not self.running:
                    logger.warning(f"By some reasons, the server is stopped, so stop server loop.")
                    break
                time.sleep(0.5)
                logger.info(f"Loop server again.")

        logger.info(f"Server thread stopped.")
        
    def _handle_client(self, client: socket.socket):
        """Handle communication with connected client."""
        logger.info("Started handling client.")
        client.settimeout(None)
        buffer = b''

        try:
            while self.running:
                # Receive data from client
                try:
                    logger.info("Waiting for command from client...")
                    data = client.recv(100)
                    if not data:
                        logger.info("Client disconnected.")
                        break

                    buffer += data
                    try:
                        command = json.loads(buffer.decode(encoding='utf-8'))
                        buffer = b''

                        def execute_wrapper():
                            try:
                                response = self.execute_command(command)
                                response_json = json.dumps(response, indent=None)
                                try:
                                    client.sendall(response_json.encode('utf-8'))
                                except:
                                    logger.info("Failed to send response to client - client disconnected.")
                            except Exception as e:
                                logger.error(f"Error executing command: {str(e)}")
                                traceback.print_exc()
                                try:
                                    error_response = {
                                        "status": "error",
                                        "message": str(e)
                                    }
                                    client.sendall(json.dumps(error_response).encode('utf-8'))
                                except:
                                    pass
                            return None

                        execute_wrapper()
                    except json.JSONDecodeError as e:
                        # Incomplete data, wait for more
                        pass
                except Exception as e:
                    logger.error(f"Error receiving data: {str(e)}")
                    break
        except Exception as e:
            logger.error(f"Error handling client: {str(e)}")
        finally:
            try:
                client.close()
            except:
                pass
            finally:
                logger.info("Stop handling client.")

    def execute_command(self, command: dict):
        """Execute a command."""
        try:
            return self._internal_execute_command(command)

        except Exception as e:
            logger.error(f"Error executing command: {str(e)}")
            traceback.print_exc()
            return {"status": "error", "message": str(e)}

    @abstractmethod
    def _internal_execute_command(self, command: dict) -> dict:
        """Internally execute command with proper context."""
        if command.get("type", "unknown") == "ping":
            return {"status": "success", "result": {"ok": True}}
        message = input("Enter server's message: ")
        return {"status": "success", "result": message}

    def __enter__(self) -> Self:
        self.start()
        return self

    def __exit__(
        self,
        exc_type: BaseException,
        exc_value,
        exc_tb: traceback.TracebackException
    ):
        self.stop()
        if exc_type:
            logger.info(f"Exit by {exc_type.__class__}: {str(exc_value)}")

        return True


@contextmanager
def open_socket_server():
    server = BaseToolServer()
    try:
        yield server
    finally:
        server.stop()


def main():
    with BaseToolServer():
        while True:
            ...


if __name__ == '__main__':
    main()
