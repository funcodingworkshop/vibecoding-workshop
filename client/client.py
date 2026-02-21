import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox
from datetime import datetime
import urllib.request
import urllib.error
import json
import time


SERVER_URL = "https://vibecoding-workshop-production.up.railway.app"
POLL_INTERVAL = 2  # seconds between inbox polls


def http(method: str, path: str, body: dict | None = None) -> dict:
    url = SERVER_URL + path
    data = json.dumps(body).encode("utf-8") if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


class ChatClient:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Real-time Chat Client")
        self.root.resizable(False, False)

        self.connected = False
        self._poll_thread: threading.Thread | None = None

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

        tk.Label(top_frame, text="To:", font=("Arial", 10, "bold")).pack(side=tk.LEFT)
        self.to_entry = tk.Entry(top_frame, width=18, font=("Arial", 10))
        self.to_entry.pack(side=tk.LEFT, padx=(4, 12))

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
        user_id = self.name_entry.get().strip() or "Guest"
        try:
            result = http("POST", f"/signin/{user_id}")
            self._log_system(result.get("message", "Signed in"))
        except Exception as e:
            messagebox.showerror("Connection Failed", str(e))
            return

        self.connected = True
        self._set_ui_connected(True)

        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()

    def _disconnect(self):
        self.connected = False
        user_id = self.name_entry.get().strip() or "Guest"
        try:
            result = http("POST", f"/signout/{user_id}")
            self._log_system(result.get("message", "Signed out"))
        except Exception as e:
            self._log_system(f"Sign out error: {e}")
        self._set_ui_connected(False)

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
        if not self.connected:
            return

        text = self.msg_entry.get().strip()
        if not text:
            return

        sender_id = self.name_entry.get().strip() or "Guest"
        receiver_id = self.to_entry.get().strip()
        if not receiver_id:
            messagebox.showwarning("Missing recipient", "Please enter a name in the 'To:' field.")
            return

        timestamp = datetime.now().isoformat()

        def do_send():
            try:
                result = http("POST", f"/message/{sender_id}", {
                    "receiver_id": receiver_id,
                    "message_text": text,
                    "current_timestamp": timestamp,
                })
                self.root.after(0, self._log_system, result.get("message", ""))
            except Exception as e:
                self.root.after(0, self._log_system, f"Send error: {e}")

        self.msg_entry.delete(0, tk.END)
        ts = datetime.now().strftime("%H:%M:%S")
        self._append_message(f"[{ts}] You → {receiver_id}: {text}")
        threading.Thread(target=do_send, daemon=True).start()

    def _poll_loop(self):
        user_id = self.name_entry.get().strip() or "Guest"
        while self.connected:
            try:
                result = http("GET", f"/messages/{user_id}")
                messages = result.get("messages", [])
                for msg in messages:
                    ts = msg.get("current_timestamp", "")
                    sender = msg.get("sender_id", "?")
                    text = msg.get("message_text", "")
                    self.root.after(0, self._append_message, f"[{ts}] {sender}: {text}")
            except Exception as e:
                if self.connected:
                    self.root.after(0, self._log_system, f"Poll error: {e}")
            time.sleep(POLL_INTERVAL)

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
