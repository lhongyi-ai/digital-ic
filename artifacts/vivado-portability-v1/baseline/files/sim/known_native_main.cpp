#include "Vknown_spectral_core.h"
#include "verilated.h"
#include <cstdint>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
#include <array>

template<class T> T word(std::ifstream& f) {T v{};f.read(reinterpret_cast<char*>(&v),sizeof(v));if(!f)throw std::runtime_error("truncated vector");return v;}
template<class T> std::vector<T> array(std::ifstream& f,size_t n) {std::vector<T> v(n);f.read(reinterpret_cast<char*>(v.data()),n*sizeof(T));if(!f)throw std::runtime_error("truncated array");return v;}
struct Clip {std::vector<int16_t> raw,windowed;std::vector<int32_t> real,imag,log;std::vector<uint64_t> power,sum;std::vector<int8_t> features;int32_t score;};

int main(int argc,char** argv) {
 try {
    if(argc!=5)throw std::runtime_error("vector report lanes sample_period_cycles");
    std::ifstream f(argv[1],std::ios::binary);if(!f)throw std::runtime_error("missing vectors");
    if(word<uint32_t>(f)!=0x3150534b)throw std::runtime_error("bad format/endian");
    const uint32_t n=word<uint32_t>(f),windows=word<uint32_t>(f),count=word<uint32_t>(f);
    const int32_t threshold=word<int32_t>(f);const uint32_t bands=n/2;
    const uint32_t lanes=std::stoul(argv[3]),period=std::stoul(argv[4]);
    std::vector<Clip> clips;
    for(uint32_t c=0;c<count;c++) {
        Clip v;v.raw=array<int16_t>(f,n*windows);v.windowed=array<int16_t>(f,n*windows);
        v.real=array<int32_t>(f,bands*windows);v.imag=array<int32_t>(f,bands*windows);
        v.power=array<uint64_t>(f,bands*windows);v.sum=array<uint64_t>(f,bands*windows);
        v.log=array<int32_t>(f,bands);v.features=array<int8_t>(f,bands);v.score=word<int32_t>(f);clips.push_back(std::move(v));
    }
    const uint64_t samples=uint64_t(n)*windows*count,frames=uint64_t(windows)*count;
    const uint64_t expected_checks=frames*(n+4*bands)+uint64_t(count)*(2*bands+1);
    std::vector<uint8_t> seen(expected_checks);uint64_t checks=0,cycle=0,sent=0;uint32_t received=0;
    std::vector<uint64_t> first_sample(count,0),last_sample(count,0),first_output(count,0);
    std::vector<std::array<uint32_t,5>> stages(count);
    VerilatedContext context;context.commandArgs(argc,argv);Vknown_spectral_core d(&context);
    auto tick=[&](){d.clk=0;d.eval();context.timeInc(1);d.clk=1;d.eval();context.timeInc(1);cycle++;};
    d.rst=1;d.in_valid=0;d.out_ready=0;d.in_last=0;d.in_sample=0;d.in_frame_id=0;
    for(int i=0;i<5;i++)tick();d.rst=0;
    bool pending=false,hold=false;uint64_t release=0,stall_events=0;std::array<uint32_t,8> held{};
    const uint64_t limit=period?samples*period+frames*(n*n/lanes+200*n)+100000:
        frames*(n*n/lanes+200*n)+samples*3+100000;
    while(received<count&&cycle<limit) {
        d.clk=0;d.eval();
        if(d.out_valid&&!hold) {
            hold=true;release=cycle+17;first_output[received]=cycle;
            held={uint32_t(d.out_score),uint32_t(d.out_frame_id),uint32_t(d.out_class),uint32_t(d.out_error),
                  uint32_t(d.cycles_pre),uint32_t(d.cycles_dft),uint32_t(d.cycles_power),uint32_t(d.cycles_nn)};
        }
        d.out_ready=hold&&cycle>=release;
        if(hold&&d.out_valid) {
            const std::array<uint32_t,8> now={uint32_t(d.out_score),uint32_t(d.out_frame_id),uint32_t(d.out_class),uint32_t(d.out_error),
                uint32_t(d.cycles_pre),uint32_t(d.cycles_dft),uint32_t(d.cycles_power),uint32_t(d.cycles_nn)};
            if(now!=held)throw std::runtime_error("output changed during stall");
        }
        if(sent<samples) {
            if(period)pending=(cycle%period)==0;
            else if(!pending)pending=(cycle%19)!=0&&(cycle%19)!=1;
            d.in_valid=pending;const auto c=sent/(n*windows),p=sent%(n*windows);
            d.in_sample=uint16_t(clips[c].raw[p]);d.in_frame_id=sent/n;d.in_last=(sent%n)==n-1;
        } else {d.in_valid=0;d.in_last=0;}
        d.eval();const bool input_fire=d.in_valid&&d.in_ready,output_fire=d.out_valid&&d.out_ready;
        if(d.in_valid&&!d.in_ready) {
            stall_events++;
            if(period)throw std::runtime_error("fixed-rate input overflow at sample "+std::to_string(sent));
        }
        if(input_fire) {
            auto c=sent/(n*windows);if(sent%(n*windows)==0)first_sample[c]=cycle;
            if(sent%(n*windows)==n*windows-1)last_sample[c]=cycle;
        }
        if(output_fire) {
            if(int32_t(d.out_score)!=clips[received].score || d.out_class!=(clips[received].score>threshold) ||
               d.out_frame_id!=received*windows||d.out_error!=0)throw std::runtime_error("classification/output metadata mismatch");
            if(d.cycles_total!=d.cycles_pre+d.cycles_dft+d.cycles_power+d.cycles_nn)throw std::runtime_error("cycle accounting mismatch");
            stages[received]={d.cycles_pre,d.cycles_dft,d.cycles_power,d.cycles_nn,d.cycles_total};
            received++;hold=false;
            std::cout<<"verified clip "<<received<<"/"<<count<<" cycle "<<cycle<<std::endl;
        }
        d.clk=1;d.eval();context.timeInc(2);cycle++;
        if(input_fire){sent++;pending=false;}
        if(d.dbg_valid) {
            uint32_t frame=d.dbg_frame,kind=d.dbg_kind,index=d.dbg_index;
            if(frame>=frames)throw std::runtime_error("debug frame out of range");
            uint32_t c=frame/windows,w=frame%windows;const Clip& v=clips[c];uint64_t expected=0,offset=0;
            if(kind==0&&index<n){expected=int64_t(v.windowed[w*n+index]);offset=uint64_t(frame)*(n+4*bands)+index;}
            else if(kind>=1&&kind<=4&&index<bands) {
                auto k=w*bands+index;
                if(kind==1)expected=int64_t(v.real[k]);else if(kind==2)expected=int64_t(v.imag[k]);else if(kind==3)expected=v.power[k];else expected=v.sum[k];
                offset=uint64_t(frame)*(n+4*bands)+n+(kind-1)*bands+index;
            } else if(w==windows-1&&kind>=5&&kind<=7) {
                offset=frames*(n+4*bands)+uint64_t(c)*(2*bands+1);
                if(kind==5&&index<bands){expected=int64_t(v.log[index]);offset+=index;}
                else if(kind==6&&index<bands){expected=int64_t(v.features[index]);offset+=bands+index;}
                else if(kind==7&&index==0){expected=int64_t(v.score);offset+=2*bands;}
                else throw std::runtime_error("bad final-stage index");
            } else throw std::runtime_error("unexpected debug stage");
            if(d.dbg_value!=expected)throw std::runtime_error("stage mismatch frame="+std::to_string(frame)+" kind="+std::to_string(kind)+" index="+std::to_string(index)+" actual="+std::to_string(int64_t(d.dbg_value))+" expected="+std::to_string(int64_t(expected)));
            if(seen[offset])throw std::runtime_error("duplicate debug value");seen[offset]=1;checks++;
        }
    }
    if(received!=count||sent!=samples||checks!=expected_checks||d.protocol_errors!=0||d.accepted_samples!=samples)
        throw std::runtime_error("timeout, missing stage, sample, or output");
    std::ofstream report(argv[2]);report<<"{\"passed\":true,\"clips\":"<<count<<",\"windows\":"<<frames<<",\"lanes\":"<<lanes
       <<",\"samples\":"<<samples<<",\"intermediate_checks\":"<<checks<<",\"cycles\":"<<cycle<<",\"sample_period_cycles\":"<<period
       <<",\"backpressure_cycles\":"<<stall_events<<",\"dropped_samples\":0,\"physical_hardware\":false,\"stages\":[";
    for(uint32_t c=0;c<count;c++){if(c)report<<",";report<<"{\"pre\":"<<stages[c][0]<<",\"dft\":"<<stages[c][1]<<",\"power\":"<<stages[c][2]
       <<",\"nn\":"<<stages[c][3]<<",\"total\":"<<stages[c][4]<<",\"first_sample_to_output\":"<<first_output[c]-first_sample[c]
       <<",\"last_sample_to_output\":"<<first_output[c]-last_sample[c]<<"}";}
    report<<"]}\n";d.final();std::cout<<"PASS "<<frames<<" windows "<<checks<<" intermediate values"<<std::endl;return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<std::endl;return 1;}
}
