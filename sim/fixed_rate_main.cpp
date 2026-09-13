#include "Vfixed_rate_tb.h"
#include "verilated.h"
#include <array>
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <limits>
#include <algorithm>
#include <stdexcept>
#include <vector>

struct RunResult {
    uint64_t cycles;
    uint64_t first_min, first_max, last_min, last_max, interval_min, interval_max;
    uint32_t generated, accepted, dropped, frames, protocol_errors, max_fifo, latency;
    double seconds;
};

static RunResult run(uint32_t frames, uint32_t period, uint32_t overload,
                     const std::array<int32_t,3>& expected, uint32_t expected_class) {
    Vfixed_rate_tb dut;
    dut.run_frames=frames; dut.period_cycles=period; dut.overload_frames=overload;
    dut.rst=1;
    for (int i=0;i<4;i++) { dut.clk=0; dut.eval(); dut.clk=1; dut.eval(); }
    dut.rst=0;
    uint64_t cycles=0, drain=0;
    uint32_t last_id=0;
    bool have_result=false;
    std::vector<uint32_t> seen;
    std::vector<uint64_t> first_sample(frames,0), last_sample(frames,0);
    uint32_t prior_generated=0;
    uint64_t first_min=std::numeric_limits<uint64_t>::max(), first_max=0;
    uint64_t last_min=std::numeric_limits<uint64_t>::max(), last_max=0;
    uint64_t interval_min=std::numeric_limits<uint64_t>::max(), interval_max=0, prior_output_cycle=0;
    const uint64_t limit=uint64_t(frames)*1024*period+1000000;
    auto started=std::chrono::steady_clock::now();
    while(cycles++ < limit) {
        dut.clk=0; dut.eval(); dut.clk=1; dut.eval();
        if(dut.generated_samples!=prior_generated) {
            uint32_t ordinal=dut.generated_samples-1;
            if(ordinal%1024==0) first_sample[ordinal/1024]=cycles;
            if(ordinal%1024==1023) last_sample[ordinal/1024]=cycles;
            prior_generated=dut.generated_samples;
        }
        if (dut.result_pulse) {
            for(int k=0;k<3;k++)
                if (int32_t(dut.result_logits[k])!=expected[k]) throw std::runtime_error("logit mismatch");
            if(dut.result_class!=expected_class || dut.result_error) throw std::runtime_error("class/error mismatch");
            if(have_result && dut.result_frame_id<=last_id) throw std::runtime_error("duplicate or reordered frame");
            if(!overload && dut.result_frame_id!=seen.size()) throw std::runtime_error("missing normal frame");
            if(dut.result_frame_id>=frames || !last_sample[dut.result_frame_id]) throw std::runtime_error("result precedes complete source frame");
            uint64_t from_first=cycles-first_sample[dut.result_frame_id];
            uint64_t from_last=cycles-last_sample[dut.result_frame_id];
            first_min=std::min(first_min,from_first); first_max=std::max(first_max,from_first);
            last_min=std::min(last_min,from_last); last_max=std::max(last_max,from_last);
            if(prior_output_cycle) {
                interval_min=std::min(interval_min,cycles-prior_output_cycle);
                interval_max=std::max(interval_max,cycles-prior_output_cycle);
            }
            prior_output_cycle=cycles;
            last_id=dut.result_frame_id; have_result=true; seen.push_back(last_id);
        }
        if(dut.source_done && ++drain==400000) break;
    }
    if(!dut.source_done) throw std::runtime_error("source deadline exceeded");
    if(dut.generated_samples!=frames*1024) throw std::runtime_error("source cadence/sample count mismatch");
    if(dut.accepted_samples+dut.dropped_samples!=dut.generated_samples) throw std::runtime_error("sample conservation failure");
    if(!overload) {
        if(dut.dropped_samples || dut.protocol_errors || dut.output_frames!=frames) throw std::runtime_error("normal-rate loss");
        if(dut.result_latency>=1024*period) throw std::runtime_error("processing misses window deadline");
    } else {
        if(!dut.dropped_samples || !dut.protocol_errors) throw std::runtime_error("overload not detected");
        for(uint32_t id=frames-3;id<frames;id++) {
            bool found=false; for(auto x:seen) if(x==id) found=true;
            if(!found) throw std::runtime_error("did not recover after overload without reset");
        }
    }
    auto seconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-started).count();
    RunResult result{};
    result.cycles=cycles; result.generated=dut.generated_samples; result.accepted=dut.accepted_samples;
    result.dropped=dut.dropped_samples; result.frames=dut.output_frames; result.protocol_errors=dut.protocol_errors;
    result.max_fifo=dut.maximum_fifo_occupancy; result.latency=dut.result_latency; result.seconds=seconds;
    result.first_min=first_min; result.first_max=first_max; result.last_min=last_min; result.last_max=last_max;
    result.interval_min=seen.size()>1 ? interval_min : 0; result.interval_max=interval_max;
    dut.final(); return result;
}

int main(int argc,char** argv) {
    Verilated::commandArgs(argc,argv);
    if(argc!=7) { std::cerr<<"frames expected0 expected1 expected2 class report.json\n"; return 2; }
    try {
        uint32_t frames=std::stoul(argv[1]);
        std::array<int32_t,3> expected{std::stoi(argv[2]),std::stoi(argv[3]),std::stoi(argv[4])};
        uint32_t cls=std::stoul(argv[5]);
        RunResult normal=run(frames,1000,0,expected,cls);
        std::cout<<"fixed rate: "<<normal.frames<<" frames, "<<normal.cycles<<" clocks, "<<normal.seconds<<" seconds\n"<<std::flush;
        RunResult overload=run(12,1000,8,expected,cls);
        std::ofstream out(argv[6]);
        auto write=[&](const char* name,const RunResult& r) {
            out<<"  \""<<name<<"\": {\"status\":\"passed\",\"cycles\":"<<r.cycles
               <<",\"generated_samples\":"<<r.generated<<",\"accepted_samples\":"<<r.accepted
               <<",\"dropped_samples\":"<<r.dropped<<",\"output_frames\":"<<r.frames
               <<",\"protocol_errors\":"<<r.protocol_errors<<",\"max_fifo_occupancy\":"<<r.max_fifo
               <<",\"processing_cycles\":"<<r.latency<<",\"wall_seconds\":"<<r.seconds<<"}";
        };
        auto write_timing=[&](const char* name,const RunResult& r) {
            out<<"  \""<<name<<"\": {\"first_sample_to_result_min\":"<<r.first_min
               <<",\"first_sample_to_result_max\":"<<r.first_max
               <<",\"last_sample_to_result_min\":"<<r.last_min
               <<",\"last_sample_to_result_max\":"<<r.last_max
               <<",\"output_interval_min\":"<<r.interval_min
               <<",\"output_interval_max\":"<<r.interval_max<<"}";
        };
        out<<"{\n"; write("normal",normal); out<<",\n"; write("overload_and_recovery",overload);
        out<<",\n"; write_timing("normal_timing_cycles",normal);
        out<<",\n"; write_timing("overload_timing_cycles",overload);
        out<<",\n  \"timing_basis\":\"source sample-offer edge to output handshake; includes input FIFO transit\","
              "\n  \"input_fifo_depth\":4,\n  \"normal_sample_period_cycles\":1000,"
              "\n  \"target_clock_hz\":12000000\n}\n";
        std::cout<<"overload/recovery passed: "<<overload.dropped<<" drops flagged\n";
    } catch(const std::exception& error) { std::cerr<<error.what()<<"\n"; return 1; }
    return 0;
}
