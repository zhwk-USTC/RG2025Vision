// frame.h
// PC <-> MCU serial protocol (frame layer, with streaming parser)
// Frame: AA | LEN | VER | SEQ | CHK | DATA... | 55
#pragma once

#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

// ---------- 常量 ----------
enum {
    PCMCU_FRAME_HEAD       = 0xAA,
    PCMCU_FRAME_TAIL       = 0x55,
    PCMCU_VERSION_DEFAULT  = 0x00,

    // LEN: 1 byte, LEN = 3 + N (VER+SEQ+CHK+DATA) -> N <= 252
    PCMCU_MAX_DATA_LEN     = 0xFF - 3,            // 252
    PCMCU_MIN_FRAME_TOTAL  = 6,                   // LEN=3 -> total 6
    PCMCU_MAX_FRAME_TOTAL  = 0xFF + 3             // 258
};

// ---------- 返回码 ----------
typedef enum pcmcu_status_e {
    PCMCU_OK                 = 0,
    PCMCU_EINVAL             = -1,  // 无效参数
    PCMCU_EDATA_TOO_LONG     = -2,  // DATA 超长
    PCMCU_EBUFSZ             = -3,  // 输出缓冲不够
    PCMCU_EFRAME_TOO_SHORT   = -4,  // 帧长 < 最小长度
    PCMCU_EHEAD_TAIL         = -5,  // 头/尾错误
    PCMCU_ELEN_INVALID       = -6,  // LEN < 3
    PCMCU_ELEN_MISMATCH      = -7,  // 帧总长与 LEN 不符
    PCMCU_ECHECKSUM          = -8   // 校验失败
} pcmcu_status_t;

// ---------- 帧编码 ----------
/**
 * @brief 构建一帧：AA LEN VER SEQ CHK DATA... 55
 * @param seq           序号(0..255)
 * @param data          DATA 指针（可为 NULL 且 data_len=0）
 * @param data_len      DATA 字节数（0..252）
 * @param ver           帧头 VER
 * @param out_buf       输出缓冲
 * @param out_buf_size  输出缓冲大小
 * @param out_frame_len 实际帧长输出（可为 NULL）
 * @return PCMCU_OK / 负错误码
 */
int pcmcu_build_frame(uint8_t seq,
                      const uint8_t *data, size_t data_len,
                      uint8_t ver,
                      uint8_t *out_buf, size_t out_buf_size,
                      size_t *out_frame_len);

// ---------- 完整帧解析（抽 DATA + 校验） ----------
/**
 * @brief 从完整帧中解析 DATA（并校验头尾/长度/校验和）
 * @param frame         输入完整帧
 * @param frame_len     完整帧长度
 * @param out_data      输出 DATA 缓冲（可为 NULL 表示仅校验）
 * @param out_data_cap  输出 DATA 缓冲容量（out_data 非 NULL 时有效）
 * @param out_data_len  实际 DATA 长度输出（可为 NULL）
 * @param out_ver       输出 VER（可为 NULL）
 * @param out_seq       输出 SEQ（可为 NULL）
 * @return PCMCU_OK / 负错误码
 */
int pcmcu_parse_frame_data(const uint8_t *frame, size_t frame_len,
                           uint8_t *out_data, size_t out_data_cap, size_t *out_data_len,
                           uint8_t *out_ver, uint8_t *out_seq);

// ---------- 流式解析（整合在本模块） ----------
#ifndef PCMCU_STREAM_MAX_BUF
#define PCMCU_STREAM_MAX_BUF 512u
#endif

typedef struct {
    uint8_t buf[PCMCU_STREAM_MAX_BUF];
    size_t  len;   // 当前缓冲已用
} pcmcu_stream_t;

/** 回调：每解析出一帧就调用。返回非 0 将中止本次 feed。 */
typedef int (*pcmcu_on_frame_fn)(const uint8_t *frame, size_t frame_len, void *user);

/** 初始化/清空流式解析器 */
static inline void pcmcu_stream_init(pcmcu_stream_t *fs) { if (fs) fs->len = 0; }
static inline void pcmcu_stream_clear(pcmcu_stream_t *fs){ if (fs) fs->len = 0; }

/**
 * @brief 流式馈入增量字节，内部自动重同步到下一个 HEAD。每当解析出完整帧即回调。
 * @param fs      解析器状态
 * @param in      新收到的字节（可为 NULL 且 in_len=0）
 * @param in_len  新字节数
 * @param onf     帧回调（可为 NULL，则仅丢弃帧）
 * @param user    回调用户参数
 * @return 0 成功；负数表示缓冲溢出等错误；回调返回非 0 将把该值向上传递
 *
 * 缓冲满策略：若追加后溢出，优先丢弃最早的字节以保留“最新数据”（等价 Python 版本的 left-trim）。
 */
int pcmcu_stream_feed(pcmcu_stream_t *fs,
                      const uint8_t *in, size_t in_len,
                      pcmcu_on_frame_fn onf, void *user);

#ifdef __cplusplus
}
#endif
