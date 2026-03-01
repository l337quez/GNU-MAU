from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, 
                               QPushButton, QComboBox, QTextEdit, QLabel, 
                               QTabWidget, QFormLayout, QScrollArea, QFrame,
                               QTableWidget, QTableWidgetItem, QHeaderView,
                               QCompleter, QAbstractItemView, QStackedWidget,
                               QGridLayout, QGroupBox, QCheckBox, QSpinBox,
                               QFileDialog)
from PySide6.QtCore import Qt, Slot, QStringListModel
from PySide6.QtGui import QFont, QColor
import subprocess
import os
import json
import hashlib
import socket
import ssl
import ipaddress
import base64
from urllib.parse import urlparse
from utils import is_windows

COMMON_HEADERS = [
    "Accept", "Accept-Charset", "Accept-Encoding", "Accept-Language", "Accept-Ranges",
    "Age", "Allow", "Authorization", "Cache-Control", "Connection", "Content-Encoding",
    "Content-Language", "Content-Length", "Content-Location", "Content-MD5",
    "Content-Range", "Content-Type", "Cookie", "Date", "ETag", "Expect", "Expires",
    "From", "Host", "If-Match", "If-Modified-Since", "If-None-Match", "If-Range",
    "If-Unmodified-Since", "Last-Modified", "Location", "Max-Forwards", "Pragma",
    "Proxy-Authenticate", "Proxy-Authorization", "Range", "Referer", "Retry-After",
    "Server", "TE", "Trailer", "Transfer-Encoding", "Upgrade", "User-Agent",
    "Vary", "Via", "Warning", "WWW-Authenticate", "X-Requested-With", "X-Forwarded-For",
    "X-Forwarded-Proto", "X-CSRF-Token"
]

class KVTable(QTableWidget):
    def __init__(self, rows=5, columns=2, parent=None, autocompletion_list=None):
        super().__init__(rows, columns, parent)
        self.setHorizontalHeaderLabels(["Key", "Value"])
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.verticalHeader().setVisible(False)
        self.setAlternatingRowColors(True)
        self.autocompletion_list = autocompletion_list
        self.itemChanged.connect(self.on_item_changed)
        self._ensure_empty_row()

    def _ensure_empty_row(self):
        row_count = self.rowCount()
        last_row_empty = True
        if row_count > 0:
            key_item = self.item(row_count - 1, 0)
            val_item = self.item(row_count - 1, 1)
            if (key_item and key_item.text().strip()) or (val_item and val_item.text().strip()):
                last_row_empty = False
        
        if last_row_empty and row_count == 0:
            self.insertRow(0)
        elif not last_row_empty:
            self.insertRow(row_count)

    def on_item_changed(self, item):
        self._ensure_empty_row()

    def get_data(self):
        data = []
        for row in range(self.rowCount()):
            key_item = self.item(row, 0)
            val_item = self.item(row, 1)
            if key_item and val_item:
                k, v = key_item.text().strip(), val_item.text().strip()
                if k:
                    data.append((k, v))
        return data

class CurlClientWidget(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(15)
        



        # Header: Method + URL + Send
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)

        self.method_combo = QComboBox()
        self.method_combo.addItems(["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
        self.method_combo.currentTextChanged.connect(self.update_body_state)
        self.method_combo.setFixedWidth(110)
        self.method_combo.setFixedHeight(35)
        self.method_combo.setStyleSheet("""
            QComboBox {
                background-color: #3e3e3e;
                color: #cccccc;
                border: 1px solid #cccccc;
                border-radius: 5px;
                padding: 5px 10px;
                font-weight: bold;
                font-size: 13px;
            }
            QComboBox::drop-down {
                border: none;
            }
        """)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://api.example.com/v1/resource")
        self.url_input.setFixedHeight(35)
        self.url_input.setStyleSheet("""
            QLineEdit {
                background-color: #3e3e3e;
                color: #cccccc;
                border: 1px solid #cccccc;
                border-radius: 5px;
                padding: 5px 10px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #4e9edb;
            }
        """)

        self.send_button = QPushButton("Send")
        self.send_button.setFixedWidth(100)
        self.send_button.setFixedHeight(35)
        self.send_button.setCursor(Qt.PointingHandCursor)
        self.send_button.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        self.send_button.clicked.connect(self.execute_curl)

        self.ping_button = QPushButton("Ping")
        self.ping_button.setFixedWidth(80)
        self.ping_button.setFixedHeight(35)
        self.ping_button.setCursor(Qt.PointingHandCursor)
        self.ping_button.setStyleSheet("""
            QPushButton {
                background-color: #8e44ad;
                color: white;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #9b59b6;
            }
        """)
        self.ping_button.clicked.connect(self.execute_ping)

        header_layout.addWidget(self.method_combo)
        header_layout.addWidget(self.url_input)
        header_layout.addWidget(self.ping_button)
        header_layout.addWidget(self.send_button)
        self.layout.addLayout(header_layout)

        # Tabs for Params, Auth, Headers, Body, SSL
        self.request_tabs = QTabWidget()

        # 1. Params Tab
        self.params_table = KVTable()
        self.request_tabs.addTab(self.params_table, "Params")

        # 2. Authorization Tab
        auth_widget = QWidget()
        auth_layout = QVBoxLayout(auth_widget)
        auth_form = QFormLayout()
        
        self.auth_type_combo = QComboBox()
        self.auth_type_combo.addItems(["No Auth", "Bearer Token", "Basic Auth"])
        self.auth_type_combo.currentIndexChanged.connect(self.on_auth_type_changed)
        
        self.auth_stack = QStackedWidget()
        
        # No Auth page
        self.auth_stack.addWidget(QLabel("This request does not use any authorization."))
        
        # Bearer Token page
        bearer_widget = QWidget()
        bearer_layout = QVBoxLayout(bearer_widget)
        self.bearer_token_input = QLineEdit()
        self.bearer_token_input.setPlaceholderText("Token")
        bearer_layout.addWidget(QLabel("Token:"))
        bearer_layout.addWidget(self.bearer_token_input)
        bearer_layout.addStretch()
        self.auth_stack.addWidget(bearer_widget)
        
        # Basic Auth page
        basic_widget = QWidget()
        basic_layout = QFormLayout(basic_widget)
        self.basic_user_input = QLineEdit()
        self.basic_pass_input = QLineEdit()
        self.basic_pass_input.setEchoMode(QLineEdit.Password)
        basic_layout.addRow("Username:", self.basic_user_input)
        basic_layout.addRow("Password:", self.basic_pass_input)
        self.auth_stack.addWidget(basic_widget)

        auth_layout.addWidget(QLabel("Auth Type:"))
        auth_layout.addWidget(self.auth_type_combo)
        auth_layout.addWidget(self.auth_stack)
        auth_layout.addStretch()
        
        self.request_tabs.addTab(auth_widget, "Authorization")

        # 3. Headers Tab
        self.headers_table = KVTable(autocompletion_list=COMMON_HEADERS)
        # Setup Completer for Headers
        self.header_completer = QCompleter(COMMON_HEADERS)
        self.header_completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.header_completer.setFilterMode(Qt.MatchContains)
        
        self.request_tabs.addTab(self.headers_table, "Headers")

        # 4. Body Tab
        body_widget = QWidget()
        body_layout = QVBoxLayout(body_widget)
        body_layout.setContentsMargins(0, 0, 0, 0)
        
        body_toolbar = QHBoxLayout()
        body_toolbar.addStretch()
        
        self.beautify_btn = QPushButton("Beautify JSON")
        self.beautify_btn.setFixedWidth(120)
        self.beautify_btn.setCursor(Qt.PointingHandCursor)
        self.beautify_btn.setStyleSheet("""
            QPushButton {
                background-color: #16a085;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #1abc9c; }
        """)
        self.beautify_btn.clicked.connect(self.beautify_body)
        body_toolbar.addWidget(self.beautify_btn)
        
        self.body_edit = QTextEdit()
        self.body_edit.setPlaceholderText('{\n  "key": "value"\n}')
        self.body_edit.setFont(QFont("Consolas", 10))
        
        body_layout.addLayout(body_toolbar)
        body_layout.addWidget(self.body_edit)
        
        self.request_tabs.addTab(body_widget, "Body")

        # 5. SSL/Extra Tab
        # 5. SSL/Extra Tab
        # 5. Options Tab (renamed from Extra/SSL)
        options_widget = QWidget()
        options_layout = QVBoxLayout(options_widget)
        
        # --- Security Group ---
        security_group = QGroupBox("Security")
        security_layout = QGridLayout(security_group)
        
        self.insecure_check = QPushButton("Unsafe / Ignore SSL (-k)")
        self.insecure_check.setCheckable(True)
        self.insecure_check.setToolTip("Disables SSL certificate verification. Use with caution.")
        self.insecure_check.setStyleSheet("""
            QPushButton { padding: 8px; border: 1px solid #3e3e3e; border-radius: 4px; text-align: left; background-color: #3e3e3e; color: #cccccc; }
            QPushButton:checked { background-color: #e74c3c; color: white; border: 1px solid #c0392b; }
        """)

        self.no_revoke_check = QPushButton("Disable Revocation Check (--ssl-no-revoke)")
        self.no_revoke_check.setCheckable(True)
        self.no_revoke_check.setToolTip("Fixes 'revocation offline' errors on Windows. Keeps SSL verification enabled.")
        self.no_revoke_check.setStyleSheet("""
            QPushButton { padding: 8px; border: 1px solid #3e3e3e; border-radius: 4px; text-align: left; background-color: #3e3e3e; color: #cccccc; }
            QPushButton:checked { background-color: #9b59b6; color: white; border: 1px solid #8e44ad; }
        """)
        
        security_layout.addWidget(self.insecure_check, 0, 0)
        security_layout.addWidget(self.no_revoke_check, 0, 1)

        # --- Network & Output Group ---
        network_group = QGroupBox("Network & Output")
        network_layout = QGridLayout(network_group)

        self.follow_redirects_check = QPushButton("Follow Redirects (-L)")
        self.follow_redirects_check.setCheckable(True)
        self.follow_redirects_check.setToolTip("Automatically follow 3xx redirects.")
        self.follow_redirects_check.setStyleSheet("""
            QPushButton { padding: 8px; border: 1px solid #3e3e3e; border-radius: 4px; text-align: left; background-color: #3e3e3e; color: #cccccc; }
            QPushButton:checked { background-color: #3498db; color: white; border: 1px solid #2980b9; }
        """)

        self.verbose_check = QPushButton("Verbose Output (-v)")
        self.verbose_check.setCheckable(True)
        self.verbose_check.setToolTip("Show detailed handshake, headers, and debug info.")
        self.verbose_check.setStyleSheet("""
            QPushButton { padding: 8px; border: 1px solid #3e3e3e; border-radius: 4px; text-align: left; background-color: #3e3e3e; color: #cccccc; }
            QPushButton:checked { background-color: #f1c40f; color: black; border: 1px solid #f39c12; }
        """)

        network_layout.addWidget(self.follow_redirects_check, 0, 0)
        network_layout.addWidget(self.verbose_check, 0, 1)

        # --- Diagnostics Group ---
        diag_group = QGroupBox("Diagnostics")
        diag_layout = QVBoxLayout(diag_group)
        
        self.check_ssl_btn = QPushButton("Check Certificate Health")
        self.check_ssl_btn.setToolTip("Runs curl -vI to inspect server certificate details and headers.")
        self.check_ssl_btn.setStyleSheet("""
            QPushButton { 
                padding: 10px; 
                background-color: #2ecc71; 
                color: white; 
                font-weight: bold; 
                border-radius: 4px; 
            }
            QPushButton:hover { background-color: #27ae60; }
        """)
        self.check_ssl_btn.clicked.connect(self.inspect_ssl)
        
        diag_layout.addWidget(self.check_ssl_btn)

        # Add groups to main layout
        options_layout.addWidget(security_group)
        options_layout.addWidget(network_group)
        options_layout.addWidget(diag_group)
        options_layout.addStretch()

        self.request_tabs.addTab(options_widget, "Options")

        self.layout.addWidget(self.request_tabs)

        # Response Section
        response_header = QHBoxLayout()
        response_label = QLabel("Response")
        response_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setFixedWidth(60)
        self.clear_btn.clicked.connect(lambda: self.response_output.clear())
        
        response_header.addWidget(response_label)
        response_header.addStretch()
        
        self.clean_output_check = QCheckBox("Show Only Response")
        self.clean_output_check.setToolTip("If checked, hides headers, progress bar, and debug info. Shows only the response body.")
        self.clean_output_check.setStyleSheet("color: #ecf0f1; font-weight: bold;")
        response_header.addWidget(self.clean_output_check)
        
        response_header.addWidget(self.clear_btn)
        self.layout.addLayout(response_header)

        self.response_output = QTextEdit()
        self.response_output.setReadOnly(True)
        self.response_output.setFont(QFont("Consolas", 10))
        self.response_output.setStyleSheet("""
            QTextEdit {
                background-color: #2e2e2e;
                color: #cccccc;
                border: 1px solid #3e3e3e;
                border-radius: 5px;
                padding: 10px;
            }
        """)
        self.layout.addWidget(self.response_output)

        # Connect cell edit to apply completer
        self.headers_table.cellClicked.connect(self.apply_completer)
        
        # Trigger initial body state
        self.update_body_state(self.method_combo.currentText())

    @Slot(str)
    def update_body_state(self, method):
        if method in ["GET", "HEAD", "OPTIONS"]:
            self.body_edit.setReadOnly(True)
            self.body_edit.setPlaceholderText(f"Body is not available for {method} requests.")
            self.body_edit.setStyleSheet("background-color: #f1f2f6; color: #7f8c8d;")
        else:
            self.body_edit.setReadOnly(False)
            self.body_edit.setPlaceholderText('{\n  "key": "value"\n}')
            self.body_edit.setStyleSheet("")

    def apply_completer(self, row, column):
        if column == 0: # Only for headers key
            line_edit = QLineEdit()
            line_edit.setStyleSheet("color: #cccccc; background-color: #3e3e3e; border: 1px solid #cccccc;")
            line_edit.setCompleter(self.header_completer)
            # If there's already text, put it in
            current_item = self.headers_table.item(row, column)
            if current_item:
                line_edit.setText(current_item.text())
            
            self.headers_table.setCellWidget(row, column, line_edit)
            line_edit.editingFinished.connect(lambda: self._finish_line_edit(row, column, line_edit))
            line_edit.setFocus()

    def _finish_line_edit(self, row, column, line_edit):
        text = line_edit.text()
        self.headers_table.removeCellWidget(row, column)
        item = QTableWidgetItem(text)
        self.headers_table.setItem(row, column, item)

    @Slot(int)
    def on_auth_type_changed(self, index):
        self.auth_stack.setCurrentIndex(index)

    @Slot()
    def beautify_body(self):
        text = self.body_edit.toPlainText()
        if not text:
            return
            
        try:
            # Parse and re-dump with indent
            json_obj = json.loads(text)
            pretty_json = json.dumps(json_obj, indent=2)
            self.body_edit.setPlainText(pretty_json)
        except json.JSONDecodeError as e:
            # Show error in response/status if possible, or just ignore
            # For now, let's print to response output for visibility
            self.response_output.setText(f"Invalid JSON: {str(e)}")

    @Slot()
    def execute_ping(self):
        self.response_output.clear()
        url = self.url_input.text().strip()
        if not url:
            self.response_output.setText("Error: URL is required")
            return

        # Extract hostname
        if not url.startswith("http"):
            hostname = url.split("/")[0]
        else:
            try:
                parsed = urlparse(url)
                hostname = parsed.hostname
                if not hostname:
                    hostname = url # Fallback
            except:
                hostname = url

        self.response_output.append(f"Pinging {hostname}...\n")
        
        # Windows uses -n, Linux/Mac uses -c
        count_flag = "-n" if is_windows() else "-c"
        cmd = ["ping", count_flag, "4", hostname]
        
        self.run_command(cmd)

    @Slot()
    def execute_curl(self):
        self.response_output.clear()
        url = self.url_input.text().strip()
        if not url:
            self.response_output.setText("Error: URL is required")
            return

        method = self.method_combo.currentText()
        
        # Parse Params
        params = self.params_table.get_data()
        if params:
            if "?" not in url:
                url += "?"
            else:
                if not url.endswith("&") and not url.endswith("?"):
                    url += "&"
            
            param_str = "&".join([f"{k}={v}" for k, v in params])
            url += param_str

        cmd = ["curl", "-X", method, url]

        # Parse Headers
        headers = self.headers_table.get_data()
        for k, v in headers:
            cmd.extend(["-H", f"{k}: {v}"])

        # Parse Auth
        auth_type = self.auth_type_combo.currentText()
        if auth_type == "Bearer Token":
            token = self.bearer_token_input.text().strip()
            if token:
                cmd.extend(["-H", f"Authorization: Bearer {token}"])
        elif auth_type == "Basic Auth":
            user = self.basic_user_input.text().strip()
            pw = self.basic_pass_input.text().strip()
            if user or pw:
                cmd.extend(["-u", f"{user}:{pw}"])

        # Parse Body
        body = self.body_edit.toPlainText().strip()
        if body and method in ["POST", "PUT", "PATCH"]:
            cmd.extend(["-d", body])

        if self.verbose_check.isChecked():
            cmd.append("-v")
            
        if self.follow_redirects_check.isChecked():
            cmd.append("-L")
        
        if self.insecure_check.isChecked():
            cmd.append("-k")
            
        if self.no_revoke_check.isChecked():
            cmd.append("--ssl-no-revoke")

        self.run_command(cmd)

    @Slot()
    def inspect_ssl(self):
        self.response_output.clear()
        url = self.url_input.text().strip()
        if not url:
            self.response_output.setText("Error: URL is required")
            return
        
        cmd = ["curl", "-v", "-I", url]
        if self.insecure_check.isChecked():
            cmd.append("-k")
            
        if self.no_revoke_check.isChecked():
            cmd.append("--ssl-no-revoke")
            
        self.run_command(cmd)

    def run_command(self, cmd):
        # Auto-append silent flag for curl if we want clean output
        if self.clean_output_check.isChecked() and cmd and cmd[0] == "curl":
            if "-s" not in cmd:
                cmd.append("-s")

        if not self.clean_output_check.isChecked():
            self.response_output.setText(f"Executing: {' '.join(cmd)}\n\n")
        else:
            self.response_output.clear()

        try:
            # Use specific encoding options to avoid crashes on Windows with non-ascii output
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, errors='replace')
            stdout, stderr = process.communicate()
            
            output = ""
            if self.clean_output_check.isChecked():
                # Clean mode: Just stdout (response body)
                if stdout:
                    output = stdout
                elif stderr:
                     # If stdout is empty but we have an error, show it so user isn't confused
                    output = f"Error: {stderr}"
            else:
                # Verbose mode: Full details
                if stdout:
                    output += "--- STDOUT ---\n" + stdout + "\n"
                if stderr:
                    output += "--- STDERR / VERBOSE ---\n" + stderr + "\n"
            
            self.response_output.append(output)
        except Exception as e:
            self.response_output.append(f"\nError executing command: {str(e)}")

    def set_clean_view(self, enabled):
        pass

class NetworkToolsWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        
        # --- Port Scanner ---
        scan_group = QGroupBox("Port Scanner")
        scan_layout = QHBoxLayout(scan_group)
        self.host_input = QLineEdit()
        self.host_input.setPlaceholderText("Hostname (e.g., google.com)")
        self.port_input = QLineEdit()
        self.port_input.setPlaceholderText("Port (e.g., 80)")
        self.port_input.setFixedWidth(100)
        self.scan_btn = QPushButton("Scan Port")
        self.scan_btn.clicked.connect(self.scan_port)
        scan_layout.addWidget(self.host_input)
        scan_layout.addWidget(self.port_input)
        scan_layout.addWidget(self.scan_btn)
        layout.addWidget(scan_group)

        # --- IP Calc ---
        ip_group = QGroupBox("IP Calculator")
        ip_layout = QHBoxLayout(ip_group)
        self.cidr_input = QLineEdit()
        self.cidr_input.setPlaceholderText("CIDR (e.g., 192.168.1.0/24)")
        self.calc_btn = QPushButton("Calculate")
        self.calc_btn.clicked.connect(self.calc_ip)
        ip_layout.addWidget(self.cidr_input)
        ip_layout.addWidget(self.calc_btn)
        layout.addWidget(ip_group)

        # Result Area
        self.result_area = QTextEdit()
        self.result_area.setReadOnly(True)
        self.result_area.setFont(QFont("Consolas", 10))
        layout.addWidget(self.result_area)

    def log(self, text):
        self.result_area.append(text)

    def scan_port(self):
        host = self.host_input.text().strip()
        port_str = self.port_input.text().strip()
        if not host or not port_str:
            self.log("Error: Host and Port required.")
            return
        
        try:
            port = int(port_str)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2) # 2s timeout
            self.log(f"Scanning {host}:{port}...")
            result = sock.connect_ex((host, port))
            if result == 0:
                self.log(f"✅ Port {port} on {host} is OPEN")
            else:
                self.log(f"❌ Port {port} on {host} is CLOSED")
            sock.close()
        except Exception as e:
            self.log(f"Error: {e}")

    def calc_ip(self):
        cidr = self.cidr_input.text().strip()
        if not cidr:
             self.log("Error: CIDR required.")
             return
        try:
            net = ipaddress.ip_network(cidr, strict=False)
            self.log(f"--- IP Network: {cidr} ---")
            self.log(f"Network Address: {net.network_address}")
            self.log(f"Broadcast: {net.broadcast_address}")
            self.log(f"Netmask: {net.netmask}")
            self.log(f"Total Hosts: {net.num_addresses}")
            self.log(f"Usable Hosts: {net.num_addresses - 2 if net.num_addresses > 2 else 0}")
            self.log("-" * 20)
        except ValueError as e:
            self.log(f"Invalid CIDR: {e}")


class SecurityToolsWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        # --- JWT Decoder ---
        jwt_group = QGroupBox("JWT Debugger (No Secret Required)")
        jwt_layout = QVBoxLayout(jwt_group)
        self.jwt_input = QLineEdit()
        self.jwt_input.setPlaceholderText("Paste JWT Token here...")
        self.jwt_decode_btn = QPushButton("Decode JWT Payload")
        self.jwt_decode_btn.clicked.connect(self.decode_jwt)
        jwt_layout.addWidget(self.jwt_input)
        jwt_layout.addWidget(self.jwt_decode_btn)
        layout.addWidget(jwt_group)

        # --- Password Hashing ---
        hash_group = QGroupBox("Password Hashing (PBKDF2)")
        hash_main_layout = QVBoxLayout(hash_group)
        
        self.pass_input = QLineEdit()
        self.pass_input.setPlaceholderText("Password to hash")
        self.pass_input.setEchoMode(QLineEdit.Password)
        hash_main_layout.addWidget(self.pass_input)
        
        rounds_row = QHBoxLayout()
        rounds_row.addWidget(QLabel("Rounds:"))
        self.rounds_input = QSpinBox()
        self.rounds_input.setRange(1, 10)
        self.rounds_input.setValue(1)
        self.rounds_input.setToolTip("Number of hash iterations (rounds)")
        rounds_row.addWidget(self.rounds_input)
        
        self.hash_btn = QPushButton("Generate Hash")
        self.hash_btn.clicked.connect(self.hash_password)
        rounds_row.addWidget(self.hash_btn)
        
        hash_main_layout.addLayout(rounds_row)
        layout.addWidget(hash_group)

        # Result Area
        self.result_area = QTextEdit()
        self.result_area.setReadOnly(True)
        self.result_area.setFont(QFont("Consolas", 10))
        layout.addWidget(self.result_area)

    def log(self, text):
        self.result_area.append(text)

    def hash_password(self):
        password = self.pass_input.text().strip()
        rounds = self.rounds_input.value()
        if not password:
            self.log("Error: Password required.")
            return
            
        try:
            # Use PBKDF2-HMAC-SHA256
            # We'll use a fixed salt for simple "hashing tool" purposes 
            # (In SRE tasks, sometimes you just need to generate a specific hash type)
            salt = b'constant_devops_salt' 
            dk = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, rounds)
            hex_hash = dk.hex()
            
            self.log(f"--- PBKDF2-SHA256 ({rounds} rounds) ---")
            self.log(f"Salt: {salt.decode()}")
            self.log(f"Hash: {hex_hash}")
            self.log("-" * 20)
        except Exception as e:
            self.log(f"Error hashing password: {e}")

    def decode_jwt(self):
        token = self.jwt_input.text().strip()
        if not token:
            self.log("Error: Token required.")
            return

        parts = token.split('.')
        if len(parts) != 3:
            self.log("Error: Invalid JWT format (expected 3 parts).")
            return
        
        try:
            # Decode Payload (Part 2)
            payload = parts[1]
            # Add padding if needed
            padding = len(payload) % 4
            if padding:
                payload += '=' * (4 - padding)
            
            decoded_bytes = base64.urlsafe_b64decode(payload)
            decoded_str = decoded_bytes.decode('utf-8')
            
            # Prettify JSON
            obj = json.loads(decoded_str)
            pretty = json.dumps(obj, indent=2)
            
            self.log("--- JWT Payload ---")
            self.log(pretty)
            self.log("-" * 20)
        except Exception as e:
            self.log(f"Error decoding JWT: {e}")


class SignatureToolsWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        # === Section 1: Generate Hash ===
        gen_group = QGroupBox("🔑 Generate File Hash")
        gen_layout = QVBoxLayout(gen_group)

        gen_desc = QLabel("Select a file to calculate its SHA-256 hash.")
        gen_desc.setWordWrap(True)
        gen_layout.addWidget(gen_desc)

        gen_file_row = QHBoxLayout()
        self.gen_file_path = QLineEdit()
        self.gen_file_path.setPlaceholderText("No file selected...")
        self.gen_file_path.setReadOnly(True)
        self.gen_browse_btn = QPushButton("Browse...")
        self.gen_browse_btn.setFixedWidth(100)
        self.gen_browse_btn.clicked.connect(self.browse_gen_file)
        gen_file_row.addWidget(self.gen_file_path)
        gen_file_row.addWidget(self.gen_browse_btn)
        gen_layout.addLayout(gen_file_row)

        self.gen_hash_btn = QPushButton("Generate SHA-256 Hash")
        self.gen_hash_btn.clicked.connect(self.generate_hash)
        gen_layout.addWidget(self.gen_hash_btn)

        gen_result_row = QHBoxLayout()
        self.gen_result = QLineEdit()
        self.gen_result.setPlaceholderText("Hash will appear here...")
        self.gen_result.setReadOnly(True)
        self.gen_result.setFont(QFont("Consolas", 10))
        self.gen_copy_btn = QPushButton("📋 Copy")
        self.gen_copy_btn.setFixedWidth(80)
        self.gen_copy_btn.clicked.connect(self.copy_gen_hash)
        gen_result_row.addWidget(self.gen_result)
        gen_result_row.addWidget(self.gen_copy_btn)
        gen_layout.addLayout(gen_result_row)

        layout.addWidget(gen_group)

        # === Section 2: Verify Hash ===
        ver_group = QGroupBox("✅ Verify File Hash")
        ver_layout = QVBoxLayout(ver_group)

        ver_desc = QLabel("Paste a known SHA-256 hash, select a file, and check if they match.")
        ver_desc.setWordWrap(True)
        ver_layout.addWidget(ver_desc)

        ver_hash_row = QHBoxLayout()
        self.ver_hash_input = QLineEdit()
        self.ver_hash_input.setPlaceholderText("Paste the expected SHA-256 hash here...")
        self.ver_hash_input.setFont(QFont("Consolas", 10))
        self.ver_paste_btn = QPushButton("📋 Paste")
        self.ver_paste_btn.setFixedWidth(80)
        self.ver_paste_btn.clicked.connect(self.paste_ver_hash)
        ver_hash_row.addWidget(self.ver_hash_input)
        ver_hash_row.addWidget(self.ver_paste_btn)
        ver_layout.addLayout(ver_hash_row)

        ver_file_row = QHBoxLayout()
        self.ver_file_path = QLineEdit()
        self.ver_file_path.setPlaceholderText("No file selected...")
        self.ver_file_path.setReadOnly(True)
        self.ver_browse_btn = QPushButton("Browse...")
        self.ver_browse_btn.setFixedWidth(100)
        self.ver_browse_btn.clicked.connect(self.browse_ver_file)
        ver_file_row.addWidget(self.ver_file_path)
        ver_file_row.addWidget(self.ver_browse_btn)
        ver_layout.addLayout(ver_file_row)

        self.ver_check_btn = QPushButton("Verify")
        self.ver_check_btn.clicked.connect(self.verify_hash)
        ver_layout.addWidget(self.ver_check_btn)

        self.ver_result = QLabel("")
        self.ver_result.setStyleSheet("font-size: 14px; font-weight: bold; padding: 8px;")
        ver_layout.addWidget(self.ver_result)

        layout.addWidget(ver_group)

        # Status label at the bottom
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("font-size: 12px; padding: 4px; color: #2ecc71;")
        layout.addWidget(self.status_label)

        layout.addStretch()

    def _compute_sha256(self, filepath):
        """Read file as bytes and compute SHA-256 hash."""
        sha256 = hashlib.sha256()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()

    def browse_gen_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select File", "", "All Files (*)")
        if path:
            self.gen_file_path.setText(path)
            self.gen_result.clear()

    def generate_hash(self):
        path = self.gen_file_path.text().strip()
        if not path:
            self.gen_result.setText("Error: Select a file first.")
            return
        try:
            file_hash = self._compute_sha256(path)
            self.gen_result.setText(file_hash)
        except Exception as e:
            self.gen_result.setText(f"Error: {e}")

    def copy_gen_hash(self):
        from PySide6.QtWidgets import QApplication
        text = self.gen_result.text()
        if text and not text.startswith("Error"):
            QApplication.clipboard().setText(text)
            self.status_label.setText("✅ Copied successfully")
            self.status_label.setStyleSheet("font-size: 12px; padding: 4px; color: #2ecc71;")
        else:
            self.status_label.setText("⚠️ Nothing to copy")
            self.status_label.setStyleSheet("font-size: 12px; padding: 4px; color: #f39c12;")

    def paste_ver_hash(self):
        from PySide6.QtWidgets import QApplication
        text = QApplication.clipboard().text()
        if text:
            self.ver_hash_input.setText(text.strip())
            self.status_label.setText("✅ Pasted from clipboard")
            self.status_label.setStyleSheet("font-size: 12px; padding: 4px; color: #2ecc71;")

    def browse_ver_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select File", "", "All Files (*)")
        if path:
            self.ver_file_path.setText(path)
            self.ver_result.setText("")

    def verify_hash(self):
        expected = self.ver_hash_input.text().strip().lower()
        path = self.ver_file_path.text().strip()

        if not expected:
            self.ver_result.setText("⚠️ Paste a hash first.")
            self.ver_result.setStyleSheet("font-size: 14px; font-weight: bold; padding: 8px; color: #f39c12;")
            return
        if not path:
            self.ver_result.setText("⚠️ Select a file first.")
            self.ver_result.setStyleSheet("font-size: 14px; font-weight: bold; padding: 8px; color: #f39c12;")
            return

        try:
            actual = self._compute_sha256(path)
            if actual == expected:
                self.ver_result.setText("✅ MATCH — The file hash matches the expected hash.")
                self.ver_result.setStyleSheet("font-size: 14px; font-weight: bold; padding: 8px; color: #2ecc71;")
            else:
                self.ver_result.setText(f"❌ NO MATCH\nExpected: {expected}\n     Got: {actual}")
                self.ver_result.setStyleSheet("font-size: 14px; font-weight: bold; padding: 8px; color: #e74c3c;")
        except Exception as e:
            self.ver_result.setText(f"Error: {e}")
            self.ver_result.setStyleSheet("font-size: 14px; font-weight: bold; padding: 8px; color: #e74c3c;")


class CurlWrapperTab(QWidget): 
    # This is now the main container, handling the tabs
    def __init__(self, main_window):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.tabs = QTabWidget()

        # Tab 1: HTTP Client (Original Logic)
        self.http_client = CurlClientWidget(main_window)
        self.tabs.addTab(self.http_client, "HTTP Client")

        # Tab 2: Network
        self.network_tools = NetworkToolsWidget()
        self.tabs.addTab(self.network_tools, "Network")

        # Tab 3: Security
        self.security_tools = SecurityToolsWidget()
        self.tabs.addTab(self.security_tools, "Security")

        # Tab 4: Signature
        self.signature_tools = SignatureToolsWidget()
        self.tabs.addTab(self.signature_tools, "Signature")

        self.layout.addWidget(self.tabs)
