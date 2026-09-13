module fifo_harness #(
    parameter integer WIDTH = 16,
    parameter integer DEPTH = 4
) (input wire clk);
    localparam integer CW = $clog2(DEPTH+1);
    (* anyseq *) reg rst, in_valid, out_ready;
    (* anyseq *) reg [WIDTH-1:0] in_data;
    wire in_ready, out_valid;
    wire [WIDTH-1:0] out_data;
    wire [CW-1:0] occupancy;
    sync_fifo #(.WIDTH(WIDTH), .DEPTH(DEPTH)) dut (.*);

    // Universally selected accepted word: track its number of predecessors.
    // `watch` is unconstrained. Every accepted word can be the chosen word;
    // this checks all 16 payload bits without duplicating the DUT's RAM.
    (* anyseq *) reg watch;
    reg tracking;
    reg [CW-1:0] ahead;
    reg [WIDTH-1:0] expected;
    reg [CW-1:0] count;
    reg past_valid = 0;
    reg seen_full = 0, seen_exchange = 0, seen_reset_busy = 0;
    reg [7:0] accepted = 0;
    wire push = in_valid && in_ready;
    wire pop = out_valid && out_ready;

    always @(posedge clk) begin
        past_valid <= 1;
        if (!past_valid) assume(rst);
        // No assumptions constrain later resets, the input data, valid, or ready.
        if (past_valid) begin
            assert(occupancy <= DEPTH);
            assert(occupancy == count);
            assert(out_valid == (!rst && count != 0));
            assert(in_ready == (!rst && (count < DEPTH || out_ready)));
            if (tracking && !rst) begin
                assert(ahead < count);
                if (ahead == 0) begin
                    assert(out_valid);
                    assert(out_data == expected);
                end
            end
            if ($past(out_valid && !out_ready && !rst) && !rst) begin
                assert(out_valid);
                assert(out_data == $past(out_data));
            end
            if ($past(rst)) begin
                assert(occupancy == 0);
                assert(!out_valid);
            end
            if (rst) begin
                assert(!out_valid);
                assert(!in_ready);
            end
        end

        if (rst) begin
            count <= 0;
            accepted <= 0;
            tracking <= 0;
            ahead <= 0;
            expected <= 0;
        end else begin
            if (!tracking && push && watch) begin
                tracking <= 1;
                expected <= in_data;
                ahead <= pop ? count - 1'b1 : count;
            end else if (tracking && pop) begin
                if (ahead == 0) tracking <= 0;
                else ahead <= ahead - 1'b1;
            end
            if (push) begin
                if (accepted < 255) accepted <= accepted + 1;
            end
            case ({push,pop})
                2'b10: count <= count + 1'b1;
                2'b01: count <= count - 1'b1;
                default: count <= count;
            endcase
        end

        if (past_valid && !rst && occupancy == DEPTH) seen_full <= 1;
        if (past_valid && !rst && occupancy == DEPTH && push && pop)
            seen_exchange <= 1;
        if (past_valid && rst && occupancy != 0) seen_reset_busy <= 1;
        cover(past_valid && !rst && occupancy == DEPTH);
        cover(past_valid && !rst && occupancy == DEPTH && push && pop);
        cover(past_valid && !rst && seen_full && occupancy == 0);
        cover(past_valid && !rst && accepted >= 3*DEPTH && seen_exchange);
        cover(past_valid && !rst && seen_reset_busy && occupancy == 0);
    end
endmodule
