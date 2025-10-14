import socket
import threading
import time
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from collections import deque
import logging
import queue

# =============================================================================
# Setup Logging
# =============================================================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log_queue = deque(maxlen=100)

# =============================================================================
# Global State and Event Queue
# =============================================================================
EVENT_QUEUE = queue.Queue()
STATE_LOCK = threading.Lock()
DEVICES_STATE = {
    "injector": {
        "name": "injector", "ip": None, "last_seen": 0,
        "isConnected": False, "isPeerConnected": False, "telemetry": {}
    },
    "fillhead": {
        "name": "fillhead", "ip": None, "last_seen": 0,
        "isConnected": False, "isPeerConnected": False, "telemetry": {}
    }
}

# =============================================================================
# Communication Management
# =============================================================================

class UdpComms:
    def __init__(self, event_queue):
        self.event_queue = event_queue
        self.CLEARCORE_PORT = 8888
        self.CLIENT_PORT = 6272
        self.BROADCAST_ADDR = '<broadcast>'
        self.DISCOVERY_INTERVAL = 2.0
        self.TELEMETRY_INTERVAL = 0.5
        self.TIMEOUT_THRESHOLD = 5.0
        self.sock = None
        self.is_running = False

    def setup_socket(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.settimeout(1.0)
        try:
            self.sock.bind(('0.0.0.0', self.CLIENT_PORT))
            logging.info(f"UDP Socket bound successfully to port {self.CLIENT_PORT}")
            return True
        except OSError as e:
            logging.error(f"FATAL: Could not bind to port {self.CLIENT_PORT}. Error: {e}")
            return False

    def start_threads(self):
        if not self.setup_socket(): return
        self.is_running = True
        threading.Thread(target=self._discovery_and_monitoring_loop, daemon=True).start()
        threading.Thread(target=self._telemetry_requester_loop, daemon=True).start()
        threading.Thread(target=self._udp_receive_loop, daemon=True).start()
        logging.info("UDP Communication threads started.")

    def stop_threads(self):
        self.is_running = False
        if self.sock: self.sock.close()
        logging.info("UDP Communication threads stopped.")

    def send_command_to_device(self, device_name, command_str):
        with STATE_LOCK:
            device = DEVICES_STATE[device_name]
            ip = device.get("ip")
            is_connected = device.get("isConnected")

        if is_connected and ip:
            try:
                if "REQUEST_TELEM" not in command_str:
                    log_queue.append(f"SEND -> {ip}:{self.CLEARCORE_PORT}: {command_str}")
                self.sock.sendto(command_str.encode(), (ip, self.CLEARCORE_PORT))
                return True, f"Command sent to {device_name}"
            except Exception as e:
                log_queue.append(f"ERROR sending to {device_name}: {e}")
                return False, f"Error sending command: {e}"
        return False, f"Cannot send to {device_name}: Not connected or IP unknown."

    def _discovery_and_monitoring_loop(self):
        while self.is_running:
            try:
                now = time.time()
                with STATE_LOCK:
                    devices_to_check = list(DEVICES_STATE.items())

                for name, device in devices_to_check:
                    if device["isConnected"] and (now - device["last_seen"]) > self.TIMEOUT_THRESHOLD:
                        self.event_queue.put(("DEVICE_TIMEOUT", name, None))

                    if not device["isConnected"]:
                        msg = f"DISCOVER_{name.upper()} PORT={self.CLIENT_PORT}"
                        logging.info(f"SENDING BROADCAST -> {self.BROADCAST_ADDR}:{self.CLEARCORE_PORT}: {msg}")
                        log_queue.append(f"SEND -> {self.BROADCAST_ADDR}:{self.CLEARCORE_PORT}: {msg}")
                        self.sock.sendto(msg.encode(), (self.BROADCAST_ADDR, self.CLEARCORE_PORT))
                time.sleep(self.DISCOVERY_INTERVAL)
            except Exception as e:
                logging.error(f"Discovery loop error: {e}")

    def _telemetry_requester_loop(self):
        while self.is_running:
            with STATE_LOCK:
                device_names = [name for name, dev in DEVICES_STATE.items() if dev.get("isConnected")]
            for name in device_names:
                self.send_command_to_device(name, "REQUEST_TELEM")
            time.sleep(self.TELEMETRY_INTERVAL)

    def _udp_receive_loop(self):
        while self.is_running:
            try:
                data, addr = self.sock.recvfrom(2048)
                msg = data.decode('utf-8', errors='replace').strip()
                source_ip = addr[0]
                
                device_name = None
                if "INJECTOR" in msg or "INJ_" in msg:
                    device_name = "injector"
                elif "FILLHEAD" in msg or "FH_" in msg:
                    device_name = "fillhead"

                if device_name:
                    # NEW LOG: Confirming we are about to queue an event
                    logging.info(f"UDP_LOOP: Queuing HEARTBEAT for {device_name} from {source_ip}")
                    self.event_queue.put(("DEVICE_HEARTBEAT", device_name, {"ip": source_ip, "msg": msg}))
                else:
                    logging.warning(f"UDP_LOOP: Received unknown message from {source_ip}: {msg}")

            except socket.timeout:
                continue
            except Exception as e:
                logging.error(f"UDP Receive Loop Error: {e}")
                time.sleep(1)

# =============================================================================
# State Management Thread
# =============================================================================

def state_manager(event_queue, comms):
    """Processes events from the queue and updates the global state."""
    while True:
        try:
            event_type, name, data = event_queue.get()
            # NEW LOG: See every event as it's pulled from the queue
            logging.info(f"STATE_MANAGER: Dequeued event '{event_type}' for '{name}'")
            
            with STATE_LOCK:
                device = DEVICES_STATE[name]

                if event_type == "DEVICE_HEARTBEAT":
                    ip = data["ip"]
                    msg = data["msg"]

                    device["last_seen"] = time.time()

                    if not device["isConnected"]:
                        logging.info(f"✅ CONNECTION ESTABLISHED for {name.upper()} at {ip}")
                        log_queue.append(f"CONNECT: {name.capitalize()} at {ip}")
                        device.update({"isConnected": True, "ip": ip})
                        check_for_peer_connection_unlocked(comms)
                    
                    elif device["ip"] != ip:
                        logging.info(f"🔄 IP ADDRESS UPDATED for {name.upper()} from {device['ip']} to {ip}")
                        log_queue.append(f"IP CHANGE: {name.capitalize()} now at {ip}")
                        device["ip"] = ip
                        check_for_peer_connection_unlocked(comms)

                    if "TELEM_GUI" in msg:
                        logging.info(f"STATE_MANAGER: Parsing telemetry for '{name}'")
                        try:
                            telem_data = parse_telemetry(name, msg)
                            device["telemetry"].update(telem_data)
                            if 'isPeerDiscovered' in telem_data and device["isPeerConnected"] != telem_data['isPeerDiscovered']:
                                device["isPeerConnected"] = telem_data['isPeerDiscovered']
                                log_queue.append(f"INFO: {name.capitalize()} peer status changed to {device['isPeerConnected']}")
                                check_for_peer_connection_unlocked(comms)
                        except Exception as e:
                            log_queue.append(f"Error parsing {name} telemetry: {e} | MSG: {msg}")
                    
                    elif "DISCOVERED" in msg:
                         log_queue.append(f"RECV <- {ip}: {msg}")

                elif event_type == "DEVICE_TIMEOUT":
                    if device["isConnected"]:
                        logging.warning(f"TIMEOUT: {name.capitalize()} at {device['ip']} disconnected.")
                        log_queue.append(f"TIMEOUT: {name.capitalize()} disconnected.")
                        device.update({"isConnected": False, "isPeerConnected": False, "telemetry": {}})
                        other_name = "fillhead" if name == "injector" else "injector"
                        if DEVICES_STATE[other_name]["isConnected"]:
                            comms.send_command_to_device(other_name, "CLEAR_PEER_IP")

        except Exception as e:
            logging.error(f"State manager error: {e}")

def check_for_peer_connection_unlocked(comms):
    injector = DEVICES_STATE["injector"]
    fillhead = DEVICES_STATE["fillhead"]
    if injector["isConnected"] and fillhead["isConnected"]:
        if not injector["isPeerConnected"] and fillhead["ip"]:
            log_queue.append(f"INFO: Brokering IP for Injector -> {fillhead['ip']}")
            comms.send_command_to_device("injector", f"SET_PEER_IP {fillhead['ip']}")
        if not fillhead["isPeerConnected"] and injector["ip"]:
            log_queue.append(f"INFO: Brokering IP for Fillhead -> {injector['ip']}")
            comms.send_command_to_device("fillhead", f"SET_PEER_IP {injector['ip']}")

def parse_telemetry(name, msg):
    """General purpose telemetry parser."""
    def _parse_key_value_payload(payload_str):
        return dict(item.split(':', 1) for item in payload_str.split(',') if ':' in item and len(item.split(':', 1)) == 2)
    def _safe_float(s, default=0.0):
        try: return float(s)
        except (ValueError, TypeError): return default

    try:
        if name == "injector":
            payload = msg.split("INJ_TELEM_GUI:")[1]
            parts = _parse_key_value_payload(payload)
            return { "mainState": parts.get("MAIN_STATE", "---"), "feedState": parts.get("FEED_STATE", "IDLE"), "errorState": parts.get("ERROR_STATE", "No Error"), "positionMachine": _safe_float(parts.get("machine_mm")), "positionCartridge": _safe_float(parts.get("cartridge_mm")), "dispensedVolume": _safe_float(parts.get("dispensed_ml")), "temperature": _safe_float(parts.get("temp_c")), "vacuum": _safe_float(parts.get('vacuum_psig')), "isPeerDiscovered": parts.get("peer_disc", "0") == "1", "peerIp": parts.get("peer_ip", "0.0.0.0"), "motors": [ {"enabled": parts.get("enabled0", "0") == "1", "homed": parts.get("homed0", "0") == "1", "torque": _safe_float(parts.get("torque0")), "position": _safe_float(parts.get("pos_mm0"))}, {"enabled": parts.get("enabled1", "0") == "1", "homed": parts.get("homed1", "0") == "1", "torque": _safe_float(parts.get("torque1")), "position": _safe_float(parts.get("pos_mm1"))}, {"enabled": parts.get("enabled2", "0") == "1", "homed": parts.get("homed2", "0") == "1", "torque": _safe_float(parts.get("torque2")), "position": _safe_float(parts.get("pos_mm2"))} ] }
        elif name == "fillhead":
            payload = msg.split("FH_TELEM_GUI:")[1].strip()
            parts = _parse_key_value_payload(payload)
            return { "stateX": parts.get("x_s", "UNKNOWN"), "stateY": parts.get("y_s", "UNKNOWN"), "stateZ": parts.get("z_s", "UNKNOWN"), "isPeerDiscovered": parts.get("pd", "0") == "1", "peerIp": parts.get("pip", "0.0.0.0"), "axes": { "x": {"position": _safe_float(parts.get("x_p")), "torque": _safe_float(parts.get("x_t")), "enabled": parts.get("x_e", "0") == "1", "homed": parts.get("x_h", "0") == "1"}, "y": {"position": _safe_float(parts.get("y_p")), "torque": _safe_float(parts.get("y_t")), "enabled": parts.get("y_e", "0") == "1", "homed": parts.get("y_h", "0") == "1"}, "z": {"position": _safe_float(parts.get("z_p")), "torque": _safe_float(parts.get("z_t")), "enabled": parts.get("z_e", "0") == "1", "homed": parts.get("z_h", "0") == "1"} } }
    except IndexError:
        logging.warning(f"Could not split telemetry message: {msg}")
    return {}

# =============================================================================
# Flask App Setup
# =============================================================================

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})
comms = UdpComms(EVENT_QUEUE)

@app.route('/api/devices', methods=['GET'])
def get_devices():
    logs = []
    while True:
        try:
            logs.append(log_queue.popleft())
        except IndexError:
            break
    with STATE_LOCK:
        devices_copy = json.loads(json.dumps(DEVICES_STATE))
    return jsonify({
        "devices": devices_copy,
        "logs": logs
    })

@app.route('/api/send_command', methods=['POST'])
def handle_send_command():
    data = request.get_json()
    if not data: return jsonify({"error": "Invalid JSON"}), 400
    device, command, params = data.get('device'), data.get('command'), data.get('params', {})
    if not all([device, command]): return jsonify({"error": "Device and command must be provided"}), 400
    command_map = { "ENABLE": "ENABLE", "DISABLE": "DISABLE", "ENABLE_PINCH": "ENABLE_PINCH", "DISABLE_PINCH": "DISABLE_PINCH", "STOP": "ABORT", "PINCH_HOME": "PINCH_HOME_MOVE", "HOME": f"MACHINE_HOME_MOVE {params.get('stroke', 50)} {params.get('rapidVel', 20)} {params.get('touchVel', 2)} {params.get('accel', 100)} {params.get('retract', 1)} {params.get('torque', 25)}", "MOVE_ABSOLUTE": f"JOG_MOVE {params.get('position', 0)} {params.get('position', 0)} {params.get('velocity', 5)} {params.get('acceleration', 25)} {params.get('torque', 20)}", "INJECT": f"INJECT_MOVE {params.get('volume')} {params.get('speed')} {params.get('accel', 5000)} {params.get('stepsPerMl')} {params.get('torque', 50)}", "PURGE": f"PURGE_MOVE {params.get('volume')} {params.get('speed')} {params.get('accel', 5000)} {params.get('stepsPerMl')} {params.get('torque', 50)}", "FH_ENABLE_X": "ENABLE_X", "FH_DISABLE_X": "DISABLE_X", "FH_ENABLE_Y": "ENABLE_Y", "FH_DISABLE_Y": "DISABLE_Y", "FH_ENABLE_Z": "ENABLE_Z", "FH_DISABLE_Z": "DISABLE_Z", "FH_HOME_X": f"HOME_X {params.get('torque', 20)} {params.get('maxDist', 420)}", "FH_HOME_Y": f"HOME_Y {params.get('torque', 20)} {params.get('maxDist', 420)}", "FH_HOME_Z": f"HOME_Z {params.get('torque', 20)} {params.get('maxDist', 420)}", "FH_MOVE_X": f"MOVE_X {params.get('distance', 10)} {params.get('velocity', 15)} {params.get('acceleration', 50)} {params.get('torque', 20)}", "FH_MOVE_Y": f"MOVE_Y {params.get('distance', 10)} {params.get('velocity', 15)} {params.get('acceleration', 50)} {params.get('torque', 20)}", "FH_MOVE_Z": f"MOVE_Z {params.get('distance', 10)} {params.get('velocity', 15)} {params.get('acceleration', 50)} {params.get('torque', 20)}", "RAW_COMMAND": params.get('raw', '') }
    raw_command = command_map.get(command)
    if not raw_command: return jsonify({"error": f"Unknown command: {command}"}), 400
    success, message = comms.send_command_to_device(device, raw_command)
    if success: return jsonify({"message": message})
    else: return jsonify({"error": message}), 500

@app.route('/api/validate_script', methods=['POST'])
def validate_script():
    return jsonify({"message": "Script validation not yet implemented."})

@app.route('/api/run_script', methods=['POST'])
def run_script():
    return jsonify({"message": "Script execution not yet implemented."})

if __name__ == '__main__':
    try:
        # Start the state manager thread
        state_thread = threading.Thread(target=state_manager, args=(EVENT_QUEUE, comms), daemon=True)
        state_thread.start()
        
        # Start the communication threads
        comms.start_threads()
        
        # Start the Flask app
        app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
    except Exception as e:
        logging.error(f"Failed to start Flask server: {e}")
