// Auto-generated. DO NOT EDIT MANUALLY.
// Generated at UTC 2025-09-05 09:07:35
#pragma once
#include <stdint.h>

#define PROTOCOL_DATA_VER_FULL  20250905090735
#define PROTOCOL_DATA_VER       0xAF

// MSG roles
#define MSG_PC_TO_MCU 0x01
#define MSG_MCU_TO_PC 0x02

// Variable IDs (T in TLV)
#define VAR_TEST_VAR_F32 0x5D
#define VAR_TEST_VAR_U8 0x67
#define VAR_TEST_VAR_U16 0xE6

// Fixed sizes (only for fixed-width variables); others are variable-length per TLV L
#define VAR_TEST_VAR_F32_SIZE 4
#define VAR_TEST_VAR_U8_SIZE 1
#define VAR_TEST_VAR_U16_SIZE 2

static const uint8_t VAR_SIZE_TABLE[256] = {
    [VAR_TEST_VAR_F32] = 4,
    [VAR_TEST_VAR_U8] = 1,
    [VAR_TEST_VAR_U16] = 2,
    // others default to 0 (variable-length)
};

