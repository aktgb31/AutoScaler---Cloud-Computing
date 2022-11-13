import time
import json
import socket
import threading
from _thread import start_new_thread

SERVER_COUNT = 0
SERVER_DETAILS = []
LOAD_GENERATOR_MODE = "LOW"


class SocketServer:
    def __init__(self, host: str, port: int) -> None:
        """Initialize the server"""
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.settimeout(0.5)
        try:
            self.socket.bind((self.host, self.port))
            print("Socket binded to %s" % (port))
            self.socket.listen()
            print("Socket is listening")
        except socket.error as e:
            print("Bind failed."+str(e))
            sys.exit()

    def start(self) -> None:
        """Start the Listener"""
        self.RUNNING = threading.Event()
        self.RUNNING.set()
        self.listener = threading.Thread(
            target=self.__run, args=(self.RUNNING,))
        self.listener.start()

    def __run(self, RUNNING) -> None:
        """Run the server"""
        while RUNNING.is_set():
            # Establish connection with client.
            try:
                conn, addr = self.socket.accept()
                print('Got connection from', addr)
                # Handle the request
                self.__requestHandler(conn)
            except socket.timeout:
                pass

    def __requestHandler(self, c: socket.socket) -> None:
        global SERVER_COUNT
        global SERVER_DETAILS
        """Handle the request from the client"""
        # receive data from the client
        data = c.recv(1024).decode()
        print(data)
        SERVER_COUNT += 1
        SERVER_DETAILS.append(json.loads(data))
        # close the connection
        c.close()

    def stop(self) -> None:
        """Stop the server"""
        self.RUNNING.clear()
        self.listener.join()

    def __del__(self) -> None:
        """Close the socket"""
        self.socket.close()


def loadGenerator(RUN: threading.Event) -> None:
    # Send requests to server in round robin way
    global SERVER_COUNT
    global SERVER_DETAILS
    global LOAD_GENERATOR_MODE

    index = 0

    while RUN.is_set():
        if SERVER_COUNT == 0 or len(SERVER_DETAILS) == 0:
            continue
        s = socket.socket()
        port = 12345
        try:
            serverIp = SERVER_DETAILS[index]["ip"]
            s.connect((serverIp, port))

            payload = "10000" if LOAD_GENERATOR_MODE == "LOW" else "1000000"
            s.sendall(payload.encode())
            data = s.recv(1024).decode()

        except Exception as e:
            print(e)
            return
        s.close()
        time.sleep(0.01)
        # if (index == SERVER_COUNT-1):
        #     time.sleep(1)
        index = (index+1) % SERVER_COUNT


if __name__ == "__main__":
    socketServer = SocketServer("127.0.0.1", 3000)
    socketServer.start()

    RUN = threading.Event()
    RUN.set()
    start_new_thread(loadGenerator, (RUN,))
    try:
        while True:
            i = input("Enter command = LOW/HIGH: ")
            if i == "LOW":
                LOAD_GENERATOR_MODE = "LOW"
            elif i == "HIGH":
                LOAD_GENERATOR_MODE = "HIGH"
            else:
                print("Invalid Command")

    except KeyboardInterrupt:
        print("Stopping server")

    RUN.clear()
    socketServer.stop()
    del socketServer
