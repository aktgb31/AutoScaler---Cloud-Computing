import socket
from threading import Thread


def request(i):
    # Create a socket object
    s = socket.socket()

    # Define the port on which you want to connect
    port = 12345

    try:
        # connect to the server on local computer
        s.connect(('192.168.122.253', port))
        #  send data to the server
        print("Sending data to server", i)
        s.sendall("100".encode())
        # receive data from the server and decoding to get the string.
        print("Recieved data from server", i,
              " Data = ", s.recv(1024).decode())

    except Exception as e:
        print(e)
    # close the connection
    s.close()


if __name__ == "__main__":
    threads = []
    for i in range(10):
        t = Thread(target=request, args=(i,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()
