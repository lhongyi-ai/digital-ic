set_param general.maxThreads 2
source config.tcl
foreach path $sources {read_verilog -sv -define AMD_FPGA $path}
synth_design -top known_spectral_core -part xc7a35tcpg236-1 -mode out_of_context -generic $generics
report_utilization -file utilization.rpt
write_checkpoint -force synthesized.dcp
if {$stage eq "impl"} {
    read_xdc core.xdc
    opt_design
    place_design
    route_design
    report_timing_summary -delay_type min_max -report_unconstrained -file timing_summary.rpt
    report_timing -from [all_registers -clock clk] -to [all_registers -clock clk] -max_paths 20 -path_type full_clock_expanded -file critical_paths.rpt
    report_timing -delay_type min -max_paths 20 -file hold_paths.rpt
    check_timing -verbose -file check_timing.rpt
    report_drc -file drc.rpt
    report_utilization -file utilization.rpt
    write_checkpoint -force routed.dcp
    set internal [get_timing_paths -from [all_registers -clock clk] -to [all_registers -clock clk] -max_paths 1]
    set setup [get_timing_paths -delay_type max -max_paths 100000]
    set hold [get_timing_paths -delay_type min -max_paths 100000]
    if {[llength $internal]==0 || [llength $setup]==0 || [llength $hold]==0} {error "Missing timed paths"}
    set tns 0.0; foreach p $setup {set s [get_property SLACK $p]; if {$s<0} {set tns [expr {$tns+$s}]}}
    set htns 0.0; foreach p $hold {set s [get_property SLACK $p]; if {$s<0} {set htns [expr {$htns+$s}]}}
    set fd [open metrics.json w]
    puts $fd [format {{"internal_delay_ns":%s,"wns_ns":%s,"tns_ns":%s,"hold_wns_ns":%s,"hold_tns_ns":%s,"path_start":"%s","path_end":"%s"}} [get_property DATAPATH_DELAY $internal] [get_property SLACK [lindex $setup 0]] $tns [get_property SLACK [lindex $hold 0]] $htns [get_property STARTPOINT_PIN $internal] [get_property ENDPOINT_PIN $internal]]
    close $fd
}
puts VIVADO_PORTABILITY_COMPLETE
