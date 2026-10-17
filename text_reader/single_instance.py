import socket
import threading

PORT = 51423


class SingleInstance:
    def __init__(self, port=PORT):
        self.port = port
        self._sock = None
        self._listen_thread = None

    def try_acquire(self):
        """Binds the guard port. Returns True if this process is the primary
        instance. Deliberately does NOT set SO_REUSEADDR: on Windows that
        would let a second process bind the same port while the first is
        still listening, defeating the exclusivity check."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(("127.0.0.1", self.port))
        except OSError:
            sock.close()
            return False
        sock.listen(5)
        self._sock = sock
        return True

    def notify_primary(self):
        try:
            with socket.create_connection(("127.0.0.1", self.port), timeout=1) as s:
                s.sendall(b"show")
        except OSError:
            pass

    def start_listening(self, on_signal):
        def accept_loop():
            while True:
                try:
                    conn, _ = self._sock.accept()
                except OSError:
                    return
                try:
                    conn.close()
                except OSError:
                    pass
                on_signal()

        self._listen_thread = threading.Thread(target=accept_loop, daemon=True)
        self._listen_thread.start()

    def close(self):
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None
