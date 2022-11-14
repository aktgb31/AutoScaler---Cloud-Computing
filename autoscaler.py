import libvirt
import socket
import json
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import time
from _thread import start_new_thread
import datetime

plt.style.use('fivethirtyeight')


class Graph:
    def __init__(self) -> None:
        self.x1 = []
        self.y1 = []
        self.x2 = []
        self.y2 = []
        self.limit = 60
        self.inc = 1
        self.linewidth = 2
        self.buffer = []

    def add(self, cpu_usage):
        self.buffer.append(cpu_usage)

    def run(self):

        def plot(i):
            if self.buffer:
                self.plot(self.buffer.pop(0))

        ani = FuncAnimation(plt.gcf(), plot, interval=500)
        plt.tight_layout()
        plt.show()

    def plot(self, cpu_usage):
        plt.cla()

        plt.plot(self.x1, self.y1, linewidth=2, label='Machine 1')
        plt.plot(self.x2, self.y2, linewidth=2, label='Machine 2')
        plt.legend(loc='upper left')
        plt.ylim(0, 100)
        plt.xlim(0, 60, 5)
        plt.xlabel("Time")
        plt.ylabel("CPU Usage")
        plt.gca().invert_xaxis()
        plt.tight_layout()

        for i in range(len(self.x1)):
            self.x1[i] += self.inc
        for i in range(len(self.x2)):
            self.x2[i] += self.inc
        if (len(cpu_usage) == 2):
            self.y2.append(cpu_usage[1])
            self.x2.append(0)
        if (len(self.x1) == self.limit):
            self.x1 = self.x1[1:]
            self.y1 = self.y1[1:]
        if (len(self.x2) == self.limit):
            self.x2 = self.x2[1:]
            self.y2 = self.y2[1:]

        self.y1.append(cpu_usage[0])
        self.x1.append(0)


class ClientSocketClient:
    def __init__(self, clientHost: str, clientPort: int) -> None:
        """Initialize the server"""
        self.clientHost = clientHost
        self.clientPort = clientPort

    def sendServerInformation(self, serverInformation: dict) -> None:
        """Send the server information to the client"""
        s = socket.socket()
        try:
            s.connect((self.clientHost, self.clientPort))
            print("Socket connected to %s" % (self.clientPort))
            s.send(json.dumps(serverInformation).encode())

        except socket.error as e:
            print(str(e))


def getDomainIpAddress(dom: libvirt.virDomain) -> str:
    """Get the IP address of the domain"""
    return str(list(dom.interfaceAddresses(
        libvirt.VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_LEASE, 0).values())[0]['addrs'][0]['addr'])


def getCPUUsage(doms: list[libvirt.virDomain], sleepTime) -> float:
    """Get the CPU usage of the domain"""
    cpu_time1 = []
    cpu_time2 = []
    for dom in doms:
        cpu_stats = dom.getCPUStats(total=True)
        cpu_time1.append(cpu_stats[0]['cpu_time'])
    time.sleep(sleepTime)
    for dom in doms:
        cpu_stats = dom.getCPUStats(total=True)
        cpu_time2.append(cpu_stats[0]['cpu_time'])

    cpu_usage = []
    for i in range(len(cpu_time1)):
        cpu_usage.append(
            100 * (cpu_time2[i] - cpu_time1[i])/1000000000/sleepTime)
    return cpu_usage


def AutoScaler(serverNamePrefix: str, serverCount: int, serverBaseImage: str, scaleUpThreshold: float, scaleUpObservationPeriod: float, sendServerInfoToClient,):
    """Initialize the AutoScaler"""
    conn = libvirt.open("qemu:///system")
    if not conn:
        print('Failed to open connection to qemu:///system')
        raise RuntimeError("Failed to open connection to qemu:///system")

    activeServers = []
    for i in range(1, serverCount + 1):
        serverName = serverNamePrefix + str(i)
        dom = conn.lookupByName(serverName)
        if not dom.isActive():
            dom.create()
        activeServers.append(dom)

    for server in activeServers:
        sendServerInfoToClient(
            {"name": dom.name(), "ip": getDomainIpAddress(dom)})

    graphPlotter = Graph()

    average_cpu_usage = [0.0 for i in range(scaleUpObservationPeriod)]
    waitBeforeNewCreate = 0

    start_new_thread(graphPlotter.run, ())

    while True:
        cpu_usage = getCPUUsage(activeServers, 0.5)
        print(
            f'Current Time: {datetime.datetime.now()} Cpu_usage : {cpu_usage}')
        graphPlotter.add(cpu_usage)
        average_cpu_usage.append(sum(cpu_usage)/len(cpu_usage))
        average_cpu_usage.pop(0)
        runningAverage = sum(average_cpu_usage)/len(average_cpu_usage)

        waitBeforeNewCreate = waitBeforeNewCreate - 1 if waitBeforeNewCreate > 0 else 0

        if runningAverage > scaleUpThreshold and waitBeforeNewCreate == 0:
            try:
                serverName = serverNamePrefix + str(serverCount + 1)
                print("Creating new server: ", serverName)
                newDom = conn.lookupByName(serverName)
                if not newDom.isActive():
                    newDom.create()
                activeServers.append(newDom)
                serverCount += 1
                sendServerInfoToClient(
                    {"name": newDom.name(), "ip": getDomainIpAddress(newDom)})
                waitBeforeNewCreate = 20
            except Exception as e:
                print(str(e))

    conn.close()


if __name__ == "__main__":
    config = {}
    try:
        with open("config.json") as config_file:
            config = json.load(config_file)
    except FileNotFoundError:
        print("Config file not found.")
        exit(1)

    clientConn = ClientSocketClient(
        config["clientAddress"], config["clientPort"])

    try:
        AutoScaler(config["serverNamePrefix"], config["serverCount"],
                   config["serverBaseImage"], config["scaleUpThreshold"],
                   config["scaleUpObservationPeriod"], clientConn.sendServerInformation)
    except RuntimeError as err:
        print("Runtime Error"+str(err))
        exit(1)
    except KeyboardInterrupt:
        print("Exiting...")
        exit(0)
