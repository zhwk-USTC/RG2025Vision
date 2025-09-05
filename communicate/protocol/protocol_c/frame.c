// frame.c
#include "frame.h"
#include <string.h>

// --------- 内部工具 ---------
static inline uint8_t u8(uint32_t x) { return (uint8_t)(x & 0xFFu); }

static uint8_t checksum_u8(uint8_t len_byte, uint8_t ver, uint8_t seq,
                           const uint8_t *data, size_t data_len)
{
    uint32_t s = (uint32_t)len_byte + (uint32_t)ver + (uint32_t)seq;
    for (size_t i = 0; i < data_len; ++i) s += data[i];
    return u8(s);
}

// --------- 帧编码 ---------
int pcmcu_build_frame(uint8_t seq,
                      const uint8_t *data, size_t data_len,
                      uint8_t ver,
                      uint8_t *out_buf, size_t out_buf_size,
                      size_t *out_frame_len)
{
    if (!out_buf) return PCMCU_EINVAL;
    if (data_len > PCMCU_MAX_DATA_LEN) return PCMCU_EDATA_TOO_LONG;

    size_t length  = 3u + data_len;          // LEN = 3 + N
    size_t tot_len = length + 3u;            // HEAD + LEN段(length) + TAIL

    if (tot_len > out_buf_size) return PCMCU_EBUFSZ;

    uint8_t chk = checksum_u8((uint8_t)length, ver, seq, data, data_len);

    uint8_t *b = out_buf;
    b[0] = PCMCU_FRAME_HEAD;
    b[1] = (uint8_t)length;
    b[2] = ver;
    b[3] = seq;
    b[4] = chk;
    if (data_len && data) {
        memcpy(&b[5], data, data_len);
    }
    b[tot_len - 1] = PCMCU_FRAME_TAIL;

    if (out_frame_len) *out_frame_len = tot_len;
    return PCMCU_OK;
}

// --------- 完整帧解析（抽 DATA + 校验） ---------
int pcmcu_parse_frame_data(const uint8_t *frame, size_t frame_len,
                           uint8_t *out_data, size_t out_data_cap, size_t *out_data_len,
                           uint8_t *out_ver, uint8_t *out_seq)
{
    if (!frame) return PCMCU_EINVAL;
    if (frame_len < (size_t)PCMCU_MIN_FRAME_TOTAL) return PCMCU_EFRAME_TOO_SHORT;
    if (frame[0] != (uint8_t)PCMCU_FRAME_HEAD || frame[frame_len-1] != (uint8_t)PCMCU_FRAME_TAIL)
        return PCMCU_EHEAD_TAIL;

    uint8_t LEN = frame[1];
    if (LEN < 3u) return PCMCU_ELEN_INVALID;

    size_t expected_total = (size_t)LEN + 3u;
    if (expected_total != frame_len) return PCMCU_ELEN_MISMATCH;

    uint8_t ver = frame[2];
    uint8_t seq = frame[3];
    uint8_t chk = frame[4];

    const uint8_t *data_ptr = &frame[5];
    size_t data_len = (frame_len >= 6) ? (frame_len - 6u) : 0u;

    uint8_t calc = checksum_u8(LEN, ver, seq, data_ptr, data_len);
    if (chk != calc) return PCMCU_ECHECKSUM;

    if (out_ver) *out_ver = ver;
    if (out_seq) *out_seq = seq;
    if (out_data_len) *out_data_len = data_len;

    if (out_data) {
        if (out_data_cap < data_len) return PCMCU_EBUFSZ;
        if (data_len) memcpy(out_data, data_ptr, data_len);
    }
    return PCMCU_OK;
}

// --------- 流式解析实现 ---------
static void left_trim(uint8_t *buf, size_t *plen, size_t n)
{
    if (n == 0 || *plen == 0) return;
    if (n >= *plen) { *plen = 0; return; }
    memmove(buf, buf + n, *plen - n);
    *plen -= n;
}

static int resync_to_head(uint8_t *buf, size_t *plen)
{
    size_t i = 0, n = *plen;
    while (i < n && buf[i] != (uint8_t)PCMCU_FRAME_HEAD) i++;
    if (i > 0) left_trim(buf, plen, i);
    return (*plen > 0 && buf[0] == (uint8_t)PCMCU_FRAME_HEAD) ? 1 : 0;
}

int pcmcu_stream_feed(pcmcu_stream_t *fs,
                      const uint8_t *in, size_t in_len,
                      pcmcu_on_frame_fn onf, void *user)
{
    if (!fs) return PCMCU_EINVAL;

    // 1) 追加新数据；若溢出，左侧丢弃（保留最新）：
    if (in_len) {
        if (in_len >= sizeof(fs->buf)) {
            // 仅保留输入尾部的 (max) 字节
            memcpy(fs->buf, in + (in_len - sizeof(fs->buf)), sizeof(fs->buf));
            fs->len = sizeof(fs->buf);
        } else {
            size_t needed = fs->len + in_len;
            if (needed > sizeof(fs->buf)) {
                size_t drop = needed - sizeof(fs->buf);
                left_trim(fs->buf, &fs->len, drop);
            }
            memcpy(fs->buf + fs->len, in, in_len);
            fs->len += in_len;
        }
    }

    // 2) 循环提取完整帧
    for (;;) {
        if (fs->len < 1) return PCMCU_OK;

        if (fs->buf[0] != (uint8_t)PCMCU_FRAME_HEAD) {
            if (!resync_to_head(fs->buf, &fs->len)) return PCMCU_OK;
        }
        if (fs->len < 2) return PCMCU_OK;

        uint8_t LEN = fs->buf[1];
        if (LEN < 3u) {
            left_trim(fs->buf, &fs->len, 1);
            continue;
        }

        size_t total = (size_t)LEN + 3u;
        if (total < (size_t)PCMCU_MIN_FRAME_TOTAL || total > (size_t)PCMCU_MAX_FRAME_TOTAL) {
            left_trim(fs->buf, &fs->len, 1);
            continue;
        }

        if (fs->len < total) return PCMCU_OK;

        if (fs->buf[total - 1] != (uint8_t)PCMCU_FRAME_TAIL) {
            left_trim(fs->buf, &fs->len, 1);
            continue;
        }

        // 至少是“结构完整”的一帧；此处先交给回调/上层
        // 上层若需要校验/抽DATA，可调用 pcmcu_parse_frame_data
        int rc = 0;
        if (onf) rc = onf(fs->buf, total, user);

        // 弹出这帧
        left_trim(fs->buf, &fs->len, total);

        if (rc != 0) return rc;  // 上层要求中止
    }
    // not reachable
}
