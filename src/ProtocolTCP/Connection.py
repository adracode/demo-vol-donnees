import os
import socket
from enum import Enum
from math import ceil

# Flag | End | ........
from .utils import path_is_correct, file_is_present

PACKET_SIZE = 1024
HEADER_SIZE = 2
DATA_SIZE = PACKET_SIZE - HEADER_SIZE


class Flag(Enum):
    DATA = 0
    RAW_DATA = 1
    ERROR = 2
    ACK = 3


class Connection:
    def __init__(self, connection=socket.socket(socket.AF_INET, socket.SOCK_STREAM), connected=False):
        self.connection = connection
        self._connected = connected

    def connect_to_server(self, address, port):
        try:
            self.connection.connect((address, port))
            self._connected = True
        except:
            raise ConnectionError(f"Cannot reach '{address}'.")

    def disconnect(self):
        self.connection.close()
        self._connected = False

    def is_connected(self):
        return self._connected

    def send_packet(self, flag, it):
        def send(packet_chunk, end):
            print("send=", b''.join(
                [flag.value.to_bytes(1, 'little'),
                 b'\1' if end else b'\0',
                 packet_chunk.encode() if flag != Flag.RAW_DATA else packet_chunk]), "\n")
            self.connection.send(b''.join(
                [flag.value.to_bytes(1, 'little'),
                 b'\1' if end else b'\0',
                 packet_chunk.encode() if flag != Flag.RAW_DATA else packet_chunk]))

        iterator = iter(it)
        try:
            current = next(iterator)
        except StopIteration as e:
            current = ""
        for chunk in iterator:
            send(current, False)
            current = chunk
        send(current, True)

    def receive_packet(self):
        end = False
        error = ""
        while not end:
            packet = self.connection.recv(PACKET_SIZE)
            print("receive=", packet, "\n")
            flag = Flag(packet[0])
            end = packet[1] == 1
            msg = packet[HEADER_SIZE:]
            if flag == Flag.ERROR:
                error += msg.decode()
            else:
                yield msg.decode() if flag != Flag.RAW_DATA else msg
        if error != "":
            raise ValueError(error)

    def send_msg(self, msg, flag=Flag.DATA):
        def split_msg():
            for i in range(0, len(msg), PACKET_SIZE - HEADER_SIZE):
                yield msg[i:i + DATA_SIZE]

        self.send_packet(flag, split_msg())

    def send_ack(self):
        self.send_msg("Le code c'est la loire", Flag.ACK)

    def send_error(self, error):
        self.send_msg("{0}".format(error), Flag.ERROR)

    def receive_msg(self):
        return "".join(list(self.receive_packet()))

    def send_file(self, path_file):
        def send_file_chunk(file):
            pos = 0
            nb_iteration = ceil(size / DATA_SIZE)
            for i in range(nb_iteration):
                file.seek(pos, 0)
                data = file.read(DATA_SIZE)
                yield data
                pos += DATA_SIZE

        size = os.path.getsize(path_file)
        self.send_msg(f"{path_file};{size}")
        file_to_send = open(path_file, "rb")
        self.send_packet(Flag.RAW_DATA, send_file_chunk(file_to_send))
        file_to_send.close()

    def receive_file(self, file_destination):
        file_to_receive = self.receive_msg()
        file_info = file_to_receive.strip().split(';')
        file_name = file_info[0]
        size = int(file_info[1])
        file = open(f"{file_destination}/{file_name}", "wb")
        for chunk in self.receive_packet():
            file.write(chunk)
        file.close()
