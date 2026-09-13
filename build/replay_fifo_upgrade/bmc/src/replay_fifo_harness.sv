// Check the actual 49-bit, two-entry FIFO instantiated by replay_system.
// Reset on the first sampled edge is the only environmental assumption.
module replay_fifo_harness(input wire clk);
    (* anyseq *) reg rst, in_valid, out_ready, watch;
    (* anyseq *) reg [48:0] in_data;
    wire in_ready, out_valid;
    wire [48:0] out_data;
    wire [1:0] occupancy;
    replay_fifo dut (.*);

    reg past_valid = 0;
    reg [1:0] count, ahead;
    reg tracking;
    reg [48:0] expected;
    reg seen_full = 0, seen_exchange = 0, seen_reset_busy = 0;
    reg [3:0] accepted;
    wire push = in_valid && in_ready;
    wire pop = out_valid && out_ready;

    always @(posedge clk) begin
        past_valid <= 1;
        if (!past_valid) assume(rst);
        if (past_valid) begin
            assert(occupancy <= 2);
            assert(occupancy == count);
            assert(out_valid == (!rst && count != 0));
            assert(in_ready == (!rst && (count < 2 || out_ready)));
            // Universally select a transaction, retain all payload bits, and
            // count the accepted predecessors that must leave before it.
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
            if ($past(rst)) assert(occupancy == 0);
        end
        if (rst) begin
            count <= 0;
            ahead <= 0;
            tracking <= 0;
            expected <= 0;
            accepted <= 0;
        end else begin
            if (!tracking && push && watch) begin
                tracking <= 1;
                expected <= in_data;
                ahead <= pop ? count - 1'b1 : count;
            end else if (tracking && pop) begin
                if (ahead == 0) tracking <= 0;
                else ahead <= ahead - 1'b1;
            end
            case ({push, pop})
                2'b10: count <= count + 1'b1;
                2'b01: count <= count - 1'b1;
                default: begin end
            endcase
            if (push && accepted != 15) accepted <= accepted + 1'b1;
        end
        if (past_valid && !rst && occupancy == 2) seen_full <= 1;
        if (past_valid && !rst && occupancy == 2 && push && pop)
            seen_exchange <= 1;
        if (past_valid && rst && occupancy != 0) seen_reset_busy <= 1;
        cover(past_valid && !rst && occupancy == 2);
        cover(past_valid && !rst && occupancy == 2 && push && pop);
        cover(past_valid && !rst && seen_full && occupancy == 0);
        cover(past_valid && !rst && accepted >= 6 && seen_exchange);
        cover(past_valid && !rst && seen_reset_busy && occupancy == 0);
    end
endmodule
