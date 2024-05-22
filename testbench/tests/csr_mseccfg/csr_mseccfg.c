#include <stdio.h>

// ============================================================================

#define read_csr(csr) ({ \
    unsigned long res; \
    asm volatile ("csrr %0, %1" : "=r"(res) : "i"(csr)); \
    res; \
})

#define write_csr(csr, val) { \
    asm volatile ("csrw %0, %1" : : "i"(csr), "r"(val)); \
}

// ============================================================================

#define CSR_MSECCFG     0x747

#define CSR_PMPCFG0     0x3A0
#define CSR_PMPADDR0    0x3B0
#define CSR_PMPADDR1    0x3B1
#define CSR_PMPADDR2    0x3B2
#define CSR_PMPADDR3    0x3B3

#define MSECCFG_MML     (1 << 0)
#define MSECCFG_MMWP    (1 << 1)
#define MSECCFG_RLB     (1 << 2)

#define PMPCFG_R        (1 << 0)
#define PMPCFG_W        (1 << 1)
#define PMPCFG_X        (1 << 2)
#define PMPCFG_TOR      (1 << 3)
#define PMPCFG_L        (1 << 7)

// ============================================================================

extern uint32_t _code_begin;
extern uint32_t _code_end;
extern uint32_t _data_begin;
extern uint32_t _data_end;

#define A(x) ((uint32_t)(&(x)))

// ============================================================================

int main () {

    volatile uint32_t reg;

    // Check that mseccfg is zeroed
    printf("Checking that mseccfg is all-zero...\n");
    reg = read_csr(CSR_MSECCFG);
    if (reg != 0) {
        printf("ERROR: mseccfg=0x%08X\n", reg);
        return -1;
    }
    printf("ok.\n");

    // Verify that mseccfg.RLB can be set and cleared
    printf("Checking if mseccfg.RLB is writeable...\n");
    reg = read_csr(CSR_MSECCFG);
    write_csr(CSR_MSECCFG, reg |  MSECCFG_RLB);

    reg = read_csr(CSR_MSECCFG);
    if (!(reg & MSECCFG_RLB)) {
        printf("ERROR: mseccfg.MML cannot be set\n");
        return -1;
    }

    reg = read_csr(CSR_MSECCFG);
    write_csr(CSR_MSECCFG, reg & ~MSECCFG_RLB);

    reg = read_csr(CSR_MSECCFG);
    if (reg & MSECCFG_RLB) {
        printf("ERROR: mseccfg.RLB cannot be cleared\n");
        return -1;
    }
    printf("ok.\n");

    // Configure PMP
    // region 1: _code_begin - _code_end, --X
    // region 3: _data_begin - _data_end, RW-
    write_csr(CSR_PMPADDR0, A(_code_begin) >> 2); // PMPADDRx stores address bits 33:2
    write_csr(CSR_PMPADDR1, A(_code_end)   >> 2);
    write_csr(CSR_PMPADDR2, A(_data_begin) >> 2);
    write_csr(CSR_PMPADDR3, A(_data_end)   >> 2);

    uint32_t pmpcfg;
    pmpcfg = ((PMPCFG_TOR | PMPCFG_X)            << (8 * 1)) | // region 1
             ((PMPCFG_TOR | PMPCFG_R | PMPCFG_W) << (8 * 3));  // region 3

    write_csr(CSR_PMPCFG0, pmpcfg);

    // Set mseccfg.RLB and check if the region can be locked and unlocked
    printf("Checking if mseccfg.RLB=1 allows PMP regions to be unlocked...\n");

    reg = read_csr(CSR_MSECCFG);
    write_csr(CSR_MSECCFG, reg |  MSECCFG_RLB);

    // Lock region 1 and check
    write_csr(CSR_PMPCFG0, pmpcfg | (PMPCFG_L << (8 * 1)));
    reg = read_csr(CSR_PMPCFG0);
    if (!(reg & (PMPCFG_L << (8 * 1)))) {
        printf("ERROR: cannot lock PMP region 0\n");
        return -1;
    }

    // Unlock region 1 and check
    write_csr(CSR_PMPCFG0, pmpcfg);
    reg = read_csr(CSR_PMPCFG0);
    if (reg & (PMPCFG_L << (8 * 1))) {
        printf("ERROR: cannot unlock PMP region 0\n");
        return -1;
    }
    printf("ok.\n");

    // Verify that when at least one PMP region is locked mseccfg.RLB cannot be
    // set.
    printf("Checking if mseccfg.RLB cannot be set if any PMP region is locked...\n");

    // Clear RLB
    reg = read_csr(CSR_MSECCFG);
    write_csr(CSR_MSECCFG, reg & ~MSECCFG_RLB);

    // Lock region 1
    write_csr(CSR_PMPCFG0, pmpcfg | (PMPCFG_L << (8 * 1)));

    // Try setting RLB and check
    reg = read_csr(CSR_MSECCFG);
    write_csr(CSR_MSECCFG, reg |  MSECCFG_RLB);

    reg = read_csr(CSR_MSECCFG);
    if (reg & MSECCFG_RLB) {
        printf("ERROR: mseccfg.RLB can still be set\n");
        return -1;
    }
    printf("ok.\n");

    // Verify that mseccfg.MML cannot be cleared once set
    printf("Checking if mseccfg.MML cannot be cleared...\n");

    // Lock region 3. Region 1 is already locked. This is necessary for the
    // test as when MML=1 non-locked regions alwaus deny access in M mode
    write_csr(CSR_PMPCFG0, pmpcfg | (PMPCFG_L << (8 * 3)));

    reg = read_csr(CSR_MSECCFG);
    write_csr(CSR_MSECCFG, reg |  MSECCFG_MML);
    reg = read_csr(CSR_MSECCFG);
    write_csr(CSR_MSECCFG, reg & ~MSECCFG_MML);

    reg = read_csr(CSR_MSECCFG);
    if (!(reg & MSECCFG_MML)) {
        printf("ERROR: mseccfg.MML can be cleared\n");
        return -1;
    }
    printf("ok.\n");

    // Verify that mseccfg.MMWP cannot be cleared once set
    printf("Checking if mseccfg.MMWP cannot be cleared...\n");
    reg = read_csr(CSR_MSECCFG);
    write_csr(CSR_MSECCFG, reg |  MSECCFG_MMWP);
    reg = read_csr(CSR_MSECCFG);
    write_csr(CSR_MSECCFG, reg & ~MSECCFG_MMWP);

    reg = read_csr(CSR_MSECCFG);
    if (!(reg & MSECCFG_MMWP)) {
        printf("ERROR: mseccfg.MMWP can be cleared\n");
        return -1;
    }
    printf("ok.\n");

    return 0;
}
