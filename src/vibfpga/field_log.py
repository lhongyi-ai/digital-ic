"""FCL1 committed field-classification logs. This format is distinct from SEN1."""
import struct
import zlib
from .field import CLASS_NAMES


def parse_field_log(blob, *, expected_model_sha256=None):
    if len(blob) < 4096:
        raise ValueError("truncated FCL1 header")
    h = struct.unpack_from("<64I", blob)
    if h[:2] != (0x314c4346,1) or h[3] != 0x434f4d54:
        raise ValueError("FCL1 missing, uncommitted or unsupported")
    if h[2]>1875 or not 0<h[6]<=480000 or h[5]>h[6] or h[7:10] != (800,12000000,256):
        raise ValueError("invalid FCL1 sampling/count geometry")
    if h[10]>2 or h[11] not in (1,4) or h[31:34] != (256,64,0x301000) or h[36]!=1875 or h[37] not in (0,1):
        raise ValueError("invalid FCL1 profile")
    if h[12]+h[13]!=h[5] or h[15]>h[12] or h[29]>=256 or h[2]*256+h[29]>h[12] or h[14]>h[12]:
        raise ValueError("inconsistent FCL1 sample accounting")
    model_sha = bytes(blob[64:96]).hex()
    if expected_model_sha256 is not None and model_sha != expected_model_sha256:
        raise ValueError("FCL1 model SHA256 mismatch")
    payload = blob[4096:4096+h[2]*64]
    if len(payload)!=h[2]*64 or zlib.crc32(payload)!=h[30]:
        raise ValueError("FCL1 payload truncated or CRC mismatch")
    signed = lambda x: x-2**32 if x>=2**31 else x
    results=[]
    previous_id=-1
    for offset in range(0,len(payload),64):
        r=struct.unpack_from("<16I",payload,offset)
        if r[0]<=previous_id or r[4]&0xff>2 or r[4]>>16:
            raise ValueError("invalid/duplicate/out-of-order FCL1 result")
        previous_id=r[0]
        results.append({"frame_id":r[0],"logits":[signed(x) for x in r[1:4]],
            "class_id":r[4]&255,"class_name":CLASS_NAMES[r[4]&255],"error_flags":(r[4]>>8)&255,
            "usable_classification":((r[4]>>8)&255)==0,
            "cycles":{"pre":r[5],"dft":r[6],"power":r[7],"nn":r[8],"total":r[9]},
            "first_service_cycle":r[10],"last_service_cycle":r[11],"result_cycle":r[12],
            "last_sample_to_result_cycles_mod32":(r[12]-r[11])%2**32,
            "accepted_samples_snapshot":r[13],"dropped_samples_snapshot":r[14],"clip_count_snapshot":r[15]})
    return {"schema_version":1,"committed":True,"model_sha256":model_sha,"class_names":CLASS_NAMES,
        "source_kind":"synthetic_pipeline_fixture" if h[37] else "physical_adxl345_training",
        "synthetic_model_not_for_deployment":bool(h[37]),"error_flags":h[4],"observed_samples":h[5],
        "target_samples":h[6],"odr_hz":h[7],"clock_hz":h[8],"n":h[9],"axis":"xyz"[h[10]],"lanes":h[11],
        "accepted_samples":h[12],"dropped_samples":h[13],"canceled_frames":h[14],"clip_count":h[15],
        "missed_service":h[24],"sensor_overruns":h[25],"first_service_cycle":h[26],"last_service_cycle":h[27],
        "service_wrap_count":h[28],"trailing_partial_samples":h[29],"source_cancellation_events":h[34],
        "device_id":h[35],"record_count":h[2],"records":results,
        "hardware_measurement_provenance":"Log decoding alone does not establish physical hardware execution.",
        "timing_note":"Service timestamps are register read times, not ADC apertures. Individual latencies use modulo32 (<one wrap)."}
