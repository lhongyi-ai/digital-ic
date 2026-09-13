// Production-dimension pin-level replay. A native driver keeps ~120 million
// FPGA clocks practical; the independent cocotb NOR suite covers error paths.
#include "Vknown_replay_system.h"
#include "verilated.h"
#include <cstdint>
#include <fstream>
#include <iostream>
#include <iterator>
#include <stdexcept>
#include <vector>
static void require(bool ok,const char* message){if(!ok)throw std::runtime_error(message);}
struct Nor {
    std::vector<uint8_t> memory=std::vector<uint8_t>(0x400000,255),data;
    bool old_cs=true,old_clock=false,asleep=true,ignored=false,wel=false;
    uint64_t cycle=0,start=0,wake=0;uint32_t address=0;
    int opcode=-1,header=0,bits=0,wip=0;uint8_t rx=0,tx=255;
    unsigned reads=0,writes=0;
    uint8_t receive(uint8_t value){
        if(opcode<0){
            opcode=value;ignored=value!=0xab&&(asleep||start<wake);
            if(ignored)return 255;
            require(value==3||value==2||value==5||value==6||value==0xab,"unsupported SPI opcode");
            return value==5?(wip>0):255;
        }
        if(ignored||opcode==0xab)return 255;
        if((opcode==3||opcode==2)&&header<3){address=(address<<8)|value;header++;
            require(address<memory.size(),"NOR address outside device");
            return header==3&&opcode==3?memory[address]:255;}
        if(opcode==3){require(++address<memory.size(),"NOR read overflow");return memory[address];}
        if(opcode==2){data.push_back(value);return 255;}
        if(opcode==5){if(wip)wip--;return wip>0;}
        return 255;
    }
    void close(){
        if(ignored)return;
        if(opcode==0xab){asleep=false;wake=cycle+40;}
        if(opcode==6){require(!wip,"WREN while busy");wel=true;}
        if(opcode==3)reads++;
        if(opcode==2){
            require(wel&&!wip&&!data.empty()&&header==3,"invalid page program");
            require((address==0x300000&&data.size()==252)||(address==0x3000fc&&data.size()==4),"unexpected write region/order");
            require((writes==0&&address==0x300000)||(writes==1&&address==0x3000fc),"commit must follow body");
            for(size_t i=0;i<data.size();i++)memory[(address&~255u)|((address+i)&255)]&=data[i];
            writes++;wel=false;wip=2;
        }
    }
    void observe(Vknown_replay_system& d){
        bool cs=d.flash_cs_n,sck=d.flash_sclk;
        if(old_cs&&!cs){opcode=-1;header=bits=0;address=0;rx=0;tx=255;data.clear();ignored=false;start=cycle;d.flash_miso=1;}
        if(!old_cs&&cs)close();
        if(!cs){
            if(!old_clock&&sck){rx=uint8_t((rx<<1)|d.flash_mosi);if(++bits==8){tx=receive(rx);bits=0;rx=0;}}
            if(old_clock&&!sck)d.flash_miso=(tx>>(7-bits))&1;
        }
        old_cs=cs;old_clock=sck;
    }
};
int main(int argc,char** argv){
 try{
    require(argc==4,"image log cycle_limit required");
    std::ifstream input(argv[1],std::ios::binary);require(bool(input),"missing image");
    std::vector<uint8_t> image((std::istreambuf_iterator<char>(input)),{});
    require(image.size()>64&&image.size()<0x200000,"invalid image size");
    Nor nor;std::copy(image.begin(),image.end(),nor.memory.begin()+0x100000);
    VerilatedContext context;context.commandArgs(argc,argv);Vknown_replay_system d(&context);
    auto tick=[&](){d.clk=0;d.eval();nor.observe(d);context.timeInc(1);
        d.clk=1;d.eval();nor.observe(d);context.timeInc(1);nor.cycle++;};
    d.rst=1;d.flash_miso=1;for(int i=0;i<5;i++)tick();d.rst=0;
    uint64_t limit=std::stoull(argv[3]);
    while(!d.status_done&&nor.cycle<limit){
        tick();if(nor.cycle%30000000==0)std::cout<<"cycle "<<nor.cycle<<"\n"<<std::flush;
    }
    require(d.status_done,"complete application timed out");require(nor.writes==2,"log commit missing");
    std::ofstream out(argv[2],std::ios::binary);out.write(reinterpret_cast<char*>(nor.memory.data()+0x300000),4096);
    require(bool(out),"log write failed");
    std::cout<<"COMPLETED cycles="<<nor.cycle<<" reads="<<nor.reads<<" errors="<<unsigned(d.status_error)<<"\n";
    return 0;
 }catch(const std::exception& e){std::cerr<<"FAIL "<<e.what()<<"\n";return 1;}
}
