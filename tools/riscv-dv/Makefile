SHELL           = /bin/bash -o pipefail

GCC_PREFIX     ?= riscv64-unknown-elf

RISCV_DV_PATH   = $(RV_ROOT)/third_party/riscv-dv
RISCV_DV_SIM   ?= pyflow
RISCV_DV_ISS   ?= spike
RISCV_DV_TEST  ?= riscv_arithmetic_basic_test
RISCV_DV_SEED  ?= 999
RISCV_DV_ITER  ?= 1
RISCV_DV_BATCH ?= 1
RISCV_DV_PRIV  ?= m

export RISCV_GCC ?=     $(GCC_PREFIX)-gcc
export RISCV_OBJCOPY ?= $(GCC_PREFIX)-objcopy
export RISCV_NM ?=      $(GCC_PREFIX)-nm

WORK_DIR       ?= work
TEST_DIR        = $(WORK_DIR)/test_$(RISCV_DV_TEST)
SIM_DIR         = $(TEST_DIR)/hdl_sim

ifeq ($(findstring u, $(RISCV_DV_PRIV)), u)
	VEER_EXTRA_CONF = "-set=user_mode=1 -set=smepmp=1"
else
	VEER_EXTRA_CONF = ""
endif

VEER_TARGET     = default
VEER_CONF       = -set build_axi4 \
                  -set reset_vec=0x80000000 \
                  -set fpga_optimize=0 \
                  $(VEER_EXTRA_CONF)

# Coverage reporting
ifeq ("$(COVERAGE)", "all")
    VERILATOR_COVERAGE = --coverage
else ifeq ("$(COVERAGE)", "branch")
    VERILATOR_COVERAGE = --coverage-line
else ifeq ("$(COVERAGE)", "toggle")
    VERILATOR_COVERAGE = --coverage-toggle
else ifeq ("$(COVERAGE)", "functional")
    VERILATOR_COVERAGE = --coverage-user
else ifneq ("$(COVERAGE)", "")
    $(error Unknown COVERAGE value '$(COVERAGE)')
endif

VERILATOR       = verilator
VERILATOR_CFLAGS= "-std=c++14"
VERILATOR_INC   = -I$(WORK_DIR) -I$(RV_ROOT)/testbench
VERILATOR_EXE   = $(RV_ROOT)/testbench/test_tb_top.cpp
# Set `TB_SILENT_FAIL` as generated instruction sequences may cause TB errors
# Errors are to be reported when execution flows discrepancy is encountered
VERILATOR_EXTRA_DEFS = +define+TB_SILENT_FAIL

HDL_FILES = $(WORK_DIR)/common_defines.vh \
            $(WORK_DIR)/el2_pdef.vh \
            $(RV_ROOT)/testbench/tb_top_pkg.sv \
            $(RV_ROOT)/testbench/tb_top.sv \
            $(RV_ROOT)/testbench/ahb_sif.sv \
            $(RV_ROOT)/design/include/el2_def.sv

# Determine verilator version if possible. Set the flag accordingly. Since
# version v5.006 -Wno-IMPLICIT was renamed to -Wno-IMPLICITSTATIC
VERILATOR_NOIMPLICIT := -Wno-IMPLICITSTATIC
VERILATOR_VERSION    := $(subst .,,$(word 2,$(shell $(VERILATOR) --version)))

ifeq ("$(.SHELLSTATUS)", "0")
    $(shell test $(VERILATOR_VERSION) -lt 5006)
    ifeq ("$(.SHELLSTATUS)", "0")
        VERILATOR_NOIMPLICIT := -Wno-IMPLICIT
    endif
endif

ISA_STRING = rv32imc_zicsr_zifencei_zba_zbb_zbc_zbs
# If compiled with U-mode we implicitly also compile with Smepmp in these tests
ifeq ($(findstring u, $(RISCV_DV_PRIV)), u)
	ISA_STRING := "${ISA_STRING}"_smepmp
endif

RISCV_DV_SIM_ARGS= \
    --priv ${RISCV_DV_PRIV}

# Append Renode-specific options
ifeq ("$(RISCV_DV_ISS)", "renode")
    ISS_OPTS += --cpu-type='VeeR_EL2'
    ISS_OPTS += --additional-cpu-parameters=''
    RISCV_DV_SIM_ARGS += \
        --iss_opts=" ${ISS_OPTS} "
endif

# riscv-dv args
RISCV_DV_ARGS = \
    --simulator $(RISCV_DV_SIM) \
    --test $(RISCV_DV_TEST) \
    --iss $(RISCV_DV_ISS) \
    --iss_timeout 120 \
    --start_seed $(RISCV_DV_SEED) \
    --iterations $(RISCV_DV_ITER) \
    --batch_size $(RISCV_DV_BATCH) \
    --isa ${ISA_STRING} \
    --mabi ilp32 \
    --custom_target $(PWD) \
    --testlist $(PWD)/testlist.yaml \
    -v -o $(TEST_DIR)

MAKEFILE  = $(abspath $(MAKEFILE_LIST))

all:
	@echo "Use 'make run'"

# Directory rules
$(WORK_DIR):
	mkdir -p $@

$(TEST_DIR):
	mkdir -p $@

# VeeR config
$(WORK_DIR)/defines.h: | $(WORK_DIR)
	BUILD_PATH=$(WORK_DIR) $(RV_ROOT)/configs/veer.config -target=$(VEER_TARGET) $(VEER_CONF)
	echo '`undef RV_ASSERT_ON' >> $(WORK_DIR)/common_defines.vh

# Verilated testbench rules
$(WORK_DIR)/verilator/Vtb_top.mk: $(WORK_DIR)/defines.h
	$(VERILATOR) --cc -CFLAGS $(VERILATOR_CFLAGS) $(VERILATOR_INC) $(VERILATOR_EXTRA_DEFS)\
        $(HDL_FILES) -f $(RV_ROOT)/testbench/flist --top-module tb_top \
		-exe $(VERILATOR_EXE) -Wno-WIDTH -Wno-UNOPTFLAT $(VERILATOR_NOIMPLICIT) --autoflush \
		--timing $(VERILATOR_COVERAGE) -fno-table -Wno-LATCH\
		-Mdir $(WORK_DIR)/verilator

$(WORK_DIR)/verilator/Vtb_top: $(WORK_DIR)/verilator/Vtb_top.mk
	$(MAKE) -C $(WORK_DIR)/verilator -f Vtb_top.mk OPT_FAST="-O3"

# Code generation
$(TEST_DIR)/generate.log: | $(TEST_DIR)
	PYTHONPATH=$(RISCV_DV_PATH)/pygen python3 $(RISCV_DV_PATH)/run.py $(RISCV_DV_ARGS) \
    --steps gen
	@touch $@

# Code patching & compilation
# remove _smepmp from ISA string, as it's not recognized by GCC
$(TEST_DIR)/compile.log: $(TEST_DIR)
	# Patch the code
	find $(TEST_DIR)/asm_test -name "*.S" -exec python3 code_fixup.py -i {} -o {} \;
	# Compile, simulate
	PYTHONPATH=$(RISCV_DV_PATH)/pygen python3 $(RISCV_DV_PATH)/run.py $(subst _smepmp,,$(RISCV_DV_ARGS)) \
    --steps gcc_compile 2>&1 | tee $@

# ISS simulation
$(TEST_DIR)/iss_sim.log: $(TEST_DIR)/compile.log | $(TEST_DIR)
	# Compile, simulate
	PYTHONPATH=$(RISCV_DV_PATH)/pygen python3 $(RISCV_DV_PATH)/run.py $(RISCV_DV_ARGS) $(RISCV_DV_SIM_ARGS) \
    --steps iss_sim 2>&1 | tee $@
	if grep -q ERROR $(TEST_DIR)/iss_sim.log; then \
		echo "ISS simulation failed"; \
		exit 1; \
	fi

# Tests are built by `run.py` script, they shouldn't be constructed by this Makefile directly
%.o:
	$(warning There are additional test files ($@), which will not be compiled. Hint: you might need to set "RISCV_DV_ITER" to a higher value)

# Generate symbols of executables
%.sym: %.o
	$(RISCV_NM) -B -n $< > $@

# Convert executables
%.hex: %.o
	$(RISCV_OBJCOPY) -O verilog $< $@

# HDL simulation
$(SIM_DIR)/%.log: $(TEST_DIR)/asm_test/%.hex $(TEST_DIR)/asm_test/%.sym $(WORK_DIR)/verilator/Vtb_top
	mkdir -p $(basename $@)
	cp $< $(basename $@)/program.hex
	cp $(basename $<).sym $(basename $@)/program.sym
	cd $(basename $@) && $(abspath $(WORK_DIR)/verilator/Vtb_top) --symbols program.sym --mailbox-sym tohost
	mv $(basename $@)/exec.log $@

# Log conversion rules
$(TEST_DIR)/spike_sim/%.csv: $(TEST_DIR)/spike_sim/%.log
	python3 $(RISCV_DV_PATH)/scripts/spike_log_to_trace_csv.py --log $< --csv $@

$(TEST_DIR)/renode_sim/%.csv: $(TEST_DIR)/renode_sim/%.log
	python3 $(RISCV_DV_PATH)/scripts/renode_log_to_trace_csv.py --log $< --csv $@

$(SIM_DIR)/%.csv: $(SIM_DIR)/%.log veer_log_to_trace_csv.py
	PYTHONPATH=$(RISCV_DV_PATH)/scripts python3 veer_log_to_trace_csv.py --log $< --csv $@

# Trace comparison
$(TEST_DIR)/comp_%.log: $(TEST_DIR)/$(RISCV_DV_ISS)_sim/%.csv $(SIM_DIR)/%.csv
	rm -rf $@
	python3 $(RISCV_DV_PATH)/scripts/instr_trace_compare.py \
		--csv_file_1 $(word 1, $^) --csv_name_1 ISS --csv_file_2 $(word 2, $^) --csv_name_2 HDL \
		--in_order_mode 1 --log $@ --verbose 10 --mismatch_print_limit 20
	cat $@

%.sv: %.py
	./$< $(RISCV_DV_PATH) $(RV_ROOT) > $@

generate:
	# Generate *.sv configuration
	#$(MAKE) -f $(MAKEFILE) riscv_core_setting.sv
	
	# Run RISC-V DV code generation
	$(MAKE) -f $(MAKEFILE) $(TEST_DIR)/generate.log

compile: $(TEST_DIR)/compile.log | $(TEST_DIR)
	find $(TEST_DIR)/asm_test -name "*.S" | sed 's|\.S|.hex|g' | xargs $(MAKE) -f $(MAKEFILE)

run:
	# Run RISC-V DV compilation and simulation
	$(MAKE) -f $(MAKEFILE) $(TEST_DIR)/iss_sim.log
	# Run HDL simulation(s) and trace comparison
	find $(TEST_DIR)/$(RISCV_DV_ISS)_sim -name "*.log" | sed 's|sim/|sim/../comp_|g' | xargs realpath --relative-to=$(PWD) | xargs $(MAKE) -f $(MAKEFILE)
	# Check for errors
	for F in $(TEST_DIR)/comp_*.log; do grep "\[PASSED\]" $$F; if [ $$? -ne 0 ]; then exit 255; fi; done

clean:
	rm -rf $(TEST_DIR)

fullclean:
	rm -rf $(WORK_DIR)

.PHONY: all generate run clean fullclean
.SECONDARY:
# Disable any default actions Makefile might invoke for suffix rules (e.g. invoking CC for our tests)
.SUFFIXES:
