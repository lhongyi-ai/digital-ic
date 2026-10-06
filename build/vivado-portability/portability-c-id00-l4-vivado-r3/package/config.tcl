set stage impl
set sources {rtl/core/vib_coeff_rom.sv rtl/platform/spram16k.sv rtl/core/known_capture.sv rtl/core/known_spectral_core.sv}
set generics {N=1024 WINDOWS=156 LANES=4 QUANT_PIPELINE=1 MODEL_DIR=model BIAS=441 THRESHOLD=-1029 LOG_CONSTANT=128145 LOG_FLOOR=-163279}
