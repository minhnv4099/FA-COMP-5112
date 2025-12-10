#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import logging
import os
import socket
import json
from typing import Optional, Dict, Any
from contextlib import contextmanager
from dataclasses import dataclass, field


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('BaseSocketClient')

DEFAULT_HOST = "localhost"
DEFAULT_PORT = 9999
ENCODING = "utf-8"


@dataclass
class BaseSocketConnection:
    host: str
    port: int
    sock: Optional[socket.socket] = None
    
    def connect(self) -> bool:
        """Connect to the server."""
        if self.sock:
            return True
        
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            logger.info(f"Connected to server at: '{self.host}:{self.port}'.")
            return True
        except Exception as e:
            logger.error(f"Failed to connect server: {str(e)}")
            self.sock = None
            return False
    
    def disconnect(self):
        if self.sock:
            try:
                self.sock.close()
            except Exception as e:
                logger.error(f"Error disconnecting from server: {str(e)}")
            finally:
                self.sock = None
                
    def receive_full_response(self, sock: socket.socket, buffer_size=8192):
        """Receive the complete response, potentially in multiple chunks.
        
        Returns:
            Raw data from server (bytes).
        """
        chunks = []
        
        sock.settimeout(180.0)
        
        try:
            while True:
                try:
                    chunk = sock.recv(buffer_size)
                    
                    if not chunk:
                        # Check if we get any chunks before
                        if not chunks:
                            raise Exception("Connection closed before receiving any data.")
                        break
                    
                    chunks.append(chunk)
                    
                    try:
                        data = b''.join(chunks)
                        json.loads(data.decode(ENCODING))
                        logger.info(f"Received complete response (parsable) ({len(data)} bytes).")
                        return data
                    except json.JSONDecodeError:
                        # Incomplete JSON, continue receiving
                        continue  
                except socket.timeout:
                    logger.warning("Socket timeout during receiving chunk.")
                    break
                except (ConnectionError, BrokenPipeError, ConnectionResetError) as e:
                    logger.error(f"Socket connection error during receive: {str(e)}")
                    raise 
        except socket.timeout:
            logger.warning(f"Socket timeout during chunked receive.")
        except Exception as e:
            logger.error(f"Error during receiving: {str(e)}")
            raise 
        
        if chunks:
            data = b''.join(chunks)
            logger.info(f"Returning data after receive completion ({len(data)} bytes).")
            try:
                json.loads(data.decode(ENCODING))
                return data
            except json.JSONDecodeError:
                raise Exception("Incomplete JSON response received.")
        else:
            raise Exception("No any received data.")
        
    def send_command(self, command_type: str, params: dict[str, Any] = None) -> Dict[str, Any]:
        if not self.sock and not self.connect():
            raise ConnectionError("Not connected to server.")
        
        command = {
            "type": command_type,
            "params": params or {}
        }
        
        try:
            logger.info(f"""Sending command:
Type: {command_type!r}
Params: {json.dumps(params, indent=2)}.""")
            
            # Send command to server
            self.sock.sendall(json.dumps(command).encode(ENCODING))
            logger.info("Sent command, blocking to wait response ...")
            
            # logger.info("Set socket timeout: 180.0s")
            self.sock.settimeout(180.0)
            
            response_data = self.receive_full_response(self.sock)
            logger.info(f"[!!!] Received {len(response_data)} bytes of data.")
            
            response: Dict[str, Any] = json.loads(response_data.decode(ENCODING))
            logger.info(f"Parsed response, status: {response.get('status', 'unknown')!r}.")

            if response.get('status') == 'error':
                logger.error(f"Error: {response.get('message')}")
                raise Exception(response.get("message", "Unknown error from server."))

            return response.get("result", {})
        except socket.timeout:
            logger.error("Socket timeout while waiting for response from server.")
            # can reconnect to server here
            # but let use method to handle this
            self.sock = None
            raise Exception(f"Timeout exception - try simplifying your request.")
        except (ConnectionError, BrokenPipeError, ConnectionResetError) as e:
            logger.error(f"Socket connection error: {str(e)}")
            self.sock = None
            raise Exception(f"Lost connection to server: {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response from server: {str(e)}")
            if 'response_data' in locals():
                response_data = locals()['response_data']
                if response_data:
                    logger.error(f"Raw reponse (first 200 bytes): {response_data[:200]}")
                else:
                    logger.error("Empty response.")
            else:
                logger.error("Failed receive any data from server")
            raise Exception(f"Invalid JSON response from server: {str(e)}")
        except Exception as e:
            logger.error(f"Error communicating with server: {str(e)}")
            self.sock = None
            raise Exception(f"Error communicating with server: {str(e)}")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

        if exc_type:
            return True
        return True


_connection: Optional[BaseSocketConnection] = None
_ping_response: bool = False


def get_connection() -> BaseSocketConnection:
    """Get the valid connection or create a new persistent one.

    Raises:
        Exception: If not get the valid connection.
    """
    global _connection, _ping_response
    # connection is existing, try pinging to check communication
    if _connection is not None:
        try:
            result = _connection.send_command('ping')
            _ping_response = result.get("ok", False)
            return _connection
        except Exception as e:
            logger.warning(f"Existing connect is no longer valid, because cannot ping: {str(e)}")
            logger.info("Disconnect.")
            _connection.disconnect()
            _connection = None

    if _connection is None:
        host = os.getenv("SERVER_HOST", DEFAULT_HOST)
        port = int(os.getenv("SERVER_PORT", DEFAULT_PORT))
        _connection = BaseSocketConnection(host=host, port=port)

        if not _connection.connect():
            logger.error("Failed to connect to server.")
            _connection = None
            raise Exception("Could not connect to server. Make sure the server is running.")
        logger.info("Create a new persistent connection to server.")
        result = _connection.send_command('ping', {'name': 'minh'})
        _ping_response = result.get("ok", False)

    return _connection


@contextmanager
def open_communication_session():
    global _connection
    try:
        try:
            get_connection()
            logger.info(f"Successfully connected to server.")
        except Exception as e:
            logger.warning(f"Could not connect to server.")
            logger.warning(f"Make sure the server is running before connecting.")

        yield _connection
    finally:
        if _connection:
            _connection.disconnect()
        _connection = None


def main():
    global _ping_response
    with open_communication_session() as conn:
        print(_ping_response)


if __name__ == '__main__':
    main()
