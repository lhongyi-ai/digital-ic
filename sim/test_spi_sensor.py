"""Pin-level SPI peripheral models; no FPGA or sensor hardware is contacted."""
import json
import os
import random
from pathlib import Path

import cocotb
from cocotb.triggers import Timer


class SpiPeripheral:
    def __init__(self, dut, cpol, cpha, half_period):
        self.dut = dut
        self.cpol, self.cpha, self.half = cpol, cpha, half_period
        self.cs, self.sclk = 1, cpol
        self.index = self.rx_byte = self.tx_byte = 0
        self.tick_count = 0
        self.last_edge = None
        self.transactions = []
        self.current = []
        self.edge_total = 0
        dut.miso.value = 0

    def start(self):
        return 0

    def receive(self, value):
        return 0

    def update_drdy(self):
        pass

    def observe(self, reset=False):
        self.tick_count += 1
        cs, sclk = int(self.dut.cs_n.value), int(self.dut.sclk.value)
        if reset:
            self.cs, self.sclk = cs, sclk
            self.current = []
            self.index = 0
            self.last_edge = None
            self.update_drdy()
            return
        if self.cs and not cs:
            assert sclk == self.cpol, "Clock must be idle on selection"
            self.current = []
            self.index = self.rx_byte = 0
            self.tx_byte = self.start()
            self.last_edge = self.tick_count
            if not self.cpha:
                self.dut.miso.value = (self.tx_byte >> 7) & 1
        if not cs and sclk != self.sclk:
            assert self.last_edge is not None
            assert self.tick_count - self.last_edge >= self.half
            self.last_edge = self.tick_count
            self.edge_total += 1
            leading = sclk != self.cpol
            sample_edge = leading if not self.cpha else not leading
            if sample_edge:
                self.rx_byte = (self.rx_byte << 1) | int(self.dut.mosi.value)
                self.index += 1
                if self.index == 8:
                    self.current.append(self.rx_byte)
                    self.tx_byte = self.receive(self.rx_byte)
                    self.index = self.rx_byte = 0
            else:
                self.dut.miso.value = (self.tx_byte >> (7 - self.index)) & 1
        if not self.cs and cs:
            assert self.index == 0 and self.current, "CS ended inside a byte"
            assert sclk == self.cpol
            assert self.last_edge is not None and self.tick_count > self.last_edge
            self.transactions.append(list(self.current))
        self.cs, self.sclk = cs, sclk
        self.update_drdy()


class Harness:
    def __init__(self, dut, peripheral):
        self.dut, self.peripheral = dut, peripheral
        self.cycles = 0

    async def tick(self, reset=False):
        self.dut.clk.value = 0
        self.dut.rst.value = int(reset)
        await Timer(5, unit="ns")
        self.dut.clk.value = 1
        await Timer(5, unit="ns")
        self.peripheral.observe(reset)
        self.cycles += 1

    async def wait(self, predicate, limit=10000):
        for _ in range(limit):
            if predicate():
                return
            await self.tick()
        raise AssertionError("Timed out waiting for DUT condition")


def save_report(report):
    path = Path(os.environ["SPI_REPORT_FILE"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n")


@cocotb.test(skip=os.environ.get("SPI_TEST_KIND") != "master")
async def generic_master(dut):
    cpol, cpha = int(os.environ["SPI_CPOL"]), int(os.environ["SPI_CPHA"])
    half = int(os.environ["SPI_HALF_PERIOD"])
    rng = random.Random(345 + 10 * cpol + cpha + half)

    class Responder(SpiPeripheral):
        responses = []

        def start(self):
            self.response_index = 0
            return self.responses[0]

        def receive(self, value):
            self.response_index += 1
            return self.responses[self.response_index] if self.response_index < len(self.responses) else 0

    peripheral = Responder(dut, cpol, cpha, half)
    h = Harness(dut, peripheral)
    dut.tx_valid.value = 0
    dut.tx_data.value = 0
    dut.tx_last.value = 0
    await h.tick(reset=True)
    await h.tick()

    async def byte(value, last, response):
        dut.tx_data.value = value
        dut.tx_last.value = last
        dut.tx_valid.value = 1
        await h.wait(lambda: int(dut.tx_ready.value))
        await h.tick()
        dut.tx_valid.value = 0
        await h.wait(lambda: int(dut.rx_valid.value), limit=32 * half + 10)
        assert int(dut.rx_data.value) == response
        assert int(dut.cs_n.value) == int(last)
        assert int(dut.busy.value) == int(not last)

    packets = []
    total_bytes = 0
    for _ in range(24):
        data = [rng.randrange(256) for _ in range(rng.randrange(1, 9))]
        replies = [rng.randrange(256) for _ in data]
        peripheral.responses = replies
        for index, (value, response) in enumerate(zip(data, replies)):
            last = index == len(data)-1
            await byte(value, last, response)
            for _ in range(rng.randrange(1, 14)):
                await h.tick()
                assert int(dut.sclk.value) == cpol
                assert int(dut.cs_n.value) == int(last)
                assert not int(dut.rx_valid.value), "RX must be a one-cycle pulse"
        packets.append(data)
        total_bytes += len(data)
    assert peripheral.transactions == packets
    assert peripheral.edge_total == 16 * total_bytes

    # Reset during a byte, then demonstrate a new complete transaction works.
    peripheral.responses = [0x9A]
    dut.tx_data.value = 0xA6
    dut.tx_last.value = 1
    dut.tx_valid.value = 1
    await h.tick()
    dut.tx_valid.value = 0
    for _ in range(3 * half):
        await h.tick()
    await h.tick(reset=True)
    assert int(dut.cs_n.value) and not int(dut.rx_valid.value)
    assert not int(dut.busy.value)
    await h.tick()
    await byte(0x5C, True, 0x9A)
    assert peripheral.transactions[-1] == [0x5C]

    # Reset while CS is held between bytes must cancel the entire transaction.
    peripheral.responses = [0x34]
    await h.tick()
    await byte(0x12, False, 0x34)
    await h.tick(reset=True)
    assert int(dut.cs_n.value) and not int(dut.busy.value)
    save_report({"test": "generic_master", "cpol": cpol, "cpha": cpha,
                 "half_period": half, "packets": 24, "bytes": total_bytes,
                 "cycles": h.cycles, "reset_midbyte": "PASS",
                 "reset_between_bytes": "PASS", "cs_hold_and_clock_spacing": "PASS"})


class Adxl345Model(SpiPeripheral):
    def __init__(self, dut, half_period):
        super().__init__(dut, 1, 1, half_period)
        self.regs = {0: 0xE5}
        self.writes = []
        self.pending = self.overrun = False
        self.sample = (0, 0, 0)
        self.snapshot = [0] * 6

    def set_sample(self, sample):
        if self.pending:
            self.overrun = True
        self.sample = tuple(sample)
        self.pending = True
        self.update_drdy()

    def update_drdy(self):
        enabled = self.regs.get(0x2E, 0) & 0x80 and self.regs.get(0x2D, 0) & 8
        self.dut.drdy.value = int(bool(enabled and self.pending))

    def start(self):
        self.command = None
        self.data_count = 0
        return 0

    def register(self, address):
        if address == 0x30:
            return (0x80 if self.pending else 0) | int(self.overrun)
        if 0x32 <= address <= 0x37:
            return self.snapshot[address - 0x32]
        return self.regs.get(address, 0)

    def receive(self, value):
        if self.command is None:
            self.command = value
            self.read = bool(value & 0x80)
            self.multibyte = bool(value & 0x40)
            self.address = value & 0x3F
            self.snapshot = [byte for word in self.sample
                             for byte in (word & 255, (word >> 8) & 255)]
            return self.register(self.address) if self.read else 0
        if self.read:
            if self.address == 0x37:
                # DATA_READY and overrun clear on XYZ data reads, not INT_SOURCE.
                self.pending = self.overrun = False
        else:
            self.regs[self.address] = value
            self.writes.append((self.address, value))
        if self.multibyte:
            self.address = (self.address + 1) & 0x3F
        self.data_count += 1
        return self.register(self.address) if self.read else 0


@cocotb.test(skip=os.environ.get("SPI_TEST_KIND") != "sensor")
async def sensor_capture(dut):
    half = int(os.environ["SPI_HALF_PERIOD"])
    rate = int(os.environ.get("SPI_RATE_CODE", "13"))
    model = Adxl345Model(dut, half)
    h = Harness(dut, model)
    dut.enable.value = 0
    dut.drdy.value = 0
    dut.sample_ready.value = 0
    await h.tick(reset=True)
    for _ in range(12):
        await h.tick()
        assert int(dut.cs_n.value) and not int(dut.init_done.value)
    dut.enable.value = 1
    await h.wait(lambda: int(dut.init_done.value))
    assert int(dut.device_id.value) == 0xE5 and not int(dut.init_error.value)
    expected_writes = [(0x2D, 0), (0x2E, 0), (0x31, 8), (0x2C, rate),
                       (0x38, 0), (0x2F, 0), (0x2E, 0x80), (0x2D, 8)]
    assert model.writes == expected_writes

    def xyz():
        return tuple(int(getattr(dut, axis).value) & 0xFFFF for axis in ("x", "y", "z"))

    first = (-32768, 32767, -1)
    model.set_sample(first)
    await h.wait(lambda: int(dut.sample_valid.value))
    assert xyz() == tuple(v & 0xFFFF for v in first)
    held = xyz()
    held_cycle = int(dut.service_cycle.value)
    for _ in range(30):
        await h.tick()
        assert int(dut.sample_valid.value) and xyz() == held
        assert int(dut.service_cycle.value) == held_cycle
    model.set_sample((123, -456, 789))
    await h.wait(lambda: int(dut.samples_captured.value) == 2)
    assert int(dut.missed_service.value) == 1 and xyz() == held
    assert int(dut.service_cycle.value) == held_cycle
    assert int(dut.sensor_overruns.value) == 0
    dut.sample_ready.value = 1
    await h.tick()
    dut.sample_ready.value = 0
    assert not int(dut.sample_valid.value)

    # Overwrite an unread conversion. INT_SOURCE must be read before XYZ clears it.
    model.set_sample((1, 2, 3))
    model.set_sample((-4, -5, -6))
    await h.wait(lambda: int(dut.sample_valid.value))
    assert xyz() == tuple(v & 0xFFFF for v in (-4, -5, -6))
    assert int(dut.sensor_overruns.value) == 1
    assert int(dut.samples_captured.value) == 3
    dut.sample_ready.value = 1
    await h.tick()

    rng = random.Random(0xAD345)
    for _ in range(32):
        sample = tuple(rng.randrange(-32768, 32768) for _ in range(3))
        model.set_sample(sample)
        await h.wait(lambda: int(dut.sample_valid.value))
        assert xyz() == tuple(v & 0xFFFF for v in sample)
        await h.tick()
    assert int(dut.samples_captured.value) == 35
    assert int(dut.missed_service.value) == 1

    # FPGA-only reset during SPI leaves the external sensor's registers intact.
    model.set_sample((111, 222, 333))
    await h.wait(lambda: not int(dut.cs_n.value))
    for _ in range(5):
        await h.tick()
    await h.tick(reset=True)
    assert not int(dut.sample_valid.value) and not int(dut.init_done.value)
    assert int(dut.samples_captured.value) == 0
    await h.wait(lambda: int(dut.init_done.value))
    model.set_sample((-100, 200, -300))
    await h.wait(lambda: int(dut.sample_valid.value))
    assert xyz() == tuple(v & 0xFFFF for v in (-100, 200, -300))

    # Disconnected/wrong device cannot pass initialization merely by clocking SPI.
    model.regs[0] = 0
    await h.tick(reset=True)
    await h.wait(lambda: int(dut.init_error.value))
    assert not int(dut.init_done.value) and int(dut.device_id.value) == 0
    for _ in range(30):
        await h.tick()
        assert int(dut.cs_n.value) and not int(dut.sample_valid.value)
    save_report({"test": "sensor_capture", "half_period": half, "rate_code": rate,
                 "cycles": h.cycles, "initialization": "PASS", "signed_xyz_burst": "PASS",
                 "output_stall_and_drop_counter": "PASS", "sensor_overrun_flag": "PASS",
                 "random_samples": 32, "reset_mid_spi_and_reinitialize": "PASS",
                 "wrong_device_id_rejected": "PASS", "hardware_measured": False})
