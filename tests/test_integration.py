"""Kiểm thử sáu chương trình qua broker MQTT thật trên cổng cục bộ tạm thời.

Chạy: python -m unittest discover -s tests -v
Yêu cầu: pip install -r requirements-broker.txt
"""

import json
import os
from pathlib import Path
import queue
import socket
import subprocess
import sys
import threading
import time
import unittest
import uuid

import paho.mqtt.client as mqtt

ROOT = Path(__file__).resolve().parents[1]


class Process:
    def __init__(self, *args):
        self.lines = []
        self.events = []
        self.process = subprocess.Popen(
            [sys.executable, "-u", *map(str, args)], cwd=ROOT,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", env={**os.environ, "PYTHONUTF8": "1"},
        )
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.reader.start()

    def _read(self):
        for line in self.process.stdout:
            self.lines.append(line)
            self.events.append((time.monotonic(), line))

    @property
    def output(self):
        return "".join(self.lines)

    def until(self, text, timeout=12):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if text in self.output:
                return
            if self.process.poll() is not None:
                self.reader.join(timeout=1)
                if text in self.output:
                    return
                break
            time.sleep(0.02)
        raise AssertionError(f"Không thấy {text!r}:\n{self.output}")

    def finish(self, inputs=None, timeout=15):
        if inputs is not None:
            self.process.stdin.write(inputs)
            self.process.stdin.flush()
            self.process.stdin.close()
        self.process.wait(timeout=timeout)
        self.reader.join(timeout=2)
        return self.process.returncode, self.output

    def close(self):
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        self.reader.join(timeout=2)
        for stream in (self.process.stdin, self.process.stdout):
            if stream and not stream.closed:
                stream.close()


class MQTTIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            cls.port = sock.getsockname()[1]
        cls.broker = Process("tools/local_broker.py", "--port", cls.port)
        try:
            cls.broker.until("BROKER READY")
        except BaseException:
            cls.broker.close()
            raise

    @classmethod
    def tearDownClass(cls):
        cls.broker.close()

    def setUp(self):
        self.children = []
        self.clients = []

    def tearDown(self):
        for child in self.children:
            child.close()
        for client in self.clients:
            client.disconnect()
            client.loop_stop()

    def start(self, filename, *args):
        child = Process(filename, "--config", "tests/fixtures/config.json",
                        "--port", self.port, "--timeout", "4", *args)
        self.children.append(child)
        return child

    def success(self, child, inputs=None, timeout=15):
        code, output = child.finish(inputs, timeout)
        self.assertEqual(code, 0, output)
        self.assertNotIn("Traceback", output)
        return output

    def observer(self, topic=None):
        ready = threading.Event()
        messages = queue.Queue()
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                             client_id=f"test-{uuid.uuid4().hex[:12]}")

        def on_connect(client, userdata, flags, code, properties):
            if code.is_failure:
                return
            if topic:
                client.subscribe(topic, qos=1)
            else:
                ready.set()

        client.on_connect = on_connect
        client.on_subscribe = lambda *args: ready.set()
        client.on_message = lambda c, u, m: messages.put((m.topic, m.payload, m.retain))
        self.clients.append(client)
        client.connect("127.0.0.1", self.port)
        client.loop_start()
        self.assertTrue(ready.wait(5), "Observer không kết nối/subscribe được.")
        return client, messages

    def publish(self, client, topic, payload, retain=False):
        info = client.publish(topic, payload, qos=1, retain=retain)
        info.wait_for_publish(timeout=4)
        self.assertTrue(info.is_published())

    def test_bai1_three_messages_and_cli_identity(self):
        subscriber = self.start("subscriber_bai1.py", "--max-messages", "3")
        subscriber.until("Đã subscribe:")
        output = self.success(self.start("publisher_bai1.py", "--name", "Sinh viên kiểm thử",
                              "--student-id", "TEST001", "--count", "3", "--interval", "0.1"))
        received = self.success(subscriber)
        self.assertEqual(received.count("Nhan duoc message:"), 3)
        self.assertEqual(received.count("Topic: iot/lab/message"), 3)
        self.assertEqual(received.count("Time:"), 3)
        self.assertIn("Xin chao tu client Python MQTT - TEST001 - Sinh viên kiểm thử", received)
        self.assertNotIn("TESTCONFIG", received)
        self.assertIn("Đã gửi [3]", output)

    def test_bai1_identity_from_config(self):
        subscriber = self.start("subscriber_bai1.py", "--max-messages", "1")
        subscriber.until("Đã subscribe:")
        self.success(self.start("publisher_bai1.py"))
        self.assertIn("TESTCONFIG - Ten trong cau hinh kiem thu", self.success(subscriber))

    def test_bai2_default_three_second_period_and_random_ranges(self):
        _, messages = self.observer("iot/lab/sensor01/data")
        sensor = self.start("sensor_publisher_bai2.py", "--count", "3", "--seed", "7")
        times = []
        for _ in range(3):
            topic, raw, _ = messages.get(timeout=7)
            times.append(time.monotonic())
            payload = json.loads(raw)
            self.assertEqual(topic, "iot/lab/sensor01/data")
            self.assertEqual(set(payload), {"device_id", "temperature", "humidity"})
            self.assertEqual(payload["device_id"], "sensor01")
            self.assertTrue(20 <= payload["temperature"] <= 40)
            self.assertTrue(30 <= payload["humidity"] <= 80)
        self.success(sensor)
        for elapsed in (times[1] - times[0], times[2] - times[1]):
            self.assertGreaterEqual(elapsed, 2.8)
            self.assertLess(elapsed, 5)

    def test_bai2_exact_thresholds_and_independent_warnings(self):
        for temp, humidity, high, low in [(35, 40, False, False), (35.1, 40, True, False),
                                          (35, 39.9, False, True), (36.1, 38.7, True, True)]:
            with self.subTest(temperature=temp, humidity=humidity):
                monitor = self.start("monitor_subscriber_bai2.py", "--max-messages", "1")
                monitor.until("Đã subscribe:")
                self.success(self.start("sensor_publisher_bai2.py", "--count", "1",
                                         "--temperature", temp, "--humidity", humidity))
                output = self.success(monitor)
                self.assertEqual("CANH BAO: Nhiet do cao" in output, high)
                self.assertEqual("CANH BAO: Do am thap" in output, low)

    def test_bai2_invalid_payloads_do_not_stop_monitor(self):
        monitor = self.start("monitor_subscriber_bai2.py", "--max-messages", "1")
        monitor.until("Đã subscribe:")
        client, _ = self.observer()
        invalid = [b"{bad", b"\xff", b"[]", b"{}",
                   b'{"device_id":"sensor01","temperature":true,"humidity":50}',
                   b'{"device_id":"sensor01","temperature":NaN,"humidity":50}',
                   b'{"device_id":"sensor01","temperature":28,"humidity":101}',
                   b'{"device_id":"sensor02","temperature":28,"humidity":50}']
        for payload in invalid:
            self.publish(client, "iot/lab/sensor01/data", payload)
        self.success(self.start("sensor_publisher_bai2.py", "--count", "1",
                                 "--temperature", "28.5", "--humidity", "65.2"))
        output = self.success(monitor)
        self.assertEqual(output.count("Bỏ qua dữ liệu không hợp lệ"), len(invalid))
        self.assertIn("Temperature: 28.5 C", output)

    def test_bai2_multiple_sensors(self):
        monitor = self.start("monitor_subscriber_bai2.py", "--all-devices", "--max-messages", "2")
        monitor.until("Đã subscribe:")
        for identifier in ("sensor01", "sensor02"):
            self.success(self.start("sensor_publisher_bai2.py", "--device-id", identifier, "--count", "1"))
        output = self.success(monitor)
        self.assertIn("Device: sensor01", output)
        self.assertIn("Device: sensor02", output)

    def test_bai3_on_off_invalid_input_and_exit(self):
        device = self.start("device_bai3.py", "--max-messages", "2")
        device.until("Trạng thái ban đầu")
        controller = self.start("controller_bai3.py")
        output = self.success(controller, "ON\nWRONG\nOFF\nEXIT\n")
        self.assertIn("Lệnh không hợp lệ", output)
        for status in ("ON", "OFF"):
            self.assertIn(f'Thiết bị đã phản hồi trạng thái {status}', output)
            self.assertIn(f'"device_id": "light01", "status": "{status}"', output)
        self.assertEqual(self.success(device).count("Đã gửi trạng thái:"), 2)

    def test_bai3_device_rejects_invalid_and_replies_to_repeated_valid_command(self):
        identifier = "light_invalid_test"
        device = self.start("device_bai3.py", "--device-id", identifier, "--max-messages", "2")
        device.until("Trạng thái ban đầu")
        client, messages = self.observer(f"iot/lab/{identifier}/status")
        self.assertEqual(json.loads(messages.get(timeout=4)[1])["status"], "OFF")
        self.publish(client, f"iot/lab/{identifier}/cmd", "TOGGLE")
        device.until("Lệnh không hợp lệ:")
        self.assertTrue(messages.empty(), "Lệnh sai không được publish trạng thái mới.")
        for _ in range(2):
            self.publish(client, f"iot/lab/{identifier}/cmd", "ON")
            self.assertEqual(json.loads(messages.get(timeout=4)[1])["status"], "ON")
        self.success(device)

    def test_bai3_retained_command_is_ignored(self):
        identifier = "light_retained_test"
        client, _ = self.observer()
        self.publish(client, f"iot/lab/{identifier}/cmd", "ON", retain=True)
        device = self.start("device_bai3.py", "--device-id", identifier, "--duration", "0.5")
        device.until("Bỏ qua lệnh retained cũ.")
        output = self.success(device)
        self.assertNotIn("Đã gửi trạng thái:", output)
        self.publish(client, f"iot/lab/{identifier}/cmd", b"", retain=True)

    def test_bai3_light_fan_pump_use_separate_topics(self):
        devices = [self.start("device_bai3.py", "--device-id", identifier, "--max-messages", "2")
                   for identifier in ("light01", "fan01", "pump01")]
        for device in devices:
            device.until("Trạng thái ban đầu")
        for identifier in ("light01", "fan01", "pump01"):
            output = self.success(self.start("controller_bai3.py", "--device-id", identifier),
                                  "ON\nOFF\nEXIT\n")
            self.assertIn(f'"device_id": "{identifier}", "status": "ON"', output)
            self.assertIn(f'"device_id": "{identifier}", "status": "OFF"', output)
        for device in devices:
            self.success(device)

    def test_bai3_no_device_times_out_instead_of_claiming_success(self):
        output_code, output = self.start("controller_bai3.py", "--device-id", "missing_device",
                                        "--response-timeout", "0.3").finish("ON\nEXIT\n")
        self.assertEqual(output_code, 1, output)
        self.assertIn("Chưa nhận được phản hồi mới", output)
        self.assertNotIn("Thiết bị đã phản hồi trạng thái", output)

    def test_bad_config_and_unreachable_broker_report_errors(self):
        child = self.start("sensor_publisher_bai2.py", "--port", "0", "--count", "1")
        code, output = child.finish()
        self.assertEqual(code, 2, output)
        self.assertIn("port phải là số nguyên", output)
        with socket.socket() as unused:
            unused.bind(("127.0.0.1", 0))
            dead_port = unused.getsockname()[1]
        child = self.start("sensor_publisher_bai2.py", "--port", dead_port, "--count", "1")
        code, output = child.finish()
        self.assertEqual(code, 1, output)
        self.assertIn("Lỗi:", output)
        self.assertNotIn("Traceback", output)


if __name__ == "__main__":
    unittest.main(verbosity=2)
