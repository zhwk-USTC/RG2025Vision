// frame.c
// C implementation for: AA | LEN | VER | SEQ | CHK | DATA... | 55
// - LEN = 3 + N   (VER + SEQ + CHK + DATA)
// - CHK = (LEN + VER + SEQ + sum(DATA bytes)) & 0xFF  # CHK 本身不参与

#include <stdint.h>
#include <stddef.h>
#include <string.h>

/* ===== 常量定义 ===== */
enum {
    FRAME_HEAD = 0xAA,
    FRAME_TAIL = 0x55,
    VERSION    = 0x00,          // 默认协议版本
    MAX_DATA_LEN = 0xFF - 3     // LEN 为 1 字节，LEN = 3 + N => N 最大 252
};

/* ===== 错误码 =====
 * 返回 0 表示成功；负数为错误。
 */
enum {
    PCMCU_OK                 = 0,
    PCMCU_EINVAL             = -1, // 参数非法
    PCMCU_EDATA_TOO_LONG     = -2, // DATA 过长
    PCMCU_EBUFSZ             = -3, // 输出缓冲区不足
    PCMCU_EFRAME_TOO_SHORT   = -4, // 输入帧太短
    PCMCU_EHEAD_TAIL         = -5, // 帧头/尾错误
    PCMCU_ELEN_INVALID       = -6, // LEN 无效（<3）
    PCMCU_ELEN_MISMATCH      = -7, // 长度不匹配
    PCMCU_ECHECKSUM          = -8  // 校验和错误
};

/* ===== 小工具 ===== */
static inline uint8_t u8_clip(int x) { return (uint8_t)(x & 0xFF); }

/* 计算 sum(DATA) */
static uint32_t sum_bytes(const uint8_t *data, size_t len) {
    uint32_t s = 0;
    if (data && len) {
        for (size_t i = 0; i < len; ++i) s += data[i];
    }
    return s;
}

/* CHK = (LEN + VER + SEQ + sum(DATA)) & 0xFF */
static uint8_t checksum(uint8_t len_byte, uint8_t ver, uint8_t seq,
                        const uint8_t *data, size_t data_len)
{
    uint32_t s = (uint32_t)len_byte + (uint32_t)ver + (uint32_t)seq + sum_bytes(data, data_len);
    return u8_clip((int)s);
}

/* 计算给定 data_len 所需的帧总长度（字节数） */
static size_t frame_size_for(size_t data_len) {
    // 总长度 = (VER + SEQ + CHK + DATA) + (HEAD + LEN + TAIL) = (3 + data_len) + 3
    return data_len + 6u;
}

/* ===== 构帧 =====
 * 构建一帧：AA LEN VER SEQ CHK DATA... 55
 * 参数：
 *   seq, ver       : 与协议同义
 *   data, data_len : 负载字节序列（可为 NULL 且 data_len=0）
 *   out_buf        : 输出缓冲区
 *   out_buf_size   : 输出缓冲区大小（字节）
 *   out_frame_len  : 实际帧长输出（可为 NULL 则忽略）
 * 返回：
 *   0 成功；负数为错误码
 */
int pcmcu_build_frame(uint8_t seq,
                      const uint8_t *data, size_t data_len,
                      uint8_t ver,
                      uint8_t *out_buf, size_t out_buf_size,
                      size_t *out_frame_len)
{
    if (!out_buf) return PCMCU_EINVAL;
    if (data_len > MAX_DATA_LEN) return PCMCU_EDATA_TOO_LONG;

    const uint8_t length = (uint8_t)(3u + (uint8_t)data_len); // LEN 字段
    const size_t total = frame_size_for(data_len);
    if (out_buf_size < total) return PCMCU_EBUFSZ;

    const uint8_t chk = checksum(length, ver, seq, data, data_len);

    // 填充
    size_t idx = 0;
    out_buf[idx++] = FRAME_HEAD;
    out_buf[idx++] = length;
    out_buf[idx++] = ver;
    out_buf[idx++] = seq;
    out_buf[idx++] = chk;

    if (data_len && data) {
        memcpy(&out_buf[idx], data, data_len);
        idx += data_len;
    }

    out_buf[idx++] = FRAME_TAIL;

    if (out_frame_len) *out_frame_len = idx;
    return PCMCU_OK;
}

/* ===== 解析（提取 DATA 字段并校验）=====
 * 从完整帧中解析出 DATA 字段，同时可回传 ver/seq。
 * 参数：
 *   frame, frame_len     : 输入完整帧
 *   out_data             : DATA 输出缓冲区（可为 NULL 表示仅校验不拷贝）
 *   out_data_cap         : out_data 容量
 *   out_data_len         : 实际 DATA 长度输出（可为 NULL 则忽略）
 *   out_ver, out_seq     : 可为 NULL（若不需要）
 * 返回：
 *   0 成功；负数为错误码
 */
int pcmcu_parse_frame_data(const uint8_t *frame, size_t frame_len,
                           uint8_t *out_data, size_t out_data_cap, size_t *out_data_len,
                           uint8_t *out_ver, uint8_t *out_seq)
{
    if (!frame) return PCMCU_EINVAL;

    // 最小帧：LEN=3（无 DATA），总长 = 3 + 3 = 6
    if (frame_len < 6u) return PCMCU_EFRAME_TOO_SHORT;
    if (frame[0] != FRAME_HEAD || frame[frame_len - 1] != FRAME_TAIL) return PCMCU_EHEAD_TAIL;

    const uint8_t length = frame[1];
    if (length < 3u) return PCMCU_ELEN_INVALID;

    const size_t expected = (size_t)length + 3u; // HEAD + LEN + LEN段(length) + TAIL
    if (frame_len != expected) return PCMCU_ELEN_MISMATCH;

    const uint8_t ver = frame[2];
    const uint8_t seq = frame[3];
    const uint8_t chk = frame[4];

    const uint8_t *data_ptr = &frame[5];
    const size_t data_len = (size_t)length - 3u;

    const uint8_t chk_calc = checksum(length, ver, seq, data_ptr, data_len);
    if (chk != chk_calc) return PCMCU_ECHECKSUM;

    if (out_ver) *out_ver = ver;
    if (out_seq) *out_seq = seq;

    if (out_data_len) *out_data_len = data_len;
    if (out_data) {
        if (out_data_cap < data_len) return PCMCU_EBUFSZ;
        if (data_len) memcpy(out_data, data_ptr, data_len);
    }
    return PCMCU_OK;
}

// /* =====（可选）一个简单示例 =====
// #include <stdio.h>
// int main(void) {
//     uint8_t payload[] = {0x10, 0x20, 0x30};
//     uint8_t frame[64];
//     size_t frame_len = 0;

//     int rc = pcmcu_build_frame(/*seq=*/0x01, payload, sizeof(payload), /*ver=*/VERSION,
//                                frame, sizeof(frame), &frame_len);
//     if (rc != PCMCU_OK) { printf("build err=%d\n", rc); return 1; }

//     uint8_t data[16], ver, seq;
//     size_t data_len = 0;
//     rc = pcmcu_parse_frame_data(frame, frame_len, data, sizeof(data), &data_len, &ver, &seq);
//     if (rc != PCMCU_OK) { printf("parse err=%d\n", rc); return 1; }

//     printf("ok: ver=%u seq=%u data_len=%zu\n", ver, seq, data_len);
//     return 0;
// }
// */
