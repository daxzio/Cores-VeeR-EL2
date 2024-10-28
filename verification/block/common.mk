# Copyright (c) 2023 Antmicro <www.antmicro.com>
# SPDX-License-Identifier: Apache-2.0

$(info $(shell cocotb-config --makefiles))

TOPLEVEL_LANG    = verilog
SIM             ?= verilator
WAVES           ?= 1

# Paths
CURDIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
CFGDIR := $(abspath $(CURDIR)/snapshots/default)
CONFIG := $(abspath $(CURDIR)/../../configs)

# Set pythonpath so that tests can access common modules
export PYTHONPATH := $(CURDIR)/common

# Common sources
COMMON_SOURCES  = $(CFGDIR)/common_defines.vh
COMMON_SOURCES += $(CFGDIR)/el2_pdef.vh
COMMON_SOURCES += $(SRCDIR)/include/el2_def.sv
COMMON_SOURCES += $(SRCDIR)/lib/beh_lib.sv

VERILOG_SOURCES := $(COMMON_SOURCES) $(VERILOG_SOURCES)

# Coverage reporting
COVERAGE_TYPE ?= ""
ifeq ("$(COVERAGE_TYPE)", "all")
    VERILATOR_COVERAGE = --coverage
else ifeq ("$(COVERAGE_TYPE)", "branch")
    VERILATOR_COVERAGE = --coverage-line
else ifeq ("$(COVERAGE_TYPE)", "toggle")
    VERILATOR_COVERAGE = --coverage-toggle
else ifeq ("$(COVERAGE_TYPE)", "functional")
    VERILATOR_COVERAGE = --coverage-user
else
    VERILATOR_COVERAGE = ""
endif

ifeq ($(SIM), verilator)
    COMPILE_ARGS += --coverage-max-width 20000
    COMPILE_ARGS += --timing
    COMPILE_ARGS += -Wall
    COMPILE_ARGS += $(CURDIR)/config.vlt

    EXTRA_ARGS   += --trace --trace-structs
    EXTRA_ARGS   += $(VERILATOR_COVERAGE)
    EXTRA_ARGS   += -I$(CFGDIR) -Wno-DECLFILENAME

    # Include test specific Verilator config if it exists
    ifneq ("$(wildcard $(TEST_DIR)/config.vlt)","")
        COMPILE_ARGS += $(TEST_DIR)/config.vlt
    endif
else ifeq ($(SIM), vcs)
    EXTRA_ARGS   += +incdir+$(CFGDIR) -assert svaext -cm line+cond+fsm+tgl+branch +vcs+lic+wait
endif


COCOTB_HDL_TIMEUNIT         = 1ns
COCOTB_HDL_TIMEPRECISION    = 10ps

# Build directory
ifneq ($(COVERAGE_TYPE),)
    SIM_BUILD := sim-build-$(COVERAGE_TYPE)
endif

include $(shell cocotb-config --makefiles)/Makefile.sim

ifeq ($(PMP_TEST),)
    EXTRA_CONFIG_OPTS = ""
else
    EXTRA_CONFIG_OPTS = "-set=pmp_entries=64"
endif

# Rules for generating VeeR config
$(CFGDIR)/common_defines.vh:
	cd $(CURDIR) && $(CONFIG)/veer.config -fpga_optimize=0 $(EXTRA_CONFIG_OPTS)
