// data.h
// 数据层 API（变量代号式 TLV）
// 依赖：protocol_defs.h（由生成脚本产出，含 Var IDs、VAR_SIZE_TABLE 等）
#pragma once

#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/* 错误码：0 成功；负数为错误 */
enum {
    DATA_OK     = 0,
    DATA_EINVAL = -1,   // 参数非法
    DATA_EBUFSZ = -2,   // 输出缓冲区不足
    DATA_EFMT   = -3,   // 数据格式错误（TLV 越界/头部错误等）
    DATA_ESIZE  = -4    // 固定宽度变量长度不匹配
};

/* TLV 追加：原子写入一项 TLV
 * buf/cap：输出缓冲与容量
 * w      ：当前写指针（偏移，通常由 data_begin 返回 2）
 * t      ：变量 ID (0..255)
 * v/l    ：值的地址与长度（0..255）
 * 返回：新写指针；失败返回 (size_t)-1
 */
size_t data_put_tlv(uint8_t *buf, size_t cap, size_t w, uint8_t t, const void *v, uint8_t l);

/* 固定宽度便捷写入（小端） */
size_t data_put_u8   (uint8_t *buf, size_t cap, size_t w, uint8_t t, uint8_t  val);
size_t data_put_u16le(uint8_t *buf, size_t cap, size_t w, uint8_t t, uint16_t val);
size_t data_put_u32le(uint8_t *buf, size_t cap, size_t w, uint8_t t, uint32_t val);

/* 新增：float32 (IEEE754, little-endian) 便捷写入 */
size_t data_put_f32le(uint8_t *buf, size_t cap, size_t w, uint8_t t, float val);

/* 基于 VAR_SIZE_TABLE 的“变量”写入：
 * 若 t 为固定宽度（VAR_SIZE_TABLE[t] != 0），则要求 l 必须等于该固定字节数；
 * 若 t 为可变长（表值为 0），则只需 0<=l<=255。
 * 成功返回新的写指针；失败返回 (size_t)-1，并可通过 *err 得知原因（可为 NULL）
 * 可能的 *err：DATA_ESIZE / DATA_EBUFSZ / DATA_EINVAL
 */
size_t data_put_var(uint8_t *buf, size_t cap, size_t w, uint8_t t, const void *v, uint8_t l, int *err);

/* 新增：按变量写入 float32（要求对应变量固定宽度为 4） */
size_t data_put_var_f32(uint8_t *buf, size_t cap, size_t w, uint8_t t, float val, int *err);

/* DATA 头部与整体编码 */
int    data_begin (uint8_t msg, uint8_t ver, uint8_t *out_buf, size_t out_cap, size_t *out_w);
size_t data_end   (size_t w);
int    data_encode(uint8_t msg, uint8_t ver,
                   const uint8_t *tlv_bytes, size_t tlv_len,
                   uint8_t *out_buf, size_t out_cap, size_t *out_data_len);

/* 结构性校验（只校验不越界/头部合法） */
int data_validate_tlvs(const uint8_t *tlv_bytes, size_t tlv_len);

/* 解码：遍历 TLV，回调每项
 * on_tlv(t, v, l, user) 返回非 0 将中止并把该值原样返回。
 */
int data_decode(const uint8_t *data, size_t data_len,
                uint8_t *out_msg, uint8_t *out_ver,
                int (*on_tlv)(uint8_t t, const uint8_t *v, uint8_t l, void *user),
                void *user);

/* 便捷：按 KV 打包（数组形式）
 * kv_t：一条 KV（t, v ptr, l）
 * data_kv_encode：将 KV 数组（kvs[0..n-1]）编码为 DATA
 */
typedef struct {
    uint8_t t;
    const uint8_t *v;
    uint8_t l;
} kv_t;

int data_kv_encode(uint8_t msg, uint8_t ver,
                   const kv_t *kvs, size_t n_kvs,
                   uint8_t *out_buf, size_t out_cap, size_t *out_len);

/* 新增：解码辅助，把 TLV 的 V/L 还原为 float32（小端）
 * 若 l != 4 或参数为空则返回 DATA_ESIZE/DATA_EINVAL
 */
int data_read_f32le(const uint8_t *v, uint8_t l, float *out_val);

#ifdef __cplusplus
}
#endif
