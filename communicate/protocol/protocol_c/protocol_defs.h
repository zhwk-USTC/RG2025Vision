// Auto-generated. DO NOT EDIT MANUALLY.
// Generated at UTC 2025-09-04 00:29:44
#pragma once
#include <stdint.h>

#define PROTOCOL_DATA_VER_FULL  20250904002944
#define PROTOCOL_DATA_VER       0x80

// MSG roles
#define MSG_PC_TO_MCU 0x01
#define MSG_MCU_TO_PC 0x02

// Variable IDs (T in TLV)
#define VAR_TEST1 0xA2
#define VAR_TEST0 0xBD

// Fixed sizes (only for fixed-width variables); others are variable-length per TLV L
#define VAR_TEST1_SIZE 2
#define VAR_TEST0_SIZE 1

static const uint8_t VAR_SIZE_TABLE[256] = {
    [VAR_TEST1] = 2,
    [VAR_TEST0] = 1,
    // others default to 0 (variable-length)
};

