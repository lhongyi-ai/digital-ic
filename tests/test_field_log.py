"""FCL1 parser tests using hand-authored bytes, NOT sensor measurements.

The fixture construction is independent of the decoder and uses the documented
64-word header / 16-word result layout. A valid CRC is recomputed for structural
negative cases so a failure cannot be attributed only to damaged payload CRC.
"""
import struct
import zlib

import pytest

from vibfpga.field_log import parse_field_log


MASK32 = (1 << 32) - 1
MODEL_BYTES = bytes(range(32))
MODEL_SHA = MODEL_BYTES.hex()
HEADER_REGION = 4096
RESULT_BYTES = 64


def record(frame_id=0, *, logits=(-(1 << 31), (1 << 31) - 1, -1),
           class_id=1, error_flags=0, last_service=0xFFFFFFF0):
    """Artificial coherent field values; no inference or physical capture."""
    pre, dft, power, nn = 769, 24960, 576, 1000
    return [frame_id, *(value & MASK32 for value in logits),
            class_id | (error_flags << 8), pre, dft, power, nn, pre + dft + power + nn,
            (last_service - 255 * 15000) & MASK32, last_service,
            (last_service + 30000) & MASK32, (frame_id + 1) * 256, 0, frame_id + 1]


def artificial_log(records=None, header_changes=None):
    if records is None:
        records = [record(), record(1, logits=(25, -12, 7), class_id=0,
                                   last_service=(0xFFFFFFF0 + 256 * 15000) & MASK32)]
    payload = b"".join(struct.pack("<16I", *row) for row in records)
    count = len(records)
    observed = count * 256
    header = [MASK32] * 64
    fields = {
        0: 0x314C4346, 1: 1, 2: count, 3: 0x434F4D54, 4: 0,
        5: observed, 6: max(1, observed), 7: 800, 8: 12_000_000, 9: 256,
        10: 2, 11: 1, 12: observed, 13: 0, 14: 0, 15: count,
        24: 0, 25: 0, 26: records[0][10] if records else 0,
        27: records[-1][11] if records else 0, 28: 1 if count > 1 else 0, 29: 0,
        30: zlib.crc32(payload), 31: 256, 32: RESULT_BYTES, 33: 0x301000,
        34: 0, 35: 0xE5, 36: 1875, 37: 1,
    }
    fields.update(header_changes or {})
    for index, value in fields.items():
        header[index] = value
    blob = bytearray(b"\xff" * HEADER_REGION + payload)
    struct.pack_into("<64I", blob, 0, *header)
    blob[64:96] = MODEL_BYTES
    return bytes(blob)


def change_record_word(blob, record_index, word_index, value):
    changed = bytearray(blob)
    struct.pack_into("<I", changed, HEADER_REGION + record_index * RESULT_BYTES + word_index * 4, value)
    count = struct.unpack_from("<I", changed, 8)[0]
    struct.pack_into("<I", changed, 30 * 4,
                     zlib.crc32(changed[HEADER_REGION:HEADER_REGION + count * RESULT_BYTES]))
    return bytes(changed)


def test_signed_logits_timestamp_wrap_and_schema():
    blob = artificial_log()
    parsed = parse_field_log(blob, expected_model_sha256=MODEL_SHA)
    assert parsed["committed"] and parsed["record_count"] == 2
    assert parsed["model_sha256"] == MODEL_SHA
    assert parsed["source_kind"] == "synthetic_pipeline_fixture"
    assert parsed["synthetic_model_not_for_deployment"] is True
    assert parsed["class_names"] == ["stopped", "rigid_support_running", "flexible_support_running"]
    assert (parsed["odr_hz"], parsed["clock_hz"], parsed["n"], parsed["axis"], parsed["lanes"]) == (800, 12_000_000, 256, "z", 1)
    first, second = parsed["records"]
    assert first["logits"] == [-(1 << 31), (1 << 31) - 1, -1]
    assert second["logits"] == [25, -12, 7]
    assert first["class_id"] == 1 and first["class_name"] == "rigid_support_running"
    assert first["usable_classification"] is True and first["error_flags"] == 0
    assert first["first_service_cycle"] == (0xFFFFFFF0 - 255 * 15000) & MASK32
    assert first["last_service_cycle"] == 0xFFFFFFF0
    assert first["result_cycle"] == (0xFFFFFFF0 + 30000) & MASK32
    assert first["last_sample_to_result_cycles_mod32"] == 30000
    assert parsed["service_wrap_count"] == 1
    assert first["cycles"] == {"pre": 769, "dft": 24960, "power": 576, "nn": 1000, "total": 27305}
    assert first["accepted_samples_snapshot"] == 256
    assert second["clip_count_snapshot"] == 2
    assert "does not establish physical" in parsed["hardware_measurement_provenance"]


def test_full_partition_padding_is_not_decoded_as_results():
    blob = artificial_log()
    full = blob + b"\xff" * (128 * 1024 - len(blob))
    assert parse_field_log(full) == parse_field_log(blob)


@pytest.mark.parametrize("error,device_id", [(2, 0x42), (4, 0xE5)])
def test_zero_result_error_log_is_valid_diagnostic(error, device_id):
    parsed = parse_field_log(artificial_log([], {4: error, 6: 4096, 35: device_id}),
                             expected_model_sha256=MODEL_SHA)
    assert parsed["records"] == [] and parsed["record_count"] == 0
    assert parsed["error_flags"] == error and parsed["observed_samples"] == 0
    assert parsed["accepted_samples"] == 0 and parsed["device_id"] == device_id


def test_record_error_flag_marks_prediction_unusable():
    parsed = parse_field_log(artificial_log([record(error_flags=0xA5)], {4: 0x10}))
    assert parsed["records"][0]["error_flags"] == 0xA5
    assert parsed["records"][0]["usable_classification"] is False
    assert parsed["records"][0]["logits"] == [-(1 << 31), (1 << 31) - 1, -1]


def test_model_hash_order_binding_and_optional_mode():
    blob = artificial_log()
    # Raw SHA bytes must preserve their order; MODEL_HASH is streamed LE by the
    # firmware, so this checks the byte result rather than endian-swapping words.
    assert parse_field_log(blob)["model_sha256"] == MODEL_SHA
    with pytest.raises(ValueError, match="model SHA256 mismatch"):
        parse_field_log(blob, expected_model_sha256=MODEL_BYTES[::-1].hex())
    changed = bytearray(blob)
    changed[64] ^= 1
    with pytest.raises(ValueError, match="model SHA256 mismatch"):
        parse_field_log(changed, expected_model_sha256=MODEL_SHA)
    # Model binding is conditional on supplying an expected hash. CRC covers
    # payload, not the full header; this distinction is intentional and explicit.
    assert parse_field_log(changed)["model_sha256"] != MODEL_SHA


@pytest.mark.parametrize("commit", [MASK32, 0xFFFFFF54, 0xFFFF4D54, 0xFF4F4D54, 0])
def test_partial_or_missing_commit_rejected(commit):
    with pytest.raises(ValueError, match="uncommitted"):
        parse_field_log(artificial_log(header_changes={3: commit}))


@pytest.mark.parametrize("word,value", [(0, 0x314E4553), (1, 2)])
def test_other_format_or_version_rejected(word, value):
    with pytest.raises(ValueError, match="unsupported"):
        parse_field_log(artificial_log(header_changes={word: value}))


def test_bad_payload_crc_rejected():
    changed = bytearray(artificial_log())
    changed[HEADER_REGION + 5] ^= 0x80
    with pytest.raises(ValueError, match="CRC mismatch"):
        parse_field_log(changed)


def test_bad_crc_for_empty_payload_rejected():
    with pytest.raises(ValueError, match="CRC mismatch"):
        parse_field_log(artificial_log([], {4: 4, 30: 1}))


@pytest.mark.parametrize("size", [0, 255, 256, 4095, 4096, 4096 + 64, 4096 + 127])
def test_header_or_payload_truncation_rejected(size):
    with pytest.raises(ValueError, match="truncated|CRC"):
        parse_field_log(artificial_log()[:size])


@pytest.mark.parametrize("record_index,value", [(1, 0), (0, 2)])
def test_duplicate_or_out_of_order_frame_with_valid_crc_rejected(record_index, value):
    blob = change_record_word(artificial_log(), record_index, 0, value)
    with pytest.raises(ValueError, match="duplicate|out-of-order"):
        parse_field_log(blob)


@pytest.mark.parametrize("packed", [3, 255, 0x10000, 0x80000000])
def test_invalid_class_or_reserved_record_bits_with_valid_crc_rejected(packed):
    blob = change_record_word(artificial_log(), 0, 4, packed)
    with pytest.raises(ValueError, match="invalid"):
        parse_field_log(blob)


@pytest.mark.parametrize("changes", [
    {2: 1876}, {6: 0}, {6: 480001}, {5: 513},
    {7: 400}, {8: 0}, {9: 1024}, {10: 3}, {11: 2},
    {31: 128}, {32: 32}, {33: 0x300FFF}, {36: 1874}, {37: 2},
])
def test_count_and_fixed_geometry_rejected(changes):
    with pytest.raises(ValueError, match="geometry|profile"):
        parse_field_log(artificial_log(header_changes=changes))


@pytest.mark.parametrize("changes", [
    {12: 511},                      # accepted + dropped != observed
    {13: 1},                        # accepted + dropped != observed
    {15: 513},                      # clips > accepted
    {14: 513},                      # canceled > accepted
    {29: 1},                        # complete results + partial exceeds accepted
    {5: 768, 6: 768, 12: 768, 29: 256},  # partial itself must be < N
    {4: 4, 5: 0, 12: 0, 15: 0},    # complete results cannot exist with zero acceptance
])
def test_counter_geometry_consistency_rejected(changes):
    with pytest.raises(ValueError):
        parse_field_log(artificial_log(header_changes=changes))


def test_partial_samples_and_canceled_history_need_not_equal_output_count():
    # Accepted samples include discarded partial/complete transactions, so an
    # equality check between accepted and saved records would be incorrect.
    changes = {4: 8, 5: 800, 6: 800, 12: 799, 13: 1, 14: 1, 29: 31, 34: 1}
    parsed = parse_field_log(artificial_log(header_changes=changes))
    assert parsed["record_count"] == 2 and parsed["trailing_partial_samples"] == 31
    assert parsed["accepted_samples"] == 799 and parsed["dropped_samples"] == 1
    assert parsed["canceled_frames"] == 1 and parsed["source_cancellation_events"] == 1


@pytest.mark.parametrize("axis,lanes", [(0, 1), (1, 4), (2, 4)])
def test_legal_axes_and_lanes_are_decoded(axis, lanes):
    parsed = parse_field_log(artificial_log(header_changes={10: axis, 11: lanes}))
    assert parsed["axis"] == "xyz"[axis] and parsed["lanes"] == lanes


def test_physical_model_tag_still_does_not_claim_hardware_execution():
    parsed = parse_field_log(artificial_log(header_changes={37: 0}))
    assert parsed["source_kind"] == "physical_adxl345_training"
    assert parsed["synthetic_model_not_for_deployment"] is False
    assert "does not establish physical" in parsed["hardware_measurement_provenance"]
