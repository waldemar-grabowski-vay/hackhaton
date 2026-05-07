// This document contains proprietary information belonging to Vay Technology GmbH. Passing on and copying of this
// document, and communication of its contents is not permitted without prior written authorization.
//
// Copyright 2026 Vay Technology GmbH. All rights reserved.

// CAN frame decoding helpers.
//
// `candump` line format (with `-t a`):
//   " (1234567890.123456)  can0  001   [64]  HH HH HH HH ..."
//
// DBC bit numbering is little-endian (Intel): bit `b` lives in byte `b/8`,
// shifted by `b%8`. Multi-bit signals span consecutive bytes, little-endian.

pub fn parse_candump_frame(line: &str) -> Vec<u8> {
    let toks: Vec<&str> = line.split_whitespace().collect();
    let Some(dlc_pos) = toks.iter().position(|t| t.starts_with('[')) else {
        return Vec::new();
    };
    toks.iter()
        .skip(dlc_pos + 1)
        .filter_map(|s| u8::from_str_radix(s, 16).ok())
        .collect()
}

pub fn decode_bit(bytes: &[u8], bit: usize) -> bool {
    let byte = bit / 8;
    let mask = 1u8 << (bit % 8);
    bytes.get(byte).map_or(false, |b| b & mask != 0)
}

pub fn decode_bits(bytes: &[u8], start_bit: usize, len: usize) -> u64 {
    if len == 0 || len > 64 {
        return 0;
    }
    let byte0 = start_bit / 8;
    let bit_in_byte = start_bit % 8;
    let total = bit_in_byte + len;
    let nbytes = (total + 7) / 8;
    let mut val: u64 = 0;
    for i in 0..nbytes.min(8) {
        if let Some(&b) = bytes.get(byte0 + i) {
            val |= (b as u64) << (i * 8);
        }
    }
    let mask = if len == 64 { u64::MAX } else { (1u64 << len) - 1 };
    (val >> bit_in_byte) & mask
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parse_strips_metadata_and_dlc() {
        let line = " (1.0)  can0  001   [4]  AA BB CC DD";
        assert_eq!(parse_candump_frame(line), vec![0xAA, 0xBB, 0xCC, 0xDD]);
    }

    #[test]
    fn bit_decode_byte21_bit0() {
        // mimicking the e-Stop frame from ts-de-ber-00010
        let bytes: Vec<u8> = (0..32)
            .map(|i| if i == 21 { 0x01 } else { 0x00 })
            .collect();
        assert!(decode_bit(&bytes, 168));
        assert!(!decode_bit(&bytes, 169));
    }

    #[test]
    fn multi_bit_decode_4bit_aligned() {
        // byte 6 = 0x03; bits 48..52 should equal 3
        let mut bytes = vec![0u8; 8];
        bytes[6] = 0x03;
        assert_eq!(decode_bits(&bytes, 48, 4), 3);
    }

    #[test]
    fn multi_bit_decode_5bit_at_lsb() {
        let bytes = [0b0001_0011, 0, 0, 0]; // low 5 bits = 0b10011 = 19
        assert_eq!(decode_bits(&bytes, 0, 5), 0b10011);
    }
}
