"""Kiểm thử với các server là tiến trình riêng, truyền CoAP qua UDP loopback."""

import asyncio
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import socket
import subprocess
import sys
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import aiocoap
from coap_common import client_context, json_message, read_json, request, uri
from monitor_client_bai2 import display_sensor


class CoAPIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        self.args = SimpleNamespace(host="127.0.0.1", port=port, timeout=2)
        self.context = await client_context()
        self.processes = []
        self.extra_contexts = []
        self.observer_tasks = []
        self.observations = []

    async def asyncTearDown(self):
        for observation in self.observations:
            if not observation.cancelled:
                observation.cancel()
        for task in self.observer_tasks:
            task.cancel()
        await asyncio.gather(*self.observer_tasks, return_exceptions=True)
        await self.context.shutdown()
        for context in self.extra_contexts:
            await context.shutdown()
        for process in self.processes:
            if process.poll() is None:
                process.terminate()
            output, _ = await asyncio.to_thread(process.communicate, timeout=5)
            self.assertNotIn("Traceback", output)

    def spawn(self, script, *options, stdin=None):
        process = subprocess.Popen(
            [sys.executable, "-X", "utf8", "-u", str(ROOT / script),
             "--host", self.args.host, "--port", str(self.args.port), *options],
            stdin=stdin, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", cwd=ROOT)
        self.processes.append(process)
        return process

    async def wait_line(self, process, target):
        lines = []
        async with asyncio.timeout(8):
            while True:
                line = await asyncio.to_thread(process.stdout.readline)
                lines.append(line)
                if target in line:
                    return "".join(lines)
                if not line:
                    self.fail(f"Tiến trình dừng trước {target}: {''.join(lines)}")

    async def server(self, script, *options, ready="SERVER READY"):
        process = self.spawn(script, *options)
        await self.wait_line(process, ready)
        return process

    async def get(self, path):
        return await request(self.context, self.args, aiocoap.GET, path)

    async def put(self, command, identifier="light01", raw=None, content_format=50):
        payload = raw if raw is not None else json.dumps(
            {"device_id": identifier, "command": command}).encode()
        return await request(self.context, self.args, aiocoap.PUT,
                             "iot/lab/light01/status", payload, content_format)

    async def observe(self, context):
        pending = context.request(aiocoap.Message(
            code=aiocoap.GET, uri=uri(self.args, "iot/lab/light01/status"), observe=0))
        self.observations.append(pending.observation)
        response = await asyncio.wait_for(pending.response, 2)
        self.assertIsNotNone(response.opt.observe)
        self.assertEqual(read_json(response)["status"], "OFF")
        queue = asyncio.Queue()

        async def collect():
            async for notification in pending.observation:
                await queue.put(notification)

        self.observer_tasks.append(asyncio.create_task(collect()))
        return queue

    async def test_message_get_post_latest_and_errors(self):
        server = await self.server("coap_server_bai1.py")
        path = "iot/lab/message"
        initial = await self.get(path)
        self.assertEqual(initial.code, aiocoap.CONTENT)
        self.assertEqual(initial.payload.decode(), "Xin chao tu CoAP Server")
        payload = "Xin chao tu CoAP Client - TEST001 - Nguyễn Văn A".encode()
        for _ in range(3):
            response = await request(self.context, self.args, aiocoap.POST, path, payload, 0)
            self.assertEqual(response.code, aiocoap.CHANGED)
        self.assertEqual((await self.get(path)).payload, payload)
        self.assertEqual((await self.get("missing")).code, aiocoap.NOT_FOUND)
        self.assertEqual((await request(self.context, self.args, aiocoap.PUT, path)).code,
                         aiocoap.METHOD_NOT_ALLOWED)
        for bad in (b"", b"\xff"):
            self.assertEqual((await request(self.context, self.args, aiocoap.POST, path, bad)).code,
                             aiocoap.BAD_REQUEST)
        server.terminate()
        output, _ = await asyncio.to_thread(server.communicate, timeout=5)
        self.assertEqual(output.count("POST request received"), 3)
        self.assertIn("Time:", output)

    async def test_message_client_cli(self):
        await self.server("coap_server_bai1.py")
        client = self.spawn("coap_client_bai1.py", "--name", "Sinh vien test", "--student-id", "TEST001", "--count", "3")
        output, _ = await asyncio.to_thread(client.communicate, timeout=8)
        self.assertEqual(client.returncode, 0, output)
        self.assertIn("2.05 Content", output)
        self.assertEqual(output.count("2.04 Changed"), 3)

    async def test_sensor_defaults_random_updates_and_polling(self):
        server = await self.server("sensor_server_bai2.py")
        for _ in range(2):
            data = read_json(await self.get("iot/lab/sensor01/data"))
            self.assertEqual(set(data), {"device_id", "temperature", "humidity"})
            self.assertTrue(20 <= data["temperature"] <= 40)
            self.assertTrue(30 <= data["humidity"] <= 80)
        monitor = self.spawn("monitor_client_bai2.py", "--count", "2")
        start = asyncio.get_running_loop().time()
        output, _ = await asyncio.to_thread(monitor.communicate, timeout=10)
        self.assertEqual(monitor.returncode, 0, output)
        self.assertEqual(output.count("Received sensor data"), 2)
        self.assertGreaterEqual(asyncio.get_running_loop().time() - start, 2.9)
        # Giá trị cập nhật từ timer server ngay cả khi không có GET.
        self.assertIn("Sensor updated:", await self.wait_line(server, "Sensor updated:"))

    async def test_sensor_fixed_values_and_selected_device(self):
        await self.server("sensor_server_bai2.py", "--device-id", "sensor02",
                          "--temperature", "36.1", "--humidity", "38.7")
        monitor = self.spawn("monitor_client_bai2.py", "--device-id", "sensor02", "--count", "1")
        output, _ = await asyncio.to_thread(monitor.communicate, timeout=8)
        self.assertEqual(monitor.returncode, 0, output)
        self.assertIn("Device: sensor02", output)
        self.assertIn("CANH BAO: Nhiet do cao", output)
        self.assertIn("CANH BAO: Do am thap", output)

    async def test_sensor_thresholds_and_invalid_payloads(self):
        for temperature, humidity, hot, dry in ((35, 40, False, False), (35.1, 40, True, False),
                                               (35, 39.9, False, True), (36, 38, True, True)):
            with self.subTest(temperature=temperature, humidity=humidity):
                response = json_message({"device_id": "sensor01", "temperature": temperature, "humidity": humidity})
                output = io.StringIO()
                with redirect_stdout(output):
                    display_sensor(response, "sensor01")
                self.assertEqual("CANH BAO: Nhiet do cao" in output.getvalue(), hot)
                self.assertEqual("CANH BAO: Do am thap" in output.getvalue(), dry)
        for data in ([], {}, {"device_id": "sensor01", "temperature": True, "humidity": 50},
                     {"device_id": "sensor01", "temperature": float("nan"), "humidity": 50}):
            with self.assertRaises(ValueError):
                display_sensor(json_message(data), "sensor01")

    async def test_light_two_observers_changes_only_and_invalid_put(self):
        await self.server("light_server_bai3.py", ready="Resource:")
        second = await client_context()
        self.extra_contexts.append(second)
        queues = [await self.observe(self.context), await self.observe(second)]
        for command in ("ON", "OFF"):
            response = await self.put(command)
            self.assertEqual(response.code, aiocoap.CHANGED)
            for queue in queues:
                changed = await asyncio.wait_for(queue.get(), 2)
                self.assertEqual(read_json(changed)["status"], command)
            self.assertEqual(read_json(await self.get("iot/lab/light01/status"))["status"], command)
            self.assertEqual((await self.put(command)).code, aiocoap.CHANGED)
            for queue in queues:
                with self.assertRaises(asyncio.TimeoutError):
                    await asyncio.wait_for(queue.get(), 0.2)
        for options in ({"command": "BAD"}, {"command": "ON", "identifier": "fan01"},
                        {"command": "ON", "raw": b"bad json"}, {"command": "ON", "raw": b"[]"},
                        {"command": "ON", "raw": b"\xff"}):
            self.assertEqual((await self.put(**options)).code, aiocoap.BAD_REQUEST)
        self.assertEqual((await self.put("ON", content_format=0)).code, aiocoap.UNSUPPORTED_CONTENT_FORMAT)
        self.assertEqual(read_json(await self.get("iot/lab/light01/status"))["status"], "OFF")

    async def test_controller_and_monitor_cli(self):
        await self.server("light_server_bai3.py", ready="Resource:")
        monitor = self.spawn("light_monitor_bai3.py", "--max-notifications", "3")
        initial = await self.wait_line(monitor, "Status: OFF")
        self.assertIn("Observe registration successful", initial)
        for command in ("ON", "OFF"):
            controller = self.spawn("light_controller_bai3.py", stdin=subprocess.PIPE)
            output, _ = await asyncio.to_thread(controller.communicate, f"WRONG\n{command}\nSTATUS\nEXIT\n", timeout=8)
            self.assertEqual(controller.returncode, 0, output)
            self.assertIn("Lệnh không hợp lệ", output)
            self.assertIn("2.04 Changed", output)
            self.assertIn(f'"status":"{command}"', output)
            update = await self.wait_line(monitor, f"Status: {command}")
            self.assertIn("State Updated", update)
        output, _ = await asyncio.to_thread(monitor.communicate, timeout=8)
        self.assertEqual(monitor.returncode, 0, output)

    async def test_server_unavailable_client_exits_with_error(self):
        client = self.spawn("coap_client_bai1.py", "--name", "Test", "--student-id", "TEST001", "--timeout", "0.3")
        output, _ = await asyncio.to_thread(client.communicate, timeout=8)
        self.assertEqual(client.returncode, 1, output)
        self.assertIn("Lỗi:", output)
        self.assertNotIn("Traceback", output)


if __name__ == "__main__":
    unittest.main()
