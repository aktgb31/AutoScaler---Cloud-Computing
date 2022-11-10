import socket
import sys
from _thread import start_new_thread
import threading


def countTillX(x: int) -> str:
    """Count till x and return the string of the count"""
    count = 0
    while count < x:
        count += 1
    return str(count)


def requestHandler(c: socket.socket) -> None:
    # Print Thread Count
    """Handle the request from the client"""
    # receive data from the client
    data = c.recv(1024).decode()
    # send the count to the client
    c.sendall(countTillX(int(data)).encode())
    # close the connection
    c.close()
    pass


class Server:
    def __init__(self, host: str, port: int) -> None:
        """Initialize the server"""
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:

            self.socket.bind((self.host, self.port))
            print("Socket binded to %s" % (port))
            self.socket.listen(5)
            print("Socket is listening")
        except socket.error as e:
            print("Bind failed."+str(e))
            sys.exit()

    def run(self) -> None:
        """Run the server"""
        while True:
            # Establish connection with client.
            conn, addr = self.socket.accept()
            print('Got connection from', addr)
            # Start a new thread to handle the request
            # start_new_thread(requestHandler, (conn,))
            requestHandler(conn)

    def __del__(self) -> None:
        """Close the socket"""
        self.socket.close()


if __name__ == "__main__":
    server = Server("", 12345)
    server.run()
