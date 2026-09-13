//      // verilator_coverage annotation
        // One synchronous quarter-wave cosine ROM per multiplier lane.
        // Coefficients are Q2.14; exact quadrant endpoints are handled explicitly.
        module vib_coeff_rom #(
            parameter integer N = 1024,
            parameter bit HANN = 0,
            parameter MODEL_DIR = "artifacts/model"
        ) (
 18621238     input wire clk,
+18621238  point: type=toggle comment=clk:0->1 hier=vibration_core.g_lane[0].coeff_rom
+18621236  point: type=toggle comment=clk:1->0 hier=vibration_core.g_lane[0].coeff_rom
+18621238  point: type=toggle comment=clk:0->1 hier=vibration_core.hann_rom
+18621236  point: type=toggle comment=clk:1->0 hier=vibration_core.hann_rom
 6094870     input wire en,
+6094870  point: type=toggle comment=en:0->1 hier=vibration_core.g_lane[0].coeff_rom
+6094870  point: type=toggle comment=en:1->0 hier=vibration_core.g_lane[0].coeff_rom
+067588  point: type=toggle comment=en:0->1 hier=vibration_core.hann_rom
+067588  point: type=toggle comment=en:1->0 hier=vibration_core.hann_rom
 3081226     input wire [$clog2(N)-1:0] phase,
+1396746  point: type=toggle comment=phase[0]:0->1 hier=vibration_core.g_lane[0].coeff_rom
+1396746  point: type=toggle comment=phase[0]:1->0 hier=vibration_core.g_lane[0].coeff_rom
+1396742  point: type=toggle comment=phase[1]:0->1 hier=vibration_core.g_lane[0].coeff_rom
+1396742  point: type=toggle comment=phase[1]:1->0 hier=vibration_core.g_lane[0].coeff_rom
+1587204  point: type=toggle comment=phase[2]:0->1 hier=vibration_core.g_lane[0].coeff_rom
+1587204  point: type=toggle comment=phase[2]:1->0 hier=vibration_core.g_lane[0].coeff_rom
+1476098  point: type=toggle comment=phase[3]:0->1 hier=vibration_core.g_lane[0].coeff_rom
+1476098  point: type=toggle comment=phase[3]:1->0 hier=vibration_core.g_lane[0].coeff_rom
+1682440  point: type=toggle comment=phase[4]:0->1 hier=vibration_core.g_lane[0].coeff_rom
+1682440  point: type=toggle comment=phase[4]:1->0 hier=vibration_core.g_lane[0].coeff_rom
+1261828  point: type=toggle comment=phase[5]:0->1 hier=vibration_core.g_lane[0].coeff_rom
+1261828  point: type=toggle comment=phase[5]:1->0 hier=vibration_core.g_lane[0].coeff_rom
+2398664  point: type=toggle comment=phase[6]:0->1 hier=vibration_core.g_lane[0].coeff_rom
+2398664  point: type=toggle comment=phase[6]:1->0 hier=vibration_core.g_lane[0].coeff_rom
+1595142  point: type=toggle comment=phase[7]:0->1 hier=vibration_core.g_lane[0].coeff_rom
+1595142  point: type=toggle comment=phase[7]:1->0 hier=vibration_core.g_lane[0].coeff_rom
+1764770  point: type=toggle comment=phase[8]:0->1 hier=vibration_core.g_lane[0].coeff_rom
+1764768  point: type=toggle comment=phase[8]:1->0 hier=vibration_core.g_lane[0].coeff_rom
+1889762  point: type=toggle comment=phase[9]:0->1 hier=vibration_core.g_lane[0].coeff_rom
+1889762  point: type=toggle comment=phase[9]:1->0 hier=vibration_core.g_lane[0].coeff_rom
+3081226  point: type=toggle comment=phase[0]:0->1 hier=vibration_core.hann_rom
+3081224  point: type=toggle comment=phase[0]:1->0 hier=vibration_core.hann_rom
+1540612  point: type=toggle comment=phase[1]:0->1 hier=vibration_core.hann_rom
+1540610  point: type=toggle comment=phase[1]:1->0 hier=vibration_core.hann_rom
+770306  point: type=toggle comment=phase[2]:0->1 hier=vibration_core.hann_rom
+770304  point: type=toggle comment=phase[2]:1->0 hier=vibration_core.hann_rom
+385154  point: type=toggle comment=phase[3]:0->1 hier=vibration_core.hann_rom
+385152  point: type=toggle comment=phase[3]:1->0 hier=vibration_core.hann_rom
+192576  point: type=toggle comment=phase[4]:0->1 hier=vibration_core.hann_rom
+192574  point: type=toggle comment=phase[4]:1->0 hier=vibration_core.hann_rom
+096288  point: type=toggle comment=phase[5]:0->1 hier=vibration_core.hann_rom
+096286  point: type=toggle comment=phase[5]:1->0 hier=vibration_core.hann_rom
+048144  point: type=toggle comment=phase[6]:0->1 hier=vibration_core.hann_rom
+048142  point: type=toggle comment=phase[6]:1->0 hier=vibration_core.hann_rom
+024072  point: type=toggle comment=phase[7]:0->1 hier=vibration_core.hann_rom
+024070  point: type=toggle comment=phase[7]:1->0 hier=vibration_core.hann_rom
+012036  point: type=toggle comment=phase[8]:0->1 hier=vibration_core.hann_rom
+012034  point: type=toggle comment=phase[8]:1->0 hier=vibration_core.hann_rom
+006018  point: type=toggle comment=phase[9]:0->1 hier=vibration_core.hann_rom
+006016  point: type=toggle comment=phase[9]:1->0 hier=vibration_core.hann_rom
~1889762     output wire signed [15:0] coefficient
+1550006  point: type=toggle comment=coefficient[0]:0->1 hier=vibration_core.g_lane[0].coeff_rom
+1550006  point: type=toggle comment=coefficient[0]:1->0 hier=vibration_core.g_lane[0].coeff_rom
+1531156  point: type=toggle comment=coefficient[10]:0->1 hier=vibration_core.g_lane[0].coeff_rom
+1531156  point: type=toggle comment=coefficient[10]:1->0 hier=vibration_core.g_lane[0].coeff_rom
+1558438  point: type=toggle comment=coefficient[11]:0->1 hier=vibration_core.g_lane[0].coeff_rom
+1558438  point: type=toggle comment=coefficient[11]:1->0 hier=vibration_core.g_lane[0].coeff_rom
+1497676  point: type=toggle comment=coefficient[12]:0->1 hier=vibration_core.g_lane[0].coeff_rom
+1497674  point: type=toggle comment=coefficient[12]:1->0 hier=vibration_core.g_lane[0].coeff_rom
+1766510  point: type=toggle comment=coefficient[13]:0->1 hier=vibration_core.g_lane[0].coeff_rom
+1766510  point: type=toggle comment=coefficient[13]:1->0 hier=vibration_core.g_lane[0].coeff_rom
+1878602  point: type=toggle comment=coefficient[14]:0->1 hier=vibration_core.g_lane[0].coeff_rom
+1878602  point: type=toggle comment=coefficient[14]:1->0 hier=vibration_core.g_lane[0].coeff_rom
+1889762  point: type=toggle comment=coefficient[15]:0->1 hier=vibration_core.g_lane[0].coeff_rom
+1889762  point: type=toggle comment=coefficient[15]:1->0 hier=vibration_core.g_lane[0].coeff_rom
+1553974  point: type=toggle comment=coefficient[1]:0->1 hier=vibration_core.g_lane[0].coeff_rom
+1553974  point: type=toggle comment=coefficient[1]:1->0 hier=vibration_core.g_lane[0].coeff_rom
+1552486  point: type=toggle comment=coefficient[2]:0->1 hier=vibration_core.g_lane[0].coeff_rom
+1552486  point: type=toggle comment=coefficient[2]:1->0 hier=vibration_core.g_lane[0].coeff_rom
+1533386  point: type=toggle comment=coefficient[3]:0->1 hier=vibration_core.g_lane[0].coeff_rom
+1533386  point: type=toggle comment=coefficient[3]:1->0 hier=vibration_core.g_lane[0].coeff_rom
+1572326  point: type=toggle comment=coefficient[4]:0->1 hier=vibration_core.g_lane[0].coeff_rom
+1572324  point: type=toggle comment=coefficient[4]:1->0 hier=vibration_core.g_lane[0].coeff_rom
+1541076  point: type=toggle comment=coefficient[5]:0->1 hier=vibration_core.g_lane[0].coeff_rom
+1541076  point: type=toggle comment=coefficient[5]:1->0 hier=vibration_core.g_lane[0].coeff_rom
+1512306  point: type=toggle comment=coefficient[6]:0->1 hier=vibration_core.g_lane[0].coeff_rom
+1512304  point: type=toggle comment=coefficient[6]:1->0 hier=vibration_core.g_lane[0].coeff_rom
+1567862  point: type=toggle comment=coefficient[7]:0->1 hier=vibration_core.g_lane[0].coeff_rom
+1567862  point: type=toggle comment=coefficient[7]:1->0 hier=vibration_core.g_lane[0].coeff_rom
+1525204  point: type=toggle comment=coefficient[8]:0->1 hier=vibration_core.g_lane[0].coeff_rom
+1525204  point: type=toggle comment=coefficient[8]:1->0 hier=vibration_core.g_lane[0].coeff_rom
+1539592  point: type=toggle comment=coefficient[9]:0->1 hier=vibration_core.g_lane[0].coeff_rom
+1539592  point: type=toggle comment=coefficient[9]:1->0 hier=vibration_core.g_lane[0].coeff_rom
+015048  point: type=toggle comment=coefficient[0]:0->1 hier=vibration_core.hann_rom
+015048  point: type=toggle comment=coefficient[0]:1->0 hier=vibration_core.hann_rom
+001056  point: type=toggle comment=coefficient[10]:0->1 hier=vibration_core.hann_rom
+001056  point: type=toggle comment=coefficient[10]:1->0 hier=vibration_core.hann_rom
+000528  point: type=toggle comment=coefficient[11]:0->1 hier=vibration_core.hann_rom
+000528  point: type=toggle comment=coefficient[11]:1->0 hier=vibration_core.hann_rom
+000264  point: type=toggle comment=coefficient[12]:0->1 hier=vibration_core.hann_rom
+000264  point: type=toggle comment=coefficient[12]:1->0 hier=vibration_core.hann_rom
+000132  point: type=toggle comment=coefficient[13]:0->1 hier=vibration_core.hann_rom
+000132  point: type=toggle comment=coefficient[13]:1->0 hier=vibration_core.hann_rom
+000066  point: type=toggle comment=coefficient[14]:0->1 hier=vibration_core.hann_rom
+000066  point: type=toggle comment=coefficient[14]:1->0 hier=vibration_core.hann_rom
-000000  point: type=toggle comment=coefficient[15]:0->1 hier=vibration_core.hann_rom
-000000  point: type=toggle comment=coefficient[15]:1->0 hier=vibration_core.hann_rom
+018084  point: type=toggle comment=coefficient[1]:0->1 hier=vibration_core.hann_rom
+018084  point: type=toggle comment=coefficient[1]:1->0 hier=vibration_core.hann_rom
+016104  point: type=toggle comment=coefficient[2]:0->1 hier=vibration_core.hann_rom
+016104  point: type=toggle comment=coefficient[2]:1->0 hier=vibration_core.hann_rom
+014520  point: type=toggle comment=coefficient[3]:0->1 hier=vibration_core.hann_rom
+014520  point: type=toggle comment=coefficient[3]:1->0 hier=vibration_core.hann_rom
+020196  point: type=toggle comment=coefficient[4]:0->1 hier=vibration_core.hann_rom
+020196  point: type=toggle comment=coefficient[4]:1->0 hier=vibration_core.hann_rom
+019668  point: type=toggle comment=coefficient[5]:0->1 hier=vibration_core.hann_rom
+019668  point: type=toggle comment=coefficient[5]:1->0 hier=vibration_core.hann_rom
+016896  point: type=toggle comment=coefficient[6]:0->1 hier=vibration_core.hann_rom
+016896  point: type=toggle comment=coefficient[6]:1->0 hier=vibration_core.hann_rom
+008448  point: type=toggle comment=coefficient[7]:0->1 hier=vibration_core.hann_rom
+008448  point: type=toggle comment=coefficient[7]:1->0 hier=vibration_core.hann_rom
+004224  point: type=toggle comment=coefficient[8]:0->1 hier=vibration_core.hann_rom
+004224  point: type=toggle comment=coefficient[8]:1->0 hier=vibration_core.hann_rom
+002112  point: type=toggle comment=coefficient[9]:0->1 hier=vibration_core.hann_rom
+002112  point: type=toggle comment=coefficient[9]:1->0 hier=vibration_core.hann_rom
        );
            localparam integer P = $clog2(N);
            localparam integer Q = P-2;
            (* ram_style = "block" *) reg signed [15:0] quarter [0:N/4-1];
~1866454     reg signed [15:0] magnitude;
+1550006  point: type=toggle comment=magnitude[0]:0->1 hier=vibration_core.g_lane[0].coeff_rom
+1550006  point: type=toggle comment=magnitude[0]:1->0 hier=vibration_core.g_lane[0].coeff_rom
+1499412  point: type=toggle comment=magnitude[10]:0->1 hier=vibration_core.g_lane[0].coeff_rom
+1499412  point: type=toggle comment=magnitude[10]:1->0 hier=vibration_core.g_lane[0].coeff_rom
+1474116  point: type=toggle comment=magnitude[11]:0->1 hier=vibration_core.g_lane[0].coeff_rom
+1474116  point: type=toggle comment=magnitude[11]:1->0 hier=vibration_core.g_lane[0].coeff_rom
+1866454  point: type=toggle comment=magnitude[12]:0->1 hier=vibration_core.g_lane[0].coeff_rom
+1866452  point: type=toggle comment=magnitude[12]:1->0 hier=vibration_core.g_lane[0].coeff_rom
+1602084  point: type=toggle comment=magnitude[13]:0->1 hier=vibration_core.g_lane[0].coeff_rom
+1602084  point: type=toggle comment=magnitude[13]:1->0 hier=vibration_core.g_lane[0].coeff_rom
+116066  point: type=toggle comment=magnitude[14]:0->1 hier=vibration_core.g_lane[0].coeff_rom
+116066  point: type=toggle comment=magnitude[14]:1->0 hier=vibration_core.g_lane[0].coeff_rom
-000000  point: type=toggle comment=magnitude[15]:0->1 hier=vibration_core.g_lane[0].coeff_rom
-000000  point: type=toggle comment=magnitude[15]:1->0 hier=vibration_core.g_lane[0].coeff_rom
+1566372  point: type=toggle comment=magnitude[1]:0->1 hier=vibration_core.g_lane[0].coeff_rom
+1566372  point: type=toggle comment=magnitude[1]:1->0 hier=vibration_core.g_lane[0].coeff_rom
+1555956  point: type=toggle comment=magnitude[2]:0->1 hier=vibration_core.g_lane[0].coeff_rom
+1555956  point: type=toggle comment=magnitude[2]:1->0 hier=vibration_core.g_lane[0].coeff_rom
+1532148  point: type=toggle comment=magnitude[3]:0->1 hier=vibration_core.g_lane[0].coeff_rom
+1532148  point: type=toggle comment=magnitude[3]:1->0 hier=vibration_core.g_lane[0].coeff_rom
+1503382  point: type=toggle comment=magnitude[4]:0->1 hier=vibration_core.g_lane[0].coeff_rom
+1503380  point: type=toggle comment=magnitude[4]:1->0 hier=vibration_core.g_lane[0].coeff_rom
+1515782  point: type=toggle comment=magnitude[5]:0->1 hier=vibration_core.g_lane[0].coeff_rom
+1515782  point: type=toggle comment=magnitude[5]:1->0 hier=vibration_core.g_lane[0].coeff_rom
+1567860  point: type=toggle comment=magnitude[6]:0->1 hier=vibration_core.g_lane[0].coeff_rom
+1567858  point: type=toggle comment=magnitude[6]:1->0 hier=vibration_core.g_lane[0].coeff_rom
+1477590  point: type=toggle comment=magnitude[7]:0->1 hier=vibration_core.g_lane[0].coeff_rom
+1477590  point: type=toggle comment=magnitude[7]:1->0 hier=vibration_core.g_lane[0].coeff_rom
+1541572  point: type=toggle comment=magnitude[8]:0->1 hier=vibration_core.g_lane[0].coeff_rom
+1541572  point: type=toggle comment=magnitude[8]:1->0 hier=vibration_core.g_lane[0].coeff_rom
+1489990  point: type=toggle comment=magnitude[9]:0->1 hier=vibration_core.g_lane[0].coeff_rom
+1489990  point: type=toggle comment=magnitude[9]:1->0 hier=vibration_core.g_lane[0].coeff_rom
+015048  point: type=toggle comment=magnitude[0]:0->1 hier=vibration_core.hann_rom
+015048  point: type=toggle comment=magnitude[0]:1->0 hier=vibration_core.hann_rom
+001056  point: type=toggle comment=magnitude[10]:0->1 hier=vibration_core.hann_rom
+001056  point: type=toggle comment=magnitude[10]:1->0 hier=vibration_core.hann_rom
+000528  point: type=toggle comment=magnitude[11]:0->1 hier=vibration_core.hann_rom
+000528  point: type=toggle comment=magnitude[11]:1->0 hier=vibration_core.hann_rom
+000264  point: type=toggle comment=magnitude[12]:0->1 hier=vibration_core.hann_rom
+000264  point: type=toggle comment=magnitude[12]:1->0 hier=vibration_core.hann_rom
-000000  point: type=toggle comment=magnitude[13]:0->1 hier=vibration_core.hann_rom
-000000  point: type=toggle comment=magnitude[13]:1->0 hier=vibration_core.hann_rom
-000000  point: type=toggle comment=magnitude[14]:0->1 hier=vibration_core.hann_rom
-000000  point: type=toggle comment=magnitude[14]:1->0 hier=vibration_core.hann_rom
-000000  point: type=toggle comment=magnitude[15]:0->1 hier=vibration_core.hann_rom
-000000  point: type=toggle comment=magnitude[15]:1->0 hier=vibration_core.hann_rom
+018216  point: type=toggle comment=magnitude[1]:0->1 hier=vibration_core.hann_rom
+018216  point: type=toggle comment=magnitude[1]:1->0 hier=vibration_core.hann_rom
+015840  point: type=toggle comment=magnitude[2]:0->1 hier=vibration_core.hann_rom
+015840  point: type=toggle comment=magnitude[2]:1->0 hier=vibration_core.hann_rom
+014784  point: type=toggle comment=magnitude[3]:0->1 hier=vibration_core.hann_rom
+014784  point: type=toggle comment=magnitude[3]:1->0 hier=vibration_core.hann_rom
+020064  point: type=toggle comment=magnitude[4]:0->1 hier=vibration_core.hann_rom
+020064  point: type=toggle comment=magnitude[4]:1->0 hier=vibration_core.hann_rom
+019536  point: type=toggle comment=magnitude[5]:0->1 hier=vibration_core.hann_rom
+019536  point: type=toggle comment=magnitude[5]:1->0 hier=vibration_core.hann_rom
+016896  point: type=toggle comment=magnitude[6]:0->1 hier=vibration_core.hann_rom
+016896  point: type=toggle comment=magnitude[6]:1->0 hier=vibration_core.hann_rom
+008448  point: type=toggle comment=magnitude[7]:0->1 hier=vibration_core.hann_rom
+008448  point: type=toggle comment=magnitude[7]:1->0 hier=vibration_core.hann_rom
+004224  point: type=toggle comment=magnitude[8]:0->1 hier=vibration_core.hann_rom
+004224  point: type=toggle comment=magnitude[8]:1->0 hier=vibration_core.hann_rom
+002112  point: type=toggle comment=magnitude[9]:0->1 hier=vibration_core.hann_rom
+002112  point: type=toggle comment=magnitude[9]:1->0 hier=vibration_core.hann_rom
 1887530     reg negative, is_zero;
+052576  point: type=toggle comment=is_zero:0->1 hier=vibration_core.g_lane[0].coeff_rom
+052576  point: type=toggle comment=is_zero:1->0 hier=vibration_core.g_lane[0].coeff_rom
+000132  point: type=toggle comment=is_zero:0->1 hier=vibration_core.hann_rom
+000132  point: type=toggle comment=is_zero:1->0 hier=vibration_core.hann_rom
+1887530  point: type=toggle comment=negative:0->1 hier=vibration_core.g_lane[0].coeff_rom
+1887530  point: type=toggle comment=negative:1->0 hier=vibration_core.g_lane[0].coeff_rom
+000066  point: type=toggle comment=negative:0->1 hier=vibration_core.hann_rom
+000066  point: type=toggle comment=negative:1->0 hier=vibration_core.hann_rom
 3081226     wire [Q-1:0] offset = phase[Q-1:0];
+1396746  point: type=toggle comment=offset[0]:0->1 hier=vibration_core.g_lane[0].coeff_rom
+1396746  point: type=toggle comment=offset[0]:1->0 hier=vibration_core.g_lane[0].coeff_rom
+1396742  point: type=toggle comment=offset[1]:0->1 hier=vibration_core.g_lane[0].coeff_rom
+1396742  point: type=toggle comment=offset[1]:1->0 hier=vibration_core.g_lane[0].coeff_rom
+1587204  point: type=toggle comment=offset[2]:0->1 hier=vibration_core.g_lane[0].coeff_rom
+1587204  point: type=toggle comment=offset[2]:1->0 hier=vibration_core.g_lane[0].coeff_rom
+1476098  point: type=toggle comment=offset[3]:0->1 hier=vibration_core.g_lane[0].coeff_rom
+1476098  point: type=toggle comment=offset[3]:1->0 hier=vibration_core.g_lane[0].coeff_rom
+1682440  point: type=toggle comment=offset[4]:0->1 hier=vibration_core.g_lane[0].coeff_rom
+1682440  point: type=toggle comment=offset[4]:1->0 hier=vibration_core.g_lane[0].coeff_rom
+1261828  point: type=toggle comment=offset[5]:0->1 hier=vibration_core.g_lane[0].coeff_rom
+1261828  point: type=toggle comment=offset[5]:1->0 hier=vibration_core.g_lane[0].coeff_rom
+2398664  point: type=toggle comment=offset[6]:0->1 hier=vibration_core.g_lane[0].coeff_rom
+2398664  point: type=toggle comment=offset[6]:1->0 hier=vibration_core.g_lane[0].coeff_rom
+1595142  point: type=toggle comment=offset[7]:0->1 hier=vibration_core.g_lane[0].coeff_rom
+1595142  point: type=toggle comment=offset[7]:1->0 hier=vibration_core.g_lane[0].coeff_rom
+3081226  point: type=toggle comment=offset[0]:0->1 hier=vibration_core.hann_rom
+3081224  point: type=toggle comment=offset[0]:1->0 hier=vibration_core.hann_rom
+1540612  point: type=toggle comment=offset[1]:0->1 hier=vibration_core.hann_rom
+1540610  point: type=toggle comment=offset[1]:1->0 hier=vibration_core.hann_rom
+770306  point: type=toggle comment=offset[2]:0->1 hier=vibration_core.hann_rom
+770304  point: type=toggle comment=offset[2]:1->0 hier=vibration_core.hann_rom
+385154  point: type=toggle comment=offset[3]:0->1 hier=vibration_core.hann_rom
+385152  point: type=toggle comment=offset[3]:1->0 hier=vibration_core.hann_rom
+192576  point: type=toggle comment=offset[4]:0->1 hier=vibration_core.hann_rom
+192574  point: type=toggle comment=offset[4]:1->0 hier=vibration_core.hann_rom
+096288  point: type=toggle comment=offset[5]:0->1 hier=vibration_core.hann_rom
+096286  point: type=toggle comment=offset[5]:1->0 hier=vibration_core.hann_rom
+048144  point: type=toggle comment=offset[6]:0->1 hier=vibration_core.hann_rom
+048142  point: type=toggle comment=offset[6]:1->0 hier=vibration_core.hann_rom
+024072  point: type=toggle comment=offset[7]:0->1 hier=vibration_core.hann_rom
+024070  point: type=toggle comment=offset[7]:1->0 hier=vibration_core.hann_rom
 1889762     wire [1:0] quadrant = phase[P-1:P-2];
+1764770  point: type=toggle comment=quadrant[0]:0->1 hier=vibration_core.g_lane[0].coeff_rom
+1764768  point: type=toggle comment=quadrant[0]:1->0 hier=vibration_core.g_lane[0].coeff_rom
+1889762  point: type=toggle comment=quadrant[1]:0->1 hier=vibration_core.g_lane[0].coeff_rom
+1889762  point: type=toggle comment=quadrant[1]:1->0 hier=vibration_core.g_lane[0].coeff_rom
+012036  point: type=toggle comment=quadrant[0]:0->1 hier=vibration_core.hann_rom
+012034  point: type=toggle comment=quadrant[0]:1->0 hier=vibration_core.hann_rom
+006018  point: type=toggle comment=quadrant[1]:0->1 hier=vibration_core.hann_rom
+006016  point: type=toggle comment=quadrant[1]:1->0 hier=vibration_core.hann_rom
 46907266     wire [Q-1:0] address = quadrant[0] ? -offset : offset;
+1396746  point: type=toggle comment=address[0]:0->1 hier=vibration_core.g_lane[0].coeff_rom
+1396746  point: type=toggle comment=address[0]:1->0 hier=vibration_core.g_lane[0].coeff_rom
+1396742  point: type=toggle comment=address[1]:0->1 hier=vibration_core.g_lane[0].coeff_rom
+1396742  point: type=toggle comment=address[1]:1->0 hier=vibration_core.g_lane[0].coeff_rom
+1512804  point: type=toggle comment=address[2]:0->1 hier=vibration_core.g_lane[0].coeff_rom
+1512804  point: type=toggle comment=address[2]:1->0 hier=vibration_core.g_lane[0].coeff_rom
+1546036  point: type=toggle comment=address[3]:0->1 hier=vibration_core.g_lane[0].coeff_rom
+1546036  point: type=toggle comment=address[3]:1->0 hier=vibration_core.g_lane[0].coeff_rom
+1565382  point: type=toggle comment=address[4]:0->1 hier=vibration_core.g_lane[0].coeff_rom
+1565382  point: type=toggle comment=address[4]:1->0 hier=vibration_core.g_lane[0].coeff_rom
+1514788  point: type=toggle comment=address[5]:0->1 hier=vibration_core.g_lane[0].coeff_rom
+1514788  point: type=toggle comment=address[5]:1->0 hier=vibration_core.g_lane[0].coeff_rom
+1393270  point: type=toggle comment=address[6]:0->1 hier=vibration_core.g_lane[0].coeff_rom
+1393270  point: type=toggle comment=address[6]:1->0 hier=vibration_core.g_lane[0].coeff_rom
+1736004  point: type=toggle comment=address[7]:0->1 hier=vibration_core.g_lane[0].coeff_rom
+1736004  point: type=toggle comment=address[7]:1->0 hier=vibration_core.g_lane[0].coeff_rom
+3081226  point: type=toggle comment=address[0]:0->1 hier=vibration_core.hann_rom
+3081224  point: type=toggle comment=address[0]:1->0 hier=vibration_core.hann_rom
+1540612  point: type=toggle comment=address[1]:0->1 hier=vibration_core.hann_rom
+1540612  point: type=toggle comment=address[1]:1->0 hier=vibration_core.hann_rom
+770306  point: type=toggle comment=address[2]:0->1 hier=vibration_core.hann_rom
+770306  point: type=toggle comment=address[2]:1->0 hier=vibration_core.hann_rom
+385154  point: type=toggle comment=address[3]:0->1 hier=vibration_core.hann_rom
+385154  point: type=toggle comment=address[3]:1->0 hier=vibration_core.hann_rom
+192576  point: type=toggle comment=address[4]:0->1 hier=vibration_core.hann_rom
+192576  point: type=toggle comment=address[4]:1->0 hier=vibration_core.hann_rom
+096288  point: type=toggle comment=address[5]:0->1 hier=vibration_core.hann_rom
+096288  point: type=toggle comment=address[5]:1->0 hier=vibration_core.hann_rom
+048144  point: type=toggle comment=address[6]:0->1 hier=vibration_core.hann_rom
+048144  point: type=toggle comment=address[6]:1->0 hier=vibration_core.hann_rom
+024072  point: type=toggle comment=address[7]:0->1 hier=vibration_core.hann_rom
+024072  point: type=toggle comment=address[7]:1->0 hier=vibration_core.hann_rom
+46347172  point: type=expr comment=(quadrant[0]==0) => 0 hier=vibration_core.g_lane[0].coeff_rom
+46907266  point: type=expr comment=(quadrant[0]==1) => 1 hier=vibration_core.g_lane[0].coeff_rom
+46466718  point: type=expr comment=(quadrant[0]==0) => 0 hier=vibration_core.hann_rom
+46787720  point: type=expr comment=(quadrant[0]==1) => 1 hier=vibration_core.hann_rom
+46907266  point: type=branch comment=cond_then hier=vibration_core.g_lane[0].coeff_rom
+46787720  point: type=branch comment=cond_then hier=vibration_core.hann_rom
+46347172  point: type=branch comment=cond_else hier=vibration_core.g_lane[0].coeff_rom
+46466718  point: type=branch comment=cond_else hier=vibration_core.hann_rom
            generate if (HANN) begin: g_hann_init
 000002         initial $readmemh({MODEL_DIR, "/hann_quarter.hex"}, quarter);
+000002  point: type=line comment=block hier=vibration_core.hann_rom
            end else begin: g_cos_init
 000002         initial $readmemh({MODEL_DIR, "/cos_quarter.hex"}, quarter);
+000002  point: type=line comment=block hier=vibration_core.g_lane[0].coeff_rom
            end endgenerate
 18621238     always @(posedge clk) begin
+18621238  point: type=line comment=block hier=vibration_core.g_lane[0].coeff_rom
+18621238  point: type=line comment=block hier=vibration_core.hann_rom
 18553650         if (en) begin
+12526368  point: type=branch comment=else hier=vibration_core.g_lane[0].coeff_rom
+18553650  point: type=branch comment=else hier=vibration_core.hann_rom
+6094870  point: type=branch comment=if hier=vibration_core.g_lane[0].coeff_rom
+067588  point: type=branch comment=if hier=vibration_core.hann_rom
 6094870             magnitude <= quarter[address];
+6094870  point: type=branch comment=if hier=vibration_core.g_lane[0].coeff_rom
+067588  point: type=branch comment=if hier=vibration_core.hann_rom
 6094870             negative <= (quadrant == 1 || quadrant == 2);
+6094870  point: type=branch comment=if hier=vibration_core.g_lane[0].coeff_rom
+067588  point: type=branch comment=if hier=vibration_core.hann_rom
+3047434  point: type=expr comment=((quadrant == 32'sh1)==0 && (quadrant == 32'sh2)==0) => 0 hier=vibration_core.g_lane[0].coeff_rom
+1523718  point: type=expr comment=((quadrant == 32'sh1)==1) => 1 hier=vibration_core.g_lane[0].coeff_rom
+1523718  point: type=expr comment=((quadrant == 32'sh2)==1) => 1 hier=vibration_core.g_lane[0].coeff_rom
+033796  point: type=expr comment=((quadrant == 32'sh1)==0 && (quadrant == 32'sh2)==0) => 0 hier=vibration_core.hann_rom
+016896  point: type=expr comment=((quadrant == 32'sh1)==1) => 1 hier=vibration_core.hann_rom
+016896  point: type=expr comment=((quadrant == 32'sh2)==1) => 1 hier=vibration_core.hann_rom
 6094870             is_zero <= quadrant[0] && offset == 0;
+6094870  point: type=branch comment=if hier=vibration_core.g_lane[0].coeff_rom
+067588  point: type=branch comment=if hier=vibration_core.hann_rom
+5989714  point: type=expr comment=((offset == 32'sh0)==0) => 0 hier=vibration_core.g_lane[0].coeff_rom
+3047440  point: type=expr comment=(quadrant[0]==0) => 0 hier=vibration_core.g_lane[0].coeff_rom
+052576  point: type=expr comment=(quadrant[0]==1 && (offset == 32'sh0)==1) => 1 hier=vibration_core.g_lane[0].coeff_rom
+067320  point: type=expr comment=((offset == 32'sh0)==0) => 0 hier=vibration_core.hann_rom
+033796  point: type=expr comment=(quadrant[0]==0) => 0 hier=vibration_core.hann_rom
+000132  point: type=expr comment=(quadrant[0]==1 && (offset == 32'sh0)==1) => 1 hier=vibration_core.hann_rom
                end
            end
~93252434     assign coefficient = is_zero ? (HANN ? 16'sd8192 : 16'sd0) :
+92465640  point: type=expr comment=(is_zero==0) => 0 hier=vibration_core.g_lane[0].coeff_rom
+788798  point: type=expr comment=(is_zero==1) => 1 hier=vibration_core.g_lane[0].coeff_rom
+93252434  point: type=expr comment=(is_zero==0) => 0 hier=vibration_core.hann_rom
+002004  point: type=expr comment=(is_zero==1) => 1 hier=vibration_core.hann_rom
+788798  point: type=branch comment=cond_then hier=vibration_core.g_lane[0].coeff_rom
+002004  point: type=branch comment=cond_then hier=vibration_core.hann_rom
+92465640  point: type=branch comment=cond_else hier=vibration_core.g_lane[0].coeff_rom
+93252434  point: type=branch comment=cond_else hier=vibration_core.hann_rom
-000000  point: type=branch comment=cond_then hier=vibration_core.g_lane[0].coeff_rom
+002004  point: type=branch comment=cond_then hier=vibration_core.hann_rom
+788798  point: type=branch comment=cond_else hier=vibration_core.g_lane[0].coeff_rom
-000000  point: type=branch comment=cond_else hier=vibration_core.hann_rom
~92744444                          negative ? (HANN ? 16'sd16384-magnitude : -magnitude) : magnitude;
+45411276  point: type=branch comment=cond_then hier=vibration_core.g_lane[0].coeff_rom
+507990  point: type=branch comment=cond_then hier=vibration_core.hann_rom
+47054364  point: type=branch comment=cond_else hier=vibration_core.g_lane[0].coeff_rom
+92744444  point: type=branch comment=cond_else hier=vibration_core.hann_rom
-000000  point: type=branch comment=cond_then hier=vibration_core.g_lane[0].coeff_rom
+507990  point: type=branch comment=cond_then hier=vibration_core.hann_rom
+45411276  point: type=branch comment=cond_else hier=vibration_core.g_lane[0].coeff_rom
-000000  point: type=branch comment=cond_else hier=vibration_core.hann_rom
        endmodule
        
