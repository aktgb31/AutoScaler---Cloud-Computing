import libvirt
import socket
import json
import matplotlib.pyplot as plt
import time


class Graph:
    def __init__(self, title: str, xlabel: str, ylabel: str, maxX: int):
        self.title = title
        self.xlabel = xlabel
        self.ylabel = ylabel
        self.maxX = maxX
        self.legend = []

        # self.x = []
        # self.y = []
        # self.colors = ['r', 'g', 'b', 'y', 'c', 'm', 'k']
        # self.plt = plt.plot()

        # self.plt.show()

    def add(self, y: list):
        # self.y.append(y)
        # if (len(y) > self.maxX):
        #     y.pop(0)
        pass


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


def __getDomainIpAddress(dom: libvirt.virDomain) -> str:
    """Get the IP address of the domain"""
    return str(list(dom.interfaceAddresses(
        libvirt.VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_LEASE, 0).values())[0]['addrs'][0]['addr'])


def __getCPUUsage(doms: list[libvirt.virDomain], sleepTime) -> float:
    """Get the CPU usage of the domain"""
    cpu_time1 = []
    cpu_time2 = []
    for dom in doms:
        # print(dom.getCPUStats(total=True))
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
            {"name": dom.name(), "ip": __getDomainIpAddress(dom)})

    graph = Graph("Server Load", "Time", "CPU Usage", 20)

    average_cpu_usage = [0.0 for i in range(scaleUpObservationPeriod)]
    waitBeforeNewCreate = 0

    while True:
        cpu_usage = __getCPUUsage(activeServers, 1)
        graph.add(cpu_usage)
        average_cpu_usage.append(sum(cpu_usage)/len(cpu_usage))
        average_cpu_usage.pop(0)
        runningAverage = sum(average_cpu_usage)/len(average_cpu_usage)

        print("Average CPU Usage: ", average_cpu_usage)
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
                    {"name": newDom.name(), "ip": __getDomainIpAddress(newDom)})
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
    except KeyboardInterrupt:
        print("Exiting...")
