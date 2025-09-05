// data.c
// 数据层编码与解析：DATA = MSG(1B) | VER(1B) | TLV...，TLV = T(1B) | L(1B) | V(L bytes)
// 变量代号式 TLV（T=变量 ID）。固定/可变长度由 protocol_c/protocol_defs.h 的 VAR_SIZE_TABLE 指示。
#include <stdint.h>
#include <stddef.h>
#include <string.h>

#include "protocol_defs.h"  // 提供：VAR_* 常量、VAR_SIZE_TABLE[256]、MSG_*、版本宏
#include "data.h"

/* ================= 内部小工具 ================= */
static inline void u16_le_store(uint8_t *p, uint16_t v) {
    p[0] = (uint8_t)(v & 0xFF);
    p[1] = (uint8_t)((v >> 8) & 0xFF);
}
static inline void u32_le_store(uint8_t *p, uint32_t v) {
    p[0] = (uint8_t)( v        & 0xFF);
    p[1] = (uint8_t)((v >> 8)  & 0xFF);
    p[2] = (uint8_t)((v >> 16) & 0xFF);
    p[3] = (uint8_t)((v >> 24) & 0xFF);
}

/* float32: 避免严格别名问题，用 memcpy 做类型转换 */
static inline void f32_le_store(uint8_t *p, float f) {
    uint32_t u;
    memcpy(&u, &f, 4);
    u32_le_store(p, u);
}
static inline float f32_le_load(const uint8_t *p) {
    uint32_t u = (uint32_t)p[0]
               | ((uint32_t)p[1] << 8)
               | ((uint32_t)p[2] << 16)
               | ((uint32_t)p[3] << 24);
    float f;
    memcpy(&f, &u, 4);
    return f;
}

/* ================= TLV 追加函数 ================= */

size_t data_put_tlv(uint8_t *buf, size_t cap, size_t w, uint8_t t, const void *v, uint8_t l)
{
    if (!buf) return (size_t)-1;
    if (w + 2u + (size_t)l > cap) return (size_t)-1;

    buf[w++] = t;
    buf[w++] = l;
    if (l && v) {
        memcpy(&buf[w], v, l);
        w += l;
    }
    return w;
}

size_t data_put_u8(uint8_t *buf, size_t cap, size_t w, uint8_t t, uint8_t val)
{
    return data_put_tlv(buf, cap, w, t, &val, 1);
}

size_t data_put_u16le(uint8_t *buf, size_t cap, size_t w, uint8_t t, uint16_t val)
{
    if (!buf) return (size_t)-1;
    if (w + 2u + 2u > cap) return (size_t)-1;
    buf[w++] = t;
    buf[w++] = 2u;
    u16_le_store(&buf[w], val);
    w += 2u;
    return w;
}

size_t data_put_u32le(uint8_t *buf, size_t cap, size_t w, uint8_t t, uint32_t val)
{
    if (!buf) return (size_t)-1;
    if (w + 2u + 4u > cap) return (size_t)-1;
    buf[w++] = t;
    buf[w++] = 4u;
    u32_le_store(&buf[w], val);
    w += 4u;
    return w;
}

size_t data_put_f32le(uint8_t *buf, size_t cap, size_t w, uint8_t t, float val)
{
    if (!buf) return (size_t)-1;
    if (w + 2u + 4u > cap) return (size_t)-1;
    buf[w++] = t;
    buf[w++] = 4u;
    f32_le_store(&buf[w], val);
    w += 4u;
    return w;
}

/* 按 VAR_SIZE_TABLE 约束追加变量 */
size_t data_put_var(uint8_t *buf, size_t cap, size_t w, uint8_t t, const void *v, uint8_t l, int *err)
{
    if (err) *err = DATA_OK;
    if (!buf) { if (err) *err = DATA_EINVAL; return (size_t)-1; }

    uint8_t expect = VAR_SIZE_TABLE[t];  // 0 表示可变长
    if (expect != 0 && l != expect) {
        if (err) *err = DATA_ESIZE;
        return (size_t)-1;
    }
    size_t nw = data_put_tlv(buf, cap, w, t, v, l);
    if (nw == (size_t)-1) { if (err) *err = DATA_EBUFSZ; }
    return nw;
}

/* 便捷：按变量写入 float32（要求变量固定宽度为 4） */
size_t data_put_var_f32(uint8_t *buf, size_t cap, size_t w, uint8_t t, float val, int *err)
{
    if (err) *err = DATA_OK;
    if (!buf) { if (err) *err = DATA_EINVAL; return (size_t)-1; }

    uint8_t expect = VAR_SIZE_TABLE[t];
    if (expect != 4) {             // 既处理 0(可变长) 也处理非 4 的固定长
        if (err) *err = DATA_ESIZE;
        return (size_t)-1;
    }
    if (w + 2u + 4u > cap) { if (err) *err = DATA_EBUFSZ; return (size_t)-1; }

    buf[w++] = t;
    buf[w++] = 4u;
    f32_le_store(&buf[w], val);
    w += 4u;
    return w;
}

/* ================= DATA 编码/解码 ================= */

int data_begin(uint8_t msg, uint8_t ver, uint8_t *out_buf, size_t out_cap, size_t *out_w)
{
    if (!out_buf || out_cap < 2u) return DATA_EBUFSZ;
    out_buf[0] = msg;
    out_buf[1] = ver;
    if (out_w) *out_w = 2u;
    return DATA_OK;
}

size_t data_end(size_t w) { return w; }

int data_encode(uint8_t msg, uint8_t ver,
                const uint8_t *tlv_bytes, size_t tlv_len,
                uint8_t *out_buf, size_t out_cap, size_t *out_data_len)
{
    if (!out_buf) return DATA_EINVAL;
    if (out_cap < 2u) return DATA_EBUFSZ;

    out_buf[0] = msg;
    out_buf[1] = ver;

    if (tlv_len) {
        if (!tlv_bytes) return DATA_EINVAL;
        if (2u + tlv_len > out_cap) return DATA_EBUFSZ;
        memcpy(&out_buf[2], tlv_bytes, tlv_len);
    }
    if (out_data_len) *out_data_len = 2u + tlv_len;
    return DATA_OK;
}

int data_validate_tlvs(const uint8_t *tlv_bytes, size_t tlv_len)
{
    size_t i = 0;
    while (i < tlv_len) {
        if (i + 2u > tlv_len) return DATA_EFMT;               // 不足以读 T/L
        uint8_t l = tlv_bytes[i + 1];
        if (i + 2u + (size_t)l > tlv_len) return DATA_EFMT;   // V 越界
        i += 2u + (size_t)l;
    }
    return DATA_OK;
}

int data_decode(const uint8_t *data, size_t data_len,
                uint8_t *out_msg, uint8_t *out_ver,
                int (*on_tlv)(uint8_t t, const uint8_t *v, uint8_t l, void *user),
                void *user)
{
    if (!data || data_len < 2u) return DATA_EFMT;

    uint8_t msg = data[0];
    uint8_t ver = data[1];
    if (out_msg) *out_msg = msg;
    if (out_ver) *out_ver = ver;

    const uint8_t *p = &data[2];
    size_t remain = data_len - 2u;

    int vr = data_validate_tlvs(p, remain);
    if (vr != DATA_OK) return vr;

    size_t i = 0;
    while (i < remain) {
        uint8_t t = p[i];
        uint8_t l = p[i + 1];
        const uint8_t *v = &p[i + 2u];

        // 固定长度变量的 L 必须匹配
        uint8_t expect = VAR_SIZE_TABLE[t];
        if (expect != 0 && l != expect) {
            return DATA_ESIZE;
        }

        if (on_tlv) {
            int rc = on_tlv(t, v, l, user);
            if (rc != 0) return rc; // 允许回调中止
        }
        i += 2u + (size_t)l;
    }
    return DATA_OK;
}

/* ================= 便捷：KV 数组直接编码 ================= */

int data_kv_encode(uint8_t msg, uint8_t ver,
                   const kv_t *kvs, size_t n_kvs,
                   uint8_t *out_buf, size_t out_cap, size_t *out_len)
{
    if (!out_buf) return DATA_EINVAL;

    size_t w = 0;
    int rc = data_begin(msg, ver, out_buf, out_cap, &w);
    if (rc != DATA_OK) return rc;

    for (size_t i = 0; i < n_kvs; ++i) {
        int err = DATA_OK;
        w = data_put_var(out_buf, out_cap, w, kvs[i].t, kvs[i].v, kvs[i].l, &err);
        if (w == (size_t)-1) {
            return (err != DATA_OK) ? err : DATA_EBUFSZ;
        }
    }

    if (out_len) *out_len = data_end(w);
    return DATA_OK;
}

/* ================= 解码辅助：读取 float32 ================= */

int data_read_f32le(const uint8_t *v, uint8_t l, float *out_val)
{
    if (!out_val || (!v && l != 0)) return DATA_EINVAL;
    if (l != 4) return DATA_ESIZE;
    *out_val = f32_le_load(v);
    return DATA_OK;
}
