"""Host parsing of bytes produced by actual RTL with behavioral peripherals.

These fixture logs are simulation artifacts, never physical measurements.
"""
import json
from pathlib import Path
import struct
import numpy as np
import pytest
from vibfpga.sensor import parse_sensor_log,sensor_log_to_csv,analyze_capture,correct_mg
from vibfpga.fixed import frontend

ROOT=Path(__file__).resolve().parents[1]


def simulated_log(case):
    directory=ROOT/f"build/sensor_system_{case}"
    if not (directory/"sensor_log.bin").exists():
        pytest.skip("Run the sensor RTL integration regression first")
    stimulus=json.loads((directory/"sensor_stimulus.json").read_text())
    assert stimulus["simulation_only"] is True
    return (directory/"sensor_log.bin").read_bytes(),stimulus


def test_rtl_generated_sensor_log_signed_data_wrap_calibration_and_csv(tmp_path):
    blob,stim=simulated_log("nominal")
    meta,raw,times=parse_sensor_log(blob)
    kept=stim["store_samples"]
    assert len(raw)==kept and meta["observed_samples"]==stim["total_samples"]
    assert meta["header_bytes"]>=128
    np.testing.assert_array_equal(raw,stim["raw_axis"][:kept])
    actual=np.array(stim["service_cycles_u32"][:kept],dtype=np.int64)
    error=(times.astype(np.int64)-actual+(1<<31))%(1<<32)-(1<<31)
    assert np.max(abs(error))<=3  # Quantized service delta, not ADC aperture time.
    service=stim["service_cycles_u32"]
    elapsed=sum((b-a)%(1<<32) for a,b in zip(service,service[1:]))
    assert meta["service_wrap_count"]==sum(b<a for a,b in zip(service,service[1:]))
    assert meta["full_service_elapsed_seconds"]==elapsed/meta["clock_hz"]
    corrected=correct_mg(np.array(stim["raw_axis"],dtype=np.int64),
        {"offset_q8":meta["cal_offset_q8"],"gain_q20":meta["cal_gain_q20"]})
    assert meta["calibrated_samples"]==len(corrected)
    assert meta["sum_calibrated_mg"]==int(corrected.sum())
    assert meta["last_calibrated_mg"]==int(corrected[-1])
    destination=tmp_path/"capture.csv"
    sensor_log_to_csv(blob,destination)
    result=analyze_capture(destination,odr=meta["odr_hz"],axis=meta["axis"])
    assert result["psd_valid_uniform_sampling_assumption"]
    assert result["capture_hardware_counters"]["observed_samples"]==meta["observed_samples"]
    assert result["adc_aperture_jitter_measured"] is False


def test_capture_wide_overrun_survives_csv_conversion(tmp_path):
    blob,_=simulated_log("nominal")
    modified=bytearray(blob)
    struct.pack_into("<I",modified,4*18,1)
    struct.pack_into("<I",modified,4*4,1<<4)
    destination=tmp_path/"overrun.csv"
    meta=sensor_log_to_csv(bytes(modified),destination)
    result=analyze_capture(destination,odr=meta["odr_hz"],axis=meta["axis"])
    assert result["capture_hardware_counters"]["observed_sensor_overruns"]==1
    assert result["psd_valid_uniform_sampling_assumption"] is False


def test_interval_overflow_crc_and_commit_are_not_silently_accepted(tmp_path):
    blob,stim=simulated_log("overflow")
    meta,raw,_=parse_sensor_log(blob)
    np.testing.assert_array_equal(raw,stim["raw_axis"][:stim["store_samples"]])
    assert meta["interval_overflows"]>0 and not meta["timestamps_reconstructable"]
    with pytest.raises(ValueError,match="interval overflow"):
        sensor_log_to_csv(blob,tmp_path/"bad.csv")
    damaged=bytearray(blob);damaged[4096]^=1
    with pytest.raises(ValueError,match="CRC"):
        parse_sensor_log(bytes(damaged))
    damaged=bytearray(blob);damaged[12:16]=b"\xff"*4
    with pytest.raises(ValueError,match="uncommitted"):
        parse_sensor_log(bytes(damaged))


@pytest.mark.parametrize("word,value",[(8,0),(8,1),(2,24001),(7,0),(5,0),(6,0),(10,3),(9,0x0b)])
def test_malformed_sensor_metadata_rejected(word,value):
    blob,_=simulated_log("nominal")
    damaged=bytearray(blob)
    struct.pack_into("<I",damaged,4*word,value)
    with pytest.raises(ValueError):parse_sensor_log(bytes(damaged))


def test_208_byte_rtl_spectrum_log_matches_integer_frontend(tmp_path):
    blob,stim=simulated_log("spectrum")
    meta,raw,_=parse_sensor_log(blob)
    profile=json.loads((ROOT/"artifacts/sensor_spectrum/model/model.json").read_text())
    assert profile["not_for_classification"] is True
    assert meta["header_bytes"]==208
    spectrum=meta["spectrum"]
    assert spectrum["complete_windows"]==len(stim["raw_axis"])//256
    assert spectrum["n"]==256 and spectrum["valid_complete_window"]
    raw_frame=np.array(stim["raw_axis"][:spectrum["complete_windows"]*256],dtype=np.int64)[-256:]
    reference=frontend(np.clip(raw_frame,-1024,1023)*32,profile)
    assert spectrum["powers"]==reference["powers"].tolist()
    assert spectrum["frequency_hz"]==[k*meta["odr_hz"]/256 for k in profile["bins"]]
    assert spectrum["is_psd_per_hz"] is False
    assert spectrum["calibrated_mg_domain"] is False
    assert spectrum["clipped_input_samples"]==int(np.count_nonzero((raw_frame < -1024)|(raw_frame>1023)))
    csv=tmp_path/"spectrum.csv"
    sensor_log_to_csv(blob,csv)
    analysis=analyze_capture(csv,odr=meta["odr_hz"],axis=meta["axis"])
    assert analysis["capture_hardware_counters"]["observed_samples"]==meta["observed_samples"]
    assert analysis["psd_valid_uniform_sampling_assumption"]
    for word,value in [(33,1024),(34,2)]:
        damaged=bytearray(blob);struct.pack_into("<I",damaged,4*word,value)
        with pytest.raises(ValueError,match="spectrum configuration"):
            parse_sensor_log(bytes(damaged))
