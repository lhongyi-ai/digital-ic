`timescale 1ns/1ps
`include "config.svh"
module known_vivado_tb;
localparam N=`N, WINDOWS=`WINDOWS, LANES=`LANES, CLIPS=`CLIPS, F=N/2;
localparam SAMPLES=N*WINDOWS*CLIPS, FRAMES=WINDOWS*CLIPS;
localparam CHECKS=FRAMES*(N+4*F)+CLIPS*(2*F+1);
reg clk=0; always #5 clk=~clk;
reg rst=1,in_valid=0,in_last=0,out_ready=0;
reg signed [15:0] in_sample=0; reg [31:0] in_frame_id=0;
wire in_ready,out_valid,out_class,dbg_valid;
wire signed [31:0] out_score;wire [31:0] out_frame_id,cycles_pre,cycles_dft,cycles_power,cycles_nn,cycles_total,protocol_errors,accepted_samples;
wire [7:0] out_error;wire [3:0] dbg_kind;wire [31:0] dbg_frame;wire [15:0] dbg_index;wire signed [63:0] dbg_value;
known_spectral_core #(.N(N),.WINDOWS(WINDOWS),.LANES(LANES),.QUANT_PIPELINE(`QUANT_PIPELINE),.MODEL_DIR("model"),.BIAS(`BIAS),.THRESHOLD(`THRESHOLD),.LOG_CONSTANT(`LOG_CONSTANT),.LOG_FLOOR(`LOG_FLOOR)) dut(.*);
reg [15:0] raw[0:SAMPLES-1];reg signed [63:0] expected[0:CHECKS-1];reg seen[0:CHECKS-1];reg signed [31:0] scores[0:CLIPS-1];
integer sent=0,received=0,checks=0,cycle=0,hold_until=0,offset,c,w,k,i,fd,probe_sent,probe_cycles;
reg input_fire,output_fire,holding=0;
reg [233:0] held;
wire [233:0] output_fields={out_score,out_frame_id,out_class,out_error,cycles_pre,cycles_dft,cycles_power,cycles_nn,cycles_total};
initial begin
    $readmemh("raw.hex",raw);$readmemh("expected.hex",expected);$readmemh("scores.hex",scores);
    for(i=0;i<CHECKS;i=i+1)seen[i]=0;
    repeat(5) @(negedge clk);rst=0;
    // Bounded fixture specifically cancels an in-flight quantization state.
    if(N==16 && `QUANT_PIPELINE==1)begin
        probe_sent=0;probe_cycles=0;
        while(dut.state!=24)begin
            @(negedge clk);probe_cycles=probe_cycles+1;
            if(probe_cycles>100000)$fatal(1,"reset probe failed to reach NORM_QUANT");
            in_valid=probe_sent<N*WINDOWS;
            if(in_valid)begin in_sample=raw[probe_sent];in_frame_id=probe_sent/N;in_last=(probe_sent%N)==N-1;end
            #1;input_fire=in_valid&&in_ready;
            @(posedge clk);#1;if(input_fire)probe_sent=probe_sent+1;
        end
        @(negedge clk);rst=1;in_valid=0;
        repeat(3)@(negedge clk);
        if(out_valid||accepted_samples||protocol_errors)$fatal(1,"reset did not cancel old transaction");
        rst=0;
    end
    while(received<CLIPS) begin
        @(negedge clk);cycle=cycle+1;
        if(cycle>FRAMES*(2*N*N/LANES+200*N)+3*SAMPLES+100000)$fatal(1,"timeout");
        if(out_valid&&!holding)begin holding=1;hold_until=cycle+17;held=output_fields;end
        if(holding&&(!out_valid||output_fields!==held))$fatal(1,"output changed during backpressure");
        out_ready=holding&&cycle>=hold_until;
        in_valid=sent<SAMPLES && ((cycle%19)>1);
        if(sent<SAMPLES)begin in_sample=raw[sent];in_frame_id=sent/N;in_last=(sent%N)==N-1;end
        #1;input_fire=in_valid&&in_ready;output_fire=out_valid&&out_ready;
        if(output_fire)begin
            if(out_score!==scores[received]||out_class!==(scores[received]>`THRESHOLD)||out_frame_id!==received*WINDOWS||out_error!==0)$fatal(1,"output mismatch clip %0d",received);
            if(cycles_total!==cycles_pre+cycles_dft+cycles_power+cycles_nn)$fatal(1,"cycle accounting mismatch");
        end
        @(posedge clk);#1;
        if(input_fire)sent=sent+1;
        if(output_fire)begin received=received+1;holding=0;end
        if(dbg_valid)begin
            if(dbg_frame>=FRAMES)$fatal(1,"bad debug frame");
            c=dbg_frame/WINDOWS;w=dbg_frame%WINDOWS;
            if(dbg_kind==0&&dbg_index<N)offset=dbg_frame*(N+4*F)+dbg_index;
            else if(dbg_kind>=1&&dbg_kind<=4&&dbg_index<F)offset=dbg_frame*(N+4*F)+N+(dbg_kind-1)*F+dbg_index;
            else if(w==WINDOWS-1&&dbg_kind>=5&&dbg_kind<=7)begin
                offset=FRAMES*(N+4*F)+c*(2*F+1);
                if(dbg_kind==5&&dbg_index<F)offset=offset+dbg_index;
                else if(dbg_kind==6&&dbg_index<F)offset=offset+F+dbg_index;
                else if(dbg_kind==7&&dbg_index==0)offset=offset+2*F;
                else $fatal(1,"bad final index");
            end else $fatal(1,"unexpected debug event");
            if(seen[offset])$fatal(1,"duplicate event");
            if(dbg_value!==expected[offset])$fatal(1,"mismatch frame %0d kind %0d index %0d actual %0d expected %0d",dbg_frame,dbg_kind,dbg_index,dbg_value,expected[offset]);
            seen[offset]=1;checks=checks+1;
        end
    end
    if(sent!=SAMPLES||checks!=CHECKS||protocol_errors!=0||accepted_samples!=SAMPLES)$fatal(1,"missing event or sample");
    fd=$fopen("simulation.json","w");$fdisplay(fd,"{\"passed\":true,\"clips\":%0d,\"windows\":%0d,\"samples\":%0d,\"intermediate_checks\":%0d,\"cycles\":%0d,\"physical_hardware\":false}",CLIPS,FRAMES,SAMPLES,CHECKS,cycle);$fclose(fd);
    $display("VIVADO_PORTABILITY_COMPLETE");$finish;
end
endmodule
