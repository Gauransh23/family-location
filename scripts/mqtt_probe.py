"""Small MQTT 3.1.1 client used to test the family broker."""

from __future__ import annotations

import base64
import os
import socket


def _enc_len(n: int) -> bytes:
    out = bytearray()
    while True:
        digit = n % 128
        n //= 128
        if n:
            digit |= 0x80
        out.append(digit)
        if not n:
            break
    return bytes(out)


def _utf8(value: str) -> bytes:
    raw = value.encode()
    return len(raw).to_bytes(2, "big") + raw


def connect_packet(client_id: str, username: str | None, password: str | None) -> bytes:
    flags = 0x02  # clean session
    payload = _utf8(client_id)
    if username is not None:
        flags |= 0x80
        payload += _utf8(username)
    if password is not None:
        flags |= 0x40
        payload += _utf8(password)
    variable = b"\x00\x04MQTT" + bytes([4, flags, 0, 30]) + payload
    return bytes([0x10]) + _enc_len(len(variable)) + variable


def subscribe_packet(topic: str, packet_id: int = 1) -> bytes:
    variable = packet_id.to_bytes(2, "big") + _utf8(topic) + bytes([1])
    return bytes([0x82]) + _enc_len(len(variable)) + variable


def publish_packet(topic: str, message: str, packet_id: int = 1) -> bytes:
    variable = _utf8(topic) + packet_id.to_bytes(2, "big") + message.encode()
    return bytes([0x32]) + _enc_len(len(variable)) + variable


def _recv_exact(sock: socket.socket, size: int) -> bytes:
    buf = b""
    while len(buf) < size:
        chunk = sock.recv(size - len(buf))
        if not chunk:
            raise ConnectionError("connection closed")
        buf += chunk
    return buf


def read_mqtt_packet(sock: socket.socket) -> tuple[int, bytes]:
    ptype = _recv_exact(sock, 1)[0]
    value = 0
    multiplier = 1
    while True:
        digit = _recv_exact(sock, 1)[0]
        value += (digit & 0x7F) * multiplier
        if digit & 0x80 == 0:
            break
        multiplier *= 128
        if multiplier > 128**3:
            raise ValueError("remaining length too large")
    body = _recv_exact(sock, value) if value else b""
    return ptype, body


def _ws_send(sock: socket.socket, payload: bytes) -> None:
    mask = os.urandom(4)
    header = bytearray([0x82])
    length = len(payload)
    if length < 126:
        header.append(0x80 | length)
    elif length < 65536:
        header.append(0x80 | 126)
        header += length.to_bytes(2, "big")
    else:
        header.append(0x80 | 127)
        header += length.to_bytes(8, "big")
    masked = bytes(byte ^ mask[i % 4] for i, byte in enumerate(payload))
    sock.sendall(bytes(header) + mask + masked)


def _ws_recv(sock: socket.socket) -> bytes:
    chunks = []
    while True:
        header = _recv_exact(sock, 2)
        opcode = header[0] & 0x0F
        length = header[1] & 0x7F
        if length == 126:
            length = int.from_bytes(_recv_exact(sock, 2), "big")
        elif length == 127:
            length = int.from_bytes(_recv_exact(sock, 8), "big")
        if header[1] & 0x80:
            mask = _recv_exact(sock, 4)
            data = bytes(b ^ mask[i % 4] for i, b in enumerate(_recv_exact(sock, length)))
        else:
            data = _recv_exact(sock, length) if length else b""
        if opcode == 0x8:
            raise ConnectionError("websocket closed")
        if opcode == 0x9:
            # ping
            pong = bytearray([0x8A, 0x80])
            mask = os.urandom(4)
            pong += mask
            pong += bytes(b ^ mask[i % 4] for i, b in enumerate(data))
            sock.sendall(pong)
            continue
        chunks.append(data)
        if header[0] & 0x80:
            return b"".join(chunks)


class MqttSession:
    def __init__(self, host: str, port: int, websocket_path: str | None = None) -> None:
        self.sock = socket.create_connection((host, port), timeout=5)
        self.sock.settimeout(5)
        self.websocket = websocket_path is not None
        self._buffer = b""
        if websocket_path is not None:
            key = base64.b64encode(os.urandom(16)).decode()
            request = (
                f"GET {websocket_path} HTTP/1.1\r\n"
                f"Host: {host}:{port}\r\n"
                "Upgrade: websocket\r\n"
                "Connection: Upgrade\r\n"
                f"Sec-WebSocket-Key: {key}\r\n"
                "Sec-WebSocket-Version: 13\r\n"
                "Sec-WebSocket-Protocol: mqtt\r\n"
                "\r\n"
            )
            self.sock.sendall(request.encode())
            raw = b""
            while b"\r\n\r\n" not in raw:
                raw += self.sock.recv(4096)
            status = raw.split(b"\r\n", 1)[0].decode()
            if " 101 " not in status:
                raise ConnectionError(status)

    def send(self, packet: bytes) -> None:
        if self.websocket:
            _ws_send(self.sock, packet)
        else:
            self.sock.sendall(packet)

    def recv(self) -> tuple[int, bytes]:
        if not self.websocket:
            return read_mqtt_packet(self.sock)
        while True:
            if self._buffer:
                try:
                    ptype, body, used = _parse_one(self._buffer)
                except NeedMore:
                    pass
                else:
                    self._buffer = self._buffer[used:]
                    return ptype, body
            self._buffer += _ws_recv(self.sock)

    def close(self) -> None:
        try:
            self.sock.close()
        except OSError:
            pass


class NeedMore(Exception):
    pass


def _parse_one(buf: bytes) -> tuple[int, bytes, int]:
    if not buf:
        raise NeedMore()
    ptype = buf[0]
    value = 0
    multiplier = 1
    index = 1
    while True:
        if index >= len(buf):
            raise NeedMore()
        digit = buf[index]
        index += 1
        value += (digit & 0x7F) * multiplier
        if digit & 0x80 == 0:
            break
        multiplier *= 128
    end = index + value
    if len(buf) < end:
        raise NeedMore()
    return ptype, buf[index:end], end


def decode_publish(ptype: int, body: bytes) -> tuple[str, str]:
    topic_len = int.from_bytes(body[:2], "big")
    topic = body[2 : 2 + topic_len].decode()
    rest = body[2 + topic_len :]
    qos = (ptype & 0x06) >> 1
    if qos:
        rest = rest[2:]
    return topic, rest.decode(errors="replace")
