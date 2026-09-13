"""Build small proof kernels from exact, hash-tracked production RTL snippets.

The arithmetic functions, serial quantizer case arms, and output equations are
not maintained copies. Extraction fails if a required source boundary changes.
The generated wrapper only supplies a transaction boundary and observation ports.
"""
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "rtl/core/vibration_core.sv"
DESTINATION = ROOT / "build/quantization_formal/generated"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def extract():
    source_bytes = SOURCE.read_bytes()
    source = source_bytes.decode()
    snippets = {}

    def take(name, pattern):
        matches = list(re.finditer(pattern, source, re.MULTILINE | re.DOTALL))
        if len(matches) != 1:
            raise RuntimeError(f"Expected exactly one production RTL snippet {name}, found {len(matches)}")
        match = matches[0]
        text = match.group(0)
        snippets[name] = {"source_start_line": source.count("\n", 0, match.start()) + 1,
                          "source_end_line": source.count("\n", 0, match.end()) + 1,
                          "sha256": sha(text.encode()), "text": text}
        return text

    functions = [take(name, rf"^    function automatic[^\n]*\b{name};.*?^    endfunction")
                 for name in ("rne", "sat12", "sat16", "relu_quant")]
    states = take("state_encoding", r"^    localparam \[4:0\] IDLE=.*?HOLD=\d+;")
    arms = take("serial_case_arms", r"^                POWER_Q_INIT: begin.*?(?=^                NN_INIT: begin)")
    decls = [take(name, rf"^    {re.escape(line)}$") for name, line in (
        ("state", "reg [4:0] state;"),
        ("feature_shifts", "reg [7:0] feature_shifts [0:15];"),
        ("features", "reg [7:0] features [0:15], hidden [0:15];"),
        ("feature_index", "reg [3:0] feature_index;"),
        ("power_index", "reg [BI_W-1:0] power_index;"),
        ("quant_storage", "reg [32:0] power_sum, quant_work;"),
        ("quant_remaining", "reg [7:0] quant_remaining;"),
        ("guard_sticky", "reg quant_guard, quant_sticky;"),
        ("nn_layer", "reg nn_layer;"),
        ("nn_group", "reg [3:0] nn_group;"),
    )]
    equations = [take(name, rf"^    wire \[7:0\] {name} = [^\n]*;$")
                 for name in ("quant_rounded", "quant_result")]
    # Compare the kernel reset of quantizer arithmetic storage with the real
    # full-core reset; other wrapper state only manages abstract transactions.
    reset_block = re.search(r"if \(rst\) begin\s*state<=IDLE;.*?\n        end else begin", source, re.DOTALL)
    if not reset_block:
        raise RuntimeError("Production core reset boundary changed")
    resets = []
    for name in ("quant_work", "quant_remaining", "quant_guard", "quant_sticky"):
        matches = re.findall(rf"\b{name}<=0;", reset_block.group(0))
        if len(matches) != 1:
            raise RuntimeError(f"Production reset assignment changed: {name}")
        resets.append(matches[0])

    kernel = """// Automatically extracted. See extraction.json for source spans and SHA256.
module quant_functions_kernel #(parameter integer HIDDEN_SHIFT=8) (
    input wire signed [39:0] value,
    input wire [5:0] shift,
    output wire signed [39:0] rounded,
    output wire signed [15:0] clipped12, clipped16,
    output wire [7:0] hidden_quantized
);
""" + "\n".join(functions) + """
    assign rounded = rne(value, {26'd0,shift});
    assign clipped12 = sat12(value);
    assign clipped16 = sat16(value);
    assign hidden_quantized = relu_quant(value);
endmodule

module quant_serial_kernel (
    input wire clk, rst, start,
    input wire [32:0] in_power,
    input wire [7:0] in_shift,
    input wire [3:0] in_index,
    output wire ready, out_valid,
    output wire [7:0] out_value, stored_value,
    output wire [3:0] out_index, out_kind,
    output wire shifting
);
    // BANDS=3 gives the widest production power_index. Its post-quantization
    // increment is retained, although DFT/power production is outside this cut.
    localparam integer BI_W=$clog2(16*3);
""" + states + "\n" + "\n".join(decls + equations) + """
    reg dbg_valid;
    reg [3:0] dbg_kind;
    reg [15:0] dbg_index;
    reg signed [39:0] dbg_value;
    assign ready = !rst && state == IDLE;
    assign out_valid = dbg_valid;
    assign out_value = dbg_value[7:0];
    assign stored_value = features[dbg_index[3:0]];
    assign out_index = dbg_index[3:0];
    assign out_kind = dbg_kind;
    assign shifting = state == POWER_Q_SHIFT;
    always @(posedge clk) begin
        if (rst) begin
            state<=IDLE; feature_index<=0; power_index<=0; power_sum<=0;
            nn_layer<=0; nn_group<=0;
            dbg_valid<=0; dbg_kind<=0; dbg_index<=0; dbg_value<=0;
            """ + " ".join(resets) + """
        end else begin
            dbg_valid<=0;
            case (state)
                IDLE: if (start) begin
                    power_sum<=in_power;
                    feature_shifts[in_index]<=in_shift;
                    feature_index<=in_index;
                    state<=POWER_Q_INIT;
                end
""" + arms + """
                // The real successor is NN_INIT or POWER_RE_MUL. This cut
                // returns to IDLE after observing the completed feature write.
                default: state<=IDLE;
            endcase
        end
    end
endmodule
"""
    DESTINATION.mkdir(parents=True, exist_ok=True)
    path = DESTINATION / "quant_extract.sv"
    path.write_text(kernel)
    manifest = {"source": str(SOURCE.relative_to(ROOT)), "source_sha256": sha(source_bytes),
                "generated_sha256": sha(kernel.encode()), "snippets": snippets,
                "quantizer_reset_assignments": resets,
                "cut": "Only arithmetic functions and feature requantization; no frontend, NN accumulation, ROM scheduling or full-core proof"}
    (DESTINATION / "extraction.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


if __name__ == "__main__":
    print(json.dumps({k: v for k, v in extract().items() if k != "snippets"}, indent=2))
