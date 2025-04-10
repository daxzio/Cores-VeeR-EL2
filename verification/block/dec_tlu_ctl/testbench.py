# Copyright (c) 2023 Antmicro
# SPDX-License-Identifier: Apache-2.0

import copy
import math
import os
import random
import struct
from dataclasses import dataclass

import csrs
import pyuvm
from cocotb.binary import BinaryValue
from cocotb.clock import Clock
from cocotb.triggers import (
    ClockCycles,
    Event,
    FallingEdge,
    First,
    Lock,
    RisingEdge,
    Timer,
)
from cocotb.types import Array, Range
from pyuvm import *

# ==============================================================================

csr_list = [getattr(csrs, mod) for mod in dir(csrs) if isinstance(getattr(csrs, mod), csrs.CSR)]


@dataclass
class TriggerAnyPktT:
    select: int = 0
    match: int = 0
    store: int = 0
    load: int = 0
    execute: int = 0
    m: int = 0
    tdata2: int = 0

    @staticmethod
    def get_from_dut(dut):
        trigger_pkt_any_select = int(dut.trigger_pkt_any_select.value)
        trigger_pkt_any_match = int(dut.trigger_pkt_any_match.value)
        trigger_pkt_any_store = int(dut.trigger_pkt_any_store.value)
        trigger_pkt_any_load = int(dut.trigger_pkt_any_load.value)
        trigger_pkt_any_execute = int(dut.trigger_pkt_any_execute.value)
        trigger_pkt_any_m = int(dut.trigger_pkt_any_m.value)
        trigger_pkt_any_tdata2 = int(dut.trigger_pkt_any_tdata2.value)
        return TriggerAnyPktT(
            trigger_pkt_any_select,
            trigger_pkt_any_match,
            trigger_pkt_any_store,
            trigger_pkt_any_load,
            trigger_pkt_any_execute,
            trigger_pkt_any_m,
            trigger_pkt_any_tdata2,
        )


class TlInputItem(uvm_sequence_item):
    """
    Trigger Logic output data
    """

    def __init__(
        self,
        pic_claimid=0,
        dec_csr_wrdata_r=0,
        mtdata1=0,
        mtdata2=0,
        mtsel=0,
        mdeau=0,
        csr_addr=0,
        dec_csr_rddata_d=0,
        ifu_ic_debug_rd_data=0,
        lsu_imprecise_error_addr_any=0,
    ):
        super().__init__("TlOutputItem")

        self.pic_claimid = pic_claimid
        self.dec_csr_wrdata_r = dec_csr_wrdata_r
        self.mtdata1 = mtdata1
        self.mtdata2 = mtdata2
        self.mtsel = mtsel
        self.csr_addr = csr_addr
        self.mtsel = mtsel
        self.mdeau = mdeau
        self.dec_csr_rddata_d = dec_csr_rddata_d
        self.ifu_ic_debug_rd_data = ifu_ic_debug_rd_data
        self.lsu_imprecise_error_addr_any = lsu_imprecise_error_addr_any

    def randomize(self, test):

        if test == "meihap":
            pic_claimid = ""
            # CSR
            dec_csr_wrdata_r = ""
            for _ in range(8):
                pic_claimid += random.choice(["0", "1"])

            for _ in range(22):
                dec_csr_wrdata_r += random.choice(["0", "1"])

            self.pic_claimid = int(pic_claimid, 2)
            self.dec_csr_wrdata_r = int(dec_csr_wrdata_r, 2) << 10
        elif test == "mhpme":
            value = ""
            for _ in range(10):
                value += random.choice(["0", "1"])
            self.dec_csr_wrdata_r = int(value, 2)
            self.csr_addr = random.choice(
                [
                    csrs.MHPME3,
                    csrs.MHPME4,
                    csrs.MHPME5,
                    csrs.MHPME6,
                ]
            )
        elif test == "mtdata":
            # bits 31:28 are hardcoded to 0x2
            mtdata1 = "0010"
            mtdata2 = ""
            mtsel = ""
            for _ in range(28):
                mtdata1 += random.choice(["0", "1"])
            # set DMODE (bit 27) to 0 so that the settigs are actually taken into account
            # in the list, bits are nubered from 0
            tmp = list(mtdata1)
            tmp[31 - 27] = "0"
            mtdata1 = "".join(tmp)
            self.mtdata1 = int(mtdata1, 2)
            for _ in range(32):
                mtdata2 += random.choice(["0", "1"])
            self.mtdata2 = int(mtdata2, 2)
            for _ in range(2):
                mtsel += random.choice(["0", "1"])
            self.mtsel = int(mtsel, 2)
        elif test == "mdseac":
            mdeau = ""
            for _ in range(32):
                mdeau += random.choice(["0", "1"])
            self.mdeau = int(mdeau, 2)
            value = ""
            for _ in range(32):
                value += random.choice(["0", "1"])
            self.lsu_imprecise_error_addr_any = int(value, 2)
            self.csr_addr = csrs.MDSEAC
        elif test == "csrs_access":
            value = ""
            for _ in range(32):
                value += random.choice(["0", "1"])
            self.dec_csr_wrdata_r = int(value, 2)
            self.csr_addr = random.choice(
                [
                    csrs.MHPMC3,
                    csrs.MHPMC3H,
                    csrs.MHPMC4,
                    csrs.MHPMC4H,
                    csrs.MHPMC5,
                    csrs.MHPMC5H,
                    csrs.MHPMC6,
                    csrs.MHPMC6H,
                    csrs.MCYCLEL,
                    csrs.MCYCLEH,
                    csrs.MINSTRETL,
                    csrs.MINSTRETH,
                    csrs.MICECT,
                    csrs.MICCMECT,
                    csrs.MDCCMECT,
                    csrs.MTVEC,
                    csrs.MHPME3,
                    csrs.MHPME4,
                    csrs.MHPME5,
                    csrs.MHPME6,
                    csrs.MRAC,
                    csrs.MEIPT,
                    csrs.MCOUNTINHIBIT,
                    csrs.MFDHT,
                    csrs.MEICURPL,
                    csrs.MFDC,
                ]
            )
        elif test == "debug_csrs_access":
            value = ""
            for _ in range(32):
                value += random.choice(["0", "1"])
            self.dec_csr_wrdata_r = int(value, 2)
            self.csr_addr = random.choice(
                [csrs.DICAD0, csrs.DICAD0H, csrs.DICAWICS, csrs.DPC, csrs.DCSR]
            )
        elif test == "debug_ic_cache":
            value = ""
            for _ in range(71):
                value += random.choice(["0", "1"])
            self.ifu_ic_debug_rd_data = int(value, 2)


class TlOutputItem(uvm_sequence_item):
    """
    Trigger Logic output data
    """

    def __init__(
        self,
        dec_tlu_meihap=0,
        mtdata1=0,
        mtdata2=0,
        mtsel=0,
        trigger_pkt_any=0,
        dec_csr_rddata_d=0,
        ifu_ic_debug_rd_data=0,
    ):
        super().__init__("TlOutputItem")
        self.dec_tlu_meihap = dec_tlu_meihap
        self.mtdata1 = mtdata1
        self.mtdata2 = mtdata2
        self.mtsel = mtsel
        self.trigger_pkt_any = trigger_pkt_any
        self.dec_csr_rddata_d = dec_csr_rddata_d
        self.ifu_ic_debug_rd_data = ifu_ic_debug_rd_data


# ==============================================================================


class TlDriver(uvm_driver):
    """
    Trigger Logic driver
    """

    def __init__(self, *args, **kwargs):
        self.dut = kwargs["dut"]
        del kwargs["dut"]
        super().__init__(*args, **kwargs)

    async def read_csr(self, address):
        self.dut.dec_csr_rdaddr_d.value = address
        await RisingEdge(self.dut.clk)

    async def write_csr(self, address, value):
        self.dut.dec_csr_wen_r.value = 0
        await RisingEdge(self.dut.clk)
        self.dut.dec_csr_wen_r.value = 1
        self.dut.dec_csr_wraddr_r.value = address
        self.dut.dec_csr_wrdata_r.value = value
        await RisingEdge(self.dut.clk)
        self.dut.dec_csr_wen_r.value = 0

    async def do_reset(self):
        self.dut.rst_l.value = 0
        await ClockCycles(self.dut.clk, 2)
        await FallingEdge(self.dut.clk)
        self.dut.rst_l.value = 1

    async def run_phase(self):

        while True:
            it = await self.seq_item_port.get_next_item()

            if isinstance(it, TlInputItem):
                test = ConfigDB().get(self, "", "TEST")
                if test == "meihap":
                    # write MEIVT
                    await self.write_csr(csrs.MEIVT, it.dec_csr_wrdata_r)
                    # write pic_claimid
                    await RisingEdge(self.dut.clk)
                    self.dut.pic_claimid.value = it.pic_claimid
                    self.dut.dec_csr_wen_r.value = 1
                    self.dut.dec_csr_wraddr_r.value = csrs.MEICPCT
                    await RisingEdge(self.dut.clk)
                    self.dut.dec_csr_wen_r.value = 0
                    # give two more cycles so that output monitor can catch the data on the outputs
                    await RisingEdge(self.dut.clk)
                    await RisingEdge(self.dut.clk)
                elif test == "mtdata":
                    # test triggers
                    await self.write_csr(csrs.MTSEL, it.mtsel)
                    await self.write_csr(csrs.MTDATA1, it.mtdata1)
                    await self.write_csr(csrs.MTDATA2, it.mtdata2)
                elif test == "mdseac":
                    # Write to unlock register
                    await self.write_csr(csrs.MDEAU, it.mdeau)
                    if self.dut.dut.mdseac_locked_f.value:
                        await FallingEdge(self.dut.mdseac_locked_f)
                    await RisingEdge(self.dut.clk)
                    # Write error
                    self.dut.lsu_imprecise_error_addr_any.value = it.lsu_imprecise_error_addr_any
                    self.dut.lsu_imprecise_error_store_any.value = 1
                    await RisingEdge(self.dut.clk)
                    self.dut.lsu_imprecise_error_store_any.value = 0
                    await RisingEdge(self.dut.clk)
                    # Read the MDSEAC register
                    await self.read_csr(it.csr_addr)
                    # Perform reset to clear the error
                    await self.do_reset()
                elif test in ["csrs_access", "mhpme"]:
                    # write a perf counter
                    await self.write_csr(it.csr_addr, it.dec_csr_wrdata_r)
                    # read it back
                    await self.read_csr(it.csr_addr)
                elif test == "debug_csrs_access":
                    # request halt
                    self.dut.dbg_halt_req.value = 1
                    for _ in range(2):
                        await RisingEdge(self.dut.clk)
                    # write a perf counter
                    await self.write_csr(it.csr_addr, it.dec_csr_wrdata_r)
                    # read it back
                    await self.read_csr(it.csr_addr)
                elif test == "debug_ic_cache":
                    self.dut.ifu_ic_debug_rd_data_valid.value = 1
                    self.dut.ifu_ic_debug_rd_data.value = it.ifu_ic_debug_rd_data
                    await RisingEdge(self.dut.clk)
                    self.dut.ifu_ic_debug_rd_data_valid.value = 0
                    self.dut.ifu_ic_debug_rd_data.value = 0
                    await self.read_csr(csrs.DICAD0)
                    await self.read_csr(csrs.DICAD0H)
                    await self.read_csr(csrs.DICAD1)
            else:
                raise RuntimeError("Unknown item '{}'".format(type(it)))

            self.seq_item_port.item_done()


class TlInputMonitor(uvm_component):
    """
    Monitor for Trigger Logic inputs
    """

    def __init__(self, *args, **kwargs):
        self.dut = kwargs["dut"]
        del kwargs["dut"]
        super().__init__(*args, **kwargs)

    def build_phase(self):
        self.ap = uvm_analysis_port("ap", self)

    async def run_phase(self):

        while True:
            test = ConfigDB().get(self, "", "TEST")

            if test == "meihap":
                # Wait for the driver to set the input signals
                await RisingEdge(self.dut.dec_csr_wen_r)
                await RisingEdge(self.dut.dec_csr_wen_r)
                # for _ in range(4):
                #    await RisingEdge(self.dut.clk)

                pic_claimid = int(self.dut.pic_claimid.value)
                meivt = int(self.dut.dec_csr_wrdata_r.value)

                self.ap.write(TlInputItem(pic_claimid=pic_claimid, dec_csr_wrdata_r=meivt))
            elif test == "mtdata":
                await RisingEdge(self.dut.dec_csr_wen_r)
                await RisingEdge(self.dut.clk)
                mtsel = int(self.dut.dec_csr_wrdata_r.value)
                await RisingEdge(self.dut.dec_csr_wen_r)
                await RisingEdge(self.dut.clk)
                mtdata1 = int(self.dut.dec_csr_wrdata_r.value)
                await RisingEdge(self.dut.dec_csr_wen_r)
                await RisingEdge(self.dut.clk)
                mtdata2 = int(self.dut.dec_csr_wrdata_r.value)
                self.ap.write(TlInputItem(mtdata1=mtdata1, mtdata2=mtdata2, mtsel=mtsel))
            elif test == "mdseac":
                await RisingEdge(self.dut.lsu_imprecise_error_store_any)
                await RisingEdge(self.dut.clk)
                csr_addr = int(self.dut.dec_csr_rdaddr_d.value)
                lsu_imprecise_error_addr_any = int(self.dut.lsu_imprecise_error_addr_any.value)
                self.ap.write(
                    TlInputItem(
                        csr_addr=csr_addr, lsu_imprecise_error_addr_any=lsu_imprecise_error_addr_any
                    )
                )
            elif test in ["csrs_access", "mhpme"]:
                # wait for reg write
                await RisingEdge(self.dut.dec_csr_wen_r)
                await RisingEdge(self.dut.clk)
                csr_addr = int(self.dut.dec_csr_wraddr_r.value)
                csr_value = int(self.dut.dec_csr_wrdata_r.value)
                self.ap.write(TlInputItem(csr_addr=csr_addr, dec_csr_wrdata_r=csr_value))
            elif test == "debug_csrs_access":
                # wait for debug mode
                for _ in range(2):
                    await RisingEdge(self.dut.clk)
                # wait for reg write
                await RisingEdge(self.dut.dec_csr_wen_r)
                await RisingEdge(self.dut.clk)
                csr_addr = int(self.dut.dec_csr_wraddr_r.value)
                csr_value = int(self.dut.dec_csr_wrdata_r.value)
                self.ap.write(TlInputItem(csr_addr=csr_addr, dec_csr_wrdata_r=csr_value))
            elif test == "debug_ic_cache":
                # wait for reg write
                await RisingEdge(self.dut.ifu_ic_debug_rd_data_valid)
                await RisingEdge(self.dut.clk)
                ic_debug_rd_data = int(self.dut.ifu_ic_debug_rd_data.value)
                self.ap.write(TlInputItem(ifu_ic_debug_rd_data=ic_debug_rd_data))


class TlOutputMonitor(uvm_component):
    """
    Monitor for Trigger Logic outputs
    """

    def __init__(self, *args, **kwargs):
        self.dut = kwargs["dut"]
        del kwargs["dut"]
        super().__init__(*args, **kwargs)

    def build_phase(self):
        self.ap = uvm_analysis_port("ap", self)

    async def run_phase(self):

        while True:
            test = ConfigDB().get(self, "", "TEST")

            if test == "meihap":
                # Wait for the driver to set the input signals and the data goes through
                await RisingEdge(self.dut.dec_csr_wen_r)
                await RisingEdge(self.dut.dec_csr_wen_r)
                for _ in range(2):
                    await RisingEdge(self.dut.clk)

                dec_tlu_meihap = int(self.dut.dec_tlu_meihap.value) << 2
                self.ap.write(TlOutputItem(dec_tlu_meihap))
            elif test == "mtdata":
                # wait for reg writes
                for _ in range(3):
                    await RisingEdge(self.dut.dec_csr_wen_r)
                # wait for the outputs
                for _ in range(2):
                    await RisingEdge(self.dut.clk)
                trigger_pkt_any = TriggerAnyPktT.get_from_dut(self.dut)
                self.ap.write(TlOutputItem(trigger_pkt_any=trigger_pkt_any))
            elif test == "mdseac":
                # Wait for when the error address is set
                await RisingEdge(self.dut.lsu_imprecise_error_store_any)
                # Wait for read
                for _ in range(3):
                    await RisingEdge(self.dut.clk)
                dec_csr_rddata_d = int(self.dut.dec_csr_rddata_d.value)
                self.ap.write(TlOutputItem(dec_csr_rddata_d=dec_csr_rddata_d))
            elif test in ["csrs_access", "mhpme"]:
                # wait for reg write
                await RisingEdge(self.dut.dec_csr_wen_r)
                # wait for read
                for _ in range(2):
                    await RisingEdge(self.dut.clk)
                dec_csr_rddata_d = int(self.dut.dec_csr_rddata_d.value)
                self.ap.write(TlOutputItem(dec_csr_rddata_d=dec_csr_rddata_d))
            elif test == "debug_csrs_access":
                # wait for debug mode
                for _ in range(2):
                    await RisingEdge(self.dut.clk)
                # wait for reg write
                await RisingEdge(self.dut.dec_csr_wen_r)
                # wait for read
                for _ in range(2):
                    await RisingEdge(self.dut.clk)
                dec_csr_rddata_d = int(self.dut.dec_csr_rddata_d.value)
                self.ap.write(TlOutputItem(dec_csr_rddata_d=dec_csr_rddata_d))
            elif test == "debug_ic_cache":
                # wait for read
                # read dicad0, dicad0h, and dicad1
                await RisingEdge(self.dut.ifu_ic_debug_rd_data_valid)
                for _ in range(2):
                    await RisingEdge(self.dut.clk)
                dicad0 = int(self.dut.dec_csr_rddata_d.value)
                await RisingEdge(self.dut.clk)
                dicad0h = int(self.dut.dec_csr_rddata_d.value)
                await RisingEdge(self.dut.clk)
                dicad1 = int(self.dut.dec_csr_rddata_d.value)
                ifu_ic_debug_rd_data = dicad0 | (dicad0h << 32) | (dicad1 << 64)
                self.ap.write(TlOutputItem(ifu_ic_debug_rd_data=ifu_ic_debug_rd_data))


# ==============================================================================


class TlScoreboard(uvm_component):
    """
    Trigger Logic scoreboard
    """

    def __init__(self, name, parent):
        super().__init__(name, parent)

        self.passed = None

    def build_phase(self):
        self.fifo_inp = uvm_tlm_analysis_fifo("fifo_inp", self)
        self.fifo_out = uvm_tlm_analysis_fifo("fifo_out", self)
        self.port_inp = uvm_get_port("port_inp", self)
        self.port_out = uvm_get_port("port_out", self)

    def connect_phase(self):
        self.port_inp.connect(self.fifo_inp.get_export)
        self.port_out.connect(self.fifo_out.get_export)

    def check_phase(self):  # noqa: C901
        # Get item pairs
        while True:
            got_inp, item_inp = self.port_inp.try_get()
            got_out, item_out = self.port_out.try_get()

            if not got_inp and got_out:
                self.logger.error("No input item for output item")
                self.passed = False
                break

            if got_inp and not got_out:
                self.logger.error("No output item for input item")
                self.passed = False
                break

            if not got_inp and not got_out:
                break

            if self.passed is None:
                self.passed = True

            test = ConfigDB().get(self, "", "TEST")

            if test == "meihap":
                sent_pic_claimid = item_inp.pic_claimid
                sent_meivt = item_inp.dec_csr_wrdata_r >> 12
                recv_pic_claimid = (item_out.dec_tlu_meihap >> 2) & 0xFF
                recv_meivt = item_out.dec_tlu_meihap >> 12

                if sent_pic_claimid != recv_pic_claimid:
                    self.logger.error(
                        "pic_claimid {} != {} (should be {})".format(
                            sent_pic_claimid, recv_pic_claimid, sent_pic_claimid
                        )
                    )
                    self.passed = False

                if sent_meivt != recv_meivt:
                    self.logger.error(
                        "meivt {} != {} (should be {})".format(sent_meivt, recv_meivt, sent_meivt)
                    )
                    self.passed = False
            elif test == "mtdata":
                tdata2_mask = 0xFFFFFFFF
                mtsel = item_inp.mtsel

                mtdata1_i = item_inp.mtdata1
                mtdata2_i = item_inp.mtdata2
                trigger_pkt_any = item_out.trigger_pkt_any

                select_i = (mtdata1_i >> 19) & 1
                match_i = (mtdata1_i >> 7) & 1
                store_i = (mtdata1_i >> 1) & 1
                load_i = ((mtdata1_i >> 0) & 1) & ~((mtdata1_i >> 19) & 1)
                execute_i = ((mtdata1_i >> 2) & 1) & ~((mtdata1_i >> 19) & 1)
                m_i = (mtdata1_i >> 6) & 1

                select_o = (trigger_pkt_any.select >> mtsel) & 1
                match_o = (trigger_pkt_any.match >> mtsel) & 1
                store_o = (trigger_pkt_any.store >> mtsel) & 1
                load_o = (trigger_pkt_any.load >> mtsel) & 1
                execute_o = (trigger_pkt_any.execute >> mtsel) & 1
                m_o = (trigger_pkt_any.m >> mtsel) & 1

                mtdata2_o = (trigger_pkt_any.tdata2 >> (mtsel * 32)) & tdata2_mask

                if mtdata2_i != mtdata2_o:
                    self.logger.error(
                        "mtdata2 {} != {} (should be {})".format(mtdata2_i, mtdata2_o, mtdata2_i)
                    )
                    self.passed = False

                if select_i != select_o:
                    self.logger.error(
                        "select {} != {} (should be {})".format(select_i, select_o, select_i)
                    )
                    self.passed = False

                if match_i != match_o:
                    self.logger.error(
                        "match {} != {} (should be {})".format(match_i, match_o, match_i)
                    )
                    self.passed = False

                if store_i != store_o:
                    self.logger.error(
                        "store {} != {} (should be {})".format(store_i, store_o, store_i)
                    )
                    self.passed = False

                if load_i != load_o:
                    self.logger.error("load {} != {} (should be {})".format(load_i, load_o, load_i))
                    self.passed = False

                if execute_i != execute_o:
                    self.logger.error(
                        "execute {} != {} (should be {})".format(execute_i, execute_o, execute_i)
                    )
                    self.passed = False

                if m_i != m_o:
                    self.logger.error("m {} != {} (should be {})".format(m_i, m_o, m_i))
                    self.passed = False

            elif test == "mhpme":
                csr = item_inp.csr_addr
                perf_reg_val_i = item_inp.dec_csr_wrdata_r
                perf_reg_val_o = item_out.dec_csr_rddata_d

                mhpme_lst = [csrs.MHPME3, csrs.MHPME4, csrs.MHPME5, csrs.MHPME6]
                c = [c for c in mhpme_lst if c == csr][0]
                perf_reg_val_i = c.out(perf_reg_val_i)

                if perf_reg_val_i != perf_reg_val_o:
                    self.logger.error(
                        "reg_val[{}] {} != {} (should be {})".format(
                            hex(csr), hex(perf_reg_val_i), hex(perf_reg_val_o), hex(perf_reg_val_i)
                        )
                    )
                    self.passed = False
            elif test == "mdseac":
                csr = item_inp.csr_addr
                error_val_i = item_inp.lsu_imprecise_error_addr_any
                mdseac_val_o = item_out.dec_csr_rddata_d

                if error_val_i != mdseac_val_o:
                    self.logger.error(
                        "reg_val[{}] {} != {} (should be {})".format(
                            hex(csr), hex(error_val_i), hex(mdseac_val_o), hex(error_val_i)
                        )
                    )
                    self.passed = False
            elif test == "csrs_access":
                csr = item_inp.csr_addr
                perf_reg_val_i = item_inp.dec_csr_wrdata_r
                perf_reg_val_o = item_out.dec_csr_rddata_d

                for c in csr_list:
                    if c == csr:
                        perf_reg_val_i = c.out(perf_reg_val_i)
                        break

                if perf_reg_val_i != perf_reg_val_o:
                    self.logger.error(
                        "reg_val[{}] {} != {} (should be {})".format(
                            hex(csr), hex(perf_reg_val_i), hex(perf_reg_val_o), hex(perf_reg_val_i)
                        )
                    )
                    self.passed = False

            elif test == "debug_csrs_access":
                csr = item_inp.csr_addr
                reg_val_i = item_inp.dec_csr_wrdata_r
                reg_val_o = item_out.dec_csr_rddata_d

                if csr == csrs.DCSR:
                    reg_val_i = csrs.DCSR.out(reg_val_i)
                elif csr == csrs.DPC:
                    reg_val_i = csrs.DPC.out(reg_val_i)
                elif csr == csrs.DICAWICS:
                    reg_val_i = csrs.DICAWICS.out(reg_val_i)

                if reg_val_i != reg_val_o:
                    self.logger.error(
                        "reg_val[{}] {} != {} (should be {})".format(
                            hex(csr), hex(reg_val_i), hex(reg_val_o), hex(reg_val_i)
                        )
                    )
                    self.passed = False
            elif test == "debug_ic_cache":
                ifu_ic_debug_rd_data_in = item_inp.ifu_ic_debug_rd_data
                ifu_ic_debug_rd_data_out = item_out.ifu_ic_debug_rd_data

                if ifu_ic_debug_rd_data_in != ifu_ic_debug_rd_data_out:
                    self.logger.error(
                        "read_data {} != {} (should be {})".format(
                            hex(ifu_ic_debug_rd_data_in),
                            hex(ifu_ic_debug_rd_data_out),
                            hex(ifu_ic_debug_rd_data_in),
                        )
                    )
                    self.passed = False

    def final_phase(self):
        if not self.passed:
            self.logger.critical("{} reports a failure".format(type(self)))
            assert False


# ==============================================================================


class TlSequence(uvm_sequence):

    def __init__(self, name, ops=None):
        super().__init__(name)

    async def body(self):
        count = ConfigDB().get(None, "", "TEST_ITERATIONS")
        test = ConfigDB().get(None, "", "TEST")

        for i in range(count):
            item = TlInputItem()
            item.randomize(test)

            await self.start_item(item)
            await self.finish_item(item)


# ==============================================================================


class BaseEnv(uvm_env):
    """
    Base PyUVM test environment
    """

    def build_phase(self):
        # Config
        ConfigDB().set(None, "*", "TEST_CLK_PERIOD", 1)
        ConfigDB().set(None, "*", "TEST_ITERATIONS", 5000)

        # Sequencers
        self.tl_seqr = uvm_sequencer("tl_seqr", self)

        # Driver
        self.tl_drv = TlDriver("tl_drv", self, dut=cocotb.top)

        # Monitors
        self.inp_mon = TlInputMonitor("inp_mon", self, dut=cocotb.top)
        self.out_mon = TlOutputMonitor("out_mon", self, dut=cocotb.top)

        # Scoreboard
        self.scoreboard = TlScoreboard("scoreboard", self)

    def connect_phase(self):
        self.tl_drv.seq_item_port.connect(self.tl_seqr.seq_item_export)

        self.inp_mon.ap.connect(self.scoreboard.fifo_inp.analysis_export)
        self.out_mon.ap.connect(self.scoreboard.fifo_out.analysis_export)


# ==============================================================================


class BaseTest(uvm_test):
    """
    Ba5e test for the module
    """

    def __init__(self, name, parent, env_class=BaseEnv):
        super().__init__(name, parent)
        self.env_class = env_class

        # Synchronize pyuvm logging level with cocotb logging level. Unclear
        # why it does not happen automatically.
        level = logging.getLevelName(os.environ.get("COCOTB_LOG_LEVEL", "INFO"))
        uvm_report_object.set_default_logging_level(level)

    def build_phase(self):
        self.env = self.env_class("env", self)

    def start_clock(self, name):
        period = ConfigDB().get(None, "", "TEST_CLK_PERIOD")
        sig = getattr(cocotb.top, name)
        clock = Clock(sig, period, units="ns")
        cocotb.start_soon(clock.start(start_high=False))

    async def do_reset(self):
        cocotb.top.rst_l.value = 0
        await ClockCycles(cocotb.top.clk, 2)
        await FallingEdge(cocotb.top.clk)
        cocotb.top.rst_l.value = 1

    async def run_phase(self):
        self.raise_objection()

        cocotb.top.rst_vec.value = 0
        cocotb.top.nmi_int.value = 0
        cocotb.top.nmi_vec.value = 0
        cocotb.top.i_cpu_halt_req.value = 0
        cocotb.top.i_cpu_run_req.value = 0
        cocotb.top.lsu_fastint_stall_any.value = 0
        cocotb.top.ifu_pmu_instr_aligned.value = 0
        cocotb.top.ifu_pmu_fetch_stall.value = 0
        cocotb.top.ifu_pmu_ic_miss.value = 0
        cocotb.top.ifu_pmu_ic_hit.value = 0
        cocotb.top.ifu_pmu_bus_error.value = 0
        cocotb.top.ifu_pmu_bus_busy.value = 0
        cocotb.top.ifu_pmu_bus_trxn.value = 0
        cocotb.top.dec_pmu_instr_decoded.value = 0
        cocotb.top.dec_pmu_decode_stall.value = 0
        cocotb.top.dec_pmu_presync_stall.value = 0
        cocotb.top.dec_pmu_postsync_stall.value = 0
        cocotb.top.lsu_store_stall_any.value = 0
        cocotb.top.dma_dccm_stall_any.value = 0
        cocotb.top.dma_iccm_stall_any.value = 0
        cocotb.top.exu_pmu_i0_br_misp.value = 0
        cocotb.top.exu_pmu_i0_br_ataken.value = 0
        cocotb.top.exu_pmu_i0_pc4.value = 0
        cocotb.top.lsu_pmu_bus_trxn.value = 0
        cocotb.top.lsu_pmu_bus_misaligned.value = 0
        cocotb.top.lsu_pmu_bus_error.value = 0
        cocotb.top.lsu_pmu_bus_busy.value = 0
        cocotb.top.lsu_pmu_load_external_m.value = 0
        cocotb.top.lsu_pmu_store_external_m.value = 0
        cocotb.top.dma_pmu_dccm_read.value = 0
        cocotb.top.dma_pmu_dccm_write.value = 0
        cocotb.top.dma_pmu_any_read.value = 0
        cocotb.top.dma_pmu_any_write.value = 0
        cocotb.top.lsu_fir_addr.value = 0
        cocotb.top.lsu_fir_error.value = 0
        cocotb.top.iccm_dma_sb_error.value = 0
        cocotb.top.lsu_single_ecc_error_incr.value = 0
        cocotb.top.dec_pause_state.value = 0
        cocotb.top.lsu_imprecise_error_store_any.value = 0
        cocotb.top.lsu_imprecise_error_load_any.value = 0
        cocotb.top.lsu_imprecise_error_addr_any.value = 0
        cocotb.top.dec_csr_wen_unq_d.value = 0
        cocotb.top.dec_csr_any_unq_d.value = 0
        cocotb.top.dec_csr_rdaddr_d.value = 0
        cocotb.top.dec_csr_wen_r.value = 0
        cocotb.top.dec_csr_rdaddr_r.value = 0
        cocotb.top.dec_csr_wraddr_r.value = 0
        cocotb.top.dec_csr_wrdata_r.value = 0
        cocotb.top.dec_csr_stall_int_ff.value = 0
        cocotb.top.dec_tlu_i0_valid_r.value = 0
        cocotb.top.exu_npc_r.value = 0
        cocotb.top.dec_tlu_i0_pc_r.value = 0
        cocotb.top.dec_illegal_inst.value = 0
        cocotb.top.dec_i0_decode_d.value = 0
        cocotb.top.exu_i0_br_hist_r.value = 0
        cocotb.top.exu_i0_br_error_r.value = 0
        cocotb.top.exu_i0_br_start_error_r.value = 0
        cocotb.top.exu_i0_br_valid_r.value = 0
        cocotb.top.exu_i0_br_mp_r.value = 0
        cocotb.top.exu_i0_br_middle_r.value = 0
        cocotb.top.exu_i0_br_way_r.value = 0
        cocotb.top.dbg_halt_req.value = 0
        cocotb.top.dbg_resume_req.value = 0
        cocotb.top.ifu_miss_state_idle.value = 0
        cocotb.top.lsu_idle_any.value = 0
        cocotb.top.dec_div_active.value = 0
        cocotb.top.ifu_ic_error_start.value = 0
        cocotb.top.ifu_iccm_rd_ecc_single_err.value = 0
        cocotb.top.ifu_ic_debug_rd_data.value = 0
        cocotb.top.ifu_ic_debug_rd_data_valid.value = 0
        cocotb.top.pic_claimid.value = 0
        cocotb.top.pic_pl.value = 0
        cocotb.top.mhwakeup.value = 0
        cocotb.top.mexintpend.value = 0
        cocotb.top.timer_int.value = 0
        cocotb.top.soft_int.value = 0
        cocotb.top.core_id.value = 0
        cocotb.top.mpc_debug_halt_req.value = 0
        cocotb.top.mpc_debug_run_req.value = 0
        cocotb.top.mpc_reset_run_req.value = 0

        # Start clocks
        self.start_clock("free_l2clk")
        self.start_clock("clk")

        # Issue reset
        await self.do_reset()

        # Wait some cycles
        await ClockCycles(cocotb.top.clk, 2)

        # Run the actual test
        await self.run()

        # Wait some cycles
        await ClockCycles(cocotb.top.clk, 10)

        self.drop_objection()

    async def run(self):
        raise NotImplementedError()
