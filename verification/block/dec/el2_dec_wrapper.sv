module el2_dec_wrapper
  import el2_pkg::*;
#(
    `include "el2_param.vh"
) (
    input logic clk,                          // Clock only while core active.  Through one clock header.  For flops with    second clock header built in.  Connected to ACTIVE_L2CLK.
    input logic active_clk,                   // Clock only while core active.  Through two clock headers. For flops without second clock header built in.
    input logic free_clk,                     // Clock always.                  Through two clock headers. For flops without second clock header built in.
    input logic free_l2clk,                   // Clock always.                  Through one clock header.  For flops with    second header built in.

    input logic lsu_fastint_stall_any,        // needed by lsu for 2nd pass of dma with ecc correction, stall next cycle

    output logic dec_extint_stall,  // Stall on external interrupt

    output logic dec_i0_decode_d,    // Valid instruction at D-stage and not blocked
    output logic dec_pause_state_cg, // to top for active state clock gating

    output logic dec_tlu_core_empty,

    input logic        rst_l,   // reset, active low
    // rst_vec is supposed to be connected to a constant in the top level
    /*pragma coverage off*/
    input logic [31:1] rst_vec, // reset vector, from core pins
    /*pragma coverage on*/

    input logic        nmi_int,  // NMI pin
    // nmi_vec is supposed to be connected to a constant in the top level
    /*pragma coverage off*/
    input logic [31:1] nmi_vec,  // NMI vector, from pins
    /*pragma coverage on*/

    input logic i_cpu_halt_req,  // Asynchronous Halt request to CPU
    input logic i_cpu_run_req,   // Asynchronous Restart request to CPU

    output logic o_cpu_halt_status,  // Halt status of core (pmu/fw)
    output logic o_cpu_halt_ack,  // Halt request ack
    output logic o_cpu_run_ack,  // Run request ack
    output logic o_debug_mode_status,         // Core to the PMU that core is in debug mode. When core is in debug mode, the PMU should refrain from sendng a halt or run request

    /*pragma coverage off*/
    input logic [31:4] core_id,  // CORE ID
    /*pragma coverage on*/

    // external MPC halt/run interface
    input  logic mpc_debug_halt_req,  // Async halt request
    input  logic mpc_debug_run_req,   // Async run request
    input  logic mpc_reset_run_req,   // Run/halt after reset
    output logic mpc_debug_halt_ack,  // Halt ack
    output logic mpc_debug_run_ack,   // Run ack
    output logic debug_brkpt_status,  // debug breakpoint

    input logic exu_pmu_i0_br_misp,    // slot 0 branch misp
    input logic exu_pmu_i0_br_ataken,  // slot 0 branch actual taken
    input logic exu_pmu_i0_pc4,        // slot 0 4 byte branch


    input logic lsu_nonblock_load_valid_m,  // valid nonblock load at m
    input logic [pt.LSU_NUM_NBLOAD_WIDTH-1:0] lsu_nonblock_load_tag_m,  // -> corresponding tag
    input logic lsu_nonblock_load_inv_r,  // invalidate request for nonblock load r
    input logic [pt.LSU_NUM_NBLOAD_WIDTH-1:0] lsu_nonblock_load_inv_tag_r,  // -> corresponding tag
    input logic lsu_nonblock_load_data_valid,  // valid nonblock load data back
    input logic lsu_nonblock_load_data_error,  // nonblock load bus error
    input logic [pt.LSU_NUM_NBLOAD_WIDTH-1:0] lsu_nonblock_load_data_tag,  // -> corresponding tag
    input logic [31:0] lsu_nonblock_load_data,  // nonblock load data

    input logic lsu_pmu_bus_trxn,          // D side bus transaction
    input logic lsu_pmu_bus_misaligned,    // D side bus misaligned
    input logic lsu_pmu_bus_error,         // D side bus error
    input logic lsu_pmu_bus_busy,          // D side bus busy
    input logic lsu_pmu_misaligned_m,      // D side load or store misaligned
    input logic lsu_pmu_load_external_m,   // D side bus load
    input logic lsu_pmu_store_external_m,  // D side bus store
    input logic dma_pmu_dccm_read,         // DMA DCCM read
    input logic dma_pmu_dccm_write,        // DMA DCCM write
    input logic dma_pmu_any_read,          // DMA read
    input logic dma_pmu_any_write,         // DMA write

    input logic [31:1] lsu_fir_addr,  // Fast int address
    input logic [ 1:0] lsu_fir_error, // Fast int lookup error

    input logic ifu_pmu_instr_aligned,  // aligned instructions
    input logic ifu_pmu_fetch_stall,    // fetch unit stalled
    input logic ifu_pmu_ic_miss,        // icache miss
    input logic ifu_pmu_ic_hit,         // icache hit
    input logic ifu_pmu_bus_error,      // Instruction side bus error
    input logic ifu_pmu_bus_busy,       // Instruction side bus busy
    input logic ifu_pmu_bus_trxn,       // Instruction side bus transaction

    input logic ifu_ic_error_start,         // IC single bit error
    input logic ifu_iccm_rd_ecc_single_err, // ICCM single bit error

    input logic [ 3:0] lsu_trigger_match_m,
    input logic        dbg_cmd_valid,        // debugger abstract command valid
    input logic        dbg_cmd_write,        // command is a write
    input logic [ 1:0] dbg_cmd_type,         // command type
    input logic [31:0] dbg_cmd_addr,         // command address
    input logic [ 1:0] dbg_cmd_wrdata,       // command write data, for fence/fence_i


    input logic       ifu_i0_icaf,      // icache access fault
    input logic [1:0] ifu_i0_icaf_type, // icache access fault type

    input logic ifu_i0_icaf_second,  // i0 has access fault on second 2B of 4B inst
    input logic ifu_i0_dbecc,        // icache/iccm double-bit error

    input logic lsu_idle_any,  // lsu idle for halting

    input logic        [pt.BTB_ADDR_HI:pt.BTB_ADDR_LO] ifu_i0_bp_index,  // BP index
    input logic        [          pt.BHT_GHR_SIZE-1:0] ifu_i0_bp_fghr,   // BP FGHR
    input logic        [         pt.BTB_BTAG_SIZE-1:0] ifu_i0_bp_btag,   // BP tag
    input logic        [      $clog2(pt.BTB_SIZE)-1:0] ifu_i0_fa_index,  // Fully associt btb index

    input logic               lsu_single_ecc_error_incr, // LSU inc SB error counter

    input logic        lsu_imprecise_error_load_any,   // LSU imprecise load bus error
    input logic        lsu_imprecise_error_store_any,  // LSU imprecise store bus error
    input logic [31:0] lsu_imprecise_error_addr_any,   // LSU imprecise bus error address

    input logic [31:0] exu_div_result,  // final div result
    input logic        exu_div_wren,    // Divide write enable to GPR

    input logic [31:0] exu_csr_rs1_x,  // rs1 for csr instruction

    input logic [31:0] lsu_result_m,      // load result
    input logic [31:0] lsu_result_corr_r, // load result - corrected load data

    input logic lsu_load_stall_any,   // This is for blocking loads
    input logic lsu_store_stall_any,  // This is for blocking stores
    input logic dma_dccm_stall_any,   // stall any load/store at decode, pmu event
    input logic dma_iccm_stall_any,   // iccm stalled, pmu event

    input logic iccm_dma_sb_error,  // ICCM DMA single bit error

    input logic exu_flush_final,  // slot0 flush

    input logic [31:1] exu_npc_r,  // next PC

    input logic [31:0] exu_i0_result_x,  // alu result x


    input logic        ifu_i0_valid,  // fetch valids to instruction buffer
    input logic [31:0] ifu_i0_instr,  // fetch inst's to instruction buffer
    input logic [31:1] ifu_i0_pc,     // pc's for instruction buffer
    input logic        ifu_i0_pc4,    // indication of 4B or 2B for corresponding inst
    input logic [31:1] exu_i0_pc_x,   // pc's for e1 from the alu's

    input logic mexintpend,  // External interrupt pending
    input logic timer_int,   // Timer interrupt pending (from pin)
    input logic soft_int,    // Software interrupt pending (from pin)

    input logic [7:0] pic_claimid,  // PIC claimid
    input logic [3:0] pic_pl,       // PIC priv level
    input logic       mhwakeup,     // High priority wakeup

    output logic [3:0] dec_tlu_meicurpl,  // to PIC, Current priv level
    output logic [3:0] dec_tlu_meipt,     // to PIC

    input logic [70:0] ifu_ic_debug_rd_data,  // diagnostic icache read data
    input logic ifu_ic_debug_rd_data_valid,  // diagnostic icache read data valid
    output el2_cache_debug_pkt_t dec_tlu_ic_diag_pkt, // packet of DICAWICS, DICAD0/1, DICAGO info for icache diagnostics


    // Debug start
    input logic dbg_halt_req,        // DM requests a halt
    input logic dbg_resume_req,      // DM requests a resume
    input logic ifu_miss_state_idle, // I-side miss buffer empty

    output logic        dec_tlu_dbg_halted,        // Core is halted and ready for debug command
    output logic        dec_tlu_debug_mode,        // Core is in debug mode
    output logic        dec_tlu_resume_ack,        // Resume acknowledge
    output logic        dec_tlu_flush_noredir_r,   // Tell fetch to idle on this flush
    output logic        dec_tlu_mpc_halted_only,   // Core is halted only due to MPC
    output logic        dec_tlu_flush_leak_one_r,  // single step
    output logic        dec_tlu_flush_err_r,       // iside perr/ecc rfpc
    output logic [31:2] dec_tlu_meihap,            // Fast ext int base

    output logic dec_debug_wdata_rs1_d,  // insert debug write data into rs1 at decode

    output logic [31:0] dec_dbg_rddata,  // debug command read data

    output logic dec_dbg_cmd_done,  // abstract command is done
    output logic dec_dbg_cmd_fail,  // abstract command failed (illegal reg address)

    // el2_trigger_pkt_t broken down to allow driving from cocotb by both SIMs
    // info needed by debug trigger blocks
    output logic [3:0]       trigger_pkt_any_select,
    output logic [3:0]       trigger_pkt_any_match,
    output logic [3:0]       trigger_pkt_any_store,
    output logic [3:0]       trigger_pkt_any_load,
    output logic [3:0]       trigger_pkt_any_execute,
    output logic [3:0]       trigger_pkt_any_m,
    output logic [3:0][31:0] trigger_pkt_any_tdata2,

    output logic       dec_tlu_force_halt,       // halt has been forced
    // Debug end
    // branch info from pipe0 for errors or counter updates
    input  logic [1:0] exu_i0_br_hist_r,         // history
    input  logic       exu_i0_br_error_r,        // error
    input  logic       exu_i0_br_start_error_r,  // start error
    input  logic       exu_i0_br_valid_r,        // valid
    input  logic       exu_i0_br_mp_r,           // mispredict
    input  logic       exu_i0_br_middle_r,       // middle of bank

    // branch info from pipe1 for errors or counter updates

    input logic exu_i0_br_way_r,  // way hit or repl

    output logic        dec_i0_rs1_en_d,  // Qualify GPR RS1 data
    output logic        dec_i0_rs2_en_d,  // Qualify GPR RS2 data
    output logic [31:0] gpr_i0_rs1_d,     // gpr rs1 data
    output logic [31:0] gpr_i0_rs2_d,     // gpr rs2 data

    output logic [31:0] dec_i0_immed_d,    // immediate data
    output logic [12:1] dec_i0_br_immed_d, // br immediate data

    output el2_alu_pkt_t i0_ap,  // alu packet

    output logic dec_i0_alu_decode_d,  // schedule on D-stage alu
    output logic dec_i0_branch_d,      // Branch in D-stage

    output logic dec_i0_select_pc_d,  // select pc onto rs1 for jal's

    output logic [31:1] dec_i0_pc_d,             // pc's at decode
    output logic [ 3:0] dec_i0_rs1_bypass_en_d,  // rs1 bypass enable
    output logic [ 3:0] dec_i0_rs2_bypass_en_d,  // rs2 bypass enable

    output logic [31:0] dec_i0_result_r,  // Result R-stage

    output el2_lsu_pkt_t lsu_p,           // lsu packet
    output logic         dec_qual_lsu_d,  // LSU instruction at D.  Use to quiet LSU operands
    output el2_mul_pkt_t mul_p,           // mul packet
    output el2_div_pkt_t div_p,           // div packet
    output logic         dec_div_cancel,  // cancel divide operation

    output logic [11:0] dec_lsu_offset_d,  // 12b offset for load/store addresses

    output logic        dec_csr_ren_d,    // CSR read enable
    output logic [31:0] dec_csr_rddata_d, // CSR read data

    output logic dec_tlu_flush_lower_r,  // tlu flush due to late mp, exception, rfpc, or int
    output logic dec_tlu_flush_lower_wb,
    output logic [31:1] dec_tlu_flush_path_r,  // tlu flush target
    output logic        dec_tlu_i0_kill_writeb_r,    // I0 is flushed, don't writeback any results to arch state
    output logic dec_tlu_fence_i_r,  // flush is a fence_i rfnpc, flush icache

    output logic [31:1] pred_correct_npc_x,  // npc if prediction is correct at e2 stage

    output el2_br_tlu_pkt_t dec_tlu_br0_r_pkt,  // slot 0 branch predictor update packet

    output logic dec_tlu_perfcnt0,  // toggles when slot0 perf counter 0 has an event inc
    output logic dec_tlu_perfcnt1,  // toggles when slot0 perf counter 1 has an event inc
    output logic dec_tlu_perfcnt2,  // toggles when slot0 perf counter 2 has an event inc
    output logic dec_tlu_perfcnt3,  // toggles when slot0 perf counter 3 has an event inc

    output el2_predict_pkt_t dec_i0_predict_p_d,  // prediction packet to alus
    output logic [pt.BHT_GHR_SIZE-1:0] i0_predict_fghr_d,  // DEC predict fghr
    output logic [pt.BTB_ADDR_HI:pt.BTB_ADDR_LO] i0_predict_index_d,  // DEC predict index
    output logic [pt.BTB_BTAG_SIZE-1:0] i0_predict_btag_d,  // DEC predict branch tag

    output logic [$clog2(pt.BTB_SIZE)-1:0] dec_fa_error_index,  // Fully associt btb error index

    output logic dec_lsu_valid_raw_d,

    output logic [31:0] dec_tlu_mrac_ff,  // CSR for memory region control

    output logic [1:0] dec_data_en,  // clock-gate control logic
    output logic [1:0] dec_ctl_en,

    input logic [15:0] ifu_i0_cinst,  // 16b compressed instruction

    output el2_trace_pkt_t trace_rv_trace_pkt,  // trace packet

    // PMP signals
    output el2_pmp_cfg_pkt_t        pmp_pmpcfg [pt.PMP_ENTRIES],
    output logic             [31:0] pmp_pmpaddr[pt.PMP_ENTRIES],

`ifdef RV_USER_MODE

    // Privilege mode
    output logic priv_mode,
    output logic priv_mode_eff,
    output logic priv_mode_ns,

    // mseccfg CSR content for PMP
    output el2_mseccfg_pkt_t mseccfg,

`endif

    // feature disable from mfdc
    output logic dec_tlu_external_ldfwd_disable,  // disable external load forwarding
    output logic dec_tlu_sideeffect_posted_disable,  // disable posted stores to side-effect address
    output logic dec_tlu_core_ecc_disable,  // disable core ECC
    output logic dec_tlu_bpred_disable,  // disable branch prediction
    output logic dec_tlu_wb_coalescing_disable,  // disable writebuffer coalescing
    output logic [2:0] dec_tlu_dma_qos_prty,  // DMA QoS priority coming from MFDC [18:16]

    // clock gating overrides from mcgc
    output logic dec_tlu_misc_clk_override,   // override misc clock domain gating
    output logic dec_tlu_ifu_clk_override,    // override fetch clock domain gating
    output logic dec_tlu_lsu_clk_override,    // override load/store clock domain gating
    output logic dec_tlu_bus_clk_override,    // override bus clock domain gating
    output logic dec_tlu_pic_clk_override,    // override PIC clock domain gating
    output logic dec_tlu_picio_clk_override,  // override PICIO clock domain gating
    output logic dec_tlu_dccm_clk_override,   // override DCCM clock domain gating
    output logic dec_tlu_icm_clk_override,    // override ICCM clock domain gating

    output logic dec_tlu_i0_commit_cmt,  // committed i0 instruction
    // Excluding scan_mode from coverage as its usage is determined by the integrator of the VeeR core.
    /*pragma coverage off*/
    input  logic scan_mode               // Flop scan mode control
    /*pragma coverage on*/

);

  el2_br_pkt_t i0_brp;  // branch packet
  el2_lsu_error_pkt_t lsu_error_pkt_r;  // LSU exception/error packet
  el2_trigger_pkt_t [3:0] trigger_pkt_any;
  // Unwrap structure support both simulators
  for (genvar i = 0; i < 4; i++) begin : g_unwrap_el2_trigger_pkt_t
    assign trigger_pkt_any_select[i] = trigger_pkt_any[i][37];
    assign trigger_pkt_any_match[i] = trigger_pkt_any[i][36];
    assign trigger_pkt_any_store[i] = trigger_pkt_any[i][35];
    assign trigger_pkt_any_load[i] = trigger_pkt_any[i][34];
    assign trigger_pkt_any_execute[i] = trigger_pkt_any[i][33];
    assign trigger_pkt_any_m[i] = trigger_pkt_any[i][32];
    assign trigger_pkt_any_tdata2[i] = trigger_pkt_any[i][31:0];
  end

  assign i0_brp = '0;
  assign lsu_error_pkt_r = '0;

  el2_dec dut (.*);
endmodule
