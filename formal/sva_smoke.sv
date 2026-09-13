module sva_smoke;
    bit clk = 0;
    bit rst = 1;
    bit inject_failure;
    integer count = 0;
    always #5 clk = !clk;
    always @(posedge clk) begin
        if (rst) count <= 0;
        else count <= count + ((inject_failure && count == 3) ? 2 : 1);
    end
    // Check the sampled implication and $past subset this project may use.
    assert property (@(posedge clk) disable iff (rst)
                     !rst |=> count == $past(count) + 1)
        else $fatal(1, "SVA_INCREMENT_FAILURE");
    initial begin
        inject_failure = $test$plusargs("FAIL");
        #12 rst = 0;
        #100 $display("SVA_SMOKE_PASS");
        $finish;
    end
endmodule
