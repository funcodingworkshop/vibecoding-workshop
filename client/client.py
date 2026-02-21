import socket
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox
from datetime import datetime


HOST = "127.0.0.1"
PORT = 5555


class ChatClient:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Real-time Chat Client")
        self.root.resizable(False, False)

        self.client_socket: socket.socket | None = None
        self.connected = False

        self._build_ui()

    # ──────────────────────────────────────────────
    # UI construction
    # ──────────────────────────────────────────────
    def _build_ui(self):
        # ── Top bar: Name + Connect ──
        top_frame = tk.Frame(self.root, padx=10, pady=6)
        top_frame.pack(fill=tk.X)

        tk.Label(top_frame, text="Name:", font=("Arial", 10, "bold")).pack(side=tk.LEFT)
        self.name_entry = tk.Entry(top_frame, width=18, font=("Arial", 10))
        self.name_entry.insert(0, "Guest")
        self.name_entry.pack(side=tk.LEFT, padx=(4, 12))

        tk.Label(top_frame, text="Host:", font=("Arial", 10)).pack(side=tk.LEFT)
        self.host_entry = tk.Entry(top_frame, width=13, font=("Arial", 10))
        self.host_entry.insert(0, HOST)
        self.host_entry.pack(side=tk.LEFT, padx=(4, 4))

        tk.Label(top_frame, text="Port:", font=("Arial", 10)).pack(side=tk.LEFT)
        self.port_entry = tk.Entry(top_frame, width=6, font=("Arial", 10))
        self.port_entry.insert(0, str(PORT))
        self.port_entry.pack(side=tk.LEFT, padx=(4, 12))

        self.connect_btn = tk.Button(
            top_frame, text="Connect", width=9,
            bg="#4CAF50", fg="white", font=("Arial", 10, "bold"),
            command=self._toggle_connection
        )
        self.connect_btn.pack(side=tk.LEFT)

        # ── Chat display ──
        self.chat_area = scrolledtext.ScrolledText(
            self.root, state=tk.DISABLED,
            width=70, height=22,
            font=("Consolas", 10),
            bg="#1e1e2e", fg="#cdd6f4",
            insertbackground="white",
            padx=6, pady=6
        )
        self.chat_area.pack(padx=10, pady=(0, 4))

        # ── Input row ──
        input_frame = tk.Frame(self.root, padx=10, pady=6)
        input_frame.pack(fill=tk.X)

        self.msg_entry = tk.Entry(
            input_frame, font=("Arial", 11),
            state=tk.DISABLED
        )
        self.msg_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        self.msg_entry.bind("<Return>", lambda _e: self._send_message())

        self.send_btn = tk.Button(
            input_frame, text="Send", width=8,
            bg="#89b4fa", fg="#1e1e2e", font=("Arial", 10, "bold"),
            state=tk.DISABLED,
            command=self._send_message
        )
        self.send_btn.pack(side=tk.LEFT)

        # ── Status bar ──
        self.status_var = tk.StringVar(value="Disconnected")
        tk.Label(
            self.root, textvariable=self.status_var,
            font=("Arial", 9), fg="gray", anchor=tk.W
        ).pack(fill=tk.X, padx=10, pady=(0, 6))

        # Safe exit
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ──────────────────────────────────────────────
    # Connection management
    # ──────────────────────────────────────────────
    def _toggle_connection(self):
        if self.connected:
            self._disconnect()
        else:
            self._connect()

    def _connect(self):
        host = self.host_entry.get().strip()
        try:
            port = int(self.port_entry.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Port must be an integer.")
            return

        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((host, port))
        except OSError as e:
            messagebox.showerror("Connection Failed", str(e))
            self.client_socket = None
            return

        self.connected = True
        self._set_ui_connected(True)
        self._log_system(f"Connected to {host}:{port}")

        # Background receiver thread (daemon → dies with main thread)
        recv_thread = threading.Thread(target=self._receive_loop, daemon=True)
        recv_thread.start()

    def _disconnect(self, notify_server=True):
        self.connected = False
        if self.client_socket:
            try:
                self.client_socket.shutdown(socket.SHUT_RDWR)
                self.client_socket.close()
            except OSError:
                pass
            self.client_socket = None
        self._set_ui_connected(False)
        self._log_system("Disconnected.")

    def _set_ui_connected(self, connected: bool):
        state = tk.NORMAL if connected else tk.DISABLED
        self.msg_entry.config(state=state)
        self.send_btn.config(state=state)
        self.connect_btn.config(
            text="Disconnect" if connected else "Connect",
            bg="#f38ba8" if connected else "#4CAF50"
        )
        self.status_var.set("Connected ✓" if connected else "Disconnected")
        if connected:
            self.msg_entry.focus_set()

    # ──────────────────────────────────────────────
    # Messaging
    # ──────────────────────────────────────────────
    def _send_message(self):
        if not self.connected or not self.client_socket:
            return

        text = self.msg_entry.get().strip()
        if not text:
            return

        name = self.name_entry.get().strip() or "Guest"
        timestamp = datetime.now().strftime("%H:%M:%S")
        message = f"[{timestamp}] {name}: {text}"

        try:
            self.client_socket.sendall(message.encode("utf-8"))
            self.msg_entry.delete(0, tk.END)
        except OSError as e:
            self._log_system(f"Send error: {e}")
            self._disconnect()

    def _receive_loop(self):
        """Runs in a background thread. Pushes received data to the UI thread."""
        while self.connected:
            try:
                data = self.client_socket.recv(4096)
                if not data:
                    # Server closed the connection
                    self.root.after(0, lambda: self._log_system("Server closed the connection."))
                    self.root.after(0, self._disconnect)
                    break
                message = data.decode("utf-8")
                self.root.after(0, self._append_message, message)
            except OSError:
                if self.connected:
                    self.root.after(0, lambda: self._log_system("Connection lost."))
                    self.root.after(0, self._disconnect)
                break

    # ──────────────────────────────────────────────
    # Chat display helpers
    # ──────────────────────────────────────────────
    def _append_message(self, message: str):
        self.chat_area.config(state=tk.NORMAL)
        self.chat_area.insert(tk.END, message + "\n")
        self.chat_area.see(tk.END)
        self.chat_area.config(state=tk.DISABLED)

    def _log_system(self, text: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self._append_message(f"--- [{ts}] {text} ---")

    # ──────────────────────────────────────────────
    # Cleanup
    # ──────────────────────────────────────────────
    def _on_close(self):
        self._disconnect()
        self.root.destroy()


# ──────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    app = ChatClient(root)
    root.mainloop()