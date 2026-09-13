//      // verilator_coverage annotation
        // Fixed-point, frame-oriented vibration classifier. No processor is required.
        // A multiplier bank is time-shared by Hann, selected-bin DFT, power and MLP.
        module vibration_core #(
            parameter integer N = 1024,
            parameter integer LANES = 4,
            parameter integer BANDS = 1,
            parameter MODEL_DIR = "artifacts/model",
            parameter integer HIDDEN_SHIFT = 7
        ) (
 18621238     input wire clk,
+18621238  point: type=toggle comment=clk:0->1 hier=vibration_core
+18621236  point: type=toggle comment=clk:1->0 hier=vibration_core
 000026     input wire rst,
+000026  point: type=toggle comment=rst:0->1 hier=vibration_core
+000026  point: type=toggle comment=rst:1->0 hier=vibration_core
 000318     input wire in_valid,
+000318  point: type=toggle comment=in_valid:0->1 hier=vibration_core
+000318  point: type=toggle comment=in_valid:1->0 hier=vibration_core
 000058     output wire in_ready,
+000058  point: type=toggle comment=in_ready:0->1 hier=vibration_core
+000056  point: type=toggle comment=in_ready:1->0 hier=vibration_core
 015786     input wire signed [15:0] in_sample,
+015728  point: type=toggle comment=in_sample[0]:0->1 hier=vibration_core
+015728  point: type=toggle comment=in_sample[0]:1->0 hier=vibration_core
+014974  point: type=toggle comment=in_sample[10]:0->1 hier=vibration_core
+014974  point: type=toggle comment=in_sample[10]:1->0 hier=vibration_core
+013069  point: type=toggle comment=in_sample[11]:0->1 hier=vibration_core
+013068  point: type=toggle comment=in_sample[11]:1->0 hier=vibration_core
+012859  point: type=toggle comment=in_sample[12]:0->1 hier=vibration_core
+012858  point: type=toggle comment=in_sample[12]:1->0 hier=vibration_core
+013466  point: type=toggle comment=in_sample[13]:0->1 hier=vibration_core
+013465  point: type=toggle comment=in_sample[13]:1->0 hier=vibration_core
+013504  point: type=toggle comment=in_sample[14]:0->1 hier=vibration_core
+013503  point: type=toggle comment=in_sample[14]:1->0 hier=vibration_core
+013350  point: type=toggle comment=in_sample[15]:0->1 hier=vibration_core
+013349  point: type=toggle comment=in_sample[15]:1->0 hier=vibration_core
+015303  point: type=toggle comment=in_sample[1]:0->1 hier=vibration_core
+015303  point: type=toggle comment=in_sample[1]:1->0 hier=vibration_core
+015142  point: type=toggle comment=in_sample[2]:0->1 hier=vibration_core
+015140  point: type=toggle comment=in_sample[2]:1->0 hier=vibration_core
+015295  point: type=toggle comment=in_sample[3]:0->1 hier=vibration_core
+015295  point: type=toggle comment=in_sample[3]:1->0 hier=vibration_core
+015192  point: type=toggle comment=in_sample[4]:0->1 hier=vibration_core
+015191  point: type=toggle comment=in_sample[4]:1->0 hier=vibration_core
+014881  point: type=toggle comment=in_sample[5]:0->1 hier=vibration_core
+014881  point: type=toggle comment=in_sample[5]:1->0 hier=vibration_core
+015399  point: type=toggle comment=in_sample[6]:0->1 hier=vibration_core
+015397  point: type=toggle comment=in_sample[6]:1->0 hier=vibration_core
+015395  point: type=toggle comment=in_sample[7]:0->1 hier=vibration_core
+015394  point: type=toggle comment=in_sample[7]:1->0 hier=vibration_core
+015786  point: type=toggle comment=in_sample[8]:0->1 hier=vibration_core
+015785  point: type=toggle comment=in_sample[8]:1->0 hier=vibration_core
+015081  point: type=toggle comment=in_sample[9]:0->1 hier=vibration_core
+015080  point: type=toggle comment=in_sample[9]:1->0 hier=vibration_core
~000038     input wire [31:0] in_frame_id,
+000038  point: type=toggle comment=in_frame_id[0]:0->1 hier=vibration_core
+000036  point: type=toggle comment=in_frame_id[0]:1->0 hier=vibration_core
-000000  point: type=toggle comment=in_frame_id[10]:0->1 hier=vibration_core
-000000  point: type=toggle comment=in_frame_id[10]:1->0 hier=vibration_core
-000000  point: type=toggle comment=in_frame_id[11]:0->1 hier=vibration_core
-000000  point: type=toggle comment=in_frame_id[11]:1->0 hier=vibration_core
-000000  point: type=toggle comment=in_frame_id[12]:0->1 hier=vibration_core
-000000  point: type=toggle comment=in_frame_id[12]:1->0 hier=vibration_core
-000000  point: type=toggle comment=in_frame_id[13]:0->1 hier=vibration_core
-000000  point: type=toggle comment=in_frame_id[13]:1->0 hier=vibration_core
-000000  point: type=toggle comment=in_frame_id[14]:0->1 hier=vibration_core
-000000  point: type=toggle comment=in_frame_id[14]:1->0 hier=vibration_core
-000000  point: type=toggle comment=in_frame_id[15]:0->1 hier=vibration_core
-000000  point: type=toggle comment=in_frame_id[15]:1->0 hier=vibration_core
-000000  point: type=toggle comment=in_frame_id[16]:0->1 hier=vibration_core
-000000  point: type=toggle comment=in_frame_id[16]:1->0 hier=vibration_core
-000000  point: type=toggle comment=in_frame_id[17]:0->1 hier=vibration_core
-000000  point: type=toggle comment=in_frame_id[17]:1->0 hier=vibration_core
-000000  point: type=toggle comment=in_frame_id[18]:0->1 hier=vibration_core
-000000  point: type=toggle comment=in_frame_id[18]:1->0 hier=vibration_core
-000000  point: type=toggle comment=in_frame_id[19]:0->1 hier=vibration_core
-000000  point: type=toggle comment=in_frame_id[19]:1->0 hier=vibration_core
+000025  point: type=toggle comment=in_frame_id[1]:0->1 hier=vibration_core
+000023  point: type=toggle comment=in_frame_id[1]:1->0 hier=vibration_core
-000000  point: type=toggle comment=in_frame_id[20]:0->1 hier=vibration_core
-000000  point: type=toggle comment=in_frame_id[20]:1->0 hier=vibration_core
-000000  point: type=toggle comment=in_frame_id[21]:0->1 hier=vibration_core
-000000  point: type=toggle comment=in_frame_id[21]:1->0 hier=vibration_core
-000000  point: type=toggle comment=in_frame_id[22]:0->1 hier=vibration_core
-000000  point: type=toggle comment=in_frame_id[22]:1->0 hier=vibration_core
-000000  point: type=toggle comment=in_frame_id[23]:0->1 hier=vibration_core
-000000  point: type=toggle comment=in_frame_id[23]:1->0 hier=vibration_core
-000000  point: type=toggle comment=in_frame_id[24]:0->1 hier=vibration_core
-000000  point: type=toggle comment=in_frame_id[24]:1->0 hier=vibration_core
-000000  point: type=toggle comment=in_frame_id[25]:0->1 hier=vibration_core
-000000  point: type=toggle comment=in_frame_id[25]:1->0 hier=vibration_core
-000000  point: type=toggle comment=in_frame_id[26]:0->1 hier=vibration_core
-000000  point: type=toggle comment=in_frame_id[26]:1->0 hier=vibration_core
-000000  point: type=toggle comment=in_frame_id[27]:0->1 hier=vibration_core
-000000  point: type=toggle comment=in_frame_id[27]:1->0 hier=vibration_core
-000000  point: type=toggle comment=in_frame_id[28]:0->1 hier=vibration_core
-000000  point: type=toggle comment=in_frame_id[28]:1->0 hier=vibration_core
-000000  point: type=toggle comment=in_frame_id[29]:0->1 hier=vibration_core
-000000  point: type=toggle comment=in_frame_id[29]:1->0 hier=vibration_core
+000023  point: type=toggle comment=in_frame_id[2]:0->1 hier=vibration_core
+000021  point: type=toggle comment=in_frame_id[2]:1->0 hier=vibration_core
-000000  point: type=toggle comment=in_frame_id[30]:0->1 hier=vibration_core
-000000  point: type=toggle comment=in_frame_id[30]:1->0 hier=vibration_core
-000000  point: type=toggle comment=in_frame_id[31]:0->1 hier=vibration_core
-000000  point: type=toggle comment=in_frame_id[31]:1->0 hier=vibration_core
+000018  point: type=toggle comment=in_frame_id[3]:0->1 hier=vibration_core
+000018  point: type=toggle comment=in_frame_id[3]:1->0 hier=vibration_core
+000010  point: type=toggle comment=in_frame_id[4]:0->1 hier=vibration_core
+000008  point: type=toggle comment=in_frame_id[4]:1->0 hier=vibration_core
+000022  point: type=toggle comment=in_frame_id[5]:0->1 hier=vibration_core
+000020  point: type=toggle comment=in_frame_id[5]:1->0 hier=vibration_core
+000010  point: type=toggle comment=in_frame_id[6]:0->1 hier=vibration_core
+000010  point: type=toggle comment=in_frame_id[6]:1->0 hier=vibration_core
+000002  point: type=toggle comment=in_frame_id[7]:0->1 hier=vibration_core
+000002  point: type=toggle comment=in_frame_id[7]:1->0 hier=vibration_core
+000014  point: type=toggle comment=in_frame_id[8]:0->1 hier=vibration_core
+000012  point: type=toggle comment=in_frame_id[8]:1->0 hier=vibration_core
-000000  point: type=toggle comment=in_frame_id[9]:0->1 hier=vibration_core
-000000  point: type=toggle comment=in_frame_id[9]:1->0 hier=vibration_core
 000072     input wire in_last,
+000072  point: type=toggle comment=in_last:0->1 hier=vibration_core
+000072  point: type=toggle comment=in_last:1->0 hier=vibration_core
 000056     output reg out_valid,
+000056  point: type=toggle comment=out_valid:0->1 hier=vibration_core
+000056  point: type=toggle comment=out_valid:1->0 hier=vibration_core
 000054     input wire out_ready,
+000054  point: type=toggle comment=out_ready:0->1 hier=vibration_core
+000052  point: type=toggle comment=out_ready:1->0 hier=vibration_core
~000036     output reg [31:0] out_frame_id,
+000036  point: type=toggle comment=out_frame_id[0]:0->1 hier=vibration_core
+000034  point: type=toggle comment=out_frame_id[0]:1->0 hier=vibration_core
-000000  point: type=toggle comment=out_frame_id[10]:0->1 hier=vibration_core
-000000  point: type=toggle comment=out_frame_id[10]:1->0 hier=vibration_core
-000000  point: type=toggle comment=out_frame_id[11]:0->1 hier=vibration_core
-000000  point: type=toggle comment=out_frame_id[11]:1->0 hier=vibration_core
-000000  point: type=toggle comment=out_frame_id[12]:0->1 hier=vibration_core
-000000  point: type=toggle comment=out_frame_id[12]:1->0 hier=vibration_core
-000000  point: type=toggle comment=out_frame_id[13]:0->1 hier=vibration_core
-000000  point: type=toggle comment=out_frame_id[13]:1->0 hier=vibration_core
-000000  point: type=toggle comment=out_frame_id[14]:0->1 hier=vibration_core
-000000  point: type=toggle comment=out_frame_id[14]:1->0 hier=vibration_core
-000000  point: type=toggle comment=out_frame_id[15]:0->1 hier=vibration_core
-000000  point: type=toggle comment=out_frame_id[15]:1->0 hier=vibration_core
-000000  point: type=toggle comment=out_frame_id[16]:0->1 hier=vibration_core
-000000  point: type=toggle comment=out_frame_id[16]:1->0 hier=vibration_core
-000000  point: type=toggle comment=out_frame_id[17]:0->1 hier=vibration_core
-000000  point: type=toggle comment=out_frame_id[17]:1->0 hier=vibration_core
-000000  point: type=toggle comment=out_frame_id[18]:0->1 hier=vibration_core
-000000  point: type=toggle comment=out_frame_id[18]:1->0 hier=vibration_core
-000000  point: type=toggle comment=out_frame_id[19]:0->1 hier=vibration_core
-000000  point: type=toggle comment=out_frame_id[19]:1->0 hier=vibration_core
+000017  point: type=toggle comment=out_frame_id[1]:0->1 hier=vibration_core
+000015  point: type=toggle comment=out_frame_id[1]:1->0 hier=vibration_core
-000000  point: type=toggle comment=out_frame_id[20]:0->1 hier=vibration_core
-000000  point: type=toggle comment=out_frame_id[20]:1->0 hier=vibration_core
-000000  point: type=toggle comment=out_frame_id[21]:0->1 hier=vibration_core
-000000  point: type=toggle comment=out_frame_id[21]:1->0 hier=vibration_core
-000000  point: type=toggle comment=out_frame_id[22]:0->1 hier=vibration_core
-000000  point: type=toggle comment=out_frame_id[22]:1->0 hier=vibration_core
-000000  point: type=toggle comment=out_frame_id[23]:0->1 hier=vibration_core
-000000  point: type=toggle comment=out_frame_id[23]:1->0 hier=vibration_core
-000000  point: type=toggle comment=out_frame_id[24]:0->1 hier=vibration_core
-000000  point: type=toggle comment=out_frame_id[24]:1->0 hier=vibration_core
-000000  point: type=toggle comment=out_frame_id[25]:0->1 hier=vibration_core
-000000  point: type=toggle comment=out_frame_id[25]:1->0 hier=vibration_core
-000000  point: type=toggle comment=out_frame_id[26]:0->1 hier=vibration_core
-000000  point: type=toggle comment=out_frame_id[26]:1->0 hier=vibration_core
-000000  point: type=toggle comment=out_frame_id[27]:0->1 hier=vibration_core
-000000  point: type=toggle comment=out_frame_id[27]:1->0 hier=vibration_core
-000000  point: type=toggle comment=out_frame_id[28]:0->1 hier=vibration_core
-000000  point: type=toggle comment=out_frame_id[28]:1->0 hier=vibration_core
-000000  point: type=toggle comment=out_frame_id[29]:0->1 hier=vibration_core
-000000  point: type=toggle comment=out_frame_id[29]:1->0 hier=vibration_core
+000019  point: type=toggle comment=out_frame_id[2]:0->1 hier=vibration_core
+000017  point: type=toggle comment=out_frame_id[2]:1->0 hier=vibration_core
-000000  point: type=toggle comment=out_frame_id[30]:0->1 hier=vibration_core
-000000  point: type=toggle comment=out_frame_id[30]:1->0 hier=vibration_core
-000000  point: type=toggle comment=out_frame_id[31]:0->1 hier=vibration_core
-000000  point: type=toggle comment=out_frame_id[31]:1->0 hier=vibration_core
+000014  point: type=toggle comment=out_frame_id[3]:0->1 hier=vibration_core
+000014  point: type=toggle comment=out_frame_id[3]:1->0 hier=vibration_core
+000008  point: type=toggle comment=out_frame_id[4]:0->1 hier=vibration_core
+000006  point: type=toggle comment=out_frame_id[4]:1->0 hier=vibration_core
+000020  point: type=toggle comment=out_frame_id[5]:0->1 hier=vibration_core
+000018  point: type=toggle comment=out_frame_id[5]:1->0 hier=vibration_core
+000010  point: type=toggle comment=out_frame_id[6]:0->1 hier=vibration_core
+000010  point: type=toggle comment=out_frame_id[6]:1->0 hier=vibration_core
+000002  point: type=toggle comment=out_frame_id[7]:0->1 hier=vibration_core
+000002  point: type=toggle comment=out_frame_id[7]:1->0 hier=vibration_core
+000012  point: type=toggle comment=out_frame_id[8]:0->1 hier=vibration_core
+000010  point: type=toggle comment=out_frame_id[8]:1->0 hier=vibration_core
-000000  point: type=toggle comment=out_frame_id[9]:0->1 hier=vibration_core
-000000  point: type=toggle comment=out_frame_id[9]:1->0 hier=vibration_core
 000098     output reg [95:0] out_logits,
+000007  point: type=toggle comment=out_logits[0]:0->1 hier=vibration_core
+000007  point: type=toggle comment=out_logits[0]:1->0 hier=vibration_core
+000024  point: type=toggle comment=out_logits[10]:0->1 hier=vibration_core
+000022  point: type=toggle comment=out_logits[10]:1->0 hier=vibration_core
+000025  point: type=toggle comment=out_logits[11]:0->1 hier=vibration_core
+000023  point: type=toggle comment=out_logits[11]:1->0 hier=vibration_core
+000027  point: type=toggle comment=out_logits[12]:0->1 hier=vibration_core
+000025  point: type=toggle comment=out_logits[12]:1->0 hier=vibration_core
+000026  point: type=toggle comment=out_logits[13]:0->1 hier=vibration_core
+000024  point: type=toggle comment=out_logits[13]:1->0 hier=vibration_core
+000025  point: type=toggle comment=out_logits[14]:0->1 hier=vibration_core
+000023  point: type=toggle comment=out_logits[14]:1->0 hier=vibration_core
+000026  point: type=toggle comment=out_logits[15]:0->1 hier=vibration_core
+000024  point: type=toggle comment=out_logits[15]:1->0 hier=vibration_core
+000026  point: type=toggle comment=out_logits[16]:0->1 hier=vibration_core
+000024  point: type=toggle comment=out_logits[16]:1->0 hier=vibration_core
+000026  point: type=toggle comment=out_logits[17]:0->1 hier=vibration_core
+000024  point: type=toggle comment=out_logits[17]:1->0 hier=vibration_core
+000026  point: type=toggle comment=out_logits[18]:0->1 hier=vibration_core
+000024  point: type=toggle comment=out_logits[18]:1->0 hier=vibration_core
+000026  point: type=toggle comment=out_logits[19]:0->1 hier=vibration_core
+000024  point: type=toggle comment=out_logits[19]:1->0 hier=vibration_core
+000022  point: type=toggle comment=out_logits[1]:0->1 hier=vibration_core
+000020  point: type=toggle comment=out_logits[1]:1->0 hier=vibration_core
+000026  point: type=toggle comment=out_logits[20]:0->1 hier=vibration_core
+000024  point: type=toggle comment=out_logits[20]:1->0 hier=vibration_core
+000026  point: type=toggle comment=out_logits[21]:0->1 hier=vibration_core
+000024  point: type=toggle comment=out_logits[21]:1->0 hier=vibration_core
+000026  point: type=toggle comment=out_logits[22]:0->1 hier=vibration_core
+000024  point: type=toggle comment=out_logits[22]:1->0 hier=vibration_core
+000026  point: type=toggle comment=out_logits[23]:0->1 hier=vibration_core
+000024  point: type=toggle comment=out_logits[23]:1->0 hier=vibration_core
+000026  point: type=toggle comment=out_logits[24]:0->1 hier=vibration_core
+000024  point: type=toggle comment=out_logits[24]:1->0 hier=vibration_core
+000026  point: type=toggle comment=out_logits[25]:0->1 hier=vibration_core
+000024  point: type=toggle comment=out_logits[25]:1->0 hier=vibration_core
+000026  point: type=toggle comment=out_logits[26]:0->1 hier=vibration_core
+000024  point: type=toggle comment=out_logits[26]:1->0 hier=vibration_core
+000026  point: type=toggle comment=out_logits[27]:0->1 hier=vibration_core
+000024  point: type=toggle comment=out_logits[27]:1->0 hier=vibration_core
+000026  point: type=toggle comment=out_logits[28]:0->1 hier=vibration_core
+000024  point: type=toggle comment=out_logits[28]:1->0 hier=vibration_core
+000026  point: type=toggle comment=out_logits[29]:0->1 hier=vibration_core
+000024  point: type=toggle comment=out_logits[29]:1->0 hier=vibration_core
+000026  point: type=toggle comment=out_logits[2]:0->1 hier=vibration_core
+000024  point: type=toggle comment=out_logits[2]:1->0 hier=vibration_core
+000026  point: type=toggle comment=out_logits[30]:0->1 hier=vibration_core
+000024  point: type=toggle comment=out_logits[30]:1->0 hier=vibration_core
+000026  point: type=toggle comment=out_logits[31]:0->1 hier=vibration_core
+000024  point: type=toggle comment=out_logits[31]:1->0 hier=vibration_core
+000026  point: type=toggle comment=out_logits[32]:0->1 hier=vibration_core
+000038  point: type=toggle comment=out_logits[32]:1->0 hier=vibration_core
+000006  point: type=toggle comment=out_logits[33]:0->1 hier=vibration_core
+000048  point: type=toggle comment=out_logits[33]:1->0 hier=vibration_core
+000013  point: type=toggle comment=out_logits[34]:0->1 hier=vibration_core
+000063  point: type=toggle comment=out_logits[34]:1->0 hier=vibration_core
+000027  point: type=toggle comment=out_logits[35]:0->1 hier=vibration_core
+000033  point: type=toggle comment=out_logits[35]:1->0 hier=vibration_core
+000014  point: type=toggle comment=out_logits[36]:0->1 hier=vibration_core
+000060  point: type=toggle comment=out_logits[36]:1->0 hier=vibration_core
+000028  point: type=toggle comment=out_logits[37]:0->1 hier=vibration_core
+000034  point: type=toggle comment=out_logits[37]:1->0 hier=vibration_core
+000003  point: type=toggle comment=out_logits[38]:0->1 hier=vibration_core
+000013  point: type=toggle comment=out_logits[38]:1->0 hier=vibration_core
+000003  point: type=toggle comment=out_logits[39]:0->1 hier=vibration_core
+000057  point: type=toggle comment=out_logits[39]:1->0 hier=vibration_core
+000004  point: type=toggle comment=out_logits[3]:0->1 hier=vibration_core
+000004  point: type=toggle comment=out_logits[3]:1->0 hier=vibration_core
+000028  point: type=toggle comment=out_logits[40]:0->1 hier=vibration_core
+000036  point: type=toggle comment=out_logits[40]:1->0 hier=vibration_core
+000003  point: type=toggle comment=out_logits[41]:0->1 hier=vibration_core
+000031  point: type=toggle comment=out_logits[41]:1->0 hier=vibration_core
+000026  point: type=toggle comment=out_logits[42]:0->1 hier=vibration_core
+000070  point: type=toggle comment=out_logits[42]:1->0 hier=vibration_core
+000025  point: type=toggle comment=out_logits[43]:0->1 hier=vibration_core
+000071  point: type=toggle comment=out_logits[43]:1->0 hier=vibration_core
+000025  point: type=toggle comment=out_logits[44]:0->1 hier=vibration_core
+000075  point: type=toggle comment=out_logits[44]:1->0 hier=vibration_core
+000026  point: type=toggle comment=out_logits[45]:0->1 hier=vibration_core
+000074  point: type=toggle comment=out_logits[45]:1->0 hier=vibration_core
+000026  point: type=toggle comment=out_logits[46]:0->1 hier=vibration_core
+000072  point: type=toggle comment=out_logits[46]:1->0 hier=vibration_core
+000026  point: type=toggle comment=out_logits[47]:0->1 hier=vibration_core
+000074  point: type=toggle comment=out_logits[47]:1->0 hier=vibration_core
+000026  point: type=toggle comment=out_logits[48]:0->1 hier=vibration_core
+000074  point: type=toggle comment=out_logits[48]:1->0 hier=vibration_core
+000026  point: type=toggle comment=out_logits[49]:0->1 hier=vibration_core
+000074  point: type=toggle comment=out_logits[49]:1->0 hier=vibration_core
+000024  point: type=toggle comment=out_logits[4]:0->1 hier=vibration_core
+000022  point: type=toggle comment=out_logits[4]:1->0 hier=vibration_core
+000026  point: type=toggle comment=out_logits[50]:0->1 hier=vibration_core
+000074  point: type=toggle comment=out_logits[50]:1->0 hier=vibration_core
+000026  point: type=toggle comment=out_logits[51]:0->1 hier=vibration_core
+000074  point: type=toggle comment=out_logits[51]:1->0 hier=vibration_core
+000026  point: type=toggle comment=out_logits[52]:0->1 hier=vibration_core
+000074  point: type=toggle comment=out_logits[52]:1->0 hier=vibration_core
+000026  point: type=toggle comment=out_logits[53]:0->1 hier=vibration_core
+000074  point: type=toggle comment=out_logits[53]:1->0 hier=vibration_core
+000026  point: type=toggle comment=out_logits[54]:0->1 hier=vibration_core
+000074  point: type=toggle comment=out_logits[54]:1->0 hier=vibration_core
+000026  point: type=toggle comment=out_logits[55]:0->1 hier=vibration_core
+000074  point: type=toggle comment=out_logits[55]:1->0 hier=vibration_core
+000026  point: type=toggle comment=out_logits[56]:0->1 hier=vibration_core
+000074  point: type=toggle comment=out_logits[56]:1->0 hier=vibration_core
+000026  point: type=toggle comment=out_logits[57]:0->1 hier=vibration_core
+000074  point: type=toggle comment=out_logits[57]:1->0 hier=vibration_core
+000026  point: type=toggle comment=out_logits[58]:0->1 hier=vibration_core
+000074  point: type=toggle comment=out_logits[58]:1->0 hier=vibration_core
+000026  point: type=toggle comment=out_logits[59]:0->1 hier=vibration_core
+000074  point: type=toggle comment=out_logits[59]:1->0 hier=vibration_core
+000004  point: type=toggle comment=out_logits[5]:0->1 hier=vibration_core
+000004  point: type=toggle comment=out_logits[5]:1->0 hier=vibration_core
+000026  point: type=toggle comment=out_logits[60]:0->1 hier=vibration_core
+000074  point: type=toggle comment=out_logits[60]:1->0 hier=vibration_core
+000026  point: type=toggle comment=out_logits[61]:0->1 hier=vibration_core
+000074  point: type=toggle comment=out_logits[61]:1->0 hier=vibration_core
+000026  point: type=toggle comment=out_logits[62]:0->1 hier=vibration_core
+000074  point: type=toggle comment=out_logits[62]:1->0 hier=vibration_core
+000026  point: type=toggle comment=out_logits[63]:0->1 hier=vibration_core
+000074  point: type=toggle comment=out_logits[63]:1->0 hier=vibration_core
+000033  point: type=toggle comment=out_logits[64]:0->1 hier=vibration_core
+000081  point: type=toggle comment=out_logits[64]:1->0 hier=vibration_core
+000048  point: type=toggle comment=out_logits[65]:0->1 hier=vibration_core
+000056  point: type=toggle comment=out_logits[65]:1->0 hier=vibration_core
+000029  point: type=toggle comment=out_logits[66]:0->1 hier=vibration_core
+000053  point: type=toggle comment=out_logits[66]:1->0 hier=vibration_core
+000030  point: type=toggle comment=out_logits[67]:0->1 hier=vibration_core
+000080  point: type=toggle comment=out_logits[67]:1->0 hier=vibration_core
+000049  point: type=toggle comment=out_logits[68]:0->1 hier=vibration_core
+000073  point: type=toggle comment=out_logits[68]:1->0 hier=vibration_core
+000017  point: type=toggle comment=out_logits[69]:0->1 hier=vibration_core
+000071  point: type=toggle comment=out_logits[69]:1->0 hier=vibration_core
+000005  point: type=toggle comment=out_logits[6]:0->1 hier=vibration_core
+000005  point: type=toggle comment=out_logits[6]:1->0 hier=vibration_core
+000029  point: type=toggle comment=out_logits[70]:0->1 hier=vibration_core
+000033  point: type=toggle comment=out_logits[70]:1->0 hier=vibration_core
+000055  point: type=toggle comment=out_logits[71]:0->1 hier=vibration_core
+000057  point: type=toggle comment=out_logits[71]:1->0 hier=vibration_core
+000029  point: type=toggle comment=out_logits[72]:0->1 hier=vibration_core
+000081  point: type=toggle comment=out_logits[72]:1->0 hier=vibration_core
+000020  point: type=toggle comment=out_logits[73]:0->1 hier=vibration_core
+000026  point: type=toggle comment=out_logits[73]:1->0 hier=vibration_core
+000050  point: type=toggle comment=out_logits[74]:0->1 hier=vibration_core
+000096  point: type=toggle comment=out_logits[74]:1->0 hier=vibration_core
+000050  point: type=toggle comment=out_logits[75]:0->1 hier=vibration_core
+000094  point: type=toggle comment=out_logits[75]:1->0 hier=vibration_core
+000049  point: type=toggle comment=out_logits[76]:0->1 hier=vibration_core
+000093  point: type=toggle comment=out_logits[76]:1->0 hier=vibration_core
+000052  point: type=toggle comment=out_logits[77]:0->1 hier=vibration_core
+000098  point: type=toggle comment=out_logits[77]:1->0 hier=vibration_core
+000051  point: type=toggle comment=out_logits[78]:0->1 hier=vibration_core
+000097  point: type=toggle comment=out_logits[78]:1->0 hier=vibration_core
+000050  point: type=toggle comment=out_logits[79]:0->1 hier=vibration_core
+000096  point: type=toggle comment=out_logits[79]:1->0 hier=vibration_core
+000028  point: type=toggle comment=out_logits[7]:0->1 hier=vibration_core
+000026  point: type=toggle comment=out_logits[7]:1->0 hier=vibration_core
+000052  point: type=toggle comment=out_logits[80]:0->1 hier=vibration_core
+000098  point: type=toggle comment=out_logits[80]:1->0 hier=vibration_core
+000052  point: type=toggle comment=out_logits[81]:0->1 hier=vibration_core
+000098  point: type=toggle comment=out_logits[81]:1->0 hier=vibration_core
+000052  point: type=toggle comment=out_logits[82]:0->1 hier=vibration_core
+000098  point: type=toggle comment=out_logits[82]:1->0 hier=vibration_core
+000052  point: type=toggle comment=out_logits[83]:0->1 hier=vibration_core
+000098  point: type=toggle comment=out_logits[83]:1->0 hier=vibration_core
+000052  point: type=toggle comment=out_logits[84]:0->1 hier=vibration_core
+000098  point: type=toggle comment=out_logits[84]:1->0 hier=vibration_core
+000052  point: type=toggle comment=out_logits[85]:0->1 hier=vibration_core
+000098  point: type=toggle comment=out_logits[85]:1->0 hier=vibration_core
+000052  point: type=toggle comment=out_logits[86]:0->1 hier=vibration_core
+000098  point: type=toggle comment=out_logits[86]:1->0 hier=vibration_core
+000052  point: type=toggle comment=out_logits[87]:0->1 hier=vibration_core
+000098  point: type=toggle comment=out_logits[87]:1->0 hier=vibration_core
+000052  point: type=toggle comment=out_logits[88]:0->1 hier=vibration_core
+000098  point: type=toggle comment=out_logits[88]:1->0 hier=vibration_core
+000052  point: type=toggle comment=out_logits[89]:0->1 hier=vibration_core
+000098  point: type=toggle comment=out_logits[89]:1->0 hier=vibration_core
+000005  point: type=toggle comment=out_logits[8]:0->1 hier=vibration_core
+000005  point: type=toggle comment=out_logits[8]:1->0 hier=vibration_core
+000052  point: type=toggle comment=out_logits[90]:0->1 hier=vibration_core
+000098  point: type=toggle comment=out_logits[90]:1->0 hier=vibration_core
+000052  point: type=toggle comment=out_logits[91]:0->1 hier=vibration_core
+000098  point: type=toggle comment=out_logits[91]:1->0 hier=vibration_core
+000052  point: type=toggle comment=out_logits[92]:0->1 hier=vibration_core
+000098  point: type=toggle comment=out_logits[92]:1->0 hier=vibration_core
+000052  point: type=toggle comment=out_logits[93]:0->1 hier=vibration_core
+000098  point: type=toggle comment=out_logits[93]:1->0 hier=vibration_core
+000052  point: type=toggle comment=out_logits[94]:0->1 hier=vibration_core
+000098  point: type=toggle comment=out_logits[94]:1->0 hier=vibration_core
+000052  point: type=toggle comment=out_logits[95]:0->1 hier=vibration_core
+000098  point: type=toggle comment=out_logits[95]:1->0 hier=vibration_core
+000014  point: type=toggle comment=out_logits[9]:0->1 hier=vibration_core
+000014  point: type=toggle comment=out_logits[9]:1->0 hier=vibration_core
 000026     output reg [1:0] out_class,
+000006  point: type=toggle comment=out_class[0]:0->1 hier=vibration_core
+000006  point: type=toggle comment=out_class[0]:1->0 hier=vibration_core
+000026  point: type=toggle comment=out_class[1]:0->1 hier=vibration_core
+000024  point: type=toggle comment=out_class[1]:1->0 hier=vibration_core
%000000     output reg [7:0] out_error,
-000000  point: type=toggle comment=out_error[0]:0->1 hier=vibration_core
-000000  point: type=toggle comment=out_error[0]:1->0 hier=vibration_core
-000000  point: type=toggle comment=out_error[1]:0->1 hier=vibration_core
-000000  point: type=toggle comment=out_error[1]:1->0 hier=vibration_core
-000000  point: type=toggle comment=out_error[2]:0->1 hier=vibration_core
-000000  point: type=toggle comment=out_error[2]:1->0 hier=vibration_core
-000000  point: type=toggle comment=out_error[3]:0->1 hier=vibration_core
-000000  point: type=toggle comment=out_error[3]:1->0 hier=vibration_core
-000000  point: type=toggle comment=out_error[4]:0->1 hier=vibration_core
-000000  point: type=toggle comment=out_error[4]:1->0 hier=vibration_core
-000000  point: type=toggle comment=out_error[5]:0->1 hier=vibration_core
-000000  point: type=toggle comment=out_error[5]:1->0 hier=vibration_core
-000000  point: type=toggle comment=out_error[6]:0->1 hier=vibration_core
-000000  point: type=toggle comment=out_error[6]:1->0 hier=vibration_core
-000000  point: type=toggle comment=out_error[7]:0->1 hier=vibration_core
-000000  point: type=toggle comment=out_error[7]:1->0 hier=vibration_core
~000024     output reg [31:0] cycles_pre,
+000024  point: type=toggle comment=cycles_pre[0]:0->1 hier=vibration_core
+000022  point: type=toggle comment=cycles_pre[0]:1->0 hier=vibration_core
+000024  point: type=toggle comment=cycles_pre[10]:0->1 hier=vibration_core
+000022  point: type=toggle comment=cycles_pre[10]:1->0 hier=vibration_core
+000024  point: type=toggle comment=cycles_pre[11]:0->1 hier=vibration_core
+000022  point: type=toggle comment=cycles_pre[11]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_pre[12]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_pre[12]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_pre[13]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_pre[13]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_pre[14]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_pre[14]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_pre[15]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_pre[15]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_pre[16]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_pre[16]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_pre[17]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_pre[17]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_pre[18]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_pre[18]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_pre[19]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_pre[19]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_pre[1]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_pre[1]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_pre[20]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_pre[20]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_pre[21]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_pre[21]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_pre[22]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_pre[22]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_pre[23]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_pre[23]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_pre[24]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_pre[24]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_pre[25]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_pre[25]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_pre[26]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_pre[26]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_pre[27]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_pre[27]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_pre[28]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_pre[28]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_pre[29]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_pre[29]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_pre[2]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_pre[2]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_pre[30]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_pre[30]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_pre[31]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_pre[31]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_pre[3]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_pre[3]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_pre[4]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_pre[4]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_pre[5]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_pre[5]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_pre[6]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_pre[6]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_pre[7]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_pre[7]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_pre[8]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_pre[8]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_pre[9]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_pre[9]:1->0 hier=vibration_core
~000024     output reg [31:0] cycles_dft,
-000000  point: type=toggle comment=cycles_dft[0]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_dft[0]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_dft[10]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_dft[10]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_dft[11]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_dft[11]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_dft[12]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_dft[12]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_dft[13]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_dft[13]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_dft[14]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_dft[14]:1->0 hier=vibration_core
+000024  point: type=toggle comment=cycles_dft[15]:0->1 hier=vibration_core
+000022  point: type=toggle comment=cycles_dft[15]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_dft[16]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_dft[16]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_dft[17]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_dft[17]:1->0 hier=vibration_core
+000024  point: type=toggle comment=cycles_dft[18]:0->1 hier=vibration_core
+000022  point: type=toggle comment=cycles_dft[18]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_dft[19]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_dft[19]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_dft[1]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_dft[1]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_dft[20]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_dft[20]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_dft[21]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_dft[21]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_dft[22]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_dft[22]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_dft[23]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_dft[23]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_dft[24]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_dft[24]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_dft[25]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_dft[25]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_dft[26]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_dft[26]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_dft[27]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_dft[27]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_dft[28]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_dft[28]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_dft[29]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_dft[29]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_dft[2]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_dft[2]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_dft[30]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_dft[30]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_dft[31]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_dft[31]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_dft[3]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_dft[3]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_dft[4]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_dft[4]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_dft[5]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_dft[5]:1->0 hier=vibration_core
+000024  point: type=toggle comment=cycles_dft[6]:0->1 hier=vibration_core
+000022  point: type=toggle comment=cycles_dft[6]:1->0 hier=vibration_core
+000024  point: type=toggle comment=cycles_dft[7]:0->1 hier=vibration_core
+000022  point: type=toggle comment=cycles_dft[7]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_dft[8]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_dft[8]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_dft[9]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_dft[9]:1->0 hier=vibration_core
~000024     output reg [31:0] cycles_power,
-000000  point: type=toggle comment=cycles_power[0]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_power[0]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_power[10]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_power[10]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_power[11]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_power[11]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_power[12]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_power[12]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_power[13]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_power[13]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_power[14]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_power[14]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_power[15]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_power[15]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_power[16]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_power[16]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_power[17]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_power[17]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_power[18]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_power[18]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_power[19]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_power[19]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_power[1]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_power[1]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_power[20]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_power[20]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_power[21]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_power[21]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_power[22]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_power[22]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_power[23]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_power[23]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_power[24]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_power[24]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_power[25]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_power[25]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_power[26]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_power[26]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_power[27]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_power[27]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_power[28]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_power[28]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_power[29]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_power[29]:1->0 hier=vibration_core
+000024  point: type=toggle comment=cycles_power[2]:0->1 hier=vibration_core
+000022  point: type=toggle comment=cycles_power[2]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_power[30]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_power[30]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_power[31]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_power[31]:1->0 hier=vibration_core
+000024  point: type=toggle comment=cycles_power[3]:0->1 hier=vibration_core
+000022  point: type=toggle comment=cycles_power[3]:1->0 hier=vibration_core
+000024  point: type=toggle comment=cycles_power[4]:0->1 hier=vibration_core
+000022  point: type=toggle comment=cycles_power[4]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_power[5]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_power[5]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_power[6]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_power[6]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_power[7]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_power[7]:1->0 hier=vibration_core
+000024  point: type=toggle comment=cycles_power[8]:0->1 hier=vibration_core
+000022  point: type=toggle comment=cycles_power[8]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_power[9]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_power[9]:1->0 hier=vibration_core
~000024     output reg [31:0] cycles_nn,
-000000  point: type=toggle comment=cycles_nn[0]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_nn[0]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_nn[10]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_nn[10]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_nn[11]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_nn[11]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_nn[12]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_nn[12]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_nn[13]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_nn[13]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_nn[14]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_nn[14]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_nn[15]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_nn[15]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_nn[16]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_nn[16]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_nn[17]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_nn[17]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_nn[18]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_nn[18]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_nn[19]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_nn[19]:1->0 hier=vibration_core
+000024  point: type=toggle comment=cycles_nn[1]:0->1 hier=vibration_core
+000022  point: type=toggle comment=cycles_nn[1]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_nn[20]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_nn[20]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_nn[21]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_nn[21]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_nn[22]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_nn[22]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_nn[23]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_nn[23]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_nn[24]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_nn[24]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_nn[25]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_nn[25]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_nn[26]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_nn[26]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_nn[27]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_nn[27]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_nn[28]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_nn[28]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_nn[29]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_nn[29]:1->0 hier=vibration_core
+000024  point: type=toggle comment=cycles_nn[2]:0->1 hier=vibration_core
+000022  point: type=toggle comment=cycles_nn[2]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_nn[30]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_nn[30]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_nn[31]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_nn[31]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_nn[3]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_nn[3]:1->0 hier=vibration_core
+000024  point: type=toggle comment=cycles_nn[4]:0->1 hier=vibration_core
+000022  point: type=toggle comment=cycles_nn[4]:1->0 hier=vibration_core
+000024  point: type=toggle comment=cycles_nn[5]:0->1 hier=vibration_core
+000022  point: type=toggle comment=cycles_nn[5]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_nn[6]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_nn[6]:1->0 hier=vibration_core
+000024  point: type=toggle comment=cycles_nn[7]:0->1 hier=vibration_core
+000022  point: type=toggle comment=cycles_nn[7]:1->0 hier=vibration_core
+000024  point: type=toggle comment=cycles_nn[8]:0->1 hier=vibration_core
+000022  point: type=toggle comment=cycles_nn[8]:1->0 hier=vibration_core
+000024  point: type=toggle comment=cycles_nn[9]:0->1 hier=vibration_core
+000022  point: type=toggle comment=cycles_nn[9]:1->0 hier=vibration_core
~000024     output reg [31:0] cycles_total,
+000024  point: type=toggle comment=cycles_total[0]:0->1 hier=vibration_core
+000022  point: type=toggle comment=cycles_total[0]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_total[10]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_total[10]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_total[11]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_total[11]:1->0 hier=vibration_core
+000024  point: type=toggle comment=cycles_total[12]:0->1 hier=vibration_core
+000022  point: type=toggle comment=cycles_total[12]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_total[13]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_total[13]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_total[14]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_total[14]:1->0 hier=vibration_core
+000024  point: type=toggle comment=cycles_total[15]:0->1 hier=vibration_core
+000022  point: type=toggle comment=cycles_total[15]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_total[16]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_total[16]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_total[17]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_total[17]:1->0 hier=vibration_core
+000024  point: type=toggle comment=cycles_total[18]:0->1 hier=vibration_core
+000022  point: type=toggle comment=cycles_total[18]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_total[19]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_total[19]:1->0 hier=vibration_core
+000024  point: type=toggle comment=cycles_total[1]:0->1 hier=vibration_core
+000022  point: type=toggle comment=cycles_total[1]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_total[20]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_total[20]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_total[21]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_total[21]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_total[22]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_total[22]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_total[23]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_total[23]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_total[24]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_total[24]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_total[25]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_total[25]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_total[26]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_total[26]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_total[27]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_total[27]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_total[28]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_total[28]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_total[29]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_total[29]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_total[2]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_total[2]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_total[30]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_total[30]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_total[31]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_total[31]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_total[3]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_total[3]:1->0 hier=vibration_core
+000024  point: type=toggle comment=cycles_total[4]:0->1 hier=vibration_core
+000022  point: type=toggle comment=cycles_total[4]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_total[5]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_total[5]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_total[6]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_total[6]:1->0 hier=vibration_core
+000024  point: type=toggle comment=cycles_total[7]:0->1 hier=vibration_core
+000022  point: type=toggle comment=cycles_total[7]:1->0 hier=vibration_core
+000024  point: type=toggle comment=cycles_total[8]:0->1 hier=vibration_core
+000022  point: type=toggle comment=cycles_total[8]:1->0 hier=vibration_core
-000000  point: type=toggle comment=cycles_total[9]:0->1 hier=vibration_core
-000000  point: type=toggle comment=cycles_total[9]:1->0 hier=vibration_core
~000004     output reg [31:0] protocol_errors,
+000004  point: type=toggle comment=protocol_errors[0]:0->1 hier=vibration_core
+000004  point: type=toggle comment=protocol_errors[0]:1->0 hier=vibration_core
-000000  point: type=toggle comment=protocol_errors[10]:0->1 hier=vibration_core
-000000  point: type=toggle comment=protocol_errors[10]:1->0 hier=vibration_core
-000000  point: type=toggle comment=protocol_errors[11]:0->1 hier=vibration_core
-000000  point: type=toggle comment=protocol_errors[11]:1->0 hier=vibration_core
-000000  point: type=toggle comment=protocol_errors[12]:0->1 hier=vibration_core
-000000  point: type=toggle comment=protocol_errors[12]:1->0 hier=vibration_core
-000000  point: type=toggle comment=protocol_errors[13]:0->1 hier=vibration_core
-000000  point: type=toggle comment=protocol_errors[13]:1->0 hier=vibration_core
-000000  point: type=toggle comment=protocol_errors[14]:0->1 hier=vibration_core
-000000  point: type=toggle comment=protocol_errors[14]:1->0 hier=vibration_core
-000000  point: type=toggle comment=protocol_errors[15]:0->1 hier=vibration_core
-000000  point: type=toggle comment=protocol_errors[15]:1->0 hier=vibration_core
-000000  point: type=toggle comment=protocol_errors[16]:0->1 hier=vibration_core
-000000  point: type=toggle comment=protocol_errors[16]:1->0 hier=vibration_core
-000000  point: type=toggle comment=protocol_errors[17]:0->1 hier=vibration_core
-000000  point: type=toggle comment=protocol_errors[17]:1->0 hier=vibration_core
-000000  point: type=toggle comment=protocol_errors[18]:0->1 hier=vibration_core
-000000  point: type=toggle comment=protocol_errors[18]:1->0 hier=vibration_core
-000000  point: type=toggle comment=protocol_errors[19]:0->1 hier=vibration_core
-000000  point: type=toggle comment=protocol_errors[19]:1->0 hier=vibration_core
+000002  point: type=toggle comment=protocol_errors[1]:0->1 hier=vibration_core
+000002  point: type=toggle comment=protocol_errors[1]:1->0 hier=vibration_core
-000000  point: type=toggle comment=protocol_errors[20]:0->1 hier=vibration_core
-000000  point: type=toggle comment=protocol_errors[20]:1->0 hier=vibration_core
-000000  point: type=toggle comment=protocol_errors[21]:0->1 hier=vibration_core
-000000  point: type=toggle comment=protocol_errors[21]:1->0 hier=vibration_core
-000000  point: type=toggle comment=protocol_errors[22]:0->1 hier=vibration_core
-000000  point: type=toggle comment=protocol_errors[22]:1->0 hier=vibration_core
-000000  point: type=toggle comment=protocol_errors[23]:0->1 hier=vibration_core
-000000  point: type=toggle comment=protocol_errors[23]:1->0 hier=vibration_core
-000000  point: type=toggle comment=protocol_errors[24]:0->1 hier=vibration_core
-000000  point: type=toggle comment=protocol_errors[24]:1->0 hier=vibration_core
-000000  point: type=toggle comment=protocol_errors[25]:0->1 hier=vibration_core
-000000  point: type=toggle comment=protocol_errors[25]:1->0 hier=vibration_core
-000000  point: type=toggle comment=protocol_errors[26]:0->1 hier=vibration_core
-000000  point: type=toggle comment=protocol_errors[26]:1->0 hier=vibration_core
-000000  point: type=toggle comment=protocol_errors[27]:0->1 hier=vibration_core
-000000  point: type=toggle comment=protocol_errors[27]:1->0 hier=vibration_core
-000000  point: type=toggle comment=protocol_errors[28]:0->1 hier=vibration_core
-000000  point: type=toggle comment=protocol_errors[28]:1->0 hier=vibration_core
-000000  point: type=toggle comment=protocol_errors[29]:0->1 hier=vibration_core
-000000  point: type=toggle comment=protocol_errors[29]:1->0 hier=vibration_core
+000002  point: type=toggle comment=protocol_errors[2]:0->1 hier=vibration_core
+000002  point: type=toggle comment=protocol_errors[2]:1->0 hier=vibration_core
-000000  point: type=toggle comment=protocol_errors[30]:0->1 hier=vibration_core
-000000  point: type=toggle comment=protocol_errors[30]:1->0 hier=vibration_core
-000000  point: type=toggle comment=protocol_errors[31]:0->1 hier=vibration_core
-000000  point: type=toggle comment=protocol_errors[31]:1->0 hier=vibration_core
-000000  point: type=toggle comment=protocol_errors[3]:0->1 hier=vibration_core
-000000  point: type=toggle comment=protocol_errors[3]:1->0 hier=vibration_core
-000000  point: type=toggle comment=protocol_errors[4]:0->1 hier=vibration_core
-000000  point: type=toggle comment=protocol_errors[4]:1->0 hier=vibration_core
-000000  point: type=toggle comment=protocol_errors[5]:0->1 hier=vibration_core
-000000  point: type=toggle comment=protocol_errors[5]:1->0 hier=vibration_core
-000000  point: type=toggle comment=protocol_errors[6]:0->1 hier=vibration_core
-000000  point: type=toggle comment=protocol_errors[6]:1->0 hier=vibration_core
-000000  point: type=toggle comment=protocol_errors[7]:0->1 hier=vibration_core
-000000  point: type=toggle comment=protocol_errors[7]:1->0 hier=vibration_core
-000000  point: type=toggle comment=protocol_errors[8]:0->1 hier=vibration_core
-000000  point: type=toggle comment=protocol_errors[8]:1->0 hier=vibration_core
-000000  point: type=toggle comment=protocol_errors[9]:0->1 hier=vibration_core
-000000  point: type=toggle comment=protocol_errors[9]:1->0 hier=vibration_core
            // Passive diagnostics: kind 0 mean, 1 windowed, 2 real, 3 imag,
            // 4 power, 5 feature, 6 hidden activation, 7 logit. Signed 40-bit value.
 076630     output reg dbg_valid,
+076630  point: type=toggle comment=dbg_valid:0->1 hier=vibration_core
+076630  point: type=toggle comment=dbg_valid:1->0 hier=vibration_core
~004060     output reg [3:0] dbg_kind,
+004060  point: type=toggle comment=dbg_kind[0]:0->1 hier=vibration_core
+004058  point: type=toggle comment=dbg_kind[0]:1->0 hier=vibration_core
+000120  point: type=toggle comment=dbg_kind[1]:0->1 hier=vibration_core
+000118  point: type=toggle comment=dbg_kind[1]:1->0 hier=vibration_core
+000062  point: type=toggle comment=dbg_kind[2]:0->1 hier=vibration_core
+000060  point: type=toggle comment=dbg_kind[2]:1->0 hier=vibration_core
-000000  point: type=toggle comment=dbg_kind[3]:0->1 hier=vibration_core
-000000  point: type=toggle comment=dbg_kind[3]:1->0 hier=vibration_core
~036282     output reg [15:0] dbg_index,
+036282  point: type=toggle comment=dbg_index[0]:0->1 hier=vibration_core
+036282  point: type=toggle comment=dbg_index[0]:1->0 hier=vibration_core
-000000  point: type=toggle comment=dbg_index[10]:0->1 hier=vibration_core
-000000  point: type=toggle comment=dbg_index[10]:1->0 hier=vibration_core
-000000  point: type=toggle comment=dbg_index[11]:0->1 hier=vibration_core
-000000  point: type=toggle comment=dbg_index[11]:1->0 hier=vibration_core
-000000  point: type=toggle comment=dbg_index[12]:0->1 hier=vibration_core
-000000  point: type=toggle comment=dbg_index[12]:1->0 hier=vibration_core
-000000  point: type=toggle comment=dbg_index[13]:0->1 hier=vibration_core
-000000  point: type=toggle comment=dbg_index[13]:1->0 hier=vibration_core
-000000  point: type=toggle comment=dbg_index[14]:0->1 hier=vibration_core
-000000  point: type=toggle comment=dbg_index[14]:1->0 hier=vibration_core
-000000  point: type=toggle comment=dbg_index[15]:0->1 hier=vibration_core
-000000  point: type=toggle comment=dbg_index[15]:1->0 hier=vibration_core
+018170  point: type=toggle comment=dbg_index[1]:0->1 hier=vibration_core
+018168  point: type=toggle comment=dbg_index[1]:1->0 hier=vibration_core
+009056  point: type=toggle comment=dbg_index[2]:0->1 hier=vibration_core
+009056  point: type=toggle comment=dbg_index[2]:1->0 hier=vibration_core
+004528  point: type=toggle comment=dbg_index[3]:0->1 hier=vibration_core
+004528  point: type=toggle comment=dbg_index[3]:1->0 hier=vibration_core
+002174  point: type=toggle comment=dbg_index[4]:0->1 hier=vibration_core
+002174  point: type=toggle comment=dbg_index[4]:1->0 hier=vibration_core
+001118  point: type=toggle comment=dbg_index[5]:0->1 hier=vibration_core
+001118  point: type=toggle comment=dbg_index[5]:1->0 hier=vibration_core
+000528  point: type=toggle comment=dbg_index[6]:0->1 hier=vibration_core
+000528  point: type=toggle comment=dbg_index[6]:1->0 hier=vibration_core
+000264  point: type=toggle comment=dbg_index[7]:0->1 hier=vibration_core
+000264  point: type=toggle comment=dbg_index[7]:1->0 hier=vibration_core
+000132  point: type=toggle comment=dbg_index[8]:0->1 hier=vibration_core
+000132  point: type=toggle comment=dbg_index[8]:1->0 hier=vibration_core
+000066  point: type=toggle comment=dbg_index[9]:0->1 hier=vibration_core
+000066  point: type=toggle comment=dbg_index[9]:1->0 hier=vibration_core
 014425     output reg signed [39:0] dbg_value
+014359  point: type=toggle comment=dbg_value[0]:0->1 hier=vibration_core
+014357  point: type=toggle comment=dbg_value[0]:1->0 hier=vibration_core
+012532  point: type=toggle comment=dbg_value[10]:0->1 hier=vibration_core
+012530  point: type=toggle comment=dbg_value[10]:1->0 hier=vibration_core
+012550  point: type=toggle comment=dbg_value[11]:0->1 hier=vibration_core
+012548  point: type=toggle comment=dbg_value[11]:1->0 hier=vibration_core
+012556  point: type=toggle comment=dbg_value[12]:0->1 hier=vibration_core
+012554  point: type=toggle comment=dbg_value[12]:1->0 hier=vibration_core
+012541  point: type=toggle comment=dbg_value[13]:0->1 hier=vibration_core
+012539  point: type=toggle comment=dbg_value[13]:1->0 hier=vibration_core
+012521  point: type=toggle comment=dbg_value[14]:0->1 hier=vibration_core
+012519  point: type=toggle comment=dbg_value[14]:1->0 hier=vibration_core
+012541  point: type=toggle comment=dbg_value[15]:0->1 hier=vibration_core
+012539  point: type=toggle comment=dbg_value[15]:1->0 hier=vibration_core
+012534  point: type=toggle comment=dbg_value[16]:0->1 hier=vibration_core
+012532  point: type=toggle comment=dbg_value[16]:1->0 hier=vibration_core
+012523  point: type=toggle comment=dbg_value[17]:0->1 hier=vibration_core
+012521  point: type=toggle comment=dbg_value[17]:1->0 hier=vibration_core
+012515  point: type=toggle comment=dbg_value[18]:0->1 hier=vibration_core
+012513  point: type=toggle comment=dbg_value[18]:1->0 hier=vibration_core
+012488  point: type=toggle comment=dbg_value[19]:0->1 hier=vibration_core
+012486  point: type=toggle comment=dbg_value[19]:1->0 hier=vibration_core
+014228  point: type=toggle comment=dbg_value[1]:0->1 hier=vibration_core
+014226  point: type=toggle comment=dbg_value[1]:1->0 hier=vibration_core
+012487  point: type=toggle comment=dbg_value[20]:0->1 hier=vibration_core
+012485  point: type=toggle comment=dbg_value[20]:1->0 hier=vibration_core
+012486  point: type=toggle comment=dbg_value[21]:0->1 hier=vibration_core
+012484  point: type=toggle comment=dbg_value[21]:1->0 hier=vibration_core
+012513  point: type=toggle comment=dbg_value[22]:0->1 hier=vibration_core
+012511  point: type=toggle comment=dbg_value[22]:1->0 hier=vibration_core
+012487  point: type=toggle comment=dbg_value[23]:0->1 hier=vibration_core
+012485  point: type=toggle comment=dbg_value[23]:1->0 hier=vibration_core
+012485  point: type=toggle comment=dbg_value[24]:0->1 hier=vibration_core
+012483  point: type=toggle comment=dbg_value[24]:1->0 hier=vibration_core
+012486  point: type=toggle comment=dbg_value[25]:0->1 hier=vibration_core
+012484  point: type=toggle comment=dbg_value[25]:1->0 hier=vibration_core
+012485  point: type=toggle comment=dbg_value[26]:0->1 hier=vibration_core
+012483  point: type=toggle comment=dbg_value[26]:1->0 hier=vibration_core
+012485  point: type=toggle comment=dbg_value[27]:0->1 hier=vibration_core
+012483  point: type=toggle comment=dbg_value[27]:1->0 hier=vibration_core
+012485  point: type=toggle comment=dbg_value[28]:0->1 hier=vibration_core
+012483  point: type=toggle comment=dbg_value[28]:1->0 hier=vibration_core
+012485  point: type=toggle comment=dbg_value[29]:0->1 hier=vibration_core
+012483  point: type=toggle comment=dbg_value[29]:1->0 hier=vibration_core
+013983  point: type=toggle comment=dbg_value[2]:0->1 hier=vibration_core
+013983  point: type=toggle comment=dbg_value[2]:1->0 hier=vibration_core
+012485  point: type=toggle comment=dbg_value[30]:0->1 hier=vibration_core
+012483  point: type=toggle comment=dbg_value[30]:1->0 hier=vibration_core
+012485  point: type=toggle comment=dbg_value[31]:0->1 hier=vibration_core
+012483  point: type=toggle comment=dbg_value[31]:1->0 hier=vibration_core
+012485  point: type=toggle comment=dbg_value[32]:0->1 hier=vibration_core
+012483  point: type=toggle comment=dbg_value[32]:1->0 hier=vibration_core
+012485  point: type=toggle comment=dbg_value[33]:0->1 hier=vibration_core
+012483  point: type=toggle comment=dbg_value[33]:1->0 hier=vibration_core
+012485  point: type=toggle comment=dbg_value[34]:0->1 hier=vibration_core
+012483  point: type=toggle comment=dbg_value[34]:1->0 hier=vibration_core
+012485  point: type=toggle comment=dbg_value[35]:0->1 hier=vibration_core
+012483  point: type=toggle comment=dbg_value[35]:1->0 hier=vibration_core
+012485  point: type=toggle comment=dbg_value[36]:0->1 hier=vibration_core
+012483  point: type=toggle comment=dbg_value[36]:1->0 hier=vibration_core
+012485  point: type=toggle comment=dbg_value[37]:0->1 hier=vibration_core
+012483  point: type=toggle comment=dbg_value[37]:1->0 hier=vibration_core
+012485  point: type=toggle comment=dbg_value[38]:0->1 hier=vibration_core
+012483  point: type=toggle comment=dbg_value[38]:1->0 hier=vibration_core
+012485  point: type=toggle comment=dbg_value[39]:0->1 hier=vibration_core
+012483  point: type=toggle comment=dbg_value[39]:1->0 hier=vibration_core
+014398  point: type=toggle comment=dbg_value[3]:0->1 hier=vibration_core
+014396  point: type=toggle comment=dbg_value[3]:1->0 hier=vibration_core
+014425  point: type=toggle comment=dbg_value[4]:0->1 hier=vibration_core
+014423  point: type=toggle comment=dbg_value[4]:1->0 hier=vibration_core
+013941  point: type=toggle comment=dbg_value[5]:0->1 hier=vibration_core
+013941  point: type=toggle comment=dbg_value[5]:1->0 hier=vibration_core
+013911  point: type=toggle comment=dbg_value[6]:0->1 hier=vibration_core
+013909  point: type=toggle comment=dbg_value[6]:1->0 hier=vibration_core
+013679  point: type=toggle comment=dbg_value[7]:0->1 hier=vibration_core
+013677  point: type=toggle comment=dbg_value[7]:1->0 hier=vibration_core
+013655  point: type=toggle comment=dbg_value[8]:0->1 hier=vibration_core
+013653  point: type=toggle comment=dbg_value[8]:1->0 hier=vibration_core
+012551  point: type=toggle comment=dbg_value[9]:0->1 hier=vibration_core
+012551  point: type=toggle comment=dbg_value[9]:1->0 hier=vibration_core
        );
            localparam integer P = $clog2(N);
            localparam integer TOTAL_BINS = 16*BANDS;
            localparam integer COMPONENTS = 2*TOTAL_BINS;
            localparam integer CW = $clog2(COMPONENTS);
            localparam integer BI_W = $clog2(TOTAL_BINS);
            localparam integer LB = LANES == 1 ? 1 : $clog2(LANES);
            localparam integer SUM_W = 16+P;
            localparam integer W1_WORDS = (16/LANES)*16;
            localparam integer W2_GROUPS = (3+LANES-1)/LANES;
            localparam integer WEIGHT_WORDS = W1_WORDS+W2_GROUPS*16;
            localparam integer WA = $clog2(WEIGHT_WORDS);
            localparam integer PRE_MAX = 3*N+1;
            localparam integer DFT_MAX = (COMPONENTS/LANES)*(3*N+LANES+1);
            localparam integer NN_MAX = (16/LANES+W2_GROUPS)*(49+LANES);
            localparam integer POWER_MAX = 16*(4*BANDS+2+33);
            localparam integer POWER_W = $clog2(POWER_MAX+1);
            localparam integer TOTAL_MAX = PRE_MAX+DFT_MAX+POWER_MAX+NN_MAX;
            localparam integer PRE_W = $clog2(PRE_MAX+1);
            localparam integer DFT_W = $clog2(DFT_MAX+1);
            localparam integer NN_W = $clog2(NN_MAX+1);
            localparam integer TOTAL_W = $clog2(TOTAL_MAX+1);
        
            localparam [4:0] IDLE=0, PRE_MEAN=1, PRE_READ=2, PRE_MUL=3,
                PRE_STORE=4, DFT_INIT=5, DFT_READ=6, DFT_MUL=7, DFT_ACC=8,
                DFT_STORE=9, POWER_RE_MUL=10, POWER_RE_ADD=11,
                POWER_IM_MUL=12, POWER_IM_ADD=13, POWER_Q_INIT=14,
                POWER_Q_SHIFT=15, POWER_QUANT=16, NN_INIT=17, NN_READ=18,
                NN_MUL=19, NN_ACC=20, NN_STORE=21, FINISH=22, HOLD=23;
 6194008     reg [4:0] state;
+6194008  point: type=toggle comment=state[0]:0->1 hier=vibration_core
+6194008  point: type=toggle comment=state[0]:1->0 hier=vibration_core
+6183998  point: type=toggle comment=state[1]:0->1 hier=vibration_core
+6183998  point: type=toggle comment=state[1]:1->0 hier=vibration_core
+6182910  point: type=toggle comment=state[2]:0->1 hier=vibration_core
+6182910  point: type=toggle comment=state[2]:1->0 hier=vibration_core
+6095768  point: type=toggle comment=state[3]:0->1 hier=vibration_core
+6095768  point: type=toggle comment=state[3]:1->0 hier=vibration_core
+000960  point: type=toggle comment=state[4]:0->1 hier=vibration_core
+000960  point: type=toggle comment=state[4]:1->0 hier=vibration_core
        
            (* ram_style = "block" *) reg signed [15:0] raw0 [0:N-1];
            (* ram_style = "block" *) reg signed [15:0] raw1 [0:N-1];
            (* ram_style = "block" *) reg signed [15:0] windowed [0:N-1];
            reg [15:0] frequency_bins [0:TOTAL_BINS-1];
~000002     reg [7:0] feature_shifts [0:15];
-000000  point: type=toggle comment=feature_shifts[0][0]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[0][0]:1->0 hier=vibration_core
+000002  point: type=toggle comment=feature_shifts[0][1]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[0][1]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[0][2]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[0][2]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[0][3]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[0][3]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[0][4]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[0][4]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[0][5]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[0][5]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[0][6]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[0][6]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[0][7]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[0][7]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[10][0]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[10][0]:1->0 hier=vibration_core
+000002  point: type=toggle comment=feature_shifts[10][1]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[10][1]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[10][2]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[10][2]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[10][3]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[10][3]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[10][4]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[10][4]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[10][5]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[10][5]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[10][6]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[10][6]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[10][7]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[10][7]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[11][0]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[11][0]:1->0 hier=vibration_core
+000002  point: type=toggle comment=feature_shifts[11][1]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[11][1]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[11][2]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[11][2]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[11][3]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[11][3]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[11][4]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[11][4]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[11][5]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[11][5]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[11][6]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[11][6]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[11][7]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[11][7]:1->0 hier=vibration_core
+000002  point: type=toggle comment=feature_shifts[12][0]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[12][0]:1->0 hier=vibration_core
+000002  point: type=toggle comment=feature_shifts[12][1]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[12][1]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[12][2]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[12][2]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[12][3]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[12][3]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[12][4]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[12][4]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[12][5]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[12][5]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[12][6]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[12][6]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[12][7]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[12][7]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[13][0]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[13][0]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[13][1]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[13][1]:1->0 hier=vibration_core
+000002  point: type=toggle comment=feature_shifts[13][2]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[13][2]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[13][3]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[13][3]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[13][4]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[13][4]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[13][5]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[13][5]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[13][6]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[13][6]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[13][7]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[13][7]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[14][0]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[14][0]:1->0 hier=vibration_core
+000002  point: type=toggle comment=feature_shifts[14][1]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[14][1]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[14][2]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[14][2]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[14][3]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[14][3]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[14][4]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[14][4]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[14][5]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[14][5]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[14][6]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[14][6]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[14][7]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[14][7]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[15][0]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[15][0]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[15][1]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[15][1]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[15][2]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[15][2]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[15][3]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[15][3]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[15][4]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[15][4]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[15][5]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[15][5]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[15][6]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[15][6]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[15][7]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[15][7]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[1][0]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[1][0]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[1][1]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[1][1]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[1][2]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[1][2]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[1][3]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[1][3]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[1][4]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[1][4]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[1][5]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[1][5]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[1][6]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[1][6]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[1][7]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[1][7]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[2][0]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[2][0]:1->0 hier=vibration_core
+000002  point: type=toggle comment=feature_shifts[2][1]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[2][1]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[2][2]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[2][2]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[2][3]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[2][3]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[2][4]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[2][4]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[2][5]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[2][5]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[2][6]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[2][6]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[2][7]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[2][7]:1->0 hier=vibration_core
+000002  point: type=toggle comment=feature_shifts[3][0]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[3][0]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[3][1]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[3][1]:1->0 hier=vibration_core
+000002  point: type=toggle comment=feature_shifts[3][2]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[3][2]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[3][3]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[3][3]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[3][4]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[3][4]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[3][5]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[3][5]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[3][6]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[3][6]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[3][7]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[3][7]:1->0 hier=vibration_core
+000002  point: type=toggle comment=feature_shifts[4][0]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[4][0]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[4][1]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[4][1]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[4][2]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[4][2]:1->0 hier=vibration_core
+000002  point: type=toggle comment=feature_shifts[4][3]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[4][3]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[4][4]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[4][4]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[4][5]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[4][5]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[4][6]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[4][6]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[4][7]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[4][7]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[5][0]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[5][0]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[5][1]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[5][1]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[5][2]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[5][2]:1->0 hier=vibration_core
+000002  point: type=toggle comment=feature_shifts[5][3]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[5][3]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[5][4]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[5][4]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[5][5]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[5][5]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[5][6]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[5][6]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[5][7]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[5][7]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[6][0]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[6][0]:1->0 hier=vibration_core
+000002  point: type=toggle comment=feature_shifts[6][1]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[6][1]:1->0 hier=vibration_core
+000002  point: type=toggle comment=feature_shifts[6][2]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[6][2]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[6][3]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[6][3]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[6][4]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[6][4]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[6][5]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[6][5]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[6][6]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[6][6]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[6][7]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[6][7]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[7][0]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[7][0]:1->0 hier=vibration_core
+000002  point: type=toggle comment=feature_shifts[7][1]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[7][1]:1->0 hier=vibration_core
+000002  point: type=toggle comment=feature_shifts[7][2]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[7][2]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[7][3]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[7][3]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[7][4]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[7][4]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[7][5]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[7][5]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[7][6]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[7][6]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[7][7]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[7][7]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[8][0]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[8][0]:1->0 hier=vibration_core
+000002  point: type=toggle comment=feature_shifts[8][1]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[8][1]:1->0 hier=vibration_core
+000002  point: type=toggle comment=feature_shifts[8][2]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[8][2]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[8][3]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[8][3]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[8][4]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[8][4]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[8][5]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[8][5]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[8][6]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[8][6]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[8][7]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[8][7]:1->0 hier=vibration_core
+000002  point: type=toggle comment=feature_shifts[9][0]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[9][0]:1->0 hier=vibration_core
+000002  point: type=toggle comment=feature_shifts[9][1]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[9][1]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[9][2]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[9][2]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[9][3]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[9][3]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[9][4]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[9][4]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[9][5]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[9][5]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[9][6]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[9][6]:1->0 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[9][7]:0->1 hier=vibration_core
-000000  point: type=toggle comment=feature_shifts[9][7]:1->0 hier=vibration_core
            reg signed [31:0] bias1 [0:15];
~000002     reg signed [31:0] bias2 [0:2];
+000002  point: type=toggle comment=bias2[0][0]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[0][0]:1->0 hier=vibration_core
+000002  point: type=toggle comment=bias2[0][10]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[0][10]:1->0 hier=vibration_core
+000002  point: type=toggle comment=bias2[0][11]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[0][11]:1->0 hier=vibration_core
+000002  point: type=toggle comment=bias2[0][12]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[0][12]:1->0 hier=vibration_core
+000002  point: type=toggle comment=bias2[0][13]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[0][13]:1->0 hier=vibration_core
+000002  point: type=toggle comment=bias2[0][14]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[0][14]:1->0 hier=vibration_core
+000002  point: type=toggle comment=bias2[0][15]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[0][15]:1->0 hier=vibration_core
+000002  point: type=toggle comment=bias2[0][16]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[0][16]:1->0 hier=vibration_core
+000002  point: type=toggle comment=bias2[0][17]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[0][17]:1->0 hier=vibration_core
+000002  point: type=toggle comment=bias2[0][18]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[0][18]:1->0 hier=vibration_core
+000002  point: type=toggle comment=bias2[0][19]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[0][19]:1->0 hier=vibration_core
+000002  point: type=toggle comment=bias2[0][1]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[0][1]:1->0 hier=vibration_core
+000002  point: type=toggle comment=bias2[0][20]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[0][20]:1->0 hier=vibration_core
+000002  point: type=toggle comment=bias2[0][21]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[0][21]:1->0 hier=vibration_core
+000002  point: type=toggle comment=bias2[0][22]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[0][22]:1->0 hier=vibration_core
+000002  point: type=toggle comment=bias2[0][23]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[0][23]:1->0 hier=vibration_core
+000002  point: type=toggle comment=bias2[0][24]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[0][24]:1->0 hier=vibration_core
+000002  point: type=toggle comment=bias2[0][25]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[0][25]:1->0 hier=vibration_core
+000002  point: type=toggle comment=bias2[0][26]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[0][26]:1->0 hier=vibration_core
+000002  point: type=toggle comment=bias2[0][27]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[0][27]:1->0 hier=vibration_core
+000002  point: type=toggle comment=bias2[0][28]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[0][28]:1->0 hier=vibration_core
+000002  point: type=toggle comment=bias2[0][29]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[0][29]:1->0 hier=vibration_core
-000000  point: type=toggle comment=bias2[0][2]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[0][2]:1->0 hier=vibration_core
+000002  point: type=toggle comment=bias2[0][30]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[0][30]:1->0 hier=vibration_core
+000002  point: type=toggle comment=bias2[0][31]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[0][31]:1->0 hier=vibration_core
+000002  point: type=toggle comment=bias2[0][3]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[0][3]:1->0 hier=vibration_core
+000002  point: type=toggle comment=bias2[0][4]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[0][4]:1->0 hier=vibration_core
+000002  point: type=toggle comment=bias2[0][5]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[0][5]:1->0 hier=vibration_core
+000002  point: type=toggle comment=bias2[0][6]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[0][6]:1->0 hier=vibration_core
+000002  point: type=toggle comment=bias2[0][7]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[0][7]:1->0 hier=vibration_core
+000002  point: type=toggle comment=bias2[0][8]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[0][8]:1->0 hier=vibration_core
+000002  point: type=toggle comment=bias2[0][9]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[0][9]:1->0 hier=vibration_core
-000000  point: type=toggle comment=bias2[1][0]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[1][0]:1->0 hier=vibration_core
+000002  point: type=toggle comment=bias2[1][10]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[1][10]:1->0 hier=vibration_core
+000002  point: type=toggle comment=bias2[1][11]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[1][11]:1->0 hier=vibration_core
+000002  point: type=toggle comment=bias2[1][12]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[1][12]:1->0 hier=vibration_core
+000002  point: type=toggle comment=bias2[1][13]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[1][13]:1->0 hier=vibration_core
+000002  point: type=toggle comment=bias2[1][14]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[1][14]:1->0 hier=vibration_core
+000002  point: type=toggle comment=bias2[1][15]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[1][15]:1->0 hier=vibration_core
+000002  point: type=toggle comment=bias2[1][16]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[1][16]:1->0 hier=vibration_core
+000002  point: type=toggle comment=bias2[1][17]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[1][17]:1->0 hier=vibration_core
+000002  point: type=toggle comment=bias2[1][18]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[1][18]:1->0 hier=vibration_core
+000002  point: type=toggle comment=bias2[1][19]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[1][19]:1->0 hier=vibration_core
+000002  point: type=toggle comment=bias2[1][1]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[1][1]:1->0 hier=vibration_core
+000002  point: type=toggle comment=bias2[1][20]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[1][20]:1->0 hier=vibration_core
+000002  point: type=toggle comment=bias2[1][21]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[1][21]:1->0 hier=vibration_core
+000002  point: type=toggle comment=bias2[1][22]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[1][22]:1->0 hier=vibration_core
+000002  point: type=toggle comment=bias2[1][23]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[1][23]:1->0 hier=vibration_core
+000002  point: type=toggle comment=bias2[1][24]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[1][24]:1->0 hier=vibration_core
+000002  point: type=toggle comment=bias2[1][25]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[1][25]:1->0 hier=vibration_core
+000002  point: type=toggle comment=bias2[1][26]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[1][26]:1->0 hier=vibration_core
+000002  point: type=toggle comment=bias2[1][27]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[1][27]:1->0 hier=vibration_core
+000002  point: type=toggle comment=bias2[1][28]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[1][28]:1->0 hier=vibration_core
+000002  point: type=toggle comment=bias2[1][29]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[1][29]:1->0 hier=vibration_core
+000002  point: type=toggle comment=bias2[1][2]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[1][2]:1->0 hier=vibration_core
+000002  point: type=toggle comment=bias2[1][30]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[1][30]:1->0 hier=vibration_core
+000002  point: type=toggle comment=bias2[1][31]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[1][31]:1->0 hier=vibration_core
-000000  point: type=toggle comment=bias2[1][3]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[1][3]:1->0 hier=vibration_core
+000002  point: type=toggle comment=bias2[1][4]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[1][4]:1->0 hier=vibration_core
-000000  point: type=toggle comment=bias2[1][5]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[1][5]:1->0 hier=vibration_core
+000002  point: type=toggle comment=bias2[1][6]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[1][6]:1->0 hier=vibration_core
-000000  point: type=toggle comment=bias2[1][7]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[1][7]:1->0 hier=vibration_core
+000002  point: type=toggle comment=bias2[1][8]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[1][8]:1->0 hier=vibration_core
+000002  point: type=toggle comment=bias2[1][9]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[1][9]:1->0 hier=vibration_core
-000000  point: type=toggle comment=bias2[2][0]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[2][0]:1->0 hier=vibration_core
-000000  point: type=toggle comment=bias2[2][10]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[2][10]:1->0 hier=vibration_core
-000000  point: type=toggle comment=bias2[2][11]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[2][11]:1->0 hier=vibration_core
-000000  point: type=toggle comment=bias2[2][12]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[2][12]:1->0 hier=vibration_core
-000000  point: type=toggle comment=bias2[2][13]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[2][13]:1->0 hier=vibration_core
-000000  point: type=toggle comment=bias2[2][14]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[2][14]:1->0 hier=vibration_core
-000000  point: type=toggle comment=bias2[2][15]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[2][15]:1->0 hier=vibration_core
-000000  point: type=toggle comment=bias2[2][16]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[2][16]:1->0 hier=vibration_core
-000000  point: type=toggle comment=bias2[2][17]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[2][17]:1->0 hier=vibration_core
-000000  point: type=toggle comment=bias2[2][18]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[2][18]:1->0 hier=vibration_core
-000000  point: type=toggle comment=bias2[2][19]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[2][19]:1->0 hier=vibration_core
-000000  point: type=toggle comment=bias2[2][1]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[2][1]:1->0 hier=vibration_core
-000000  point: type=toggle comment=bias2[2][20]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[2][20]:1->0 hier=vibration_core
-000000  point: type=toggle comment=bias2[2][21]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[2][21]:1->0 hier=vibration_core
-000000  point: type=toggle comment=bias2[2][22]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[2][22]:1->0 hier=vibration_core
-000000  point: type=toggle comment=bias2[2][23]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[2][23]:1->0 hier=vibration_core
-000000  point: type=toggle comment=bias2[2][24]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[2][24]:1->0 hier=vibration_core
-000000  point: type=toggle comment=bias2[2][25]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[2][25]:1->0 hier=vibration_core
-000000  point: type=toggle comment=bias2[2][26]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[2][26]:1->0 hier=vibration_core
-000000  point: type=toggle comment=bias2[2][27]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[2][27]:1->0 hier=vibration_core
-000000  point: type=toggle comment=bias2[2][28]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[2][28]:1->0 hier=vibration_core
-000000  point: type=toggle comment=bias2[2][29]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[2][29]:1->0 hier=vibration_core
+000002  point: type=toggle comment=bias2[2][2]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[2][2]:1->0 hier=vibration_core
-000000  point: type=toggle comment=bias2[2][30]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[2][30]:1->0 hier=vibration_core
-000000  point: type=toggle comment=bias2[2][31]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[2][31]:1->0 hier=vibration_core
-000000  point: type=toggle comment=bias2[2][3]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[2][3]:1->0 hier=vibration_core
+000002  point: type=toggle comment=bias2[2][4]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[2][4]:1->0 hier=vibration_core
+000002  point: type=toggle comment=bias2[2][5]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[2][5]:1->0 hier=vibration_core
+000002  point: type=toggle comment=bias2[2][6]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[2][6]:1->0 hier=vibration_core
+000002  point: type=toggle comment=bias2[2][7]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[2][7]:1->0 hier=vibration_core
-000000  point: type=toggle comment=bias2[2][8]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[2][8]:1->0 hier=vibration_core
-000000  point: type=toggle comment=bias2[2][9]:0->1 hier=vibration_core
-000000  point: type=toggle comment=bias2[2][9]:1->0 hier=vibration_core
 000002     initial begin
+000002  point: type=line comment=block hier=vibration_core
 000002         $readmemh({MODEL_DIR, "/feature_shifts.hex"}, feature_shifts);
+000002  point: type=line comment=block hier=vibration_core
 000002         $readmemh({MODEL_DIR, "/b1.hex"}, bias1);
+000002  point: type=line comment=block hier=vibration_core
 000002         $readmemh({MODEL_DIR, "/b2.hex"}, bias2);
+000002  point: type=line comment=block hier=vibration_core
            end
        
            generate if (BANDS == 3) begin: g_neighbor_bins
 000002         initial $readmemh({MODEL_DIR, "/dft_bins.hex"}, frequency_bins);
+000002  point: type=line comment=block hier=vibration_core
            end else begin: g_single_bins
                initial $readmemh({MODEL_DIR, "/bins.hex"}, frequency_bins);
            end endgenerate
 000040     reg [1:0] full, busy;
+000040  point: type=toggle comment=full[0]:0->1 hier=vibration_core
+000040  point: type=toggle comment=full[0]:1->0 hier=vibration_core
+000030  point: type=toggle comment=full[1]:0->1 hier=vibration_core
+000030  point: type=toggle comment=full[1]:1->0 hier=vibration_core
+000040  point: type=toggle comment=busy[0]:0->1 hier=vibration_core
+000040  point: type=toggle comment=busy[0]:1->0 hier=vibration_core
+000030  point: type=toggle comment=busy[1]:0->1 hier=vibration_core
+000030  point: type=toggle comment=busy[1]:1->0 hier=vibration_core
 000040     reg write_bank, read_bank, active_bank;
+000040  point: type=toggle comment=read_bank:0->1 hier=vibration_core
+000038  point: type=toggle comment=read_bank:1->0 hier=vibration_core
+000030  point: type=toggle comment=active_bank:0->1 hier=vibration_core
+000030  point: type=toggle comment=active_bank:1->0 hier=vibration_core
+000040  point: type=toggle comment=write_bank:0->1 hier=vibration_core
+000038  point: type=toggle comment=write_bank:1->0 hier=vibration_core
 000074     reg receiving, draining;
+000002  point: type=toggle comment=draining:0->1 hier=vibration_core
+000002  point: type=toggle comment=draining:1->0 hier=vibration_core
+000074  point: type=toggle comment=receiving:0->1 hier=vibration_core
+000074  point: type=toggle comment=receiving:1->0 hier=vibration_core
 036844     reg [P-1:0] input_index;
+036844  point: type=toggle comment=input_index[0]:0->1 hier=vibration_core
+036842  point: type=toggle comment=input_index[0]:1->0 hier=vibration_core
+018446  point: type=toggle comment=input_index[1]:0->1 hier=vibration_core
+018444  point: type=toggle comment=input_index[1]:1->0 hier=vibration_core
+009224  point: type=toggle comment=input_index[2]:0->1 hier=vibration_core
+009222  point: type=toggle comment=input_index[2]:1->0 hier=vibration_core
+004610  point: type=toggle comment=input_index[3]:0->1 hier=vibration_core
+004608  point: type=toggle comment=input_index[3]:1->0 hier=vibration_core
+002306  point: type=toggle comment=input_index[4]:0->1 hier=vibration_core
+002304  point: type=toggle comment=input_index[4]:1->0 hier=vibration_core
+001152  point: type=toggle comment=input_index[5]:0->1 hier=vibration_core
+001150  point: type=toggle comment=input_index[5]:1->0 hier=vibration_core
+000576  point: type=toggle comment=input_index[6]:0->1 hier=vibration_core
+000574  point: type=toggle comment=input_index[6]:1->0 hier=vibration_core
+000288  point: type=toggle comment=input_index[7]:0->1 hier=vibration_core
+000286  point: type=toggle comment=input_index[7]:1->0 hier=vibration_core
+000144  point: type=toggle comment=input_index[8]:0->1 hier=vibration_core
+000142  point: type=toggle comment=input_index[8]:1->0 hier=vibration_core
+000072  point: type=toggle comment=input_index[9]:0->1 hier=vibration_core
+000070  point: type=toggle comment=input_index[9]:1->0 hier=vibration_core
~000038     reg [31:0] receiving_id, frame_ids [0:1];
+000038  point: type=toggle comment=receiving_id[0]:0->1 hier=vibration_core
+000036  point: type=toggle comment=receiving_id[0]:1->0 hier=vibration_core
-000000  point: type=toggle comment=receiving_id[10]:0->1 hier=vibration_core
-000000  point: type=toggle comment=receiving_id[10]:1->0 hier=vibration_core
-000000  point: type=toggle comment=receiving_id[11]:0->1 hier=vibration_core
-000000  point: type=toggle comment=receiving_id[11]:1->0 hier=vibration_core
-000000  point: type=toggle comment=receiving_id[12]:0->1 hier=vibration_core
-000000  point: type=toggle comment=receiving_id[12]:1->0 hier=vibration_core
-000000  point: type=toggle comment=receiving_id[13]:0->1 hier=vibration_core
-000000  point: type=toggle comment=receiving_id[13]:1->0 hier=vibration_core
-000000  point: type=toggle comment=receiving_id[14]:0->1 hier=vibration_core
-000000  point: type=toggle comment=receiving_id[14]:1->0 hier=vibration_core
-000000  point: type=toggle comment=receiving_id[15]:0->1 hier=vibration_core
-000000  point: type=toggle comment=receiving_id[15]:1->0 hier=vibration_core
-000000  point: type=toggle comment=receiving_id[16]:0->1 hier=vibration_core
-000000  point: type=toggle comment=receiving_id[16]:1->0 hier=vibration_core
-000000  point: type=toggle comment=receiving_id[17]:0->1 hier=vibration_core
-000000  point: type=toggle comment=receiving_id[17]:1->0 hier=vibration_core
-000000  point: type=toggle comment=receiving_id[18]:0->1 hier=vibration_core
-000000  point: type=toggle comment=receiving_id[18]:1->0 hier=vibration_core
-000000  point: type=toggle comment=receiving_id[19]:0->1 hier=vibration_core
-000000  point: type=toggle comment=receiving_id[19]:1->0 hier=vibration_core
+000025  point: type=toggle comment=receiving_id[1]:0->1 hier=vibration_core
+000023  point: type=toggle comment=receiving_id[1]:1->0 hier=vibration_core
-000000  point: type=toggle comment=receiving_id[20]:0->1 hier=vibration_core
-000000  point: type=toggle comment=receiving_id[20]:1->0 hier=vibration_core
-000000  point: type=toggle comment=receiving_id[21]:0->1 hier=vibration_core
-000000  point: type=toggle comment=receiving_id[21]:1->0 hier=vibration_core
-000000  point: type=toggle comment=receiving_id[22]:0->1 hier=vibration_core
-000000  point: type=toggle comment=receiving_id[22]:1->0 hier=vibration_core
-000000  point: type=toggle comment=receiving_id[23]:0->1 hier=vibration_core
-000000  point: type=toggle comment=receiving_id[23]:1->0 hier=vibration_core
-000000  point: type=toggle comment=receiving_id[24]:0->1 hier=vibration_core
-000000  point: type=toggle comment=receiving_id[24]:1->0 hier=vibration_core
-000000  point: type=toggle comment=receiving_id[25]:0->1 hier=vibration_core
-000000  point: type=toggle comment=receiving_id[25]:1->0 hier=vibration_core
-000000  point: type=toggle comment=receiving_id[26]:0->1 hier=vibration_core
-000000  point: type=toggle comment=receiving_id[26]:1->0 hier=vibration_core
-000000  point: type=toggle comment=receiving_id[27]:0->1 hier=vibration_core
-000000  point: type=toggle comment=receiving_id[27]:1->0 hier=vibration_core
-000000  point: type=toggle comment=receiving_id[28]:0->1 hier=vibration_core
-000000  point: type=toggle comment=receiving_id[28]:1->0 hier=vibration_core
-000000  point: type=toggle comment=receiving_id[29]:0->1 hier=vibration_core
-000000  point: type=toggle comment=receiving_id[29]:1->0 hier=vibration_core
+000023  point: type=toggle comment=receiving_id[2]:0->1 hier=vibration_core
+000021  point: type=toggle comment=receiving_id[2]:1->0 hier=vibration_core
-000000  point: type=toggle comment=receiving_id[30]:0->1 hier=vibration_core
-000000  point: type=toggle comment=receiving_id[30]:1->0 hier=vibration_core
-000000  point: type=toggle comment=receiving_id[31]:0->1 hier=vibration_core
-000000  point: type=toggle comment=receiving_id[31]:1->0 hier=vibration_core
+000018  point: type=toggle comment=receiving_id[3]:0->1 hier=vibration_core
+000018  point: type=toggle comment=receiving_id[3]:1->0 hier=vibration_core
+000010  point: type=toggle comment=receiving_id[4]:0->1 hier=vibration_core
+000008  point: type=toggle comment=receiving_id[4]:1->0 hier=vibration_core
+000022  point: type=toggle comment=receiving_id[5]:0->1 hier=vibration_core
+000020  point: type=toggle comment=receiving_id[5]:1->0 hier=vibration_core
+000010  point: type=toggle comment=receiving_id[6]:0->1 hier=vibration_core
+000010  point: type=toggle comment=receiving_id[6]:1->0 hier=vibration_core
+000002  point: type=toggle comment=receiving_id[7]:0->1 hier=vibration_core
+000002  point: type=toggle comment=receiving_id[7]:1->0 hier=vibration_core
+000014  point: type=toggle comment=receiving_id[8]:0->1 hier=vibration_core
+000012  point: type=toggle comment=receiving_id[8]:1->0 hier=vibration_core
-000000  point: type=toggle comment=receiving_id[9]:0->1 hier=vibration_core
-000000  point: type=toggle comment=receiving_id[9]:1->0 hier=vibration_core
+000004  point: type=toggle comment=frame_ids[0][0]:0->1 hier=vibration_core
+000002  point: type=toggle comment=frame_ids[0][0]:1->0 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[0][10]:0->1 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[0][10]:1->0 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[0][11]:0->1 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[0][11]:1->0 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[0][12]:0->1 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[0][12]:1->0 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[0][13]:0->1 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[0][13]:1->0 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[0][14]:0->1 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[0][14]:1->0 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[0][15]:0->1 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[0][15]:1->0 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[0][16]:0->1 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[0][16]:1->0 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[0][17]:0->1 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[0][17]:1->0 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[0][18]:0->1 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[0][18]:1->0 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[0][19]:0->1 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[0][19]:1->0 hier=vibration_core
+000017  point: type=toggle comment=frame_ids[0][1]:0->1 hier=vibration_core
+000015  point: type=toggle comment=frame_ids[0][1]:1->0 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[0][20]:0->1 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[0][20]:1->0 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[0][21]:0->1 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[0][21]:1->0 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[0][22]:0->1 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[0][22]:1->0 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[0][23]:0->1 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[0][23]:1->0 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[0][24]:0->1 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[0][24]:1->0 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[0][25]:0->1 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[0][25]:1->0 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[0][26]:0->1 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[0][26]:1->0 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[0][27]:0->1 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[0][27]:1->0 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[0][28]:0->1 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[0][28]:1->0 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[0][29]:0->1 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[0][29]:1->0 hier=vibration_core
+000010  point: type=toggle comment=frame_ids[0][2]:0->1 hier=vibration_core
+000008  point: type=toggle comment=frame_ids[0][2]:1->0 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[0][30]:0->1 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[0][30]:1->0 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[0][31]:0->1 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[0][31]:1->0 hier=vibration_core
+000004  point: type=toggle comment=frame_ids[0][3]:0->1 hier=vibration_core
+000004  point: type=toggle comment=frame_ids[0][3]:1->0 hier=vibration_core
+000002  point: type=toggle comment=frame_ids[0][4]:0->1 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[0][4]:1->0 hier=vibration_core
+000004  point: type=toggle comment=frame_ids[0][5]:0->1 hier=vibration_core
+000002  point: type=toggle comment=frame_ids[0][5]:1->0 hier=vibration_core
+000002  point: type=toggle comment=frame_ids[0][6]:0->1 hier=vibration_core
+000002  point: type=toggle comment=frame_ids[0][6]:1->0 hier=vibration_core
+000002  point: type=toggle comment=frame_ids[0][7]:0->1 hier=vibration_core
+000002  point: type=toggle comment=frame_ids[0][7]:1->0 hier=vibration_core
+000002  point: type=toggle comment=frame_ids[0][8]:0->1 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[0][8]:1->0 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[0][9]:0->1 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[0][9]:1->0 hier=vibration_core
+000004  point: type=toggle comment=frame_ids[1][0]:0->1 hier=vibration_core
+000004  point: type=toggle comment=frame_ids[1][0]:1->0 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[1][10]:0->1 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[1][10]:1->0 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[1][11]:0->1 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[1][11]:1->0 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[1][12]:0->1 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[1][12]:1->0 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[1][13]:0->1 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[1][13]:1->0 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[1][14]:0->1 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[1][14]:1->0 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[1][15]:0->1 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[1][15]:1->0 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[1][16]:0->1 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[1][16]:1->0 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[1][17]:0->1 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[1][17]:1->0 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[1][18]:0->1 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[1][18]:1->0 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[1][19]:0->1 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[1][19]:1->0 hier=vibration_core
+000013  point: type=toggle comment=frame_ids[1][1]:0->1 hier=vibration_core
+000011  point: type=toggle comment=frame_ids[1][1]:1->0 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[1][20]:0->1 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[1][20]:1->0 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[1][21]:0->1 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[1][21]:1->0 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[1][22]:0->1 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[1][22]:1->0 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[1][23]:0->1 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[1][23]:1->0 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[1][24]:0->1 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[1][24]:1->0 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[1][25]:0->1 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[1][25]:1->0 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[1][26]:0->1 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[1][26]:1->0 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[1][27]:0->1 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[1][27]:1->0 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[1][28]:0->1 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[1][28]:1->0 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[1][29]:0->1 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[1][29]:1->0 hier=vibration_core
+000009  point: type=toggle comment=frame_ids[1][2]:0->1 hier=vibration_core
+000007  point: type=toggle comment=frame_ids[1][2]:1->0 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[1][30]:0->1 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[1][30]:1->0 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[1][31]:0->1 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[1][31]:1->0 hier=vibration_core
+000002  point: type=toggle comment=frame_ids[1][3]:0->1 hier=vibration_core
+000002  point: type=toggle comment=frame_ids[1][3]:1->0 hier=vibration_core
+000002  point: type=toggle comment=frame_ids[1][4]:0->1 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[1][4]:1->0 hier=vibration_core
+000004  point: type=toggle comment=frame_ids[1][5]:0->1 hier=vibration_core
+000002  point: type=toggle comment=frame_ids[1][5]:1->0 hier=vibration_core
+000002  point: type=toggle comment=frame_ids[1][6]:0->1 hier=vibration_core
+000002  point: type=toggle comment=frame_ids[1][6]:1->0 hier=vibration_core
+000002  point: type=toggle comment=frame_ids[1][7]:0->1 hier=vibration_core
+000002  point: type=toggle comment=frame_ids[1][7]:1->0 hier=vibration_core
+000002  point: type=toggle comment=frame_ids[1][8]:0->1 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[1][8]:1->0 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[1][9]:0->1 hier=vibration_core
-000000  point: type=toggle comment=frame_ids[1][9]:1->0 hier=vibration_core
 018005     reg signed [SUM_W-1:0] input_sum, frame_sums [0:1];
+018005  point: type=toggle comment=input_sum[0]:0->1 hier=vibration_core
+018005  point: type=toggle comment=input_sum[0]:1->0 hier=vibration_core
+015723  point: type=toggle comment=input_sum[10]:0->1 hier=vibration_core
+015723  point: type=toggle comment=input_sum[10]:1->0 hier=vibration_core
+016778  point: type=toggle comment=input_sum[11]:0->1 hier=vibration_core
+016777  point: type=toggle comment=input_sum[11]:1->0 hier=vibration_core
+015080  point: type=toggle comment=input_sum[12]:0->1 hier=vibration_core
+015080  point: type=toggle comment=input_sum[12]:1->0 hier=vibration_core
+014303  point: type=toggle comment=input_sum[13]:0->1 hier=vibration_core
+014302  point: type=toggle comment=input_sum[13]:1->0 hier=vibration_core
+015759  point: type=toggle comment=input_sum[14]:0->1 hier=vibration_core
+015759  point: type=toggle comment=input_sum[14]:1->0 hier=vibration_core
+011614  point: type=toggle comment=input_sum[15]:0->1 hier=vibration_core
+011614  point: type=toggle comment=input_sum[15]:1->0 hier=vibration_core
+008927  point: type=toggle comment=input_sum[16]:0->1 hier=vibration_core
+008927  point: type=toggle comment=input_sum[16]:1->0 hier=vibration_core
+008075  point: type=toggle comment=input_sum[17]:0->1 hier=vibration_core
+008075  point: type=toggle comment=input_sum[17]:1->0 hier=vibration_core
+007641  point: type=toggle comment=input_sum[18]:0->1 hier=vibration_core
+007641  point: type=toggle comment=input_sum[18]:1->0 hier=vibration_core
+007396  point: type=toggle comment=input_sum[19]:0->1 hier=vibration_core
+007396  point: type=toggle comment=input_sum[19]:1->0 hier=vibration_core
+015985  point: type=toggle comment=input_sum[1]:0->1 hier=vibration_core
+015984  point: type=toggle comment=input_sum[1]:1->0 hier=vibration_core
+007373  point: type=toggle comment=input_sum[20]:0->1 hier=vibration_core
+007373  point: type=toggle comment=input_sum[20]:1->0 hier=vibration_core
+007365  point: type=toggle comment=input_sum[21]:0->1 hier=vibration_core
+007365  point: type=toggle comment=input_sum[21]:1->0 hier=vibration_core
+007360  point: type=toggle comment=input_sum[22]:0->1 hier=vibration_core
+007360  point: type=toggle comment=input_sum[22]:1->0 hier=vibration_core
+007358  point: type=toggle comment=input_sum[23]:0->1 hier=vibration_core
+007358  point: type=toggle comment=input_sum[23]:1->0 hier=vibration_core
+007358  point: type=toggle comment=input_sum[24]:0->1 hier=vibration_core
+007358  point: type=toggle comment=input_sum[24]:1->0 hier=vibration_core
+007358  point: type=toggle comment=input_sum[25]:0->1 hier=vibration_core
+007358  point: type=toggle comment=input_sum[25]:1->0 hier=vibration_core
+015096  point: type=toggle comment=input_sum[2]:0->1 hier=vibration_core
+015095  point: type=toggle comment=input_sum[2]:1->0 hier=vibration_core
+014448  point: type=toggle comment=input_sum[3]:0->1 hier=vibration_core
+014447  point: type=toggle comment=input_sum[3]:1->0 hier=vibration_core
+014571  point: type=toggle comment=input_sum[4]:0->1 hier=vibration_core
+014570  point: type=toggle comment=input_sum[4]:1->0 hier=vibration_core
+014255  point: type=toggle comment=input_sum[5]:0->1 hier=vibration_core
+014255  point: type=toggle comment=input_sum[5]:1->0 hier=vibration_core
+014184  point: type=toggle comment=input_sum[6]:0->1 hier=vibration_core
+014183  point: type=toggle comment=input_sum[6]:1->0 hier=vibration_core
+014392  point: type=toggle comment=input_sum[7]:0->1 hier=vibration_core
+014391  point: type=toggle comment=input_sum[7]:1->0 hier=vibration_core
+014077  point: type=toggle comment=input_sum[8]:0->1 hier=vibration_core
+014076  point: type=toggle comment=input_sum[8]:1->0 hier=vibration_core
+017767  point: type=toggle comment=input_sum[9]:0->1 hier=vibration_core
+017766  point: type=toggle comment=input_sum[9]:1->0 hier=vibration_core
+000007  point: type=toggle comment=frame_sums[0][0]:0->1 hier=vibration_core
+000007  point: type=toggle comment=frame_sums[0][0]:1->0 hier=vibration_core
+000004  point: type=toggle comment=frame_sums[0][10]:0->1 hier=vibration_core
+000004  point: type=toggle comment=frame_sums[0][10]:1->0 hier=vibration_core
+000007  point: type=toggle comment=frame_sums[0][11]:0->1 hier=vibration_core
+000006  point: type=toggle comment=frame_sums[0][11]:1->0 hier=vibration_core
+000006  point: type=toggle comment=frame_sums[0][12]:0->1 hier=vibration_core
+000006  point: type=toggle comment=frame_sums[0][12]:1->0 hier=vibration_core
+000006  point: type=toggle comment=frame_sums[0][13]:0->1 hier=vibration_core
+000005  point: type=toggle comment=frame_sums[0][13]:1->0 hier=vibration_core
+000005  point: type=toggle comment=frame_sums[0][14]:0->1 hier=vibration_core
+000005  point: type=toggle comment=frame_sums[0][14]:1->0 hier=vibration_core
+000005  point: type=toggle comment=frame_sums[0][15]:0->1 hier=vibration_core
+000005  point: type=toggle comment=frame_sums[0][15]:1->0 hier=vibration_core
+000002  point: type=toggle comment=frame_sums[0][16]:0->1 hier=vibration_core
+000002  point: type=toggle comment=frame_sums[0][16]:1->0 hier=vibration_core
+000005  point: type=toggle comment=frame_sums[0][17]:0->1 hier=vibration_core
+000005  point: type=toggle comment=frame_sums[0][17]:1->0 hier=vibration_core
+000005  point: type=toggle comment=frame_sums[0][18]:0->1 hier=vibration_core
+000005  point: type=toggle comment=frame_sums[0][18]:1->0 hier=vibration_core
+000001  point: type=toggle comment=frame_sums[0][19]:0->1 hier=vibration_core
+000001  point: type=toggle comment=frame_sums[0][19]:1->0 hier=vibration_core
+000005  point: type=toggle comment=frame_sums[0][1]:0->1 hier=vibration_core
+000004  point: type=toggle comment=frame_sums[0][1]:1->0 hier=vibration_core
+000001  point: type=toggle comment=frame_sums[0][20]:0->1 hier=vibration_core
+000001  point: type=toggle comment=frame_sums[0][20]:1->0 hier=vibration_core
+000003  point: type=toggle comment=frame_sums[0][21]:0->1 hier=vibration_core
+000003  point: type=toggle comment=frame_sums[0][21]:1->0 hier=vibration_core
+000003  point: type=toggle comment=frame_sums[0][22]:0->1 hier=vibration_core
+000003  point: type=toggle comment=frame_sums[0][22]:1->0 hier=vibration_core
+000003  point: type=toggle comment=frame_sums[0][23]:0->1 hier=vibration_core
+000003  point: type=toggle comment=frame_sums[0][23]:1->0 hier=vibration_core
+000002  point: type=toggle comment=frame_sums[0][24]:0->1 hier=vibration_core
+000002  point: type=toggle comment=frame_sums[0][24]:1->0 hier=vibration_core
+000002  point: type=toggle comment=frame_sums[0][25]:0->1 hier=vibration_core
+000002  point: type=toggle comment=frame_sums[0][25]:1->0 hier=vibration_core
+000008  point: type=toggle comment=frame_sums[0][2]:0->1 hier=vibration_core
+000007  point: type=toggle comment=frame_sums[0][2]:1->0 hier=vibration_core
+000003  point: type=toggle comment=frame_sums[0][3]:0->1 hier=vibration_core
+000002  point: type=toggle comment=frame_sums[0][3]:1->0 hier=vibration_core
+000005  point: type=toggle comment=frame_sums[0][4]:0->1 hier=vibration_core
+000004  point: type=toggle comment=frame_sums[0][4]:1->0 hier=vibration_core
+000002  point: type=toggle comment=frame_sums[0][5]:0->1 hier=vibration_core
+000002  point: type=toggle comment=frame_sums[0][5]:1->0 hier=vibration_core
+000006  point: type=toggle comment=frame_sums[0][6]:0->1 hier=vibration_core
+000005  point: type=toggle comment=frame_sums[0][6]:1->0 hier=vibration_core
+000005  point: type=toggle comment=frame_sums[0][7]:0->1 hier=vibration_core
+000004  point: type=toggle comment=frame_sums[0][7]:1->0 hier=vibration_core
+000004  point: type=toggle comment=frame_sums[0][8]:0->1 hier=vibration_core
+000003  point: type=toggle comment=frame_sums[0][8]:1->0 hier=vibration_core
+000004  point: type=toggle comment=frame_sums[0][9]:0->1 hier=vibration_core
+000003  point: type=toggle comment=frame_sums[0][9]:1->0 hier=vibration_core
+000005  point: type=toggle comment=frame_sums[1][0]:0->1 hier=vibration_core
+000003  point: type=toggle comment=frame_sums[1][0]:1->0 hier=vibration_core
+000007  point: type=toggle comment=frame_sums[1][10]:0->1 hier=vibration_core
+000006  point: type=toggle comment=frame_sums[1][10]:1->0 hier=vibration_core
+000006  point: type=toggle comment=frame_sums[1][11]:0->1 hier=vibration_core
+000004  point: type=toggle comment=frame_sums[1][11]:1->0 hier=vibration_core
+000007  point: type=toggle comment=frame_sums[1][12]:0->1 hier=vibration_core
+000006  point: type=toggle comment=frame_sums[1][12]:1->0 hier=vibration_core
+000005  point: type=toggle comment=frame_sums[1][13]:0->1 hier=vibration_core
+000005  point: type=toggle comment=frame_sums[1][13]:1->0 hier=vibration_core
+000004  point: type=toggle comment=frame_sums[1][14]:0->1 hier=vibration_core
+000003  point: type=toggle comment=frame_sums[1][14]:1->0 hier=vibration_core
+000005  point: type=toggle comment=frame_sums[1][15]:0->1 hier=vibration_core
+000004  point: type=toggle comment=frame_sums[1][15]:1->0 hier=vibration_core
+000004  point: type=toggle comment=frame_sums[1][16]:0->1 hier=vibration_core
+000004  point: type=toggle comment=frame_sums[1][16]:1->0 hier=vibration_core
+000005  point: type=toggle comment=frame_sums[1][17]:0->1 hier=vibration_core
+000004  point: type=toggle comment=frame_sums[1][17]:1->0 hier=vibration_core
+000004  point: type=toggle comment=frame_sums[1][18]:0->1 hier=vibration_core
+000003  point: type=toggle comment=frame_sums[1][18]:1->0 hier=vibration_core
+000002  point: type=toggle comment=frame_sums[1][19]:0->1 hier=vibration_core
+000002  point: type=toggle comment=frame_sums[1][19]:1->0 hier=vibration_core
+000001  point: type=toggle comment=frame_sums[1][1]:0->1 hier=vibration_core
+000001  point: type=toggle comment=frame_sums[1][1]:1->0 hier=vibration_core
+000002  point: type=toggle comment=frame_sums[1][20]:0->1 hier=vibration_core
+000002  point: type=toggle comment=frame_sums[1][20]:1->0 hier=vibration_core
+000004  point: type=toggle comment=frame_sums[1][21]:0->1 hier=vibration_core
+000004  point: type=toggle comment=frame_sums[1][21]:1->0 hier=vibration_core
+000004  point: type=toggle comment=frame_sums[1][22]:0->1 hier=vibration_core
+000004  point: type=toggle comment=frame_sums[1][22]:1->0 hier=vibration_core
+000004  point: type=toggle comment=frame_sums[1][23]:0->1 hier=vibration_core
+000004  point: type=toggle comment=frame_sums[1][23]:1->0 hier=vibration_core
+000005  point: type=toggle comment=frame_sums[1][24]:0->1 hier=vibration_core
+000005  point: type=toggle comment=frame_sums[1][24]:1->0 hier=vibration_core
+000005  point: type=toggle comment=frame_sums[1][25]:0->1 hier=vibration_core
+000005  point: type=toggle comment=frame_sums[1][25]:1->0 hier=vibration_core
+000006  point: type=toggle comment=frame_sums[1][2]:0->1 hier=vibration_core
+000005  point: type=toggle comment=frame_sums[1][2]:1->0 hier=vibration_core
+000005  point: type=toggle comment=frame_sums[1][3]:0->1 hier=vibration_core
+000004  point: type=toggle comment=frame_sums[1][3]:1->0 hier=vibration_core
+000004  point: type=toggle comment=frame_sums[1][4]:0->1 hier=vibration_core
+000003  point: type=toggle comment=frame_sums[1][4]:1->0 hier=vibration_core
+000003  point: type=toggle comment=frame_sums[1][5]:0->1 hier=vibration_core
+000003  point: type=toggle comment=frame_sums[1][5]:1->0 hier=vibration_core
+000004  point: type=toggle comment=frame_sums[1][6]:0->1 hier=vibration_core
+000004  point: type=toggle comment=frame_sums[1][6]:1->0 hier=vibration_core
+000005  point: type=toggle comment=frame_sums[1][7]:0->1 hier=vibration_core
+000005  point: type=toggle comment=frame_sums[1][7]:1->0 hier=vibration_core
+000004  point: type=toggle comment=frame_sums[1][8]:0->1 hier=vibration_core
+000003  point: type=toggle comment=frame_sums[1][8]:1->0 hier=vibration_core
+000005  point: type=toggle comment=frame_sums[1][9]:0->1 hier=vibration_core
+000005  point: type=toggle comment=frame_sums[1][9]:1->0 hier=vibration_core
 92735848     wire restart_input = !receiving || in_frame_id != receiving_id;
+000080  point: type=toggle comment=restart_input:0->1 hier=vibration_core
+000078  point: type=toggle comment=restart_input:1->0 hier=vibration_core
+32893065  point: type=expr comment=((in_frame_id != receiving_id)==1) => 1 hier=vibration_core
+92735848  point: type=expr comment=(receiving==0) => 1 hier=vibration_core
+518568  point: type=expr comment=(receiving==1 && (in_frame_id != receiving_id)==0) => 0 hier=vibration_core
 015786     wire signed [SUM_W-1:0] extended_sample = {{(SUM_W-16){in_sample[15]}}, in_sample};
+015728  point: type=toggle comment=extended_sample[0]:0->1 hier=vibration_core
+015728  point: type=toggle comment=extended_sample[0]:1->0 hier=vibration_core
+014974  point: type=toggle comment=extended_sample[10]:0->1 hier=vibration_core
+014974  point: type=toggle comment=extended_sample[10]:1->0 hier=vibration_core
+013069  point: type=toggle comment=extended_sample[11]:0->1 hier=vibration_core
+013068  point: type=toggle comment=extended_sample[11]:1->0 hier=vibration_core
+012859  point: type=toggle comment=extended_sample[12]:0->1 hier=vibration_core
+012858  point: type=toggle comment=extended_sample[12]:1->0 hier=vibration_core
+013466  point: type=toggle comment=extended_sample[13]:0->1 hier=vibration_core
+013465  point: type=toggle comment=extended_sample[13]:1->0 hier=vibration_core
+013504  point: type=toggle comment=extended_sample[14]:0->1 hier=vibration_core
+013503  point: type=toggle comment=extended_sample[14]:1->0 hier=vibration_core
+013350  point: type=toggle comment=extended_sample[15]:0->1 hier=vibration_core
+013349  point: type=toggle comment=extended_sample[15]:1->0 hier=vibration_core
+013350  point: type=toggle comment=extended_sample[16]:0->1 hier=vibration_core
+013349  point: type=toggle comment=extended_sample[16]:1->0 hier=vibration_core
+013350  point: type=toggle comment=extended_sample[17]:0->1 hier=vibration_core
+013349  point: type=toggle comment=extended_sample[17]:1->0 hier=vibration_core
+013350  point: type=toggle comment=extended_sample[18]:0->1 hier=vibration_core
+013349  point: type=toggle comment=extended_sample[18]:1->0 hier=vibration_core
+013350  point: type=toggle comment=extended_sample[19]:0->1 hier=vibration_core
+013349  point: type=toggle comment=extended_sample[19]:1->0 hier=vibration_core
+015303  point: type=toggle comment=extended_sample[1]:0->1 hier=vibration_core
+015303  point: type=toggle comment=extended_sample[1]:1->0 hier=vibration_core
+013350  point: type=toggle comment=extended_sample[20]:0->1 hier=vibration_core
+013349  point: type=toggle comment=extended_sample[20]:1->0 hier=vibration_core
+013350  point: type=toggle comment=extended_sample[21]:0->1 hier=vibration_core
+013349  point: type=toggle comment=extended_sample[21]:1->0 hier=vibration_core
+013350  point: type=toggle comment=extended_sample[22]:0->1 hier=vibration_core
+013349  point: type=toggle comment=extended_sample[22]:1->0 hier=vibration_core
+013350  point: type=toggle comment=extended_sample[23]:0->1 hier=vibration_core
+013349  point: type=toggle comment=extended_sample[23]:1->0 hier=vibration_core
+013350  point: type=toggle comment=extended_sample[24]:0->1 hier=vibration_core
+013349  point: type=toggle comment=extended_sample[24]:1->0 hier=vibration_core
+013350  point: type=toggle comment=extended_sample[25]:0->1 hier=vibration_core
+013349  point: type=toggle comment=extended_sample[25]:1->0 hier=vibration_core
+015142  point: type=toggle comment=extended_sample[2]:0->1 hier=vibration_core
+015140  point: type=toggle comment=extended_sample[2]:1->0 hier=vibration_core
+015295  point: type=toggle comment=extended_sample[3]:0->1 hier=vibration_core
+015295  point: type=toggle comment=extended_sample[3]:1->0 hier=vibration_core
+015192  point: type=toggle comment=extended_sample[4]:0->1 hier=vibration_core
+015191  point: type=toggle comment=extended_sample[4]:1->0 hier=vibration_core
+014881  point: type=toggle comment=extended_sample[5]:0->1 hier=vibration_core
+014881  point: type=toggle comment=extended_sample[5]:1->0 hier=vibration_core
+015399  point: type=toggle comment=extended_sample[6]:0->1 hier=vibration_core
+015397  point: type=toggle comment=extended_sample[6]:1->0 hier=vibration_core
+015395  point: type=toggle comment=extended_sample[7]:0->1 hier=vibration_core
+015394  point: type=toggle comment=extended_sample[7]:1->0 hier=vibration_core
+015786  point: type=toggle comment=extended_sample[8]:0->1 hier=vibration_core
+015785  point: type=toggle comment=extended_sample[8]:1->0 hier=vibration_core
+015081  point: type=toggle comment=extended_sample[9]:0->1 hier=vibration_core
+015080  point: type=toggle comment=extended_sample[9]:1->0 hier=vibration_core
 54393073     assign in_ready = !rst && (receiving || (!full[write_bank] && !busy[write_bank]));
+440254  point: type=expr comment=(receiving==0 && busy[write_bank+:1]==1) => 0 hier=vibration_core
+38420543  point: type=expr comment=(receiving==0 && full[write_bank+:1]==1) => 0 hier=vibration_core
+54393073  point: type=expr comment=(rst==0 && full[write_bank+:1]==0 && busy[write_bank+:1]==0) => 1 hier=vibration_core
+518584  point: type=expr comment=(rst==0 && receiving==1) => 1 hier=vibration_core
+000568  point: type=expr comment=(rst==1) => 0 hier=vibration_core
        
~000036     reg [31:0] active_id;
+000036  point: type=toggle comment=active_id[0]:0->1 hier=vibration_core
+000034  point: type=toggle comment=active_id[0]:1->0 hier=vibration_core
-000000  point: type=toggle comment=active_id[10]:0->1 hier=vibration_core
-000000  point: type=toggle comment=active_id[10]:1->0 hier=vibration_core
-000000  point: type=toggle comment=active_id[11]:0->1 hier=vibration_core
-000000  point: type=toggle comment=active_id[11]:1->0 hier=vibration_core
-000000  point: type=toggle comment=active_id[12]:0->1 hier=vibration_core
-000000  point: type=toggle comment=active_id[12]:1->0 hier=vibration_core
-000000  point: type=toggle comment=active_id[13]:0->1 hier=vibration_core
-000000  point: type=toggle comment=active_id[13]:1->0 hier=vibration_core
-000000  point: type=toggle comment=active_id[14]:0->1 hier=vibration_core
-000000  point: type=toggle comment=active_id[14]:1->0 hier=vibration_core
-000000  point: type=toggle comment=active_id[15]:0->1 hier=vibration_core
-000000  point: type=toggle comment=active_id[15]:1->0 hier=vibration_core
-000000  point: type=toggle comment=active_id[16]:0->1 hier=vibration_core
-000000  point: type=toggle comment=active_id[16]:1->0 hier=vibration_core
-000000  point: type=toggle comment=active_id[17]:0->1 hier=vibration_core
-000000  point: type=toggle comment=active_id[17]:1->0 hier=vibration_core
-000000  point: type=toggle comment=active_id[18]:0->1 hier=vibration_core
-000000  point: type=toggle comment=active_id[18]:1->0 hier=vibration_core
-000000  point: type=toggle comment=active_id[19]:0->1 hier=vibration_core
-000000  point: type=toggle comment=active_id[19]:1->0 hier=vibration_core
+000025  point: type=toggle comment=active_id[1]:0->1 hier=vibration_core
+000023  point: type=toggle comment=active_id[1]:1->0 hier=vibration_core
-000000  point: type=toggle comment=active_id[20]:0->1 hier=vibration_core
-000000  point: type=toggle comment=active_id[20]:1->0 hier=vibration_core
-000000  point: type=toggle comment=active_id[21]:0->1 hier=vibration_core
-000000  point: type=toggle comment=active_id[21]:1->0 hier=vibration_core
-000000  point: type=toggle comment=active_id[22]:0->1 hier=vibration_core
-000000  point: type=toggle comment=active_id[22]:1->0 hier=vibration_core
-000000  point: type=toggle comment=active_id[23]:0->1 hier=vibration_core
-000000  point: type=toggle comment=active_id[23]:1->0 hier=vibration_core
-000000  point: type=toggle comment=active_id[24]:0->1 hier=vibration_core
-000000  point: type=toggle comment=active_id[24]:1->0 hier=vibration_core
-000000  point: type=toggle comment=active_id[25]:0->1 hier=vibration_core
-000000  point: type=toggle comment=active_id[25]:1->0 hier=vibration_core
-000000  point: type=toggle comment=active_id[26]:0->1 hier=vibration_core
-000000  point: type=toggle comment=active_id[26]:1->0 hier=vibration_core
-000000  point: type=toggle comment=active_id[27]:0->1 hier=vibration_core
-000000  point: type=toggle comment=active_id[27]:1->0 hier=vibration_core
-000000  point: type=toggle comment=active_id[28]:0->1 hier=vibration_core
-000000  point: type=toggle comment=active_id[28]:1->0 hier=vibration_core
-000000  point: type=toggle comment=active_id[29]:0->1 hier=vibration_core
-000000  point: type=toggle comment=active_id[29]:1->0 hier=vibration_core
+000023  point: type=toggle comment=active_id[2]:0->1 hier=vibration_core
+000021  point: type=toggle comment=active_id[2]:1->0 hier=vibration_core
-000000  point: type=toggle comment=active_id[30]:0->1 hier=vibration_core
-000000  point: type=toggle comment=active_id[30]:1->0 hier=vibration_core
-000000  point: type=toggle comment=active_id[31]:0->1 hier=vibration_core
-000000  point: type=toggle comment=active_id[31]:1->0 hier=vibration_core
+000016  point: type=toggle comment=active_id[3]:0->1 hier=vibration_core
+000016  point: type=toggle comment=active_id[3]:1->0 hier=vibration_core
+000010  point: type=toggle comment=active_id[4]:0->1 hier=vibration_core
+000008  point: type=toggle comment=active_id[4]:1->0 hier=vibration_core
+000022  point: type=toggle comment=active_id[5]:0->1 hier=vibration_core
+000020  point: type=toggle comment=active_id[5]:1->0 hier=vibration_core
+000010  point: type=toggle comment=active_id[6]:0->1 hier=vibration_core
+000010  point: type=toggle comment=active_id[6]:1->0 hier=vibration_core
+000002  point: type=toggle comment=active_id[7]:0->1 hier=vibration_core
+000002  point: type=toggle comment=active_id[7]:1->0 hier=vibration_core
+000014  point: type=toggle comment=active_id[8]:0->1 hier=vibration_core
+000012  point: type=toggle comment=active_id[8]:1->0 hier=vibration_core
-000000  point: type=toggle comment=active_id[9]:0->1 hier=vibration_core
-000000  point: type=toggle comment=active_id[9]:1->0 hier=vibration_core
 3081226     reg [P-1:0] point;
+3081226  point: type=toggle comment=point[0]:0->1 hier=vibration_core
+3081224  point: type=toggle comment=point[0]:1->0 hier=vibration_core
+1540612  point: type=toggle comment=point[1]:0->1 hier=vibration_core
+1540610  point: type=toggle comment=point[1]:1->0 hier=vibration_core
+770306  point: type=toggle comment=point[2]:0->1 hier=vibration_core
+770304  point: type=toggle comment=point[2]:1->0 hier=vibration_core
+385154  point: type=toggle comment=point[3]:0->1 hier=vibration_core
+385152  point: type=toggle comment=point[3]:1->0 hier=vibration_core
+192576  point: type=toggle comment=point[4]:0->1 hier=vibration_core
+192574  point: type=toggle comment=point[4]:1->0 hier=vibration_core
+096288  point: type=toggle comment=point[5]:0->1 hier=vibration_core
+096286  point: type=toggle comment=point[5]:1->0 hier=vibration_core
+048144  point: type=toggle comment=point[6]:0->1 hier=vibration_core
+048142  point: type=toggle comment=point[6]:1->0 hier=vibration_core
+024072  point: type=toggle comment=point[7]:0->1 hier=vibration_core
+024070  point: type=toggle comment=point[7]:1->0 hier=vibration_core
+012036  point: type=toggle comment=point[8]:0->1 hier=vibration_core
+012034  point: type=toggle comment=point[8]:1->0 hier=vibration_core
+006018  point: type=toggle comment=point[9]:0->1 hier=vibration_core
+006016  point: type=toggle comment=point[9]:1->0 hier=vibration_core
 1223424     reg signed [15:0] mean, raw_q, sample_q;
+000024  point: type=toggle comment=mean[0]:0->1 hier=vibration_core
+000023  point: type=toggle comment=mean[0]:1->0 hier=vibration_core
+000001  point: type=toggle comment=mean[10]:0->1 hier=vibration_core
+000001  point: type=toggle comment=mean[10]:1->0 hier=vibration_core
+000007  point: type=toggle comment=mean[11]:0->1 hier=vibration_core
+000007  point: type=toggle comment=mean[11]:1->0 hier=vibration_core
+000007  point: type=toggle comment=mean[12]:0->1 hier=vibration_core
+000007  point: type=toggle comment=mean[12]:1->0 hier=vibration_core
+000007  point: type=toggle comment=mean[13]:0->1 hier=vibration_core
+000007  point: type=toggle comment=mean[13]:1->0 hier=vibration_core
+000007  point: type=toggle comment=mean[14]:0->1 hier=vibration_core
+000007  point: type=toggle comment=mean[14]:1->0 hier=vibration_core
+000007  point: type=toggle comment=mean[15]:0->1 hier=vibration_core
+000007  point: type=toggle comment=mean[15]:1->0 hier=vibration_core
+000029  point: type=toggle comment=mean[1]:0->1 hier=vibration_core
+000028  point: type=toggle comment=mean[1]:1->0 hier=vibration_core
+000018  point: type=toggle comment=mean[2]:0->1 hier=vibration_core
+000018  point: type=toggle comment=mean[2]:1->0 hier=vibration_core
+000016  point: type=toggle comment=mean[3]:0->1 hier=vibration_core
+000015  point: type=toggle comment=mean[3]:1->0 hier=vibration_core
+000019  point: type=toggle comment=mean[4]:0->1 hier=vibration_core
+000019  point: type=toggle comment=mean[4]:1->0 hier=vibration_core
+000016  point: type=toggle comment=mean[5]:0->1 hier=vibration_core
+000016  point: type=toggle comment=mean[5]:1->0 hier=vibration_core
+000006  point: type=toggle comment=mean[6]:0->1 hier=vibration_core
+000006  point: type=toggle comment=mean[6]:1->0 hier=vibration_core
+000016  point: type=toggle comment=mean[7]:0->1 hier=vibration_core
+000016  point: type=toggle comment=mean[7]:1->0 hier=vibration_core
+000016  point: type=toggle comment=mean[8]:0->1 hier=vibration_core
+000016  point: type=toggle comment=mean[8]:1->0 hier=vibration_core
+000001  point: type=toggle comment=mean[9]:0->1 hier=vibration_core
+000001  point: type=toggle comment=mean[9]:1->0 hier=vibration_core
+014668  point: type=toggle comment=raw_q[0]:0->1 hier=vibration_core
+014668  point: type=toggle comment=raw_q[0]:1->0 hier=vibration_core
+013966  point: type=toggle comment=raw_q[10]:0->1 hier=vibration_core
+013966  point: type=toggle comment=raw_q[10]:1->0 hier=vibration_core
+012153  point: type=toggle comment=raw_q[11]:0->1 hier=vibration_core
+012152  point: type=toggle comment=raw_q[11]:1->0 hier=vibration_core
+011962  point: type=toggle comment=raw_q[12]:0->1 hier=vibration_core
+011961  point: type=toggle comment=raw_q[12]:1->0 hier=vibration_core
+012537  point: type=toggle comment=raw_q[13]:0->1 hier=vibration_core
+012536  point: type=toggle comment=raw_q[13]:1->0 hier=vibration_core
+012562  point: type=toggle comment=raw_q[14]:0->1 hier=vibration_core
+012561  point: type=toggle comment=raw_q[14]:1->0 hier=vibration_core
+012421  point: type=toggle comment=raw_q[15]:0->1 hier=vibration_core
+012420  point: type=toggle comment=raw_q[15]:1->0 hier=vibration_core
+014237  point: type=toggle comment=raw_q[1]:0->1 hier=vibration_core
+014237  point: type=toggle comment=raw_q[1]:1->0 hier=vibration_core
+014112  point: type=toggle comment=raw_q[2]:0->1 hier=vibration_core
+014110  point: type=toggle comment=raw_q[2]:1->0 hier=vibration_core
+014259  point: type=toggle comment=raw_q[3]:0->1 hier=vibration_core
+014259  point: type=toggle comment=raw_q[3]:1->0 hier=vibration_core
+014148  point: type=toggle comment=raw_q[4]:0->1 hier=vibration_core
+014147  point: type=toggle comment=raw_q[4]:1->0 hier=vibration_core
+013893  point: type=toggle comment=raw_q[5]:0->1 hier=vibration_core
+013893  point: type=toggle comment=raw_q[5]:1->0 hier=vibration_core
+014375  point: type=toggle comment=raw_q[6]:0->1 hier=vibration_core
+014373  point: type=toggle comment=raw_q[6]:1->0 hier=vibration_core
+014338  point: type=toggle comment=raw_q[7]:0->1 hier=vibration_core
+014337  point: type=toggle comment=raw_q[7]:1->0 hier=vibration_core
+014723  point: type=toggle comment=raw_q[8]:0->1 hier=vibration_core
+014722  point: type=toggle comment=raw_q[8]:1->0 hier=vibration_core
+014064  point: type=toggle comment=raw_q[9]:0->1 hier=vibration_core
+014063  point: type=toggle comment=raw_q[9]:1->0 hier=vibration_core
+1197504  point: type=toggle comment=sample_q[0]:0->1 hier=vibration_core
+1197504  point: type=toggle comment=sample_q[0]:1->0 hier=vibration_core
+1068768  point: type=toggle comment=sample_q[10]:0->1 hier=vibration_core
+1068768  point: type=toggle comment=sample_q[10]:1->0 hier=vibration_core
+1070208  point: type=toggle comment=sample_q[11]:0->1 hier=vibration_core
+1070208  point: type=toggle comment=sample_q[11]:1->0 hier=vibration_core
+1070208  point: type=toggle comment=sample_q[12]:0->1 hier=vibration_core
+1070208  point: type=toggle comment=sample_q[12]:1->0 hier=vibration_core
+1070208  point: type=toggle comment=sample_q[13]:0->1 hier=vibration_core
+1070208  point: type=toggle comment=sample_q[13]:1->0 hier=vibration_core
+1070208  point: type=toggle comment=sample_q[14]:0->1 hier=vibration_core
+1070208  point: type=toggle comment=sample_q[14]:1->0 hier=vibration_core
+1070208  point: type=toggle comment=sample_q[15]:0->1 hier=vibration_core
+1070208  point: type=toggle comment=sample_q[15]:1->0 hier=vibration_core
+1190208  point: type=toggle comment=sample_q[1]:0->1 hier=vibration_core
+1190208  point: type=toggle comment=sample_q[1]:1->0 hier=vibration_core
+1170240  point: type=toggle comment=sample_q[2]:0->1 hier=vibration_core
+1170240  point: type=toggle comment=sample_q[2]:1->0 hier=vibration_core
+1216800  point: type=toggle comment=sample_q[3]:0->1 hier=vibration_core
+1216800  point: type=toggle comment=sample_q[3]:1->0 hier=vibration_core
+1223424  point: type=toggle comment=sample_q[4]:0->1 hier=vibration_core
+1223424  point: type=toggle comment=sample_q[4]:1->0 hier=vibration_core
+1182624  point: type=toggle comment=sample_q[5]:0->1 hier=vibration_core
+1182624  point: type=toggle comment=sample_q[5]:1->0 hier=vibration_core
+1185024  point: type=toggle comment=sample_q[6]:0->1 hier=vibration_core
+1185024  point: type=toggle comment=sample_q[6]:1->0 hier=vibration_core
+1166688  point: type=toggle comment=sample_q[7]:0->1 hier=vibration_core
+1166688  point: type=toggle comment=sample_q[7]:1->0 hier=vibration_core
+1167840  point: type=toggle comment=sample_q[8]:0->1 hier=vibration_core
+1167840  point: type=toggle comment=sample_q[8]:1->0 hier=vibration_core
+1072608  point: type=toggle comment=sample_q[9]:0->1 hier=vibration_core
+1072608  point: type=toggle comment=sample_q[9]:1->0 hier=vibration_core
~020196     wire signed [15:0] hann_q;
+015048  point: type=toggle comment=hann_q[0]:0->1 hier=vibration_core
+015048  point: type=toggle comment=hann_q[0]:1->0 hier=vibration_core
+001056  point: type=toggle comment=hann_q[10]:0->1 hier=vibration_core
+001056  point: type=toggle comment=hann_q[10]:1->0 hier=vibration_core
+000528  point: type=toggle comment=hann_q[11]:0->1 hier=vibration_core
+000528  point: type=toggle comment=hann_q[11]:1->0 hier=vibration_core
+000264  point: type=toggle comment=hann_q[12]:0->1 hier=vibration_core
+000264  point: type=toggle comment=hann_q[12]:1->0 hier=vibration_core
+000132  point: type=toggle comment=hann_q[13]:0->1 hier=vibration_core
+000132  point: type=toggle comment=hann_q[13]:1->0 hier=vibration_core
+000066  point: type=toggle comment=hann_q[14]:0->1 hier=vibration_core
+000066  point: type=toggle comment=hann_q[14]:1->0 hier=vibration_core
-000000  point: type=toggle comment=hann_q[15]:0->1 hier=vibration_core
-000000  point: type=toggle comment=hann_q[15]:1->0 hier=vibration_core
+018084  point: type=toggle comment=hann_q[1]:0->1 hier=vibration_core
+018084  point: type=toggle comment=hann_q[1]:1->0 hier=vibration_core
+016104  point: type=toggle comment=hann_q[2]:0->1 hier=vibration_core
+016104  point: type=toggle comment=hann_q[2]:1->0 hier=vibration_core
+014520  point: type=toggle comment=hann_q[3]:0->1 hier=vibration_core
+014520  point: type=toggle comment=hann_q[3]:1->0 hier=vibration_core
+020196  point: type=toggle comment=hann_q[4]:0->1 hier=vibration_core
+020196  point: type=toggle comment=hann_q[4]:1->0 hier=vibration_core
+019668  point: type=toggle comment=hann_q[5]:0->1 hier=vibration_core
+019668  point: type=toggle comment=hann_q[5]:1->0 hier=vibration_core
+016896  point: type=toggle comment=hann_q[6]:0->1 hier=vibration_core
+016896  point: type=toggle comment=hann_q[6]:1->0 hier=vibration_core
+008448  point: type=toggle comment=hann_q[7]:0->1 hier=vibration_core
+008448  point: type=toggle comment=hann_q[7]:1->0 hier=vibration_core
+004224  point: type=toggle comment=hann_q[8]:0->1 hier=vibration_core
+004224  point: type=toggle comment=hann_q[8]:1->0 hier=vibration_core
+002112  point: type=toggle comment=hann_q[9]:0->1 hier=vibration_core
+002112  point: type=toggle comment=hann_q[9]:1->0 hier=vibration_core
 002976     reg [CW-1:0] dft_group;
+002976  point: type=toggle comment=dft_group[0]:0->1 hier=vibration_core
+002974  point: type=toggle comment=dft_group[0]:1->0 hier=vibration_core
+001488  point: type=toggle comment=dft_group[1]:0->1 hier=vibration_core
+001486  point: type=toggle comment=dft_group[1]:1->0 hier=vibration_core
+000744  point: type=toggle comment=dft_group[2]:0->1 hier=vibration_core
+000742  point: type=toggle comment=dft_group[2]:1->0 hier=vibration_core
+000372  point: type=toggle comment=dft_group[3]:0->1 hier=vibration_core
+000370  point: type=toggle comment=dft_group[3]:1->0 hier=vibration_core
+000186  point: type=toggle comment=dft_group[4]:0->1 hier=vibration_core
+000184  point: type=toggle comment=dft_group[4]:1->0 hier=vibration_core
+000062  point: type=toggle comment=dft_group[5]:0->1 hier=vibration_core
+000062  point: type=toggle comment=dft_group[5]:1->0 hier=vibration_core
+000062  point: type=toggle comment=dft_group[6]:0->1 hier=vibration_core
+000060  point: type=toggle comment=dft_group[6]:1->0 hier=vibration_core
%000000     reg [LB-1:0] store_lane;
-000000  point: type=toggle comment=store_lane[0]:0->1 hier=vibration_core
-000000  point: type=toggle comment=store_lane[0]:1->0 hier=vibration_core
 2398664     reg [P-1:0] phase [0:LANES-1];
+1396746  point: type=toggle comment=phase[0][0]:0->1 hier=vibration_core
+1396746  point: type=toggle comment=phase[0][0]:1->0 hier=vibration_core
+1396742  point: type=toggle comment=phase[0][1]:0->1 hier=vibration_core
+1396742  point: type=toggle comment=phase[0][1]:1->0 hier=vibration_core
+1587204  point: type=toggle comment=phase[0][2]:0->1 hier=vibration_core
+1587204  point: type=toggle comment=phase[0][2]:1->0 hier=vibration_core
+1476098  point: type=toggle comment=phase[0][3]:0->1 hier=vibration_core
+1476098  point: type=toggle comment=phase[0][3]:1->0 hier=vibration_core
+1682440  point: type=toggle comment=phase[0][4]:0->1 hier=vibration_core
+1682440  point: type=toggle comment=phase[0][4]:1->0 hier=vibration_core
+1261828  point: type=toggle comment=phase[0][5]:0->1 hier=vibration_core
+1261828  point: type=toggle comment=phase[0][5]:1->0 hier=vibration_core
+2398664  point: type=toggle comment=phase[0][6]:0->1 hier=vibration_core
+2398664  point: type=toggle comment=phase[0][6]:1->0 hier=vibration_core
+1595142  point: type=toggle comment=phase[0][7]:0->1 hier=vibration_core
+1595142  point: type=toggle comment=phase[0][7]:1->0 hier=vibration_core
+1764770  point: type=toggle comment=phase[0][8]:0->1 hier=vibration_core
+1764768  point: type=toggle comment=phase[0][8]:1->0 hier=vibration_core
+1889762  point: type=toggle comment=phase[0][9]:0->1 hier=vibration_core
+1889762  point: type=toggle comment=phase[0][9]:1->0 hier=vibration_core
 1889762     wire signed [15:0] coefficient [0:LANES-1];
+1550006  point: type=toggle comment=coefficient[0][0]:0->1 hier=vibration_core
+1550006  point: type=toggle comment=coefficient[0][0]:1->0 hier=vibration_core
+1531156  point: type=toggle comment=coefficient[0][10]:0->1 hier=vibration_core
+1531156  point: type=toggle comment=coefficient[0][10]:1->0 hier=vibration_core
+1558438  point: type=toggle comment=coefficient[0][11]:0->1 hier=vibration_core
+1558438  point: type=toggle comment=coefficient[0][11]:1->0 hier=vibration_core
+1497676  point: type=toggle comment=coefficient[0][12]:0->1 hier=vibration_core
+1497674  point: type=toggle comment=coefficient[0][12]:1->0 hier=vibration_core
+1766510  point: type=toggle comment=coefficient[0][13]:0->1 hier=vibration_core
+1766510  point: type=toggle comment=coefficient[0][13]:1->0 hier=vibration_core
+1878602  point: type=toggle comment=coefficient[0][14]:0->1 hier=vibration_core
+1878602  point: type=toggle comment=coefficient[0][14]:1->0 hier=vibration_core
+1889762  point: type=toggle comment=coefficient[0][15]:0->1 hier=vibration_core
+1889762  point: type=toggle comment=coefficient[0][15]:1->0 hier=vibration_core
+1553974  point: type=toggle comment=coefficient[0][1]:0->1 hier=vibration_core
+1553974  point: type=toggle comment=coefficient[0][1]:1->0 hier=vibration_core
+1552486  point: type=toggle comment=coefficient[0][2]:0->1 hier=vibration_core
+1552486  point: type=toggle comment=coefficient[0][2]:1->0 hier=vibration_core
+1533386  point: type=toggle comment=coefficient[0][3]:0->1 hier=vibration_core
+1533386  point: type=toggle comment=coefficient[0][3]:1->0 hier=vibration_core
+1572326  point: type=toggle comment=coefficient[0][4]:0->1 hier=vibration_core
+1572324  point: type=toggle comment=coefficient[0][4]:1->0 hier=vibration_core
+1541076  point: type=toggle comment=coefficient[0][5]:0->1 hier=vibration_core
+1541076  point: type=toggle comment=coefficient[0][5]:1->0 hier=vibration_core
+1512306  point: type=toggle comment=coefficient[0][6]:0->1 hier=vibration_core
+1512304  point: type=toggle comment=coefficient[0][6]:1->0 hier=vibration_core
+1567862  point: type=toggle comment=coefficient[0][7]:0->1 hier=vibration_core
+1567862  point: type=toggle comment=coefficient[0][7]:1->0 hier=vibration_core
+1525204  point: type=toggle comment=coefficient[0][8]:0->1 hier=vibration_core
+1525204  point: type=toggle comment=coefficient[0][8]:1->0 hier=vibration_core
+1539592  point: type=toggle comment=coefficient[0][9]:0->1 hier=vibration_core
+1539592  point: type=toggle comment=coefficient[0][9]:1->0 hier=vibration_core
 1162839     reg signed [39:0] accumulator [0:LANES-1];
+618987  point: type=toggle comment=accumulator[0][0]:0->1 hier=vibration_core
+618985  point: type=toggle comment=accumulator[0][0]:1->0 hier=vibration_core
+1132389  point: type=toggle comment=accumulator[0][10]:0->1 hier=vibration_core
+1132387  point: type=toggle comment=accumulator[0][10]:1->0 hier=vibration_core
+1128777  point: type=toggle comment=accumulator[0][11]:0->1 hier=vibration_core
+1128775  point: type=toggle comment=accumulator[0][11]:1->0 hier=vibration_core
+1119748  point: type=toggle comment=accumulator[0][12]:0->1 hier=vibration_core
+1119746  point: type=toggle comment=accumulator[0][12]:1->0 hier=vibration_core
+1103623  point: type=toggle comment=accumulator[0][13]:0->1 hier=vibration_core
+1103621  point: type=toggle comment=accumulator[0][13]:1->0 hier=vibration_core
+1162839  point: type=toggle comment=accumulator[0][14]:0->1 hier=vibration_core
+1162837  point: type=toggle comment=accumulator[0][14]:1->0 hier=vibration_core
+1149340  point: type=toggle comment=accumulator[0][15]:0->1 hier=vibration_core
+1149338  point: type=toggle comment=accumulator[0][15]:1->0 hier=vibration_core
+1125305  point: type=toggle comment=accumulator[0][16]:0->1 hier=vibration_core
+1125303  point: type=toggle comment=accumulator[0][16]:1->0 hier=vibration_core
+1087979  point: type=toggle comment=accumulator[0][17]:0->1 hier=vibration_core
+1087977  point: type=toggle comment=accumulator[0][17]:1->0 hier=vibration_core
+1039420  point: type=toggle comment=accumulator[0][18]:0->1 hier=vibration_core
+1039418  point: type=toggle comment=accumulator[0][18]:1->0 hier=vibration_core
+971329  point: type=toggle comment=accumulator[0][19]:0->1 hier=vibration_core
+971327  point: type=toggle comment=accumulator[0][19]:1->0 hier=vibration_core
+891348  point: type=toggle comment=accumulator[0][1]:0->1 hier=vibration_core
+891346  point: type=toggle comment=accumulator[0][1]:1->0 hier=vibration_core
+898629  point: type=toggle comment=accumulator[0][20]:0->1 hier=vibration_core
+898627  point: type=toggle comment=accumulator[0][20]:1->0 hier=vibration_core
+826832  point: type=toggle comment=accumulator[0][21]:0->1 hier=vibration_core
+826830  point: type=toggle comment=accumulator[0][21]:1->0 hier=vibration_core
+759886  point: type=toggle comment=accumulator[0][22]:0->1 hier=vibration_core
+759884  point: type=toggle comment=accumulator[0][22]:1->0 hier=vibration_core
+604140  point: type=toggle comment=accumulator[0][23]:0->1 hier=vibration_core
+604138  point: type=toggle comment=accumulator[0][23]:1->0 hier=vibration_core
+533712  point: type=toggle comment=accumulator[0][24]:0->1 hier=vibration_core
+533710  point: type=toggle comment=accumulator[0][24]:1->0 hier=vibration_core
+489278  point: type=toggle comment=accumulator[0][25]:0->1 hier=vibration_core
+489276  point: type=toggle comment=accumulator[0][25]:1->0 hier=vibration_core
+473671  point: type=toggle comment=accumulator[0][26]:0->1 hier=vibration_core
+473669  point: type=toggle comment=accumulator[0][26]:1->0 hier=vibration_core
+467580  point: type=toggle comment=accumulator[0][27]:0->1 hier=vibration_core
+467578  point: type=toggle comment=accumulator[0][27]:1->0 hier=vibration_core
+465417  point: type=toggle comment=accumulator[0][28]:0->1 hier=vibration_core
+465415  point: type=toggle comment=accumulator[0][28]:1->0 hier=vibration_core
+464906  point: type=toggle comment=accumulator[0][29]:0->1 hier=vibration_core
+464904  point: type=toggle comment=accumulator[0][29]:1->0 hier=vibration_core
+1044498  point: type=toggle comment=accumulator[0][2]:0->1 hier=vibration_core
+1044498  point: type=toggle comment=accumulator[0][2]:1->0 hier=vibration_core
+464748  point: type=toggle comment=accumulator[0][30]:0->1 hier=vibration_core
+464746  point: type=toggle comment=accumulator[0][30]:1->0 hier=vibration_core
+464725  point: type=toggle comment=accumulator[0][31]:0->1 hier=vibration_core
+464723  point: type=toggle comment=accumulator[0][31]:1->0 hier=vibration_core
+464723  point: type=toggle comment=accumulator[0][32]:0->1 hier=vibration_core
+464721  point: type=toggle comment=accumulator[0][32]:1->0 hier=vibration_core
+464721  point: type=toggle comment=accumulator[0][33]:0->1 hier=vibration_core
+464719  point: type=toggle comment=accumulator[0][33]:1->0 hier=vibration_core
+464721  point: type=toggle comment=accumulator[0][34]:0->1 hier=vibration_core
+464719  point: type=toggle comment=accumulator[0][34]:1->0 hier=vibration_core
+464721  point: type=toggle comment=accumulator[0][35]:0->1 hier=vibration_core
+464719  point: type=toggle comment=accumulator[0][35]:1->0 hier=vibration_core
+464721  point: type=toggle comment=accumulator[0][36]:0->1 hier=vibration_core
+464719  point: type=toggle comment=accumulator[0][36]:1->0 hier=vibration_core
+464721  point: type=toggle comment=accumulator[0][37]:0->1 hier=vibration_core
+464719  point: type=toggle comment=accumulator[0][37]:1->0 hier=vibration_core
+464721  point: type=toggle comment=accumulator[0][38]:0->1 hier=vibration_core
+464719  point: type=toggle comment=accumulator[0][38]:1->0 hier=vibration_core
+464721  point: type=toggle comment=accumulator[0][39]:0->1 hier=vibration_core
+464719  point: type=toggle comment=accumulator[0][39]:1->0 hier=vibration_core
+1089150  point: type=toggle comment=accumulator[0][3]:0->1 hier=vibration_core
+1089148  point: type=toggle comment=accumulator[0][3]:1->0 hier=vibration_core
+1122001  point: type=toggle comment=accumulator[0][4]:0->1 hier=vibration_core
+1121999  point: type=toggle comment=accumulator[0][4]:1->0 hier=vibration_core
+1136886  point: type=toggle comment=accumulator[0][5]:0->1 hier=vibration_core
+1136886  point: type=toggle comment=accumulator[0][5]:1->0 hier=vibration_core
+1139993  point: type=toggle comment=accumulator[0][6]:0->1 hier=vibration_core
+1139991  point: type=toggle comment=accumulator[0][6]:1->0 hier=vibration_core
+1144198  point: type=toggle comment=accumulator[0][7]:0->1 hier=vibration_core
+1144196  point: type=toggle comment=accumulator[0][7]:1->0 hier=vibration_core
+1141485  point: type=toggle comment=accumulator[0][8]:0->1 hier=vibration_core
+1141483  point: type=toggle comment=accumulator[0][8]:1->0 hier=vibration_core
+1135820  point: type=toggle comment=accumulator[0][9]:0->1 hier=vibration_core
+1135820  point: type=toggle comment=accumulator[0][9]:1->0 hier=vibration_core
            reg signed [15:0] real_part [0:TOTAL_BINS-1], imag_part [0:TOTAL_BINS-1];
~000013     reg [7:0] features [0:15], hidden [0:15];
+000008  point: type=toggle comment=features[0][0]:0->1 hier=vibration_core
+000008  point: type=toggle comment=features[0][0]:1->0 hier=vibration_core
+000007  point: type=toggle comment=features[0][1]:0->1 hier=vibration_core
+000007  point: type=toggle comment=features[0][1]:1->0 hier=vibration_core
+000007  point: type=toggle comment=features[0][2]:0->1 hier=vibration_core
+000007  point: type=toggle comment=features[0][2]:1->0 hier=vibration_core
+000007  point: type=toggle comment=features[0][3]:0->1 hier=vibration_core
+000007  point: type=toggle comment=features[0][3]:1->0 hier=vibration_core
+000007  point: type=toggle comment=features[0][4]:0->1 hier=vibration_core
+000007  point: type=toggle comment=features[0][4]:1->0 hier=vibration_core
+000008  point: type=toggle comment=features[0][5]:0->1 hier=vibration_core
+000008  point: type=toggle comment=features[0][5]:1->0 hier=vibration_core
+000006  point: type=toggle comment=features[0][6]:0->1 hier=vibration_core
+000006  point: type=toggle comment=features[0][6]:1->0 hier=vibration_core
-000000  point: type=toggle comment=features[0][7]:0->1 hier=vibration_core
-000000  point: type=toggle comment=features[0][7]:1->0 hier=vibration_core
+000007  point: type=toggle comment=features[10][0]:0->1 hier=vibration_core
+000007  point: type=toggle comment=features[10][0]:1->0 hier=vibration_core
+000007  point: type=toggle comment=features[10][1]:0->1 hier=vibration_core
+000007  point: type=toggle comment=features[10][1]:1->0 hier=vibration_core
+000007  point: type=toggle comment=features[10][2]:0->1 hier=vibration_core
+000007  point: type=toggle comment=features[10][2]:1->0 hier=vibration_core
+000005  point: type=toggle comment=features[10][3]:0->1 hier=vibration_core
+000005  point: type=toggle comment=features[10][3]:1->0 hier=vibration_core
+000007  point: type=toggle comment=features[10][4]:0->1 hier=vibration_core
+000007  point: type=toggle comment=features[10][4]:1->0 hier=vibration_core
+000005  point: type=toggle comment=features[10][5]:0->1 hier=vibration_core
+000005  point: type=toggle comment=features[10][5]:1->0 hier=vibration_core
+000005  point: type=toggle comment=features[10][6]:0->1 hier=vibration_core
+000005  point: type=toggle comment=features[10][6]:1->0 hier=vibration_core
-000000  point: type=toggle comment=features[10][7]:0->1 hier=vibration_core
-000000  point: type=toggle comment=features[10][7]:1->0 hier=vibration_core
+000006  point: type=toggle comment=features[11][0]:0->1 hier=vibration_core
+000006  point: type=toggle comment=features[11][0]:1->0 hier=vibration_core
+000006  point: type=toggle comment=features[11][1]:0->1 hier=vibration_core
+000006  point: type=toggle comment=features[11][1]:1->0 hier=vibration_core
+000007  point: type=toggle comment=features[11][2]:0->1 hier=vibration_core
+000007  point: type=toggle comment=features[11][2]:1->0 hier=vibration_core
+000007  point: type=toggle comment=features[11][3]:0->1 hier=vibration_core
+000007  point: type=toggle comment=features[11][3]:1->0 hier=vibration_core
+000005  point: type=toggle comment=features[11][4]:0->1 hier=vibration_core
+000005  point: type=toggle comment=features[11][4]:1->0 hier=vibration_core
+000005  point: type=toggle comment=features[11][5]:0->1 hier=vibration_core
+000005  point: type=toggle comment=features[11][5]:1->0 hier=vibration_core
+000005  point: type=toggle comment=features[11][6]:0->1 hier=vibration_core
+000005  point: type=toggle comment=features[11][6]:1->0 hier=vibration_core
-000000  point: type=toggle comment=features[11][7]:0->1 hier=vibration_core
-000000  point: type=toggle comment=features[11][7]:1->0 hier=vibration_core
+000007  point: type=toggle comment=features[12][0]:0->1 hier=vibration_core
+000007  point: type=toggle comment=features[12][0]:1->0 hier=vibration_core
+000007  point: type=toggle comment=features[12][1]:0->1 hier=vibration_core
+000007  point: type=toggle comment=features[12][1]:1->0 hier=vibration_core
+000005  point: type=toggle comment=features[12][2]:0->1 hier=vibration_core
+000005  point: type=toggle comment=features[12][2]:1->0 hier=vibration_core
+000005  point: type=toggle comment=features[12][3]:0->1 hier=vibration_core
+000005  point: type=toggle comment=features[12][3]:1->0 hier=vibration_core
+000008  point: type=toggle comment=features[12][4]:0->1 hier=vibration_core
+000008  point: type=toggle comment=features[12][4]:1->0 hier=vibration_core
+000005  point: type=toggle comment=features[12][5]:0->1 hier=vibration_core
+000005  point: type=toggle comment=features[12][5]:1->0 hier=vibration_core
+000006  point: type=toggle comment=features[12][6]:0->1 hier=vibration_core
+000006  point: type=toggle comment=features[12][6]:1->0 hier=vibration_core
-000000  point: type=toggle comment=features[12][7]:0->1 hier=vibration_core
-000000  point: type=toggle comment=features[12][7]:1->0 hier=vibration_core
+000008  point: type=toggle comment=features[13][0]:0->1 hier=vibration_core
+000008  point: type=toggle comment=features[13][0]:1->0 hier=vibration_core
+000006  point: type=toggle comment=features[13][1]:0->1 hier=vibration_core
+000006  point: type=toggle comment=features[13][1]:1->0 hier=vibration_core
+000007  point: type=toggle comment=features[13][2]:0->1 hier=vibration_core
+000007  point: type=toggle comment=features[13][2]:1->0 hier=vibration_core
+000006  point: type=toggle comment=features[13][3]:0->1 hier=vibration_core
+000006  point: type=toggle comment=features[13][3]:1->0 hier=vibration_core
+000005  point: type=toggle comment=features[13][4]:0->1 hier=vibration_core
+000005  point: type=toggle comment=features[13][4]:1->0 hier=vibration_core
+000005  point: type=toggle comment=features[13][5]:0->1 hier=vibration_core
+000005  point: type=toggle comment=features[13][5]:1->0 hier=vibration_core
+000005  point: type=toggle comment=features[13][6]:0->1 hier=vibration_core
+000005  point: type=toggle comment=features[13][6]:1->0 hier=vibration_core
-000000  point: type=toggle comment=features[13][7]:0->1 hier=vibration_core
-000000  point: type=toggle comment=features[13][7]:1->0 hier=vibration_core
+000008  point: type=toggle comment=features[14][0]:0->1 hier=vibration_core
+000008  point: type=toggle comment=features[14][0]:1->0 hier=vibration_core
+000007  point: type=toggle comment=features[14][1]:0->1 hier=vibration_core
+000007  point: type=toggle comment=features[14][1]:1->0 hier=vibration_core
+000005  point: type=toggle comment=features[14][2]:0->1 hier=vibration_core
+000005  point: type=toggle comment=features[14][2]:1->0 hier=vibration_core
+000007  point: type=toggle comment=features[14][3]:0->1 hier=vibration_core
+000007  point: type=toggle comment=features[14][3]:1->0 hier=vibration_core
+000005  point: type=toggle comment=features[14][4]:0->1 hier=vibration_core
+000005  point: type=toggle comment=features[14][4]:1->0 hier=vibration_core
+000006  point: type=toggle comment=features[14][5]:0->1 hier=vibration_core
+000006  point: type=toggle comment=features[14][5]:1->0 hier=vibration_core
+000005  point: type=toggle comment=features[14][6]:0->1 hier=vibration_core
+000005  point: type=toggle comment=features[14][6]:1->0 hier=vibration_core
-000000  point: type=toggle comment=features[14][7]:0->1 hier=vibration_core
-000000  point: type=toggle comment=features[14][7]:1->0 hier=vibration_core
+000008  point: type=toggle comment=features[15][0]:0->1 hier=vibration_core
+000008  point: type=toggle comment=features[15][0]:1->0 hier=vibration_core
+000006  point: type=toggle comment=features[15][1]:0->1 hier=vibration_core
+000006  point: type=toggle comment=features[15][1]:1->0 hier=vibration_core
+000008  point: type=toggle comment=features[15][2]:0->1 hier=vibration_core
+000008  point: type=toggle comment=features[15][2]:1->0 hier=vibration_core
+000006  point: type=toggle comment=features[15][3]:0->1 hier=vibration_core
+000006  point: type=toggle comment=features[15][3]:1->0 hier=vibration_core
+000007  point: type=toggle comment=features[15][4]:0->1 hier=vibration_core
+000007  point: type=toggle comment=features[15][4]:1->0 hier=vibration_core
+000005  point: type=toggle comment=features[15][5]:0->1 hier=vibration_core
+000005  point: type=toggle comment=features[15][5]:1->0 hier=vibration_core
+000005  point: type=toggle comment=features[15][6]:0->1 hier=vibration_core
+000005  point: type=toggle comment=features[15][6]:1->0 hier=vibration_core
-000000  point: type=toggle comment=features[15][7]:0->1 hier=vibration_core
-000000  point: type=toggle comment=features[15][7]:1->0 hier=vibration_core
+000007  point: type=toggle comment=features[1][0]:0->1 hier=vibration_core
+000007  point: type=toggle comment=features[1][0]:1->0 hier=vibration_core
+000007  point: type=toggle comment=features[1][1]:0->1 hier=vibration_core
+000007  point: type=toggle comment=features[1][1]:1->0 hier=vibration_core
+000008  point: type=toggle comment=features[1][2]:0->1 hier=vibration_core
+000008  point: type=toggle comment=features[1][2]:1->0 hier=vibration_core
+000007  point: type=toggle comment=features[1][3]:0->1 hier=vibration_core
+000007  point: type=toggle comment=features[1][3]:1->0 hier=vibration_core
+000005  point: type=toggle comment=features[1][4]:0->1 hier=vibration_core
+000005  point: type=toggle comment=features[1][4]:1->0 hier=vibration_core
+000005  point: type=toggle comment=features[1][5]:0->1 hier=vibration_core
+000005  point: type=toggle comment=features[1][5]:1->0 hier=vibration_core
+000005  point: type=toggle comment=features[1][6]:0->1 hier=vibration_core
+000005  point: type=toggle comment=features[1][6]:1->0 hier=vibration_core
-000000  point: type=toggle comment=features[1][7]:0->1 hier=vibration_core
-000000  point: type=toggle comment=features[1][7]:1->0 hier=vibration_core
+000007  point: type=toggle comment=features[2][0]:0->1 hier=vibration_core
+000007  point: type=toggle comment=features[2][0]:1->0 hier=vibration_core
+000006  point: type=toggle comment=features[2][1]:0->1 hier=vibration_core
+000006  point: type=toggle comment=features[2][1]:1->0 hier=vibration_core
+000005  point: type=toggle comment=features[2][2]:0->1 hier=vibration_core
+000005  point: type=toggle comment=features[2][2]:1->0 hier=vibration_core
+000006  point: type=toggle comment=features[2][3]:0->1 hier=vibration_core
+000006  point: type=toggle comment=features[2][3]:1->0 hier=vibration_core
+000006  point: type=toggle comment=features[2][4]:0->1 hier=vibration_core
+000006  point: type=toggle comment=features[2][4]:1->0 hier=vibration_core
+000005  point: type=toggle comment=features[2][5]:0->1 hier=vibration_core
+000005  point: type=toggle comment=features[2][5]:1->0 hier=vibration_core
+000005  point: type=toggle comment=features[2][6]:0->1 hier=vibration_core
+000005  point: type=toggle comment=features[2][6]:1->0 hier=vibration_core
-000000  point: type=toggle comment=features[2][7]:0->1 hier=vibration_core
-000000  point: type=toggle comment=features[2][7]:1->0 hier=vibration_core
+000010  point: type=toggle comment=features[3][0]:0->1 hier=vibration_core
+000008  point: type=toggle comment=features[3][0]:1->0 hier=vibration_core
+000011  point: type=toggle comment=features[3][1]:0->1 hier=vibration_core
+000009  point: type=toggle comment=features[3][1]:1->0 hier=vibration_core
+000010  point: type=toggle comment=features[3][2]:0->1 hier=vibration_core
+000008  point: type=toggle comment=features[3][2]:1->0 hier=vibration_core
+000009  point: type=toggle comment=features[3][3]:0->1 hier=vibration_core
+000007  point: type=toggle comment=features[3][3]:1->0 hier=vibration_core
+000010  point: type=toggle comment=features[3][4]:0->1 hier=vibration_core
+000008  point: type=toggle comment=features[3][4]:1->0 hier=vibration_core
+000009  point: type=toggle comment=features[3][5]:0->1 hier=vibration_core
+000007  point: type=toggle comment=features[3][5]:1->0 hier=vibration_core
+000009  point: type=toggle comment=features[3][6]:0->1 hier=vibration_core
+000007  point: type=toggle comment=features[3][6]:1->0 hier=vibration_core
-000000  point: type=toggle comment=features[3][7]:0->1 hier=vibration_core
-000000  point: type=toggle comment=features[3][7]:1->0 hier=vibration_core
+000007  point: type=toggle comment=features[4][0]:0->1 hier=vibration_core
+000007  point: type=toggle comment=features[4][0]:1->0 hier=vibration_core
+000007  point: type=toggle comment=features[4][1]:0->1 hier=vibration_core
+000007  point: type=toggle comment=features[4][1]:1->0 hier=vibration_core
+000005  point: type=toggle comment=features[4][2]:0->1 hier=vibration_core
+000005  point: type=toggle comment=features[4][2]:1->0 hier=vibration_core
+000006  point: type=toggle comment=features[4][3]:0->1 hier=vibration_core
+000006  point: type=toggle comment=features[4][3]:1->0 hier=vibration_core
+000006  point: type=toggle comment=features[4][4]:0->1 hier=vibration_core
+000006  point: type=toggle comment=features[4][4]:1->0 hier=vibration_core
+000006  point: type=toggle comment=features[4][5]:0->1 hier=vibration_core
+000006  point: type=toggle comment=features[4][5]:1->0 hier=vibration_core
+000005  point: type=toggle comment=features[4][6]:0->1 hier=vibration_core
+000005  point: type=toggle comment=features[4][6]:1->0 hier=vibration_core
-000000  point: type=toggle comment=features[4][7]:0->1 hier=vibration_core
-000000  point: type=toggle comment=features[4][7]:1->0 hier=vibration_core
+000007  point: type=toggle comment=features[5][0]:0->1 hier=vibration_core
+000007  point: type=toggle comment=features[5][0]:1->0 hier=vibration_core
+000005  point: type=toggle comment=features[5][1]:0->1 hier=vibration_core
+000005  point: type=toggle comment=features[5][1]:1->0 hier=vibration_core
+000005  point: type=toggle comment=features[5][2]:0->1 hier=vibration_core
+000005  point: type=toggle comment=features[5][2]:1->0 hier=vibration_core
+000007  point: type=toggle comment=features[5][3]:0->1 hier=vibration_core
+000007  point: type=toggle comment=features[5][3]:1->0 hier=vibration_core
+000006  point: type=toggle comment=features[5][4]:0->1 hier=vibration_core
+000006  point: type=toggle comment=features[5][4]:1->0 hier=vibration_core
+000006  point: type=toggle comment=features[5][5]:0->1 hier=vibration_core
+000006  point: type=toggle comment=features[5][5]:1->0 hier=vibration_core
+000005  point: type=toggle comment=features[5][6]:0->1 hier=vibration_core
+000005  point: type=toggle comment=features[5][6]:1->0 hier=vibration_core
-000000  point: type=toggle comment=features[5][7]:0->1 hier=vibration_core
-000000  point: type=toggle comment=features[5][7]:1->0 hier=vibration_core
+000007  point: type=toggle comment=features[6][0]:0->1 hier=vibration_core
+000007  point: type=toggle comment=features[6][0]:1->0 hier=vibration_core
+000006  point: type=toggle comment=features[6][1]:0->1 hier=vibration_core
+000006  point: type=toggle comment=features[6][1]:1->0 hier=vibration_core
+000006  point: type=toggle comment=features[6][2]:0->1 hier=vibration_core
+000006  point: type=toggle comment=features[6][2]:1->0 hier=vibration_core
+000006  point: type=toggle comment=features[6][3]:0->1 hier=vibration_core
+000006  point: type=toggle comment=features[6][3]:1->0 hier=vibration_core
+000006  point: type=toggle comment=features[6][4]:0->1 hier=vibration_core
+000006  point: type=toggle comment=features[6][4]:1->0 hier=vibration_core
+000005  point: type=toggle comment=features[6][5]:0->1 hier=vibration_core
+000005  point: type=toggle comment=features[6][5]:1->0 hier=vibration_core
+000007  point: type=toggle comment=features[6][6]:0->1 hier=vibration_core
+000007  point: type=toggle comment=features[6][6]:1->0 hier=vibration_core
-000000  point: type=toggle comment=features[6][7]:0->1 hier=vibration_core
-000000  point: type=toggle comment=features[6][7]:1->0 hier=vibration_core
+000008  point: type=toggle comment=features[7][0]:0->1 hier=vibration_core
+000008  point: type=toggle comment=features[7][0]:1->0 hier=vibration_core
+000005  point: type=toggle comment=features[7][1]:0->1 hier=vibration_core
+000005  point: type=toggle comment=features[7][1]:1->0 hier=vibration_core
+000007  point: type=toggle comment=features[7][2]:0->1 hier=vibration_core
+000007  point: type=toggle comment=features[7][2]:1->0 hier=vibration_core
+000005  point: type=toggle comment=features[7][3]:0->1 hier=vibration_core
+000005  point: type=toggle comment=features[7][3]:1->0 hier=vibration_core
+000007  point: type=toggle comment=features[7][4]:0->1 hier=vibration_core
+000007  point: type=toggle comment=features[7][4]:1->0 hier=vibration_core
+000006  point: type=toggle comment=features[7][5]:0->1 hier=vibration_core
+000006  point: type=toggle comment=features[7][5]:1->0 hier=vibration_core
+000006  point: type=toggle comment=features[7][6]:0->1 hier=vibration_core
+000006  point: type=toggle comment=features[7][6]:1->0 hier=vibration_core
-000000  point: type=toggle comment=features[7][7]:0->1 hier=vibration_core
-000000  point: type=toggle comment=features[7][7]:1->0 hier=vibration_core
+000008  point: type=toggle comment=features[8][0]:0->1 hier=vibration_core
+000008  point: type=toggle comment=features[8][0]:1->0 hier=vibration_core
+000007  point: type=toggle comment=features[8][1]:0->1 hier=vibration_core
+000007  point: type=toggle comment=features[8][1]:1->0 hier=vibration_core
+000008  point: type=toggle comment=features[8][2]:0->1 hier=vibration_core
+000008  point: type=toggle comment=features[8][2]:1->0 hier=vibration_core
+000006  point: type=toggle comment=features[8][3]:0->1 hier=vibration_core
+000006  point: type=toggle comment=features[8][3]:1->0 hier=vibration_core
+000007  point: type=toggle comment=features[8][4]:0->1 hier=vibration_core
+000007  point: type=toggle comment=features[8][4]:1->0 hier=vibration_core
+000006  point: type=toggle comment=features[8][5]:0->1 hier=vibration_core
+000006  point: type=toggle comment=features[8][5]:1->0 hier=vibration_core
+000006  point: type=toggle comment=features[8][6]:0->1 hier=vibration_core
+000006  point: type=toggle comment=features[8][6]:1->0 hier=vibration_core
-000000  point: type=toggle comment=features[8][7]:0->1 hier=vibration_core
-000000  point: type=toggle comment=features[8][7]:1->0 hier=vibration_core
+000007  point: type=toggle comment=features[9][0]:0->1 hier=vibration_core
+000007  point: type=toggle comment=features[9][0]:1->0 hier=vibration_core
+000007  point: type=toggle comment=features[9][1]:0->1 hier=vibration_core
+000007  point: type=toggle comment=features[9][1]:1->0 hier=vibration_core
+000008  point: type=toggle comment=features[9][2]:0->1 hier=vibration_core
+000008  point: type=toggle comment=features[9][2]:1->0 hier=vibration_core
+000007  point: type=toggle comment=features[9][3]:0->1 hier=vibration_core
+000007  point: type=toggle comment=features[9][3]:1->0 hier=vibration_core
+000006  point: type=toggle comment=features[9][4]:0->1 hier=vibration_core
+000006  point: type=toggle comment=features[9][4]:1->0 hier=vibration_core
+000006  point: type=toggle comment=features[9][5]:0->1 hier=vibration_core
+000006  point: type=toggle comment=features[9][5]:1->0 hier=vibration_core
+000005  point: type=toggle comment=features[9][6]:0->1 hier=vibration_core
+000005  point: type=toggle comment=features[9][6]:1->0 hier=vibration_core
-000000  point: type=toggle comment=features[9][7]:0->1 hier=vibration_core
-000000  point: type=toggle comment=features[9][7]:1->0 hier=vibration_core
+000007  point: type=toggle comment=hidden[0][0]:0->1 hier=vibration_core
+000007  point: type=toggle comment=hidden[0][0]:1->0 hier=vibration_core
+000010  point: type=toggle comment=hidden[0][1]:0->1 hier=vibration_core
+000008  point: type=toggle comment=hidden[0][1]:1->0 hier=vibration_core
+000006  point: type=toggle comment=hidden[0][2]:0->1 hier=vibration_core
+000006  point: type=toggle comment=hidden[0][2]:1->0 hier=vibration_core
+000005  point: type=toggle comment=hidden[0][3]:0->1 hier=vibration_core
+000005  point: type=toggle comment=hidden[0][3]:1->0 hier=vibration_core
+000006  point: type=toggle comment=hidden[0][4]:0->1 hier=vibration_core
+000006  point: type=toggle comment=hidden[0][4]:1->0 hier=vibration_core
-000000  point: type=toggle comment=hidden[0][5]:0->1 hier=vibration_core
-000000  point: type=toggle comment=hidden[0][5]:1->0 hier=vibration_core
+000004  point: type=toggle comment=hidden[0][6]:0->1 hier=vibration_core
+000004  point: type=toggle comment=hidden[0][6]:1->0 hier=vibration_core
-000000  point: type=toggle comment=hidden[0][7]:0->1 hier=vibration_core
-000000  point: type=toggle comment=hidden[0][7]:1->0 hier=vibration_core
+000010  point: type=toggle comment=hidden[10][0]:0->1 hier=vibration_core
+000010  point: type=toggle comment=hidden[10][0]:1->0 hier=vibration_core
+000009  point: type=toggle comment=hidden[10][1]:0->1 hier=vibration_core
+000007  point: type=toggle comment=hidden[10][1]:1->0 hier=vibration_core
+000011  point: type=toggle comment=hidden[10][2]:0->1 hier=vibration_core
+000009  point: type=toggle comment=hidden[10][2]:1->0 hier=vibration_core
+000011  point: type=toggle comment=hidden[10][3]:0->1 hier=vibration_core
+000011  point: type=toggle comment=hidden[10][3]:1->0 hier=vibration_core
-000000  point: type=toggle comment=hidden[10][4]:0->1 hier=vibration_core
-000000  point: type=toggle comment=hidden[10][4]:1->0 hier=vibration_core
-000000  point: type=toggle comment=hidden[10][5]:0->1 hier=vibration_core
-000000  point: type=toggle comment=hidden[10][5]:1->0 hier=vibration_core
-000000  point: type=toggle comment=hidden[10][6]:0->1 hier=vibration_core
-000000  point: type=toggle comment=hidden[10][6]:1->0 hier=vibration_core
-000000  point: type=toggle comment=hidden[10][7]:0->1 hier=vibration_core
-000000  point: type=toggle comment=hidden[10][7]:1->0 hier=vibration_core
+000001  point: type=toggle comment=hidden[11][0]:0->1 hier=vibration_core
+000001  point: type=toggle comment=hidden[11][0]:1->0 hier=vibration_core
+000009  point: type=toggle comment=hidden[11][1]:0->1 hier=vibration_core
+000007  point: type=toggle comment=hidden[11][1]:1->0 hier=vibration_core
+000002  point: type=toggle comment=hidden[11][2]:0->1 hier=vibration_core
+000002  point: type=toggle comment=hidden[11][2]:1->0 hier=vibration_core
+000001  point: type=toggle comment=hidden[11][3]:0->1 hier=vibration_core
+000001  point: type=toggle comment=hidden[11][3]:1->0 hier=vibration_core
+000001  point: type=toggle comment=hidden[11][4]:0->1 hier=vibration_core
+000001  point: type=toggle comment=hidden[11][4]:1->0 hier=vibration_core
-000000  point: type=toggle comment=hidden[11][5]:0->1 hier=vibration_core
-000000  point: type=toggle comment=hidden[11][5]:1->0 hier=vibration_core
+000004  point: type=toggle comment=hidden[11][6]:0->1 hier=vibration_core
+000004  point: type=toggle comment=hidden[11][6]:1->0 hier=vibration_core
-000000  point: type=toggle comment=hidden[11][7]:0->1 hier=vibration_core
-000000  point: type=toggle comment=hidden[11][7]:1->0 hier=vibration_core
-000000  point: type=toggle comment=hidden[12][0]:0->1 hier=vibration_core
-000000  point: type=toggle comment=hidden[12][0]:1->0 hier=vibration_core
-000000  point: type=toggle comment=hidden[12][1]:0->1 hier=vibration_core
-000000  point: type=toggle comment=hidden[12][1]:1->0 hier=vibration_core
-000000  point: type=toggle comment=hidden[12][2]:0->1 hier=vibration_core
-000000  point: type=toggle comment=hidden[12][2]:1->0 hier=vibration_core
-000000  point: type=toggle comment=hidden[12][3]:0->1 hier=vibration_core
-000000  point: type=toggle comment=hidden[12][3]:1->0 hier=vibration_core
-000000  point: type=toggle comment=hidden[12][4]:0->1 hier=vibration_core
-000000  point: type=toggle comment=hidden[12][4]:1->0 hier=vibration_core
-000000  point: type=toggle comment=hidden[12][5]:0->1 hier=vibration_core
-000000  point: type=toggle comment=hidden[12][5]:1->0 hier=vibration_core
-000000  point: type=toggle comment=hidden[12][6]:0->1 hier=vibration_core
-000000  point: type=toggle comment=hidden[12][6]:1->0 hier=vibration_core
-000000  point: type=toggle comment=hidden[12][7]:0->1 hier=vibration_core
-000000  point: type=toggle comment=hidden[12][7]:1->0 hier=vibration_core
+000013  point: type=toggle comment=hidden[13][0]:0->1 hier=vibration_core
+000011  point: type=toggle comment=hidden[13][0]:1->0 hier=vibration_core
+000012  point: type=toggle comment=hidden[13][1]:0->1 hier=vibration_core
+000010  point: type=toggle comment=hidden[13][1]:1->0 hier=vibration_core
+000003  point: type=toggle comment=hidden[13][2]:0->1 hier=vibration_core
+000003  point: type=toggle comment=hidden[13][2]:1->0 hier=vibration_core
+000013  point: type=toggle comment=hidden[13][3]:0->1 hier=vibration_core
+000011  point: type=toggle comment=hidden[13][3]:1->0 hier=vibration_core
+000008  point: type=toggle comment=hidden[13][4]:0->1 hier=vibration_core
+000008  point: type=toggle comment=hidden[13][4]:1->0 hier=vibration_core
-000000  point: type=toggle comment=hidden[13][5]:0->1 hier=vibration_core
-000000  point: type=toggle comment=hidden[13][5]:1->0 hier=vibration_core
-000000  point: type=toggle comment=hidden[13][6]:0->1 hier=vibration_core
-000000  point: type=toggle comment=hidden[13][6]:1->0 hier=vibration_core
-000000  point: type=toggle comment=hidden[13][7]:0->1 hier=vibration_core
-000000  point: type=toggle comment=hidden[13][7]:1->0 hier=vibration_core
-000000  point: type=toggle comment=hidden[14][0]:0->1 hier=vibration_core
-000000  point: type=toggle comment=hidden[14][0]:1->0 hier=vibration_core
-000000  point: type=toggle comment=hidden[14][1]:0->1 hier=vibration_core
-000000  point: type=toggle comment=hidden[14][1]:1->0 hier=vibration_core
-000000  point: type=toggle comment=hidden[14][2]:0->1 hier=vibration_core
-000000  point: type=toggle comment=hidden[14][2]:1->0 hier=vibration_core
-000000  point: type=toggle comment=hidden[14][3]:0->1 hier=vibration_core
-000000  point: type=toggle comment=hidden[14][3]:1->0 hier=vibration_core
-000000  point: type=toggle comment=hidden[14][4]:0->1 hier=vibration_core
-000000  point: type=toggle comment=hidden[14][4]:1->0 hier=vibration_core
-000000  point: type=toggle comment=hidden[14][5]:0->1 hier=vibration_core
-000000  point: type=toggle comment=hidden[14][5]:1->0 hier=vibration_core
-000000  point: type=toggle comment=hidden[14][6]:0->1 hier=vibration_core
-000000  point: type=toggle comment=hidden[14][6]:1->0 hier=vibration_core
-000000  point: type=toggle comment=hidden[14][7]:0->1 hier=vibration_core
-000000  point: type=toggle comment=hidden[14][7]:1->0 hier=vibration_core
+000007  point: type=toggle comment=hidden[15][0]:0->1 hier=vibration_core
+000007  point: type=toggle comment=hidden[15][0]:1->0 hier=vibration_core
+000005  point: type=toggle comment=hidden[15][1]:0->1 hier=vibration_core
+000005  point: type=toggle comment=hidden[15][1]:1->0 hier=vibration_core
+000006  point: type=toggle comment=hidden[15][2]:0->1 hier=vibration_core
+000006  point: type=toggle comment=hidden[15][2]:1->0 hier=vibration_core
+000005  point: type=toggle comment=hidden[15][3]:0->1 hier=vibration_core
+000005  point: type=toggle comment=hidden[15][3]:1->0 hier=vibration_core
+000005  point: type=toggle comment=hidden[15][4]:0->1 hier=vibration_core
+000005  point: type=toggle comment=hidden[15][4]:1->0 hier=vibration_core
+000004  point: type=toggle comment=hidden[15][5]:0->1 hier=vibration_core
+000004  point: type=toggle comment=hidden[15][5]:1->0 hier=vibration_core
-000000  point: type=toggle comment=hidden[15][6]:0->1 hier=vibration_core
-000000  point: type=toggle comment=hidden[15][6]:1->0 hier=vibration_core
-000000  point: type=toggle comment=hidden[15][7]:0->1 hier=vibration_core
-000000  point: type=toggle comment=hidden[15][7]:1->0 hier=vibration_core
+000012  point: type=toggle comment=hidden[1][0]:0->1 hier=vibration_core
+000012  point: type=toggle comment=hidden[1][0]:1->0 hier=vibration_core
+000003  point: type=toggle comment=hidden[1][1]:0->1 hier=vibration_core
+000003  point: type=toggle comment=hidden[1][1]:1->0 hier=vibration_core
+000011  point: type=toggle comment=hidden[1][2]:0->1 hier=vibration_core
+000009  point: type=toggle comment=hidden[1][2]:1->0 hier=vibration_core
+000004  point: type=toggle comment=hidden[1][3]:0->1 hier=vibration_core
+000004  point: type=toggle comment=hidden[1][3]:1->0 hier=vibration_core
+000003  point: type=toggle comment=hidden[1][4]:0->1 hier=vibration_core
+000003  point: type=toggle comment=hidden[1][4]:1->0 hier=vibration_core
+000004  point: type=toggle comment=hidden[1][5]:0->1 hier=vibration_core
+000004  point: type=toggle comment=hidden[1][5]:1->0 hier=vibration_core
+000004  point: type=toggle comment=hidden[1][6]:0->1 hier=vibration_core
+000004  point: type=toggle comment=hidden[1][6]:1->0 hier=vibration_core
-000000  point: type=toggle comment=hidden[1][7]:0->1 hier=vibration_core
-000000  point: type=toggle comment=hidden[1][7]:1->0 hier=vibration_core
-000000  point: type=toggle comment=hidden[2][0]:0->1 hier=vibration_core
-000000  point: type=toggle comment=hidden[2][0]:1->0 hier=vibration_core
-000000  point: type=toggle comment=hidden[2][1]:0->1 hier=vibration_core
-000000  point: type=toggle comment=hidden[2][1]:1->0 hier=vibration_core
-000000  point: type=toggle comment=hidden[2][2]:0->1 hier=vibration_core
-000000  point: type=toggle comment=hidden[2][2]:1->0 hier=vibration_core
-000000  point: type=toggle comment=hidden[2][3]:0->1 hier=vibration_core
-000000  point: type=toggle comment=hidden[2][3]:1->0 hier=vibration_core
-000000  point: type=toggle comment=hidden[2][4]:0->1 hier=vibration_core
-000000  point: type=toggle comment=hidden[2][4]:1->0 hier=vibration_core
-000000  point: type=toggle comment=hidden[2][5]:0->1 hier=vibration_core
-000000  point: type=toggle comment=hidden[2][5]:1->0 hier=vibration_core
-000000  point: type=toggle comment=hidden[2][6]:0->1 hier=vibration_core
-000000  point: type=toggle comment=hidden[2][6]:1->0 hier=vibration_core
-000000  point: type=toggle comment=hidden[2][7]:0->1 hier=vibration_core
-000000  point: type=toggle comment=hidden[2][7]:1->0 hier=vibration_core
+000012  point: type=toggle comment=hidden[3][0]:0->1 hier=vibration_core
+000010  point: type=toggle comment=hidden[3][0]:1->0 hier=vibration_core
+000004  point: type=toggle comment=hidden[3][1]:0->1 hier=vibration_core
+000004  point: type=toggle comment=hidden[3][1]:1->0 hier=vibration_core
+000009  point: type=toggle comment=hidden[3][2]:0->1 hier=vibration_core
+000007  point: type=toggle comment=hidden[3][2]:1->0 hier=vibration_core
+000005  point: type=toggle comment=hidden[3][3]:0->1 hier=vibration_core
+000005  point: type=toggle comment=hidden[3][3]:1->0 hier=vibration_core
+000006  point: type=toggle comment=hidden[3][4]:0->1 hier=vibration_core
+000006  point: type=toggle comment=hidden[3][4]:1->0 hier=vibration_core
-000000  point: type=toggle comment=hidden[3][5]:0->1 hier=vibration_core
-000000  point: type=toggle comment=hidden[3][5]:1->0 hier=vibration_core
+000004  point: type=toggle comment=hidden[3][6]:0->1 hier=vibration_core
+000004  point: type=toggle comment=hidden[3][6]:1->0 hier=vibration_core
-000000  point: type=toggle comment=hidden[3][7]:0->1 hier=vibration_core
-000000  point: type=toggle comment=hidden[3][7]:1->0 hier=vibration_core
-000000  point: type=toggle comment=hidden[4][0]:0->1 hier=vibration_core
-000000  point: type=toggle comment=hidden[4][0]:1->0 hier=vibration_core
-000000  point: type=toggle comment=hidden[4][1]:0->1 hier=vibration_core
-000000  point: type=toggle comment=hidden[4][1]:1->0 hier=vibration_core
-000000  point: type=toggle comment=hidden[4][2]:0->1 hier=vibration_core
-000000  point: type=toggle comment=hidden[4][2]:1->0 hier=vibration_core
-000000  point: type=toggle comment=hidden[4][3]:0->1 hier=vibration_core
-000000  point: type=toggle comment=hidden[4][3]:1->0 hier=vibration_core
-000000  point: type=toggle comment=hidden[4][4]:0->1 hier=vibration_core
-000000  point: type=toggle comment=hidden[4][4]:1->0 hier=vibration_core
-000000  point: type=toggle comment=hidden[4][5]:0->1 hier=vibration_core
-000000  point: type=toggle comment=hidden[4][5]:1->0 hier=vibration_core
-000000  point: type=toggle comment=hidden[4][6]:0->1 hier=vibration_core
-000000  point: type=toggle comment=hidden[4][6]:1->0 hier=vibration_core
-000000  point: type=toggle comment=hidden[4][7]:0->1 hier=vibration_core
-000000  point: type=toggle comment=hidden[4][7]:1->0 hier=vibration_core
+000012  point: type=toggle comment=hidden[5][0]:0->1 hier=vibration_core
+000012  point: type=toggle comment=hidden[5][0]:1->0 hier=vibration_core
+000003  point: type=toggle comment=hidden[5][1]:0->1 hier=vibration_core
+000003  point: type=toggle comment=hidden[5][1]:1->0 hier=vibration_core
+000004  point: type=toggle comment=hidden[5][2]:0->1 hier=vibration_core
+000004  point: type=toggle comment=hidden[5][2]:1->0 hier=vibration_core
+000004  point: type=toggle comment=hidden[5][3]:0->1 hier=vibration_core
+000004  point: type=toggle comment=hidden[5][3]:1->0 hier=vibration_core
+000001  point: type=toggle comment=hidden[5][4]:0->1 hier=vibration_core
+000001  point: type=toggle comment=hidden[5][4]:1->0 hier=vibration_core
+000005  point: type=toggle comment=hidden[5][5]:0->1 hier=vibration_core
+000005  point: type=toggle comment=hidden[5][5]:1->0 hier=vibration_core
+000004  point: type=toggle comment=hidden[5][6]:0->1 hier=vibration_core
+000004  point: type=toggle comment=hidden[5][6]:1->0 hier=vibration_core
-000000  point: type=toggle comment=hidden[5][7]:0->1 hier=vibration_core
-000000  point: type=toggle comment=hidden[5][7]:1->0 hier=vibration_core
+000012  point: type=toggle comment=hidden[6][0]:0->1 hier=vibration_core
+000010  point: type=toggle comment=hidden[6][0]:1->0 hier=vibration_core
+000005  point: type=toggle comment=hidden[6][1]:0->1 hier=vibration_core
+000005  point: type=toggle comment=hidden[6][1]:1->0 hier=vibration_core
+000011  point: type=toggle comment=hidden[6][2]:0->1 hier=vibration_core
+000011  point: type=toggle comment=hidden[6][2]:1->0 hier=vibration_core
+000012  point: type=toggle comment=hidden[6][3]:0->1 hier=vibration_core
+000010  point: type=toggle comment=hidden[6][3]:1->0 hier=vibration_core
+000001  point: type=toggle comment=hidden[6][4]:0->1 hier=vibration_core
+000001  point: type=toggle comment=hidden[6][4]:1->0 hier=vibration_core
+000005  point: type=toggle comment=hidden[6][5]:0->1 hier=vibration_core
+000005  point: type=toggle comment=hidden[6][5]:1->0 hier=vibration_core
-000000  point: type=toggle comment=hidden[6][6]:0->1 hier=vibration_core
-000000  point: type=toggle comment=hidden[6][6]:1->0 hier=vibration_core
-000000  point: type=toggle comment=hidden[6][7]:0->1 hier=vibration_core
-000000  point: type=toggle comment=hidden[6][7]:1->0 hier=vibration_core
-000000  point: type=toggle comment=hidden[7][0]:0->1 hier=vibration_core
-000000  point: type=toggle comment=hidden[7][0]:1->0 hier=vibration_core
-000000  point: type=toggle comment=hidden[7][1]:0->1 hier=vibration_core
-000000  point: type=toggle comment=hidden[7][1]:1->0 hier=vibration_core
-000000  point: type=toggle comment=hidden[7][2]:0->1 hier=vibration_core
-000000  point: type=toggle comment=hidden[7][2]:1->0 hier=vibration_core
-000000  point: type=toggle comment=hidden[7][3]:0->1 hier=vibration_core
-000000  point: type=toggle comment=hidden[7][3]:1->0 hier=vibration_core
-000000  point: type=toggle comment=hidden[7][4]:0->1 hier=vibration_core
-000000  point: type=toggle comment=hidden[7][4]:1->0 hier=vibration_core
-000000  point: type=toggle comment=hidden[7][5]:0->1 hier=vibration_core
-000000  point: type=toggle comment=hidden[7][5]:1->0 hier=vibration_core
-000000  point: type=toggle comment=hidden[7][6]:0->1 hier=vibration_core
-000000  point: type=toggle comment=hidden[7][6]:1->0 hier=vibration_core
-000000  point: type=toggle comment=hidden[7][7]:0->1 hier=vibration_core
-000000  point: type=toggle comment=hidden[7][7]:1->0 hier=vibration_core
+000008  point: type=toggle comment=hidden[8][0]:0->1 hier=vibration_core
+000006  point: type=toggle comment=hidden[8][0]:1->0 hier=vibration_core
+000009  point: type=toggle comment=hidden[8][1]:0->1 hier=vibration_core
+000007  point: type=toggle comment=hidden[8][1]:1->0 hier=vibration_core
+000013  point: type=toggle comment=hidden[8][2]:0->1 hier=vibration_core
+000011  point: type=toggle comment=hidden[8][2]:1->0 hier=vibration_core
+000009  point: type=toggle comment=hidden[8][3]:0->1 hier=vibration_core
+000009  point: type=toggle comment=hidden[8][3]:1->0 hier=vibration_core
+000006  point: type=toggle comment=hidden[8][4]:0->1 hier=vibration_core
+000006  point: type=toggle comment=hidden[8][4]:1->0 hier=vibration_core
+000004  point: type=toggle comment=hidden[8][5]:0->1 hier=vibration_core
+000004  point: type=toggle comment=hidden[8][5]:1->0 hier=vibration_core
-000000  point: type=toggle comment=hidden[8][6]:0->1 hier=vibration_core
-000000  point: type=toggle comment=hidden[8][6]:1->0 hier=vibration_core
-000000  point: type=toggle comment=hidden[8][7]:0->1 hier=vibration_core
-000000  point: type=toggle comment=hidden[8][7]:1->0 hier=vibration_core
+000006  point: type=toggle comment=hidden[9][0]:0->1 hier=vibration_core
+000006  point: type=toggle comment=hidden[9][0]:1->0 hier=vibration_core
+000011  point: type=toggle comment=hidden[9][1]:0->1 hier=vibration_core
+000009  point: type=toggle comment=hidden[9][1]:1->0 hier=vibration_core
+000004  point: type=toggle comment=hidden[9][2]:0->1 hier=vibration_core
+000004  point: type=toggle comment=hidden[9][2]:1->0 hier=vibration_core
+000005  point: type=toggle comment=hidden[9][3]:0->1 hier=vibration_core
+000005  point: type=toggle comment=hidden[9][3]:1->0 hier=vibration_core
+000006  point: type=toggle comment=hidden[9][4]:0->1 hier=vibration_core
+000006  point: type=toggle comment=hidden[9][4]:1->0 hier=vibration_core
-000000  point: type=toggle comment=hidden[9][5]:0->1 hier=vibration_core
-000000  point: type=toggle comment=hidden[9][5]:1->0 hier=vibration_core
+000004  point: type=toggle comment=hidden[9][6]:0->1 hier=vibration_core
+000004  point: type=toggle comment=hidden[9][6]:1->0 hier=vibration_core
-000000  point: type=toggle comment=hidden[9][7]:0->1 hier=vibration_core
-000000  point: type=toggle comment=hidden[9][7]:1->0 hier=vibration_core
 000480     reg [3:0] feature_index;
+000480  point: type=toggle comment=feature_index[0]:0->1 hier=vibration_core
+000478  point: type=toggle comment=feature_index[0]:1->0 hier=vibration_core
+000240  point: type=toggle comment=feature_index[1]:0->1 hier=vibration_core
+000238  point: type=toggle comment=feature_index[1]:1->0 hier=vibration_core
+000120  point: type=toggle comment=feature_index[2]:0->1 hier=vibration_core
+000118  point: type=toggle comment=feature_index[2]:1->0 hier=vibration_core
+000060  point: type=toggle comment=feature_index[3]:0->1 hier=vibration_core
+000058  point: type=toggle comment=feature_index[3]:1->0 hier=vibration_core
 001442     reg [BI_W-1:0] power_index;
+001442  point: type=toggle comment=power_index[0]:0->1 hier=vibration_core
+001440  point: type=toggle comment=power_index[0]:1->0 hier=vibration_core
+000722  point: type=toggle comment=power_index[1]:0->1 hier=vibration_core
+000720  point: type=toggle comment=power_index[1]:1->0 hier=vibration_core
+000360  point: type=toggle comment=power_index[2]:0->1 hier=vibration_core
+000358  point: type=toggle comment=power_index[2]:1->0 hier=vibration_core
+000180  point: type=toggle comment=power_index[3]:0->1 hier=vibration_core
+000178  point: type=toggle comment=power_index[3]:1->0 hier=vibration_core
+000060  point: type=toggle comment=power_index[4]:0->1 hier=vibration_core
+000060  point: type=toggle comment=power_index[4]:1->0 hier=vibration_core
+000060  point: type=toggle comment=power_index[5]:0->1 hier=vibration_core
+000058  point: type=toggle comment=power_index[5]:1->0 hier=vibration_core
 000962     reg [1:0] band_part;
+000962  point: type=toggle comment=band_part[0]:0->1 hier=vibration_core
+000962  point: type=toggle comment=band_part[0]:1->0 hier=vibration_core
+000962  point: type=toggle comment=band_part[1]:0->1 hier=vibration_core
+000962  point: type=toggle comment=band_part[1]:1->0 hier=vibration_core
~000208     reg [32:0] band_sum;
+000208  point: type=toggle comment=band_sum[0]:0->1 hier=vibration_core
+000208  point: type=toggle comment=band_sum[0]:1->0 hier=vibration_core
+000094  point: type=toggle comment=band_sum[10]:0->1 hier=vibration_core
+000094  point: type=toggle comment=band_sum[10]:1->0 hier=vibration_core
+000088  point: type=toggle comment=band_sum[11]:0->1 hier=vibration_core
+000088  point: type=toggle comment=band_sum[11]:1->0 hier=vibration_core
+000090  point: type=toggle comment=band_sum[12]:0->1 hier=vibration_core
+000090  point: type=toggle comment=band_sum[12]:1->0 hier=vibration_core
+000092  point: type=toggle comment=band_sum[13]:0->1 hier=vibration_core
+000092  point: type=toggle comment=band_sum[13]:1->0 hier=vibration_core
+000078  point: type=toggle comment=band_sum[14]:0->1 hier=vibration_core
+000078  point: type=toggle comment=band_sum[14]:1->0 hier=vibration_core
+000082  point: type=toggle comment=band_sum[15]:0->1 hier=vibration_core
+000082  point: type=toggle comment=band_sum[15]:1->0 hier=vibration_core
+000063  point: type=toggle comment=band_sum[16]:0->1 hier=vibration_core
+000063  point: type=toggle comment=band_sum[16]:1->0 hier=vibration_core
+000042  point: type=toggle comment=band_sum[17]:0->1 hier=vibration_core
+000042  point: type=toggle comment=band_sum[17]:1->0 hier=vibration_core
+000004  point: type=toggle comment=band_sum[18]:0->1 hier=vibration_core
+000004  point: type=toggle comment=band_sum[18]:1->0 hier=vibration_core
+000032  point: type=toggle comment=band_sum[19]:0->1 hier=vibration_core
+000032  point: type=toggle comment=band_sum[19]:1->0 hier=vibration_core
+000181  point: type=toggle comment=band_sum[1]:0->1 hier=vibration_core
+000181  point: type=toggle comment=band_sum[1]:1->0 hier=vibration_core
+000015  point: type=toggle comment=band_sum[20]:0->1 hier=vibration_core
+000015  point: type=toggle comment=band_sum[20]:1->0 hier=vibration_core
+000029  point: type=toggle comment=band_sum[21]:0->1 hier=vibration_core
+000029  point: type=toggle comment=band_sum[21]:1->0 hier=vibration_core
+000002  point: type=toggle comment=band_sum[22]:0->1 hier=vibration_core
+000002  point: type=toggle comment=band_sum[22]:1->0 hier=vibration_core
-000000  point: type=toggle comment=band_sum[23]:0->1 hier=vibration_core
-000000  point: type=toggle comment=band_sum[23]:1->0 hier=vibration_core
+000001  point: type=toggle comment=band_sum[24]:0->1 hier=vibration_core
+000001  point: type=toggle comment=band_sum[24]:1->0 hier=vibration_core
-000000  point: type=toggle comment=band_sum[25]:0->1 hier=vibration_core
-000000  point: type=toggle comment=band_sum[25]:1->0 hier=vibration_core
-000000  point: type=toggle comment=band_sum[26]:0->1 hier=vibration_core
-000000  point: type=toggle comment=band_sum[26]:1->0 hier=vibration_core
-000000  point: type=toggle comment=band_sum[27]:0->1 hier=vibration_core
-000000  point: type=toggle comment=band_sum[27]:1->0 hier=vibration_core
-000000  point: type=toggle comment=band_sum[28]:0->1 hier=vibration_core
-000000  point: type=toggle comment=band_sum[28]:1->0 hier=vibration_core
-000000  point: type=toggle comment=band_sum[29]:0->1 hier=vibration_core
-000000  point: type=toggle comment=band_sum[29]:1->0 hier=vibration_core
+000134  point: type=toggle comment=band_sum[2]:0->1 hier=vibration_core
+000134  point: type=toggle comment=band_sum[2]:1->0 hier=vibration_core
-000000  point: type=toggle comment=band_sum[30]:0->1 hier=vibration_core
-000000  point: type=toggle comment=band_sum[30]:1->0 hier=vibration_core
-000000  point: type=toggle comment=band_sum[31]:0->1 hier=vibration_core
-000000  point: type=toggle comment=band_sum[31]:1->0 hier=vibration_core
-000000  point: type=toggle comment=band_sum[32]:0->1 hier=vibration_core
-000000  point: type=toggle comment=band_sum[32]:1->0 hier=vibration_core
+000160  point: type=toggle comment=band_sum[3]:0->1 hier=vibration_core
+000160  point: type=toggle comment=band_sum[3]:1->0 hier=vibration_core
+000153  point: type=toggle comment=band_sum[4]:0->1 hier=vibration_core
+000153  point: type=toggle comment=band_sum[4]:1->0 hier=vibration_core
+000138  point: type=toggle comment=band_sum[5]:0->1 hier=vibration_core
+000138  point: type=toggle comment=band_sum[5]:1->0 hier=vibration_core
+000126  point: type=toggle comment=band_sum[6]:0->1 hier=vibration_core
+000126  point: type=toggle comment=band_sum[6]:1->0 hier=vibration_core
+000087  point: type=toggle comment=band_sum[7]:0->1 hier=vibration_core
+000087  point: type=toggle comment=band_sum[7]:1->0 hier=vibration_core
+000105  point: type=toggle comment=band_sum[8]:0->1 hier=vibration_core
+000105  point: type=toggle comment=band_sum[8]:1->0 hier=vibration_core
+000107  point: type=toggle comment=band_sum[9]:0->1 hier=vibration_core
+000107  point: type=toggle comment=band_sum[9]:1->0 hier=vibration_core
 1216575     wire [32:0] one_bin_power = power_sum + {1'b0,product[0]};
+932426  point: type=toggle comment=one_bin_power[0]:0->1 hier=vibration_core
+932426  point: type=toggle comment=one_bin_power[0]:1->0 hier=vibration_core
+1196975  point: type=toggle comment=one_bin_power[10]:0->1 hier=vibration_core
+1196975  point: type=toggle comment=one_bin_power[10]:1->0 hier=vibration_core
+1197207  point: type=toggle comment=one_bin_power[11]:0->1 hier=vibration_core
+1197207  point: type=toggle comment=one_bin_power[11]:1->0 hier=vibration_core
+1201340  point: type=toggle comment=one_bin_power[12]:0->1 hier=vibration_core
+1201340  point: type=toggle comment=one_bin_power[12]:1->0 hier=vibration_core
+1196990  point: type=toggle comment=one_bin_power[13]:0->1 hier=vibration_core
+1196990  point: type=toggle comment=one_bin_power[13]:1->0 hier=vibration_core
+1198054  point: type=toggle comment=one_bin_power[14]:0->1 hier=vibration_core
+1198054  point: type=toggle comment=one_bin_power[14]:1->0 hier=vibration_core
+1197516  point: type=toggle comment=one_bin_power[15]:0->1 hier=vibration_core
+1197516  point: type=toggle comment=one_bin_power[15]:1->0 hier=vibration_core
+1196601  point: type=toggle comment=one_bin_power[16]:0->1 hier=vibration_core
+1196601  point: type=toggle comment=one_bin_power[16]:1->0 hier=vibration_core
+1198109  point: type=toggle comment=one_bin_power[17]:0->1 hier=vibration_core
+1198109  point: type=toggle comment=one_bin_power[17]:1->0 hier=vibration_core
+1195059  point: type=toggle comment=one_bin_power[18]:0->1 hier=vibration_core
+1195059  point: type=toggle comment=one_bin_power[18]:1->0 hier=vibration_core
+1191701  point: type=toggle comment=one_bin_power[19]:0->1 hier=vibration_core
+1191701  point: type=toggle comment=one_bin_power[19]:1->0 hier=vibration_core
+1135745  point: type=toggle comment=one_bin_power[1]:0->1 hier=vibration_core
+1135745  point: type=toggle comment=one_bin_power[1]:1->0 hier=vibration_core
+1196792  point: type=toggle comment=one_bin_power[20]:0->1 hier=vibration_core
+1196792  point: type=toggle comment=one_bin_power[20]:1->0 hier=vibration_core
+1189627  point: type=toggle comment=one_bin_power[21]:0->1 hier=vibration_core
+1189627  point: type=toggle comment=one_bin_power[21]:1->0 hier=vibration_core
+1188774  point: type=toggle comment=one_bin_power[22]:0->1 hier=vibration_core
+1188774  point: type=toggle comment=one_bin_power[22]:1->0 hier=vibration_core
+1216575  point: type=toggle comment=one_bin_power[23]:0->1 hier=vibration_core
+1216575  point: type=toggle comment=one_bin_power[23]:1->0 hier=vibration_core
+1212920  point: type=toggle comment=one_bin_power[24]:0->1 hier=vibration_core
+1212920  point: type=toggle comment=one_bin_power[24]:1->0 hier=vibration_core
+1212898  point: type=toggle comment=one_bin_power[25]:0->1 hier=vibration_core
+1212898  point: type=toggle comment=one_bin_power[25]:1->0 hier=vibration_core
+1212896  point: type=toggle comment=one_bin_power[26]:0->1 hier=vibration_core
+1212896  point: type=toggle comment=one_bin_power[26]:1->0 hier=vibration_core
+1212896  point: type=toggle comment=one_bin_power[27]:0->1 hier=vibration_core
+1212896  point: type=toggle comment=one_bin_power[27]:1->0 hier=vibration_core
+1212896  point: type=toggle comment=one_bin_power[28]:0->1 hier=vibration_core
+1212896  point: type=toggle comment=one_bin_power[28]:1->0 hier=vibration_core
+1212896  point: type=toggle comment=one_bin_power[29]:0->1 hier=vibration_core
+1212896  point: type=toggle comment=one_bin_power[29]:1->0 hier=vibration_core
+1187623  point: type=toggle comment=one_bin_power[2]:0->1 hier=vibration_core
+1187623  point: type=toggle comment=one_bin_power[2]:1->0 hier=vibration_core
+1212896  point: type=toggle comment=one_bin_power[30]:0->1 hier=vibration_core
+1212896  point: type=toggle comment=one_bin_power[30]:1->0 hier=vibration_core
+1212896  point: type=toggle comment=one_bin_power[31]:0->1 hier=vibration_core
+1212896  point: type=toggle comment=one_bin_power[31]:1->0 hier=vibration_core
+018680  point: type=toggle comment=one_bin_power[32]:0->1 hier=vibration_core
+018680  point: type=toggle comment=one_bin_power[32]:1->0 hier=vibration_core
+1194560  point: type=toggle comment=one_bin_power[3]:0->1 hier=vibration_core
+1194560  point: type=toggle comment=one_bin_power[3]:1->0 hier=vibration_core
+1194410  point: type=toggle comment=one_bin_power[4]:0->1 hier=vibration_core
+1194410  point: type=toggle comment=one_bin_power[4]:1->0 hier=vibration_core
+1199424  point: type=toggle comment=one_bin_power[5]:0->1 hier=vibration_core
+1199424  point: type=toggle comment=one_bin_power[5]:1->0 hier=vibration_core
+1198150  point: type=toggle comment=one_bin_power[6]:0->1 hier=vibration_core
+1198150  point: type=toggle comment=one_bin_power[6]:1->0 hier=vibration_core
+1195051  point: type=toggle comment=one_bin_power[7]:0->1 hier=vibration_core
+1195051  point: type=toggle comment=one_bin_power[7]:1->0 hier=vibration_core
+1200013  point: type=toggle comment=one_bin_power[8]:0->1 hier=vibration_core
+1200013  point: type=toggle comment=one_bin_power[8]:1->0 hier=vibration_core
+1197428  point: type=toggle comment=one_bin_power[9]:0->1 hier=vibration_core
+1197428  point: type=toggle comment=one_bin_power[9]:1->0 hier=vibration_core
~1216572     wire [33:0] band_sum_next = {1'b0,band_sum}+{1'b0,one_bin_power};
+932547  point: type=toggle comment=band_sum_next[0]:0->1 hier=vibration_core
+932547  point: type=toggle comment=band_sum_next[0]:1->0 hier=vibration_core
+1197045  point: type=toggle comment=band_sum_next[10]:0->1 hier=vibration_core
+1197045  point: type=toggle comment=band_sum_next[10]:1->0 hier=vibration_core
+1197252  point: type=toggle comment=band_sum_next[11]:0->1 hier=vibration_core
+1197252  point: type=toggle comment=band_sum_next[11]:1->0 hier=vibration_core
+1201417  point: type=toggle comment=band_sum_next[12]:0->1 hier=vibration_core
+1201417  point: type=toggle comment=band_sum_next[12]:1->0 hier=vibration_core
+1197052  point: type=toggle comment=band_sum_next[13]:0->1 hier=vibration_core
+1197052  point: type=toggle comment=band_sum_next[13]:1->0 hier=vibration_core
+1198143  point: type=toggle comment=band_sum_next[14]:0->1 hier=vibration_core
+1198143  point: type=toggle comment=band_sum_next[14]:1->0 hier=vibration_core
+1197594  point: type=toggle comment=band_sum_next[15]:0->1 hier=vibration_core
+1197594  point: type=toggle comment=band_sum_next[15]:1->0 hier=vibration_core
+1196699  point: type=toggle comment=band_sum_next[16]:0->1 hier=vibration_core
+1196699  point: type=toggle comment=band_sum_next[16]:1->0 hier=vibration_core
+1198142  point: type=toggle comment=band_sum_next[17]:0->1 hier=vibration_core
+1198142  point: type=toggle comment=band_sum_next[17]:1->0 hier=vibration_core
+1195073  point: type=toggle comment=band_sum_next[18]:0->1 hier=vibration_core
+1195073  point: type=toggle comment=band_sum_next[18]:1->0 hier=vibration_core
+1191721  point: type=toggle comment=band_sum_next[19]:0->1 hier=vibration_core
+1191721  point: type=toggle comment=band_sum_next[19]:1->0 hier=vibration_core
+1135887  point: type=toggle comment=band_sum_next[1]:0->1 hier=vibration_core
+1135887  point: type=toggle comment=band_sum_next[1]:1->0 hier=vibration_core
+1196833  point: type=toggle comment=band_sum_next[20]:0->1 hier=vibration_core
+1196833  point: type=toggle comment=band_sum_next[20]:1->0 hier=vibration_core
+1189647  point: type=toggle comment=band_sum_next[21]:0->1 hier=vibration_core
+1189647  point: type=toggle comment=band_sum_next[21]:1->0 hier=vibration_core
+1188791  point: type=toggle comment=band_sum_next[22]:0->1 hier=vibration_core
+1188791  point: type=toggle comment=band_sum_next[22]:1->0 hier=vibration_core
+1216572  point: type=toggle comment=band_sum_next[23]:0->1 hier=vibration_core
+1216572  point: type=toggle comment=band_sum_next[23]:1->0 hier=vibration_core
+1212920  point: type=toggle comment=band_sum_next[24]:0->1 hier=vibration_core
+1212920  point: type=toggle comment=band_sum_next[24]:1->0 hier=vibration_core
+1212898  point: type=toggle comment=band_sum_next[25]:0->1 hier=vibration_core
+1212898  point: type=toggle comment=band_sum_next[25]:1->0 hier=vibration_core
+1212896  point: type=toggle comment=band_sum_next[26]:0->1 hier=vibration_core
+1212896  point: type=toggle comment=band_sum_next[26]:1->0 hier=vibration_core
+1212896  point: type=toggle comment=band_sum_next[27]:0->1 hier=vibration_core
+1212896  point: type=toggle comment=band_sum_next[27]:1->0 hier=vibration_core
+1212896  point: type=toggle comment=band_sum_next[28]:0->1 hier=vibration_core
+1212896  point: type=toggle comment=band_sum_next[28]:1->0 hier=vibration_core
+1212896  point: type=toggle comment=band_sum_next[29]:0->1 hier=vibration_core
+1212896  point: type=toggle comment=band_sum_next[29]:1->0 hier=vibration_core
+1187782  point: type=toggle comment=band_sum_next[2]:0->1 hier=vibration_core
+1187782  point: type=toggle comment=band_sum_next[2]:1->0 hier=vibration_core
+1212896  point: type=toggle comment=band_sum_next[30]:0->1 hier=vibration_core
+1212896  point: type=toggle comment=band_sum_next[30]:1->0 hier=vibration_core
+1212896  point: type=toggle comment=band_sum_next[31]:0->1 hier=vibration_core
+1212896  point: type=toggle comment=band_sum_next[31]:1->0 hier=vibration_core
+018680  point: type=toggle comment=band_sum_next[32]:0->1 hier=vibration_core
+018680  point: type=toggle comment=band_sum_next[32]:1->0 hier=vibration_core
-000000  point: type=toggle comment=band_sum_next[33]:0->1 hier=vibration_core
-000000  point: type=toggle comment=band_sum_next[33]:1->0 hier=vibration_core
+1194664  point: type=toggle comment=band_sum_next[3]:0->1 hier=vibration_core
+1194664  point: type=toggle comment=band_sum_next[3]:1->0 hier=vibration_core
+1194544  point: type=toggle comment=band_sum_next[4]:0->1 hier=vibration_core
+1194544  point: type=toggle comment=band_sum_next[4]:1->0 hier=vibration_core
+1199492  point: type=toggle comment=band_sum_next[5]:0->1 hier=vibration_core
+1199492  point: type=toggle comment=band_sum_next[5]:1->0 hier=vibration_core
+1198258  point: type=toggle comment=band_sum_next[6]:0->1 hier=vibration_core
+1198258  point: type=toggle comment=band_sum_next[6]:1->0 hier=vibration_core
+1195117  point: type=toggle comment=band_sum_next[7]:0->1 hier=vibration_core
+1195117  point: type=toggle comment=band_sum_next[7]:1->0 hier=vibration_core
+1200138  point: type=toggle comment=band_sum_next[8]:0->1 hier=vibration_core
+1200138  point: type=toggle comment=band_sum_next[8]:1->0 hier=vibration_core
+1197478  point: type=toggle comment=band_sum_next[9]:0->1 hier=vibration_core
+1197478  point: type=toggle comment=band_sum_next[9]:1->0 hier=vibration_core
~000337     reg [32:0] power_sum, quant_work;
+000290  point: type=toggle comment=power_sum[0]:0->1 hier=vibration_core
+000290  point: type=toggle comment=power_sum[0]:1->0 hier=vibration_core
+000136  point: type=toggle comment=power_sum[10]:0->1 hier=vibration_core
+000136  point: type=toggle comment=power_sum[10]:1->0 hier=vibration_core
+000134  point: type=toggle comment=power_sum[11]:0->1 hier=vibration_core
+000134  point: type=toggle comment=power_sum[11]:1->0 hier=vibration_core
+000134  point: type=toggle comment=power_sum[12]:0->1 hier=vibration_core
+000134  point: type=toggle comment=power_sum[12]:1->0 hier=vibration_core
+000119  point: type=toggle comment=power_sum[13]:0->1 hier=vibration_core
+000119  point: type=toggle comment=power_sum[13]:1->0 hier=vibration_core
+000099  point: type=toggle comment=power_sum[14]:0->1 hier=vibration_core
+000099  point: type=toggle comment=power_sum[14]:1->0 hier=vibration_core
+000082  point: type=toggle comment=power_sum[15]:0->1 hier=vibration_core
+000082  point: type=toggle comment=power_sum[15]:1->0 hier=vibration_core
+000060  point: type=toggle comment=power_sum[16]:0->1 hier=vibration_core
+000060  point: type=toggle comment=power_sum[16]:1->0 hier=vibration_core
+000067  point: type=toggle comment=power_sum[17]:0->1 hier=vibration_core
+000067  point: type=toggle comment=power_sum[17]:1->0 hier=vibration_core
+000038  point: type=toggle comment=power_sum[18]:0->1 hier=vibration_core
+000038  point: type=toggle comment=power_sum[18]:1->0 hier=vibration_core
+000009  point: type=toggle comment=power_sum[19]:0->1 hier=vibration_core
+000009  point: type=toggle comment=power_sum[19]:1->0 hier=vibration_core
+000129  point: type=toggle comment=power_sum[1]:0->1 hier=vibration_core
+000129  point: type=toggle comment=power_sum[1]:1->0 hier=vibration_core
+000014  point: type=toggle comment=power_sum[20]:0->1 hier=vibration_core
+000014  point: type=toggle comment=power_sum[20]:1->0 hier=vibration_core
+000015  point: type=toggle comment=power_sum[21]:0->1 hier=vibration_core
+000015  point: type=toggle comment=power_sum[21]:1->0 hier=vibration_core
+000030  point: type=toggle comment=power_sum[22]:0->1 hier=vibration_core
+000030  point: type=toggle comment=power_sum[22]:1->0 hier=vibration_core
+000003  point: type=toggle comment=power_sum[23]:0->1 hier=vibration_core
+000003  point: type=toggle comment=power_sum[23]:1->0 hier=vibration_core
+000001  point: type=toggle comment=power_sum[24]:0->1 hier=vibration_core
+000001  point: type=toggle comment=power_sum[24]:1->0 hier=vibration_core
+000001  point: type=toggle comment=power_sum[25]:0->1 hier=vibration_core
+000001  point: type=toggle comment=power_sum[25]:1->0 hier=vibration_core
-000000  point: type=toggle comment=power_sum[26]:0->1 hier=vibration_core
-000000  point: type=toggle comment=power_sum[26]:1->0 hier=vibration_core
-000000  point: type=toggle comment=power_sum[27]:0->1 hier=vibration_core
-000000  point: type=toggle comment=power_sum[27]:1->0 hier=vibration_core
-000000  point: type=toggle comment=power_sum[28]:0->1 hier=vibration_core
-000000  point: type=toggle comment=power_sum[28]:1->0 hier=vibration_core
-000000  point: type=toggle comment=power_sum[29]:0->1 hier=vibration_core
-000000  point: type=toggle comment=power_sum[29]:1->0 hier=vibration_core
+000238  point: type=toggle comment=power_sum[2]:0->1 hier=vibration_core
+000238  point: type=toggle comment=power_sum[2]:1->0 hier=vibration_core
-000000  point: type=toggle comment=power_sum[30]:0->1 hier=vibration_core
-000000  point: type=toggle comment=power_sum[30]:1->0 hier=vibration_core
-000000  point: type=toggle comment=power_sum[31]:0->1 hier=vibration_core
-000000  point: type=toggle comment=power_sum[31]:1->0 hier=vibration_core
-000000  point: type=toggle comment=power_sum[32]:0->1 hier=vibration_core
-000000  point: type=toggle comment=power_sum[32]:1->0 hier=vibration_core
+000186  point: type=toggle comment=power_sum[3]:0->1 hier=vibration_core
+000186  point: type=toggle comment=power_sum[3]:1->0 hier=vibration_core
+000191  point: type=toggle comment=power_sum[4]:0->1 hier=vibration_core
+000191  point: type=toggle comment=power_sum[4]:1->0 hier=vibration_core
+000159  point: type=toggle comment=power_sum[5]:0->1 hier=vibration_core
+000159  point: type=toggle comment=power_sum[5]:1->0 hier=vibration_core
+000163  point: type=toggle comment=power_sum[6]:0->1 hier=vibration_core
+000163  point: type=toggle comment=power_sum[6]:1->0 hier=vibration_core
+000129  point: type=toggle comment=power_sum[7]:0->1 hier=vibration_core
+000129  point: type=toggle comment=power_sum[7]:1->0 hier=vibration_core
+000109  point: type=toggle comment=power_sum[8]:0->1 hier=vibration_core
+000109  point: type=toggle comment=power_sum[8]:1->0 hier=vibration_core
+000134  point: type=toggle comment=power_sum[9]:0->1 hier=vibration_core
+000134  point: type=toggle comment=power_sum[9]:1->0 hier=vibration_core
+000337  point: type=toggle comment=quant_work[0]:0->1 hier=vibration_core
+000337  point: type=toggle comment=quant_work[0]:1->0 hier=vibration_core
+000172  point: type=toggle comment=quant_work[10]:0->1 hier=vibration_core
+000172  point: type=toggle comment=quant_work[10]:1->0 hier=vibration_core
+000178  point: type=toggle comment=quant_work[11]:0->1 hier=vibration_core
+000178  point: type=toggle comment=quant_work[11]:1->0 hier=vibration_core
+000175  point: type=toggle comment=quant_work[12]:0->1 hier=vibration_core
+000175  point: type=toggle comment=quant_work[12]:1->0 hier=vibration_core
+000160  point: type=toggle comment=quant_work[13]:0->1 hier=vibration_core
+000160  point: type=toggle comment=quant_work[13]:1->0 hier=vibration_core
+000148  point: type=toggle comment=quant_work[14]:0->1 hier=vibration_core
+000148  point: type=toggle comment=quant_work[14]:1->0 hier=vibration_core
+000120  point: type=toggle comment=quant_work[15]:0->1 hier=vibration_core
+000120  point: type=toggle comment=quant_work[15]:1->0 hier=vibration_core
+000092  point: type=toggle comment=quant_work[16]:0->1 hier=vibration_core
+000092  point: type=toggle comment=quant_work[16]:1->0 hier=vibration_core
+000088  point: type=toggle comment=quant_work[17]:0->1 hier=vibration_core
+000088  point: type=toggle comment=quant_work[17]:1->0 hier=vibration_core
+000063  point: type=toggle comment=quant_work[18]:0->1 hier=vibration_core
+000063  point: type=toggle comment=quant_work[18]:1->0 hier=vibration_core
+000034  point: type=toggle comment=quant_work[19]:0->1 hier=vibration_core
+000034  point: type=toggle comment=quant_work[19]:1->0 hier=vibration_core
+000310  point: type=toggle comment=quant_work[1]:0->1 hier=vibration_core
+000310  point: type=toggle comment=quant_work[1]:1->0 hier=vibration_core
+000034  point: type=toggle comment=quant_work[20]:0->1 hier=vibration_core
+000034  point: type=toggle comment=quant_work[20]:1->0 hier=vibration_core
+000032  point: type=toggle comment=quant_work[21]:0->1 hier=vibration_core
+000032  point: type=toggle comment=quant_work[21]:1->0 hier=vibration_core
+000031  point: type=toggle comment=quant_work[22]:0->1 hier=vibration_core
+000031  point: type=toggle comment=quant_work[22]:1->0 hier=vibration_core
+000003  point: type=toggle comment=quant_work[23]:0->1 hier=vibration_core
+000003  point: type=toggle comment=quant_work[23]:1->0 hier=vibration_core
+000001  point: type=toggle comment=quant_work[24]:0->1 hier=vibration_core
+000001  point: type=toggle comment=quant_work[24]:1->0 hier=vibration_core
+000001  point: type=toggle comment=quant_work[25]:0->1 hier=vibration_core
+000001  point: type=toggle comment=quant_work[25]:1->0 hier=vibration_core
-000000  point: type=toggle comment=quant_work[26]:0->1 hier=vibration_core
-000000  point: type=toggle comment=quant_work[26]:1->0 hier=vibration_core
-000000  point: type=toggle comment=quant_work[27]:0->1 hier=vibration_core
-000000  point: type=toggle comment=quant_work[27]:1->0 hier=vibration_core
-000000  point: type=toggle comment=quant_work[28]:0->1 hier=vibration_core
-000000  point: type=toggle comment=quant_work[28]:1->0 hier=vibration_core
-000000  point: type=toggle comment=quant_work[29]:0->1 hier=vibration_core
-000000  point: type=toggle comment=quant_work[29]:1->0 hier=vibration_core
+000288  point: type=toggle comment=quant_work[2]:0->1 hier=vibration_core
+000288  point: type=toggle comment=quant_work[2]:1->0 hier=vibration_core
-000000  point: type=toggle comment=quant_work[30]:0->1 hier=vibration_core
-000000  point: type=toggle comment=quant_work[30]:1->0 hier=vibration_core
-000000  point: type=toggle comment=quant_work[31]:0->1 hier=vibration_core
-000000  point: type=toggle comment=quant_work[31]:1->0 hier=vibration_core
-000000  point: type=toggle comment=quant_work[32]:0->1 hier=vibration_core
-000000  point: type=toggle comment=quant_work[32]:1->0 hier=vibration_core
+000264  point: type=toggle comment=quant_work[3]:0->1 hier=vibration_core
+000264  point: type=toggle comment=quant_work[3]:1->0 hier=vibration_core
+000268  point: type=toggle comment=quant_work[4]:0->1 hier=vibration_core
+000268  point: type=toggle comment=quant_work[4]:1->0 hier=vibration_core
+000231  point: type=toggle comment=quant_work[5]:0->1 hier=vibration_core
+000231  point: type=toggle comment=quant_work[5]:1->0 hier=vibration_core
+000223  point: type=toggle comment=quant_work[6]:0->1 hier=vibration_core
+000223  point: type=toggle comment=quant_work[6]:1->0 hier=vibration_core
+000192  point: type=toggle comment=quant_work[7]:0->1 hier=vibration_core
+000192  point: type=toggle comment=quant_work[7]:1->0 hier=vibration_core
+000168  point: type=toggle comment=quant_work[8]:0->1 hier=vibration_core
+000168  point: type=toggle comment=quant_work[8]:1->0 hier=vibration_core
+000169  point: type=toggle comment=quant_work[9]:0->1 hier=vibration_core
+000169  point: type=toggle comment=quant_work[9]:1->0 hier=vibration_core
~001920     reg [7:0] quant_remaining;
+001920  point: type=toggle comment=quant_remaining[0]:0->1 hier=vibration_core
+001920  point: type=toggle comment=quant_remaining[0]:1->0 hier=vibration_core
+001142  point: type=toggle comment=quant_remaining[1]:0->1 hier=vibration_core
+001142  point: type=toggle comment=quant_remaining[1]:1->0 hier=vibration_core
+000420  point: type=toggle comment=quant_remaining[2]:0->1 hier=vibration_core
+000420  point: type=toggle comment=quant_remaining[2]:1->0 hier=vibration_core
+000120  point: type=toggle comment=quant_remaining[3]:0->1 hier=vibration_core
+000120  point: type=toggle comment=quant_remaining[3]:1->0 hier=vibration_core
-000000  point: type=toggle comment=quant_remaining[4]:0->1 hier=vibration_core
-000000  point: type=toggle comment=quant_remaining[4]:1->0 hier=vibration_core
-000000  point: type=toggle comment=quant_remaining[5]:0->1 hier=vibration_core
-000000  point: type=toggle comment=quant_remaining[5]:1->0 hier=vibration_core
-000000  point: type=toggle comment=quant_remaining[6]:0->1 hier=vibration_core
-000000  point: type=toggle comment=quant_remaining[6]:1->0 hier=vibration_core
-000000  point: type=toggle comment=quant_remaining[7]:0->1 hier=vibration_core
-000000  point: type=toggle comment=quant_remaining[7]:1->0 hier=vibration_core
 000322     reg quant_guard, quant_sticky;
+000205  point: type=toggle comment=quant_sticky:0->1 hier=vibration_core
+000205  point: type=toggle comment=quant_sticky:1->0 hier=vibration_core
+000322  point: type=toggle comment=quant_guard:0->1 hier=vibration_core
+000322  point: type=toggle comment=quant_guard:1->0 hier=vibration_core
 93243823     wire [7:0] quant_rounded = {1'b0,quant_work[6:0]} + {7'd0,(quant_guard && (quant_sticky || quant_work[0]))};
+000395  point: type=toggle comment=quant_rounded[0]:0->1 hier=vibration_core
+000395  point: type=toggle comment=quant_rounded[0]:1->0 hier=vibration_core
+000321  point: type=toggle comment=quant_rounded[1]:0->1 hier=vibration_core
+000321  point: type=toggle comment=quant_rounded[1]:1->0 hier=vibration_core
+000308  point: type=toggle comment=quant_rounded[2]:0->1 hier=vibration_core
+000308  point: type=toggle comment=quant_rounded[2]:1->0 hier=vibration_core
+000264  point: type=toggle comment=quant_rounded[3]:0->1 hier=vibration_core
+000264  point: type=toggle comment=quant_rounded[3]:1->0 hier=vibration_core
+000268  point: type=toggle comment=quant_rounded[4]:0->1 hier=vibration_core
+000268  point: type=toggle comment=quant_rounded[4]:1->0 hier=vibration_core
+000231  point: type=toggle comment=quant_rounded[5]:0->1 hier=vibration_core
+000231  point: type=toggle comment=quant_rounded[5]:1->0 hier=vibration_core
+000224  point: type=toggle comment=quant_rounded[6]:0->1 hier=vibration_core
+000224  point: type=toggle comment=quant_rounded[6]:1->0 hier=vibration_core
+000002  point: type=toggle comment=quant_rounded[7]:0->1 hier=vibration_core
+000002  point: type=toggle comment=quant_rounded[7]:1->0 hier=vibration_core
+93243823  point: type=expr comment=(quant_guard==0) => 0 hier=vibration_core
+007560  point: type=expr comment=(quant_guard==1 && quant_sticky==1) => 1 hier=vibration_core
+004650  point: type=expr comment=(quant_guard==1 && quant_work[0]==1) => 1 hier=vibration_core
+88737345  point: type=expr comment=(quant_sticky==0 && quant_work[0]==0) => 0 hier=vibration_core
~91709098     wire [7:0] quant_result = ((|quant_work[32:7]) || quant_rounded[7]) ? 8'd127 : quant_rounded;
+000251  point: type=toggle comment=quant_result[0]:0->1 hier=vibration_core
+000251  point: type=toggle comment=quant_result[0]:1->0 hier=vibration_core
+000180  point: type=toggle comment=quant_result[1]:0->1 hier=vibration_core
+000180  point: type=toggle comment=quant_result[1]:1->0 hier=vibration_core
+000165  point: type=toggle comment=quant_result[2]:0->1 hier=vibration_core
+000165  point: type=toggle comment=quant_result[2]:1->0 hier=vibration_core
+000150  point: type=toggle comment=quant_result[3]:0->1 hier=vibration_core
+000150  point: type=toggle comment=quant_result[3]:1->0 hier=vibration_core
+000132  point: type=toggle comment=quant_result[4]:0->1 hier=vibration_core
+000132  point: type=toggle comment=quant_result[4]:1->0 hier=vibration_core
+000122  point: type=toggle comment=quant_result[5]:0->1 hier=vibration_core
+000122  point: type=toggle comment=quant_result[5]:1->0 hier=vibration_core
+000083  point: type=toggle comment=quant_result[6]:0->1 hier=vibration_core
+000083  point: type=toggle comment=quant_result[6]:1->0 hier=vibration_core
-000000  point: type=toggle comment=quant_result[7]:0->1 hier=vibration_core
-000000  point: type=toggle comment=quant_result[7]:1->0 hier=vibration_core
+000020  point: type=expr comment=(quant_rounded[7]==1) => 1 hier=vibration_core
+91709098  point: type=expr comment=(quant_work[32:7][0]==0 && quant_work[32:7][1]==0 && quant_work[32:7][2]==0 && quant_work[32:7][3]==0 && quant_work[32:7][4]==0 && quant_work[32:7][5]==0 && quant_work[32:7][6]==0 && quant_work[32:7][7]==0 && quant_work[32:7][8]==0 && quant_work[32:7][9]==0 && quant_work[32:7][10]==0 && quant_work[32:7][11]==0 && quant_work[32:7][12]==0 && quant_work[32:7][13]==0 && quant_work[32:7][14]==0 && quant_work[32:7][15]==0 && quant_work[32:7][16]==0 && quant_work[32:7][17]==0 && quant_work[32:7][18]==0 && quant_work[32:7][19]==0 && quant_work[32:7][20]==0 && quant_work[32:7][21]==0 && quant_work[32:7][22]==0 && quant_work[32:7][23]==0 && quant_work[32:7][24]==0 && quant_work[32:7][25]==0 && quant_rounded[7]==0) => 0 hier=vibration_core
+1541090  point: type=expr comment=(quant_work[32:7][0]==1) => 1 hier=vibration_core
+1537245  point: type=expr comment=(quant_work[32:7][10]==1) => 1 hier=vibration_core
+000460  point: type=expr comment=(quant_work[32:7][11]==1) => 1 hier=vibration_core
+000180  point: type=expr comment=(quant_work[32:7][12]==1) => 1 hier=vibration_core
+000235  point: type=expr comment=(quant_work[32:7][13]==1) => 1 hier=vibration_core
+000160  point: type=expr comment=(quant_work[32:7][14]==1) => 1 hier=vibration_core
+000155  point: type=expr comment=(quant_work[32:7][15]==1) => 1 hier=vibration_core
+000015  point: type=expr comment=(quant_work[32:7][16]==1) => 1 hier=vibration_core
+000005  point: type=expr comment=(quant_work[32:7][17]==1) => 1 hier=vibration_core
+000005  point: type=expr comment=(quant_work[32:7][18]==1) => 1 hier=vibration_core
-000000  point: type=expr comment=(quant_work[32:7][19]==1) => 1 hier=vibration_core
+1541665  point: type=expr comment=(quant_work[32:7][1]==1) => 1 hier=vibration_core
-000000  point: type=expr comment=(quant_work[32:7][20]==1) => 1 hier=vibration_core
-000000  point: type=expr comment=(quant_work[32:7][21]==1) => 1 hier=vibration_core
-000000  point: type=expr comment=(quant_work[32:7][22]==1) => 1 hier=vibration_core
-000000  point: type=expr comment=(quant_work[32:7][23]==1) => 1 hier=vibration_core
-000000  point: type=expr comment=(quant_work[32:7][24]==1) => 1 hier=vibration_core
-000000  point: type=expr comment=(quant_work[32:7][25]==1) => 1 hier=vibration_core
+1538944  point: type=expr comment=(quant_work[32:7][2]==1) => 1 hier=vibration_core
+1539694  point: type=expr comment=(quant_work[32:7][3]==1) => 1 hier=vibration_core
+1538889  point: type=expr comment=(quant_work[32:7][4]==1) => 1 hier=vibration_core
+1537985  point: type=expr comment=(quant_work[32:7][5]==1) => 1 hier=vibration_core
+1540004  point: type=expr comment=(quant_work[32:7][6]==1) => 1 hier=vibration_core
+001745  point: type=expr comment=(quant_work[32:7][7]==1) => 1 hier=vibration_core
+001961  point: type=expr comment=(quant_work[32:7][8]==1) => 1 hier=vibration_core
+000975  point: type=expr comment=(quant_work[32:7][9]==1) => 1 hier=vibration_core
+1545340  point: type=branch comment=cond_then hier=vibration_core
+91709098  point: type=branch comment=cond_else hier=vibration_core
 000058     reg nn_layer;
+000058  point: type=toggle comment=nn_layer:0->1 hier=vibration_core
+000056  point: type=toggle comment=nn_layer:1->0 hier=vibration_core
 000522     reg [3:0] nn_group;
+000522  point: type=toggle comment=nn_group[0]:0->1 hier=vibration_core
+000522  point: type=toggle comment=nn_group[0]:1->0 hier=vibration_core
+000290  point: type=toggle comment=nn_group[1]:0->1 hier=vibration_core
+000288  point: type=toggle comment=nn_group[1]:1->0 hier=vibration_core
+000116  point: type=toggle comment=nn_group[2]:0->1 hier=vibration_core
+000116  point: type=toggle comment=nn_group[2]:1->0 hier=vibration_core
+000058  point: type=toggle comment=nn_group[3]:0->1 hier=vibration_core
+000058  point: type=toggle comment=nn_group[3]:1->0 hier=vibration_core
 008816     reg [3:0] nn_input;
+008816  point: type=toggle comment=nn_input[0]:0->1 hier=vibration_core
+008814  point: type=toggle comment=nn_input[0]:1->0 hier=vibration_core
+004408  point: type=toggle comment=nn_input[1]:0->1 hier=vibration_core
+004406  point: type=toggle comment=nn_input[1]:1->0 hier=vibration_core
+002204  point: type=toggle comment=nn_input[2]:0->1 hier=vibration_core
+002202  point: type=toggle comment=nn_input[2]:1->0 hier=vibration_core
+001102  point: type=toggle comment=nn_input[3]:0->1 hier=vibration_core
+001100  point: type=toggle comment=nn_input[3]:1->0 hier=vibration_core
~001678     reg [7:0] activation_q;
+001678  point: type=toggle comment=activation_q[0]:0->1 hier=vibration_core
+001678  point: type=toggle comment=activation_q[0]:1->0 hier=vibration_core
+001381  point: type=toggle comment=activation_q[1]:0->1 hier=vibration_core
+001381  point: type=toggle comment=activation_q[1]:1->0 hier=vibration_core
+001512  point: type=toggle comment=activation_q[2]:0->1 hier=vibration_core
+001512  point: type=toggle comment=activation_q[2]:1->0 hier=vibration_core
+001172  point: type=toggle comment=activation_q[3]:0->1 hier=vibration_core
+001172  point: type=toggle comment=activation_q[3]:1->0 hier=vibration_core
+000874  point: type=toggle comment=activation_q[4]:0->1 hier=vibration_core
+000874  point: type=toggle comment=activation_q[4]:1->0 hier=vibration_core
+000683  point: type=toggle comment=activation_q[5]:0->1 hier=vibration_core
+000683  point: type=toggle comment=activation_q[5]:1->0 hier=vibration_core
+000637  point: type=toggle comment=activation_q[6]:0->1 hier=vibration_core
+000637  point: type=toggle comment=activation_q[6]:1->0 hier=vibration_core
-000000  point: type=toggle comment=activation_q[7]:0->1 hier=vibration_core
-000000  point: type=toggle comment=activation_q[7]:1->0 hier=vibration_core
 000028     reg signed [31:0] logits [0:2];
+000008  point: type=toggle comment=logits[0][0]:0->1 hier=vibration_core
+000008  point: type=toggle comment=logits[0][0]:1->0 hier=vibration_core
+000024  point: type=toggle comment=logits[0][10]:0->1 hier=vibration_core
+000022  point: type=toggle comment=logits[0][10]:1->0 hier=vibration_core
+000025  point: type=toggle comment=logits[0][11]:0->1 hier=vibration_core
+000023  point: type=toggle comment=logits[0][11]:1->0 hier=vibration_core
+000027  point: type=toggle comment=logits[0][12]:0->1 hier=vibration_core
+000025  point: type=toggle comment=logits[0][12]:1->0 hier=vibration_core
+000026  point: type=toggle comment=logits[0][13]:0->1 hier=vibration_core
+000024  point: type=toggle comment=logits[0][13]:1->0 hier=vibration_core
+000025  point: type=toggle comment=logits[0][14]:0->1 hier=vibration_core
+000023  point: type=toggle comment=logits[0][14]:1->0 hier=vibration_core
+000026  point: type=toggle comment=logits[0][15]:0->1 hier=vibration_core
+000024  point: type=toggle comment=logits[0][15]:1->0 hier=vibration_core
+000026  point: type=toggle comment=logits[0][16]:0->1 hier=vibration_core
+000024  point: type=toggle comment=logits[0][16]:1->0 hier=vibration_core
+000026  point: type=toggle comment=logits[0][17]:0->1 hier=vibration_core
+000024  point: type=toggle comment=logits[0][17]:1->0 hier=vibration_core
+000026  point: type=toggle comment=logits[0][18]:0->1 hier=vibration_core
+000024  point: type=toggle comment=logits[0][18]:1->0 hier=vibration_core
+000026  point: type=toggle comment=logits[0][19]:0->1 hier=vibration_core
+000024  point: type=toggle comment=logits[0][19]:1->0 hier=vibration_core
+000022  point: type=toggle comment=logits[0][1]:0->1 hier=vibration_core
+000020  point: type=toggle comment=logits[0][1]:1->0 hier=vibration_core
+000026  point: type=toggle comment=logits[0][20]:0->1 hier=vibration_core
+000024  point: type=toggle comment=logits[0][20]:1->0 hier=vibration_core
+000026  point: type=toggle comment=logits[0][21]:0->1 hier=vibration_core
+000024  point: type=toggle comment=logits[0][21]:1->0 hier=vibration_core
+000026  point: type=toggle comment=logits[0][22]:0->1 hier=vibration_core
+000024  point: type=toggle comment=logits[0][22]:1->0 hier=vibration_core
+000026  point: type=toggle comment=logits[0][23]:0->1 hier=vibration_core
+000024  point: type=toggle comment=logits[0][23]:1->0 hier=vibration_core
+000026  point: type=toggle comment=logits[0][24]:0->1 hier=vibration_core
+000024  point: type=toggle comment=logits[0][24]:1->0 hier=vibration_core
+000026  point: type=toggle comment=logits[0][25]:0->1 hier=vibration_core
+000024  point: type=toggle comment=logits[0][25]:1->0 hier=vibration_core
+000026  point: type=toggle comment=logits[0][26]:0->1 hier=vibration_core
+000024  point: type=toggle comment=logits[0][26]:1->0 hier=vibration_core
+000026  point: type=toggle comment=logits[0][27]:0->1 hier=vibration_core
+000024  point: type=toggle comment=logits[0][27]:1->0 hier=vibration_core
+000026  point: type=toggle comment=logits[0][28]:0->1 hier=vibration_core
+000024  point: type=toggle comment=logits[0][28]:1->0 hier=vibration_core
+000026  point: type=toggle comment=logits[0][29]:0->1 hier=vibration_core
+000024  point: type=toggle comment=logits[0][29]:1->0 hier=vibration_core
+000026  point: type=toggle comment=logits[0][2]:0->1 hier=vibration_core
+000024  point: type=toggle comment=logits[0][2]:1->0 hier=vibration_core
+000026  point: type=toggle comment=logits[0][30]:0->1 hier=vibration_core
+000024  point: type=toggle comment=logits[0][30]:1->0 hier=vibration_core
+000026  point: type=toggle comment=logits[0][31]:0->1 hier=vibration_core
+000024  point: type=toggle comment=logits[0][31]:1->0 hier=vibration_core
+000005  point: type=toggle comment=logits[0][3]:0->1 hier=vibration_core
+000005  point: type=toggle comment=logits[0][3]:1->0 hier=vibration_core
+000024  point: type=toggle comment=logits[0][4]:0->1 hier=vibration_core
+000022  point: type=toggle comment=logits[0][4]:1->0 hier=vibration_core
+000004  point: type=toggle comment=logits[0][5]:0->1 hier=vibration_core
+000004  point: type=toggle comment=logits[0][5]:1->0 hier=vibration_core
+000006  point: type=toggle comment=logits[0][6]:0->1 hier=vibration_core
+000006  point: type=toggle comment=logits[0][6]:1->0 hier=vibration_core
+000028  point: type=toggle comment=logits[0][7]:0->1 hier=vibration_core
+000026  point: type=toggle comment=logits[0][7]:1->0 hier=vibration_core
+000006  point: type=toggle comment=logits[0][8]:0->1 hier=vibration_core
+000006  point: type=toggle comment=logits[0][8]:1->0 hier=vibration_core
+000015  point: type=toggle comment=logits[0][9]:0->1 hier=vibration_core
+000015  point: type=toggle comment=logits[0][9]:1->0 hier=vibration_core
+000026  point: type=toggle comment=logits[1][0]:0->1 hier=vibration_core
+000024  point: type=toggle comment=logits[1][0]:1->0 hier=vibration_core
+000026  point: type=toggle comment=logits[1][10]:0->1 hier=vibration_core
+000024  point: type=toggle comment=logits[1][10]:1->0 hier=vibration_core
+000025  point: type=toggle comment=logits[1][11]:0->1 hier=vibration_core
+000023  point: type=toggle comment=logits[1][11]:1->0 hier=vibration_core
+000025  point: type=toggle comment=logits[1][12]:0->1 hier=vibration_core
+000023  point: type=toggle comment=logits[1][12]:1->0 hier=vibration_core
+000026  point: type=toggle comment=logits[1][13]:0->1 hier=vibration_core
+000024  point: type=toggle comment=logits[1][13]:1->0 hier=vibration_core
+000026  point: type=toggle comment=logits[1][14]:0->1 hier=vibration_core
+000024  point: type=toggle comment=logits[1][14]:1->0 hier=vibration_core
+000026  point: type=toggle comment=logits[1][15]:0->1 hier=vibration_core
+000024  point: type=toggle comment=logits[1][15]:1->0 hier=vibration_core
+000026  point: type=toggle comment=logits[1][16]:0->1 hier=vibration_core
+000024  point: type=toggle comment=logits[1][16]:1->0 hier=vibration_core
+000026  point: type=toggle comment=logits[1][17]:0->1 hier=vibration_core
+000024  point: type=toggle comment=logits[1][17]:1->0 hier=vibration_core
+000026  point: type=toggle comment=logits[1][18]:0->1 hier=vibration_core
+000024  point: type=toggle comment=logits[1][18]:1->0 hier=vibration_core
+000026  point: type=toggle comment=logits[1][19]:0->1 hier=vibration_core
+000024  point: type=toggle comment=logits[1][19]:1->0 hier=vibration_core
+000007  point: type=toggle comment=logits[1][1]:0->1 hier=vibration_core
+000007  point: type=toggle comment=logits[1][1]:1->0 hier=vibration_core
+000026  point: type=toggle comment=logits[1][20]:0->1 hier=vibration_core
+000024  point: type=toggle comment=logits[1][20]:1->0 hier=vibration_core
+000026  point: type=toggle comment=logits[1][21]:0->1 hier=vibration_core
+000024  point: type=toggle comment=logits[1][21]:1->0 hier=vibration_core
+000026  point: type=toggle comment=logits[1][22]:0->1 hier=vibration_core
+000024  point: type=toggle comment=logits[1][22]:1->0 hier=vibration_core
+000026  point: type=toggle comment=logits[1][23]:0->1 hier=vibration_core
+000024  point: type=toggle comment=logits[1][23]:1->0 hier=vibration_core
+000026  point: type=toggle comment=logits[1][24]:0->1 hier=vibration_core
+000024  point: type=toggle comment=logits[1][24]:1->0 hier=vibration_core
+000026  point: type=toggle comment=logits[1][25]:0->1 hier=vibration_core
+000024  point: type=toggle comment=logits[1][25]:1->0 hier=vibration_core
+000026  point: type=toggle comment=logits[1][26]:0->1 hier=vibration_core
+000024  point: type=toggle comment=logits[1][26]:1->0 hier=vibration_core
+000026  point: type=toggle comment=logits[1][27]:0->1 hier=vibration_core
+000024  point: type=toggle comment=logits[1][27]:1->0 hier=vibration_core
+000026  point: type=toggle comment=logits[1][28]:0->1 hier=vibration_core
+000024  point: type=toggle comment=logits[1][28]:1->0 hier=vibration_core
+000026  point: type=toggle comment=logits[1][29]:0->1 hier=vibration_core
+000024  point: type=toggle comment=logits[1][29]:1->0 hier=vibration_core
+000013  point: type=toggle comment=logits[1][2]:0->1 hier=vibration_core
+000013  point: type=toggle comment=logits[1][2]:1->0 hier=vibration_core
+000026  point: type=toggle comment=logits[1][30]:0->1 hier=vibration_core
+000024  point: type=toggle comment=logits[1][30]:1->0 hier=vibration_core
+000026  point: type=toggle comment=logits[1][31]:0->1 hier=vibration_core
+000024  point: type=toggle comment=logits[1][31]:1->0 hier=vibration_core
+000027  point: type=toggle comment=logits[1][3]:0->1 hier=vibration_core
+000025  point: type=toggle comment=logits[1][3]:1->0 hier=vibration_core
+000015  point: type=toggle comment=logits[1][4]:0->1 hier=vibration_core
+000015  point: type=toggle comment=logits[1][4]:1->0 hier=vibration_core
+000028  point: type=toggle comment=logits[1][5]:0->1 hier=vibration_core
+000026  point: type=toggle comment=logits[1][5]:1->0 hier=vibration_core
+000003  point: type=toggle comment=logits[1][6]:0->1 hier=vibration_core
+000003  point: type=toggle comment=logits[1][6]:1->0 hier=vibration_core
+000003  point: type=toggle comment=logits[1][7]:0->1 hier=vibration_core
+000003  point: type=toggle comment=logits[1][7]:1->0 hier=vibration_core
+000028  point: type=toggle comment=logits[1][8]:0->1 hier=vibration_core
+000026  point: type=toggle comment=logits[1][8]:1->0 hier=vibration_core
+000003  point: type=toggle comment=logits[1][9]:0->1 hier=vibration_core
+000003  point: type=toggle comment=logits[1][9]:1->0 hier=vibration_core
+000026  point: type=toggle comment=logits[2][0]:0->1 hier=vibration_core
+000024  point: type=toggle comment=logits[2][0]:1->0 hier=vibration_core
+000026  point: type=toggle comment=logits[2][10]:0->1 hier=vibration_core
+000024  point: type=toggle comment=logits[2][10]:1->0 hier=vibration_core
+000025  point: type=toggle comment=logits[2][11]:0->1 hier=vibration_core
+000023  point: type=toggle comment=logits[2][11]:1->0 hier=vibration_core
+000022  point: type=toggle comment=logits[2][12]:0->1 hier=vibration_core
+000020  point: type=toggle comment=logits[2][12]:1->0 hier=vibration_core
+000026  point: type=toggle comment=logits[2][13]:0->1 hier=vibration_core
+000024  point: type=toggle comment=logits[2][13]:1->0 hier=vibration_core
+000026  point: type=toggle comment=logits[2][14]:0->1 hier=vibration_core
+000024  point: type=toggle comment=logits[2][14]:1->0 hier=vibration_core
+000024  point: type=toggle comment=logits[2][15]:0->1 hier=vibration_core
+000022  point: type=toggle comment=logits[2][15]:1->0 hier=vibration_core
+000026  point: type=toggle comment=logits[2][16]:0->1 hier=vibration_core
+000024  point: type=toggle comment=logits[2][16]:1->0 hier=vibration_core
+000026  point: type=toggle comment=logits[2][17]:0->1 hier=vibration_core
+000024  point: type=toggle comment=logits[2][17]:1->0 hier=vibration_core
+000026  point: type=toggle comment=logits[2][18]:0->1 hier=vibration_core
+000024  point: type=toggle comment=logits[2][18]:1->0 hier=vibration_core
+000026  point: type=toggle comment=logits[2][19]:0->1 hier=vibration_core
+000024  point: type=toggle comment=logits[2][19]:1->0 hier=vibration_core
+000026  point: type=toggle comment=logits[2][1]:0->1 hier=vibration_core
+000024  point: type=toggle comment=logits[2][1]:1->0 hier=vibration_core
+000026  point: type=toggle comment=logits[2][20]:0->1 hier=vibration_core
+000024  point: type=toggle comment=logits[2][20]:1->0 hier=vibration_core
+000026  point: type=toggle comment=logits[2][21]:0->1 hier=vibration_core
+000024  point: type=toggle comment=logits[2][21]:1->0 hier=vibration_core
+000026  point: type=toggle comment=logits[2][22]:0->1 hier=vibration_core
+000024  point: type=toggle comment=logits[2][22]:1->0 hier=vibration_core
+000026  point: type=toggle comment=logits[2][23]:0->1 hier=vibration_core
+000024  point: type=toggle comment=logits[2][23]:1->0 hier=vibration_core
+000026  point: type=toggle comment=logits[2][24]:0->1 hier=vibration_core
+000024  point: type=toggle comment=logits[2][24]:1->0 hier=vibration_core
+000026  point: type=toggle comment=logits[2][25]:0->1 hier=vibration_core
+000024  point: type=toggle comment=logits[2][25]:1->0 hier=vibration_core
+000026  point: type=toggle comment=logits[2][26]:0->1 hier=vibration_core
+000024  point: type=toggle comment=logits[2][26]:1->0 hier=vibration_core
+000026  point: type=toggle comment=logits[2][27]:0->1 hier=vibration_core
+000024  point: type=toggle comment=logits[2][27]:1->0 hier=vibration_core
+000026  point: type=toggle comment=logits[2][28]:0->1 hier=vibration_core
+000024  point: type=toggle comment=logits[2][28]:1->0 hier=vibration_core
+000026  point: type=toggle comment=logits[2][29]:0->1 hier=vibration_core
+000024  point: type=toggle comment=logits[2][29]:1->0 hier=vibration_core
+000003  point: type=toggle comment=logits[2][2]:0->1 hier=vibration_core
+000003  point: type=toggle comment=logits[2][2]:1->0 hier=vibration_core
+000026  point: type=toggle comment=logits[2][30]:0->1 hier=vibration_core
+000024  point: type=toggle comment=logits[2][30]:1->0 hier=vibration_core
+000026  point: type=toggle comment=logits[2][31]:0->1 hier=vibration_core
+000024  point: type=toggle comment=logits[2][31]:1->0 hier=vibration_core
+000026  point: type=toggle comment=logits[2][3]:0->1 hier=vibration_core
+000024  point: type=toggle comment=logits[2][3]:1->0 hier=vibration_core
+000025  point: type=toggle comment=logits[2][4]:0->1 hier=vibration_core
+000023  point: type=toggle comment=logits[2][4]:1->0 hier=vibration_core
+000013  point: type=toggle comment=logits[2][5]:0->1 hier=vibration_core
+000013  point: type=toggle comment=logits[2][5]:1->0 hier=vibration_core
+000024  point: type=toggle comment=logits[2][6]:0->1 hier=vibration_core
+000022  point: type=toggle comment=logits[2][6]:1->0 hier=vibration_core
+000027  point: type=toggle comment=logits[2][7]:0->1 hier=vibration_core
+000025  point: type=toggle comment=logits[2][7]:1->0 hier=vibration_core
+000024  point: type=toggle comment=logits[2][8]:0->1 hier=vibration_core
+000022  point: type=toggle comment=logits[2][8]:1->0 hier=vibration_core
+000007  point: type=toggle comment=logits[2][9]:0->1 hier=vibration_core
+000007  point: type=toggle comment=logits[2][9]:1->0 hier=vibration_core
%000000     reg [7:0] arithmetic_errors;
-000000  point: type=toggle comment=arithmetic_errors[0]:0->1 hier=vibration_core
-000000  point: type=toggle comment=arithmetic_errors[0]:1->0 hier=vibration_core
-000000  point: type=toggle comment=arithmetic_errors[1]:0->1 hier=vibration_core
-000000  point: type=toggle comment=arithmetic_errors[1]:1->0 hier=vibration_core
-000000  point: type=toggle comment=arithmetic_errors[2]:0->1 hier=vibration_core
-000000  point: type=toggle comment=arithmetic_errors[2]:1->0 hier=vibration_core
-000000  point: type=toggle comment=arithmetic_errors[3]:0->1 hier=vibration_core
-000000  point: type=toggle comment=arithmetic_errors[3]:1->0 hier=vibration_core
-000000  point: type=toggle comment=arithmetic_errors[4]:0->1 hier=vibration_core
-000000  point: type=toggle comment=arithmetic_errors[4]:1->0 hier=vibration_core
-000000  point: type=toggle comment=arithmetic_errors[5]:0->1 hier=vibration_core
-000000  point: type=toggle comment=arithmetic_errors[5]:1->0 hier=vibration_core
-000000  point: type=toggle comment=arithmetic_errors[6]:0->1 hier=vibration_core
-000000  point: type=toggle comment=arithmetic_errors[6]:1->0 hier=vibration_core
-000000  point: type=toggle comment=arithmetic_errors[7]:0->1 hier=vibration_core
-000000  point: type=toggle comment=arithmetic_errors[7]:1->0 hier=vibration_core
 101448     reg [PRE_W-1:0] count_pre;
+101448  point: type=toggle comment=count_pre[0]:0->1 hier=vibration_core
+101446  point: type=toggle comment=count_pre[0]:1->0 hier=vibration_core
+000132  point: type=toggle comment=count_pre[10]:0->1 hier=vibration_core
+000130  point: type=toggle comment=count_pre[10]:1->0 hier=vibration_core
+000066  point: type=toggle comment=count_pre[11]:0->1 hier=vibration_core
+000064  point: type=toggle comment=count_pre[11]:1->0 hier=vibration_core
+050690  point: type=toggle comment=count_pre[1]:0->1 hier=vibration_core
+050690  point: type=toggle comment=count_pre[1]:1->0 hier=vibration_core
+025344  point: type=toggle comment=count_pre[2]:0->1 hier=vibration_core
+025344  point: type=toggle comment=count_pre[2]:1->0 hier=vibration_core
+012672  point: type=toggle comment=count_pre[3]:0->1 hier=vibration_core
+012672  point: type=toggle comment=count_pre[3]:1->0 hier=vibration_core
+006336  point: type=toggle comment=count_pre[4]:0->1 hier=vibration_core
+006336  point: type=toggle comment=count_pre[4]:1->0 hier=vibration_core
+003168  point: type=toggle comment=count_pre[5]:0->1 hier=vibration_core
+003168  point: type=toggle comment=count_pre[5]:1->0 hier=vibration_core
+001584  point: type=toggle comment=count_pre[6]:0->1 hier=vibration_core
+001584  point: type=toggle comment=count_pre[6]:1->0 hier=vibration_core
+000792  point: type=toggle comment=count_pre[7]:0->1 hier=vibration_core
+000792  point: type=toggle comment=count_pre[7]:1->0 hier=vibration_core
+000396  point: type=toggle comment=count_pre[8]:0->1 hier=vibration_core
+000396  point: type=toggle comment=count_pre[8]:1->0 hier=vibration_core
+000198  point: type=toggle comment=count_pre[9]:0->1 hier=vibration_core
+000198  point: type=toggle comment=count_pre[9]:1->0 hier=vibration_core
 9148256     reg [DFT_W-1:0] count_dft;
+9148256  point: type=toggle comment=count_dft[0]:0->1 hier=vibration_core
+9148256  point: type=toggle comment=count_dft[0]:1->0 hier=vibration_core
+008928  point: type=toggle comment=count_dft[10]:0->1 hier=vibration_core
+008928  point: type=toggle comment=count_dft[10]:1->0 hier=vibration_core
+004464  point: type=toggle comment=count_dft[11]:0->1 hier=vibration_core
+004464  point: type=toggle comment=count_dft[11]:1->0 hier=vibration_core
+002232  point: type=toggle comment=count_dft[12]:0->1 hier=vibration_core
+002232  point: type=toggle comment=count_dft[12]:1->0 hier=vibration_core
+001116  point: type=toggle comment=count_dft[13]:0->1 hier=vibration_core
+001116  point: type=toggle comment=count_dft[13]:1->0 hier=vibration_core
+000558  point: type=toggle comment=count_dft[14]:0->1 hier=vibration_core
+000558  point: type=toggle comment=count_dft[14]:1->0 hier=vibration_core
+000310  point: type=toggle comment=count_dft[15]:0->1 hier=vibration_core
+000308  point: type=toggle comment=count_dft[15]:1->0 hier=vibration_core
+000124  point: type=toggle comment=count_dft[16]:0->1 hier=vibration_core
+000124  point: type=toggle comment=count_dft[16]:1->0 hier=vibration_core
+000062  point: type=toggle comment=count_dft[17]:0->1 hier=vibration_core
+000062  point: type=toggle comment=count_dft[17]:1->0 hier=vibration_core
+000062  point: type=toggle comment=count_dft[18]:0->1 hier=vibration_core
+000060  point: type=toggle comment=count_dft[18]:1->0 hier=vibration_core
+4574128  point: type=toggle comment=count_dft[1]:0->1 hier=vibration_core
+4574128  point: type=toggle comment=count_dft[1]:1->0 hier=vibration_core
+2287064  point: type=toggle comment=count_dft[2]:0->1 hier=vibration_core
+2287064  point: type=toggle comment=count_dft[2]:1->0 hier=vibration_core
+1143532  point: type=toggle comment=count_dft[3]:0->1 hier=vibration_core
+1143532  point: type=toggle comment=count_dft[3]:1->0 hier=vibration_core
+571766  point: type=toggle comment=count_dft[4]:0->1 hier=vibration_core
+571766  point: type=toggle comment=count_dft[4]:1->0 hier=vibration_core
+285882  point: type=toggle comment=count_dft[5]:0->1 hier=vibration_core
+285882  point: type=toggle comment=count_dft[5]:1->0 hier=vibration_core
+142972  point: type=toggle comment=count_dft[6]:0->1 hier=vibration_core
+142970  point: type=toggle comment=count_dft[6]:1->0 hier=vibration_core
+071486  point: type=toggle comment=count_dft[7]:0->1 hier=vibration_core
+071484  point: type=toggle comment=count_dft[7]:1->0 hier=vibration_core
+035712  point: type=toggle comment=count_dft[8]:0->1 hier=vibration_core
+035712  point: type=toggle comment=count_dft[8]:1->0 hier=vibration_core
+017856  point: type=toggle comment=count_dft[9]:0->1 hier=vibration_core
+017856  point: type=toggle comment=count_dft[9]:1->0 hier=vibration_core
~008534     reg [POWER_W-1:0] count_power;
+008534  point: type=toggle comment=count_power[0]:0->1 hier=vibration_core
+008534  point: type=toggle comment=count_power[0]:1->0 hier=vibration_core
+004266  point: type=toggle comment=count_power[1]:0->1 hier=vibration_core
+004266  point: type=toggle comment=count_power[1]:1->0 hier=vibration_core
+002164  point: type=toggle comment=count_power[2]:0->1 hier=vibration_core
+002162  point: type=toggle comment=count_power[2]:1->0 hier=vibration_core
+001082  point: type=toggle comment=count_power[3]:0->1 hier=vibration_core
+001080  point: type=toggle comment=count_power[3]:1->0 hier=vibration_core
+000540  point: type=toggle comment=count_power[4]:0->1 hier=vibration_core
+000538  point: type=toggle comment=count_power[4]:1->0 hier=vibration_core
+000240  point: type=toggle comment=count_power[5]:0->1 hier=vibration_core
+000240  point: type=toggle comment=count_power[5]:1->0 hier=vibration_core
+000120  point: type=toggle comment=count_power[6]:0->1 hier=vibration_core
+000120  point: type=toggle comment=count_power[6]:1->0 hier=vibration_core
+000060  point: type=toggle comment=count_power[7]:0->1 hier=vibration_core
+000060  point: type=toggle comment=count_power[7]:1->0 hier=vibration_core
+000060  point: type=toggle comment=count_power[8]:0->1 hier=vibration_core
+000058  point: type=toggle comment=count_power[8]:1->0 hier=vibration_core
-000000  point: type=toggle comment=count_power[9]:0->1 hier=vibration_core
-000000  point: type=toggle comment=count_power[9]:1->0 hier=vibration_core
 027554     reg [NN_W-1:0] count_nn;
+027554  point: type=toggle comment=count_nn[0]:0->1 hier=vibration_core
+027554  point: type=toggle comment=count_nn[0]:1->0 hier=vibration_core
+013806  point: type=toggle comment=count_nn[1]:0->1 hier=vibration_core
+013804  point: type=toggle comment=count_nn[1]:1->0 hier=vibration_core
+006902  point: type=toggle comment=count_nn[2]:0->1 hier=vibration_core
+006900  point: type=toggle comment=count_nn[2]:1->0 hier=vibration_core
+003422  point: type=toggle comment=count_nn[3]:0->1 hier=vibration_core
+003422  point: type=toggle comment=count_nn[3]:1->0 hier=vibration_core
+001740  point: type=toggle comment=count_nn[4]:0->1 hier=vibration_core
+001738  point: type=toggle comment=count_nn[4]:1->0 hier=vibration_core
+000870  point: type=toggle comment=count_nn[5]:0->1 hier=vibration_core
+000868  point: type=toggle comment=count_nn[5]:1->0 hier=vibration_core
+000406  point: type=toggle comment=count_nn[6]:0->1 hier=vibration_core
+000406  point: type=toggle comment=count_nn[6]:1->0 hier=vibration_core
+000232  point: type=toggle comment=count_nn[7]:0->1 hier=vibration_core
+000230  point: type=toggle comment=count_nn[7]:1->0 hier=vibration_core
+000116  point: type=toggle comment=count_nn[8]:0->1 hier=vibration_core
+000114  point: type=toggle comment=count_nn[8]:1->0 hier=vibration_core
+000058  point: type=toggle comment=count_nn[9]:0->1 hier=vibration_core
+000056  point: type=toggle comment=count_nn[9]:1->0 hier=vibration_core
 9285786     reg [TOTAL_W-1:0] count_total;
+9285786  point: type=toggle comment=count_total[0]:0->1 hier=vibration_core
+9285784  point: type=toggle comment=count_total[0]:1->0 hier=vibration_core
+009060  point: type=toggle comment=count_total[10]:0->1 hier=vibration_core
+009060  point: type=toggle comment=count_total[10]:1->0 hier=vibration_core
+004530  point: type=toggle comment=count_total[11]:0->1 hier=vibration_core
+004530  point: type=toggle comment=count_total[11]:1->0 hier=vibration_core
+002290  point: type=toggle comment=count_total[12]:0->1 hier=vibration_core
+002288  point: type=toggle comment=count_total[12]:1->0 hier=vibration_core
+001116  point: type=toggle comment=count_total[13]:0->1 hier=vibration_core
+001116  point: type=toggle comment=count_total[13]:1->0 hier=vibration_core
+000558  point: type=toggle comment=count_total[14]:0->1 hier=vibration_core
+000558  point: type=toggle comment=count_total[14]:1->0 hier=vibration_core
+000310  point: type=toggle comment=count_total[15]:0->1 hier=vibration_core
+000308  point: type=toggle comment=count_total[15]:1->0 hier=vibration_core
+000124  point: type=toggle comment=count_total[16]:0->1 hier=vibration_core
+000124  point: type=toggle comment=count_total[16]:1->0 hier=vibration_core
+000062  point: type=toggle comment=count_total[17]:0->1 hier=vibration_core
+000062  point: type=toggle comment=count_total[17]:1->0 hier=vibration_core
+000062  point: type=toggle comment=count_total[18]:0->1 hier=vibration_core
+000060  point: type=toggle comment=count_total[18]:1->0 hier=vibration_core
+4642892  point: type=toggle comment=count_total[1]:0->1 hier=vibration_core
+4642890  point: type=toggle comment=count_total[1]:1->0 hier=vibration_core
+2321418  point: type=toggle comment=count_total[2]:0->1 hier=vibration_core
+2321418  point: type=toggle comment=count_total[2]:1->0 hier=vibration_core
+1160708  point: type=toggle comment=count_total[3]:0->1 hier=vibration_core
+1160708  point: type=toggle comment=count_total[3]:1->0 hier=vibration_core
+580382  point: type=toggle comment=count_total[4]:0->1 hier=vibration_core
+580380  point: type=toggle comment=count_total[4]:1->0 hier=vibration_core
+290162  point: type=toggle comment=count_total[5]:0->1 hier=vibration_core
+290162  point: type=toggle comment=count_total[5]:1->0 hier=vibration_core
+145082  point: type=toggle comment=count_total[6]:0->1 hier=vibration_core
+145082  point: type=toggle comment=count_total[6]:1->0 hier=vibration_core
+072570  point: type=toggle comment=count_total[7]:0->1 hier=vibration_core
+072568  point: type=toggle comment=count_total[7]:1->0 hier=vibration_core
+036284  point: type=toggle comment=count_total[8]:0->1 hier=vibration_core
+036282  point: type=toggle comment=count_total[8]:1->0 hier=vibration_core
+018112  point: type=toggle comment=count_total[9]:0->1 hier=vibration_core
+018112  point: type=toggle comment=count_total[9]:1->0 hier=vibration_core
        
 3209044     reg signed [15:0] operand_a [0:LANES-1], operand_b [0:LANES-1];
+2402173  point: type=toggle comment=operand_a[0][0]:0->1 hier=vibration_core
+2402173  point: type=toggle comment=operand_a[0][0]:1->0 hier=vibration_core
+2341992  point: type=toggle comment=operand_a[0][10]:0->1 hier=vibration_core
+2341992  point: type=toggle comment=operand_a[0][10]:1->0 hier=vibration_core
+2340296  point: type=toggle comment=operand_a[0][11]:0->1 hier=vibration_core
+2340296  point: type=toggle comment=operand_a[0][11]:1->0 hier=vibration_core
+2340296  point: type=toggle comment=operand_a[0][12]:0->1 hier=vibration_core
+2340296  point: type=toggle comment=operand_a[0][12]:1->0 hier=vibration_core
+2340295  point: type=toggle comment=operand_a[0][13]:0->1 hier=vibration_core
+2340295  point: type=toggle comment=operand_a[0][13]:1->0 hier=vibration_core
+2340295  point: type=toggle comment=operand_a[0][14]:0->1 hier=vibration_core
+2340295  point: type=toggle comment=operand_a[0][14]:1->0 hier=vibration_core
+2340295  point: type=toggle comment=operand_a[0][15]:0->1 hier=vibration_core
+2340295  point: type=toggle comment=operand_a[0][15]:1->0 hier=vibration_core
+2403629  point: type=toggle comment=operand_a[0][1]:0->1 hier=vibration_core
+2403629  point: type=toggle comment=operand_a[0][1]:1->0 hier=vibration_core
+2358783  point: type=toggle comment=operand_a[0][2]:0->1 hier=vibration_core
+2358783  point: type=toggle comment=operand_a[0][2]:1->0 hier=vibration_core
+2403163  point: type=toggle comment=operand_a[0][3]:0->1 hier=vibration_core
+2403163  point: type=toggle comment=operand_a[0][3]:1->0 hier=vibration_core
+2308055  point: type=toggle comment=operand_a[0][4]:0->1 hier=vibration_core
+2308055  point: type=toggle comment=operand_a[0][4]:1->0 hier=vibration_core
+2314659  point: type=toggle comment=operand_a[0][5]:0->1 hier=vibration_core
+2314659  point: type=toggle comment=operand_a[0][5]:1->0 hier=vibration_core
+2333207  point: type=toggle comment=operand_a[0][6]:0->1 hier=vibration_core
+2333207  point: type=toggle comment=operand_a[0][6]:1->0 hier=vibration_core
+2348744  point: type=toggle comment=operand_a[0][7]:0->1 hier=vibration_core
+2348744  point: type=toggle comment=operand_a[0][7]:1->0 hier=vibration_core
+2340219  point: type=toggle comment=operand_a[0][8]:0->1 hier=vibration_core
+2340219  point: type=toggle comment=operand_a[0][8]:1->0 hier=vibration_core
+2336991  point: type=toggle comment=operand_a[0][9]:0->1 hier=vibration_core
+2336991  point: type=toggle comment=operand_a[0][9]:1->0 hier=vibration_core
+3209044  point: type=toggle comment=operand_b[0][0]:0->1 hier=vibration_core
+3209044  point: type=toggle comment=operand_b[0][0]:1->0 hier=vibration_core
+3032264  point: type=toggle comment=operand_b[0][10]:0->1 hier=vibration_core
+3032264  point: type=toggle comment=operand_b[0][10]:1->0 hier=vibration_core
+3032278  point: type=toggle comment=operand_b[0][11]:0->1 hier=vibration_core
+3032278  point: type=toggle comment=operand_b[0][11]:1->0 hier=vibration_core
+3032276  point: type=toggle comment=operand_b[0][12]:0->1 hier=vibration_core
+3032276  point: type=toggle comment=operand_b[0][12]:1->0 hier=vibration_core
+3032409  point: type=toggle comment=operand_b[0][13]:0->1 hier=vibration_core
+3032409  point: type=toggle comment=operand_b[0][13]:1->0 hier=vibration_core
+3062443  point: type=toggle comment=operand_b[0][14]:0->1 hier=vibration_core
+3062443  point: type=toggle comment=operand_b[0][14]:1->0 hier=vibration_core
+3030497  point: type=toggle comment=operand_b[0][15]:0->1 hier=vibration_core
+3030497  point: type=toggle comment=operand_b[0][15]:1->0 hier=vibration_core
+3025243  point: type=toggle comment=operand_b[0][1]:0->1 hier=vibration_core
+3025243  point: type=toggle comment=operand_b[0][1]:1->0 hier=vibration_core
+3155360  point: type=toggle comment=operand_b[0][2]:0->1 hier=vibration_core
+3155360  point: type=toggle comment=operand_b[0][2]:1->0 hier=vibration_core
+3009591  point: type=toggle comment=operand_b[0][3]:0->1 hier=vibration_core
+3009591  point: type=toggle comment=operand_b[0][3]:1->0 hier=vibration_core
+3050910  point: type=toggle comment=operand_b[0][4]:0->1 hier=vibration_core
+3050910  point: type=toggle comment=operand_b[0][4]:1->0 hier=vibration_core
+3081087  point: type=toggle comment=operand_b[0][5]:0->1 hier=vibration_core
+3081087  point: type=toggle comment=operand_b[0][5]:1->0 hier=vibration_core
+3042948  point: type=toggle comment=operand_b[0][6]:0->1 hier=vibration_core
+3042948  point: type=toggle comment=operand_b[0][6]:1->0 hier=vibration_core
+3032373  point: type=toggle comment=operand_b[0][7]:0->1 hier=vibration_core
+3032373  point: type=toggle comment=operand_b[0][7]:1->0 hier=vibration_core
+3032307  point: type=toggle comment=operand_b[0][8]:0->1 hier=vibration_core
+3032307  point: type=toggle comment=operand_b[0][8]:1->0 hier=vibration_core
+3032274  point: type=toggle comment=operand_b[0][9]:0->1 hier=vibration_core
+3032274  point: type=toggle comment=operand_b[0][9]:1->0 hier=vibration_core
 1228185     reg signed [31:0] product [0:LANES-1];
+932136  point: type=toggle comment=product[0][0]:0->1 hier=vibration_core
+932136  point: type=toggle comment=product[0][0]:1->0 hier=vibration_core
+1197087  point: type=toggle comment=product[0][10]:0->1 hier=vibration_core
+1197087  point: type=toggle comment=product[0][10]:1->0 hier=vibration_core
+1197435  point: type=toggle comment=product[0][11]:0->1 hier=vibration_core
+1197435  point: type=toggle comment=product[0][11]:1->0 hier=vibration_core
+1201506  point: type=toggle comment=product[0][12]:0->1 hier=vibration_core
+1201506  point: type=toggle comment=product[0][12]:1->0 hier=vibration_core
+1197032  point: type=toggle comment=product[0][13]:0->1 hier=vibration_core
+1197032  point: type=toggle comment=product[0][13]:1->0 hier=vibration_core
+1197961  point: type=toggle comment=product[0][14]:0->1 hier=vibration_core
+1197961  point: type=toggle comment=product[0][14]:1->0 hier=vibration_core
+1198265  point: type=toggle comment=product[0][15]:0->1 hier=vibration_core
+1198265  point: type=toggle comment=product[0][15]:1->0 hier=vibration_core
+1198092  point: type=toggle comment=product[0][16]:0->1 hier=vibration_core
+1198092  point: type=toggle comment=product[0][16]:1->0 hier=vibration_core
+1199946  point: type=toggle comment=product[0][17]:0->1 hier=vibration_core
+1199946  point: type=toggle comment=product[0][17]:1->0 hier=vibration_core
+1201551  point: type=toggle comment=product[0][18]:0->1 hier=vibration_core
+1201551  point: type=toggle comment=product[0][18]:1->0 hier=vibration_core
+1202022  point: type=toggle comment=product[0][19]:0->1 hier=vibration_core
+1202022  point: type=toggle comment=product[0][19]:1->0 hier=vibration_core
+1135384  point: type=toggle comment=product[0][1]:0->1 hier=vibration_core
+1135384  point: type=toggle comment=product[0][1]:1->0 hier=vibration_core
+1208282  point: type=toggle comment=product[0][20]:0->1 hier=vibration_core
+1208282  point: type=toggle comment=product[0][20]:1->0 hier=vibration_core
+1201223  point: type=toggle comment=product[0][21]:0->1 hier=vibration_core
+1201223  point: type=toggle comment=product[0][21]:1->0 hier=vibration_core
+1200348  point: type=toggle comment=product[0][22]:0->1 hier=vibration_core
+1200348  point: type=toggle comment=product[0][22]:1->0 hier=vibration_core
+1228185  point: type=toggle comment=product[0][23]:0->1 hier=vibration_core
+1228185  point: type=toggle comment=product[0][23]:1->0 hier=vibration_core
+1224536  point: type=toggle comment=product[0][24]:0->1 hier=vibration_core
+1224536  point: type=toggle comment=product[0][24]:1->0 hier=vibration_core
+1224513  point: type=toggle comment=product[0][25]:0->1 hier=vibration_core
+1224513  point: type=toggle comment=product[0][25]:1->0 hier=vibration_core
+1224513  point: type=toggle comment=product[0][26]:0->1 hier=vibration_core
+1224513  point: type=toggle comment=product[0][26]:1->0 hier=vibration_core
+1224513  point: type=toggle comment=product[0][27]:0->1 hier=vibration_core
+1224513  point: type=toggle comment=product[0][27]:1->0 hier=vibration_core
+1224513  point: type=toggle comment=product[0][28]:0->1 hier=vibration_core
+1224513  point: type=toggle comment=product[0][28]:1->0 hier=vibration_core
+1224513  point: type=toggle comment=product[0][29]:0->1 hier=vibration_core
+1224513  point: type=toggle comment=product[0][29]:1->0 hier=vibration_core
+1187280  point: type=toggle comment=product[0][2]:0->1 hier=vibration_core
+1187280  point: type=toggle comment=product[0][2]:1->0 hier=vibration_core
+1224513  point: type=toggle comment=product[0][30]:0->1 hier=vibration_core
+1224513  point: type=toggle comment=product[0][30]:1->0 hier=vibration_core
+1224513  point: type=toggle comment=product[0][31]:0->1 hier=vibration_core
+1224513  point: type=toggle comment=product[0][31]:1->0 hier=vibration_core
+1194818  point: type=toggle comment=product[0][3]:0->1 hier=vibration_core
+1194818  point: type=toggle comment=product[0][3]:1->0 hier=vibration_core
+1194257  point: type=toggle comment=product[0][4]:0->1 hier=vibration_core
+1194257  point: type=toggle comment=product[0][4]:1->0 hier=vibration_core
+1199487  point: type=toggle comment=product[0][5]:0->1 hier=vibration_core
+1199487  point: type=toggle comment=product[0][5]:1->0 hier=vibration_core
+1198269  point: type=toggle comment=product[0][6]:0->1 hier=vibration_core
+1198269  point: type=toggle comment=product[0][6]:1->0 hier=vibration_core
+1194639  point: type=toggle comment=product[0][7]:0->1 hier=vibration_core
+1194639  point: type=toggle comment=product[0][7]:1->0 hier=vibration_core
+1199772  point: type=toggle comment=product[0][8]:0->1 hier=vibration_core
+1199772  point: type=toggle comment=product[0][8]:1->0 hier=vibration_core
+1197280  point: type=toggle comment=product[0][9]:0->1 hier=vibration_core
+1197280  point: type=toggle comment=product[0][9]:1->0 hier=vibration_core
 6185860     reg multiply_enable;
+6185860  point: type=toggle comment=multiply_enable:0->1 hier=vibration_core
+6185860  point: type=toggle comment=multiply_enable:1->0 hier=vibration_core
 56988776     wire [WA-1:0] weight_address = WA'(nn_layer ? W1_WORDS + int'(nn_group)/LANES*16 + int'(nn_input) : int'(nn_group)/LANES*16 + int'(nn_input));
+008816  point: type=toggle comment=weight_address[0]:0->1 hier=vibration_core
+008814  point: type=toggle comment=weight_address[0]:1->0 hier=vibration_core
+004408  point: type=toggle comment=weight_address[1]:0->1 hier=vibration_core
+004406  point: type=toggle comment=weight_address[1]:1->0 hier=vibration_core
+002204  point: type=toggle comment=weight_address[2]:0->1 hier=vibration_core
+002202  point: type=toggle comment=weight_address[2]:1->0 hier=vibration_core
+001102  point: type=toggle comment=weight_address[3]:0->1 hier=vibration_core
+001100  point: type=toggle comment=weight_address[3]:1->0 hier=vibration_core
+000522  point: type=toggle comment=weight_address[4]:0->1 hier=vibration_core
+000522  point: type=toggle comment=weight_address[4]:1->0 hier=vibration_core
+000290  point: type=toggle comment=weight_address[5]:0->1 hier=vibration_core
+000288  point: type=toggle comment=weight_address[5]:1->0 hier=vibration_core
+000116  point: type=toggle comment=weight_address[6]:0->1 hier=vibration_core
+000116  point: type=toggle comment=weight_address[6]:1->0 hier=vibration_core
+000058  point: type=toggle comment=weight_address[7]:0->1 hier=vibration_core
+000058  point: type=toggle comment=weight_address[7]:1->0 hier=vibration_core
+000058  point: type=toggle comment=weight_address[8]:0->1 hier=vibration_core
+000056  point: type=toggle comment=weight_address[8]:1->0 hier=vibration_core
+36265662  point: type=expr comment=(nn_layer==0) => 0 hier=vibration_core
+56988776  point: type=expr comment=(nn_layer==1) => 1 hier=vibration_core
+56988776  point: type=branch comment=cond_then hier=vibration_core
+36265662  point: type=branch comment=cond_else hier=vibration_core
 002976     wire [CW-1:0] dft_component = dft_group + CW'(store_lane);
+002976  point: type=toggle comment=dft_component[0]:0->1 hier=vibration_core
+002974  point: type=toggle comment=dft_component[0]:1->0 hier=vibration_core
+001488  point: type=toggle comment=dft_component[1]:0->1 hier=vibration_core
+001486  point: type=toggle comment=dft_component[1]:1->0 hier=vibration_core
+000744  point: type=toggle comment=dft_component[2]:0->1 hier=vibration_core
+000742  point: type=toggle comment=dft_component[2]:1->0 hier=vibration_core
+000372  point: type=toggle comment=dft_component[3]:0->1 hier=vibration_core
+000370  point: type=toggle comment=dft_component[3]:1->0 hier=vibration_core
+000186  point: type=toggle comment=dft_component[4]:0->1 hier=vibration_core
+000184  point: type=toggle comment=dft_component[4]:1->0 hier=vibration_core
+000062  point: type=toggle comment=dft_component[5]:0->1 hier=vibration_core
+000062  point: type=toggle comment=dft_component[5]:1->0 hier=vibration_core
+000062  point: type=toggle comment=dft_component[6]:0->1 hier=vibration_core
+000060  point: type=toggle comment=dft_component[6]:1->0 hier=vibration_core
 001488     wire [BI_W-1:0] dft_bin_index = dft_component[CW-1:1];
+001488  point: type=toggle comment=dft_bin_index[0]:0->1 hier=vibration_core
+001486  point: type=toggle comment=dft_bin_index[0]:1->0 hier=vibration_core
+000744  point: type=toggle comment=dft_bin_index[1]:0->1 hier=vibration_core
+000742  point: type=toggle comment=dft_bin_index[1]:1->0 hier=vibration_core
+000372  point: type=toggle comment=dft_bin_index[2]:0->1 hier=vibration_core
+000370  point: type=toggle comment=dft_bin_index[2]:1->0 hier=vibration_core
+000186  point: type=toggle comment=dft_bin_index[3]:0->1 hier=vibration_core
+000184  point: type=toggle comment=dft_bin_index[3]:1->0 hier=vibration_core
+000062  point: type=toggle comment=dft_bin_index[4]:0->1 hier=vibration_core
+000062  point: type=toggle comment=dft_bin_index[4]:1->0 hier=vibration_core
+000062  point: type=toggle comment=dft_bin_index[5]:0->1 hier=vibration_core
+000060  point: type=toggle comment=dft_bin_index[5]:1->0 hier=vibration_core
 000522     wire [3:0] nn_output_index = nn_group + 4'(store_lane);
+000522  point: type=toggle comment=nn_output_index[0]:0->1 hier=vibration_core
+000522  point: type=toggle comment=nn_output_index[0]:1->0 hier=vibration_core
+000290  point: type=toggle comment=nn_output_index[1]:0->1 hier=vibration_core
+000288  point: type=toggle comment=nn_output_index[1]:1->0 hier=vibration_core
+000116  point: type=toggle comment=nn_output_index[2]:0->1 hier=vibration_core
+000116  point: type=toggle comment=nn_output_index[2]:1->0 hier=vibration_core
+000058  point: type=toggle comment=nn_output_index[3]:0->1 hier=vibration_core
+000058  point: type=toggle comment=nn_output_index[3]:1->0 hier=vibration_core
~1162839     wire signed [39:0] selected_accumulator = accumulator[LANES == 1 ? 0 : store_lane];
+618987  point: type=toggle comment=selected_accumulator[0]:0->1 hier=vibration_core
+618985  point: type=toggle comment=selected_accumulator[0]:1->0 hier=vibration_core
+1132389  point: type=toggle comment=selected_accumulator[10]:0->1 hier=vibration_core
+1132387  point: type=toggle comment=selected_accumulator[10]:1->0 hier=vibration_core
+1128777  point: type=toggle comment=selected_accumulator[11]:0->1 hier=vibration_core
+1128775  point: type=toggle comment=selected_accumulator[11]:1->0 hier=vibration_core
+1119748  point: type=toggle comment=selected_accumulator[12]:0->1 hier=vibration_core
+1119746  point: type=toggle comment=selected_accumulator[12]:1->0 hier=vibration_core
+1103623  point: type=toggle comment=selected_accumulator[13]:0->1 hier=vibration_core
+1103621  point: type=toggle comment=selected_accumulator[13]:1->0 hier=vibration_core
+1162839  point: type=toggle comment=selected_accumulator[14]:0->1 hier=vibration_core
+1162837  point: type=toggle comment=selected_accumulator[14]:1->0 hier=vibration_core
+1149340  point: type=toggle comment=selected_accumulator[15]:0->1 hier=vibration_core
+1149338  point: type=toggle comment=selected_accumulator[15]:1->0 hier=vibration_core
+1125305  point: type=toggle comment=selected_accumulator[16]:0->1 hier=vibration_core
+1125303  point: type=toggle comment=selected_accumulator[16]:1->0 hier=vibration_core
+1087979  point: type=toggle comment=selected_accumulator[17]:0->1 hier=vibration_core
+1087977  point: type=toggle comment=selected_accumulator[17]:1->0 hier=vibration_core
+1039420  point: type=toggle comment=selected_accumulator[18]:0->1 hier=vibration_core
+1039418  point: type=toggle comment=selected_accumulator[18]:1->0 hier=vibration_core
+971329  point: type=toggle comment=selected_accumulator[19]:0->1 hier=vibration_core
+971327  point: type=toggle comment=selected_accumulator[19]:1->0 hier=vibration_core
+891348  point: type=toggle comment=selected_accumulator[1]:0->1 hier=vibration_core
+891346  point: type=toggle comment=selected_accumulator[1]:1->0 hier=vibration_core
+898629  point: type=toggle comment=selected_accumulator[20]:0->1 hier=vibration_core
+898627  point: type=toggle comment=selected_accumulator[20]:1->0 hier=vibration_core
+826832  point: type=toggle comment=selected_accumulator[21]:0->1 hier=vibration_core
+826830  point: type=toggle comment=selected_accumulator[21]:1->0 hier=vibration_core
+759886  point: type=toggle comment=selected_accumulator[22]:0->1 hier=vibration_core
+759884  point: type=toggle comment=selected_accumulator[22]:1->0 hier=vibration_core
+604140  point: type=toggle comment=selected_accumulator[23]:0->1 hier=vibration_core
+604138  point: type=toggle comment=selected_accumulator[23]:1->0 hier=vibration_core
+533712  point: type=toggle comment=selected_accumulator[24]:0->1 hier=vibration_core
+533710  point: type=toggle comment=selected_accumulator[24]:1->0 hier=vibration_core
+489278  point: type=toggle comment=selected_accumulator[25]:0->1 hier=vibration_core
+489276  point: type=toggle comment=selected_accumulator[25]:1->0 hier=vibration_core
+473671  point: type=toggle comment=selected_accumulator[26]:0->1 hier=vibration_core
+473669  point: type=toggle comment=selected_accumulator[26]:1->0 hier=vibration_core
+467580  point: type=toggle comment=selected_accumulator[27]:0->1 hier=vibration_core
+467578  point: type=toggle comment=selected_accumulator[27]:1->0 hier=vibration_core
+465417  point: type=toggle comment=selected_accumulator[28]:0->1 hier=vibration_core
+465415  point: type=toggle comment=selected_accumulator[28]:1->0 hier=vibration_core
+464906  point: type=toggle comment=selected_accumulator[29]:0->1 hier=vibration_core
+464904  point: type=toggle comment=selected_accumulator[29]:1->0 hier=vibration_core
+1044498  point: type=toggle comment=selected_accumulator[2]:0->1 hier=vibration_core
+1044498  point: type=toggle comment=selected_accumulator[2]:1->0 hier=vibration_core
+464748  point: type=toggle comment=selected_accumulator[30]:0->1 hier=vibration_core
+464746  point: type=toggle comment=selected_accumulator[30]:1->0 hier=vibration_core
+464725  point: type=toggle comment=selected_accumulator[31]:0->1 hier=vibration_core
+464723  point: type=toggle comment=selected_accumulator[31]:1->0 hier=vibration_core
+464723  point: type=toggle comment=selected_accumulator[32]:0->1 hier=vibration_core
+464721  point: type=toggle comment=selected_accumulator[32]:1->0 hier=vibration_core
+464721  point: type=toggle comment=selected_accumulator[33]:0->1 hier=vibration_core
+464719  point: type=toggle comment=selected_accumulator[33]:1->0 hier=vibration_core
+464721  point: type=toggle comment=selected_accumulator[34]:0->1 hier=vibration_core
+464719  point: type=toggle comment=selected_accumulator[34]:1->0 hier=vibration_core
+464721  point: type=toggle comment=selected_accumulator[35]:0->1 hier=vibration_core
+464719  point: type=toggle comment=selected_accumulator[35]:1->0 hier=vibration_core
+464721  point: type=toggle comment=selected_accumulator[36]:0->1 hier=vibration_core
+464719  point: type=toggle comment=selected_accumulator[36]:1->0 hier=vibration_core
+464721  point: type=toggle comment=selected_accumulator[37]:0->1 hier=vibration_core
+464719  point: type=toggle comment=selected_accumulator[37]:1->0 hier=vibration_core
+464721  point: type=toggle comment=selected_accumulator[38]:0->1 hier=vibration_core
+464719  point: type=toggle comment=selected_accumulator[38]:1->0 hier=vibration_core
+464721  point: type=toggle comment=selected_accumulator[39]:0->1 hier=vibration_core
+464719  point: type=toggle comment=selected_accumulator[39]:1->0 hier=vibration_core
+1089150  point: type=toggle comment=selected_accumulator[3]:0->1 hier=vibration_core
+1089148  point: type=toggle comment=selected_accumulator[3]:1->0 hier=vibration_core
+1122001  point: type=toggle comment=selected_accumulator[4]:0->1 hier=vibration_core
+1121999  point: type=toggle comment=selected_accumulator[4]:1->0 hier=vibration_core
+1136886  point: type=toggle comment=selected_accumulator[5]:0->1 hier=vibration_core
+1136886  point: type=toggle comment=selected_accumulator[5]:1->0 hier=vibration_core
+1139993  point: type=toggle comment=selected_accumulator[6]:0->1 hier=vibration_core
+1139991  point: type=toggle comment=selected_accumulator[6]:1->0 hier=vibration_core
+1144198  point: type=toggle comment=selected_accumulator[7]:0->1 hier=vibration_core
+1144196  point: type=toggle comment=selected_accumulator[7]:1->0 hier=vibration_core
+1141485  point: type=toggle comment=selected_accumulator[8]:0->1 hier=vibration_core
+1141483  point: type=toggle comment=selected_accumulator[8]:1->0 hier=vibration_core
+1135820  point: type=toggle comment=selected_accumulator[9]:0->1 hier=vibration_core
+1135820  point: type=toggle comment=selected_accumulator[9]:1->0 hier=vibration_core
-000000  point: type=expr comment=((LANES == 32'sh1)==0) => 0 hier=vibration_core
+000002  point: type=expr comment=((LANES == 32'sh1)==1) => 1 hier=vibration_core
 004582     wire signed [7:0] weight_q [0:LANES-1];
+004292  point: type=toggle comment=weight_q[0][0]:0->1 hier=vibration_core
+004292  point: type=toggle comment=weight_q[0][0]:1->0 hier=vibration_core
+004524  point: type=toggle comment=weight_q[0][1]:0->1 hier=vibration_core
+004524  point: type=toggle comment=weight_q[0][1]:1->0 hier=vibration_core
+004582  point: type=toggle comment=weight_q[0][2]:0->1 hier=vibration_core
+004580  point: type=toggle comment=weight_q[0][2]:1->0 hier=vibration_core
+004408  point: type=toggle comment=weight_q[0][3]:0->1 hier=vibration_core
+004406  point: type=toggle comment=weight_q[0][3]:1->0 hier=vibration_core
+004350  point: type=toggle comment=weight_q[0][4]:0->1 hier=vibration_core
+004350  point: type=toggle comment=weight_q[0][4]:1->0 hier=vibration_core
+003944  point: type=toggle comment=weight_q[0][5]:0->1 hier=vibration_core
+003944  point: type=toggle comment=weight_q[0][5]:1->0 hier=vibration_core
+002668  point: type=toggle comment=weight_q[0][6]:0->1 hier=vibration_core
+002666  point: type=toggle comment=weight_q[0][6]:1->0 hier=vibration_core
+002842  point: type=toggle comment=weight_q[0][7]:0->1 hier=vibration_core
+002840  point: type=toggle comment=weight_q[0][7]:1->0 hier=vibration_core
        
 489740     function automatic signed [39:0] rne;
+489740  point: type=line comment=block hier=vibration_core
                input signed [39:0] value;
                input integer shift;
 489740         reg signed [39:0] quotient;
+489740  point: type=line comment=block hier=vibration_core
 489740         reg [39:0] remainder, halfway;
+489740  point: type=line comment=block hier=vibration_core
 489740         begin
+489740  point: type=line comment=block hier=vibration_core
~489740             if (shift == 0) rne = value;
-000000  point: type=branch comment=if hier=vibration_core
+489740  point: type=branch comment=else hier=vibration_core
 489740             else begin
+489740  point: type=branch comment=else hier=vibration_core
 489740                 quotient = value >>> shift;
+489740  point: type=branch comment=else hier=vibration_core
 489740                 remainder = value & ((40'd1 << shift)-1);
+489740  point: type=branch comment=else hier=vibration_core
 489740                 halfway = 40'd1 << (shift-1);
+489740  point: type=branch comment=else hier=vibration_core
 489740                 rne = quotient + (((remainder > halfway) || ((remainder == halfway) && quotient[0])) ? 40'sd1 : 40'sd0);
+489740  point: type=branch comment=else hier=vibration_core
+004893  point: type=expr comment=((remainder == halfway)==1 && quotient[0]==1) => 1 hier=vibration_core
+290676  point: type=expr comment=((remainder > halfway)==0 && (remainder == halfway)==0) => 0 hier=vibration_core
+202423  point: type=expr comment=((remainder > halfway)==0 && quotient[0]==0) => 0 hier=vibration_core
+188687  point: type=expr comment=((remainder > halfway)==1) => 1 hier=vibration_core
                    end
                end
            endfunction
 475840     function automatic signed [15:0] sat12;
+475840  point: type=line comment=block hier=vibration_core
                input signed [39:0] value;
 475840         begin
+475840  point: type=line comment=block hier=vibration_core
%000000             if (value > 2047) sat12 = 16'sd2047;
-000000  point: type=line comment=elsif hier=vibration_core
~475840             else if (value < -2048) sat12 = -16'sd2048;
-000000  point: type=line comment=if hier=vibration_core
+475840  point: type=line comment=else hier=vibration_core
 475840             else sat12 = value[15:0];
+475840  point: type=line comment=else hier=vibration_core
                end
            endfunction
 011904     function automatic signed [15:0] sat16;
+011904  point: type=line comment=block hier=vibration_core
                input signed [39:0] value;
 011904         begin
+011904  point: type=line comment=block hier=vibration_core
%000000             if (value > 32767) sat16 = 16'sd32767;
-000000  point: type=line comment=elsif hier=vibration_core
~011904             else if (value < -32768) sat16 = -16'sd32768;
-000000  point: type=line comment=if hier=vibration_core
+011904  point: type=line comment=else hier=vibration_core
 011904             else sat16 = value[15:0];
+011904  point: type=line comment=else hier=vibration_core
                end
            endfunction
 001856     function automatic [7:0] relu_quant;
+001856  point: type=line comment=block hier=vibration_core
                input signed [39:0] value;
 001856         reg signed [39:0] rounded;
+001856  point: type=line comment=block hier=vibration_core
 001856         begin
+001856  point: type=line comment=block hier=vibration_core
 001856             rounded = rne(value, HIDDEN_SHIFT);
+001856  point: type=line comment=block hier=vibration_core
 000876             if (rounded <= 0) relu_quant = 0;
+000876  point: type=line comment=elsif hier=vibration_core
~000980             else if (rounded > 127) relu_quant = 127;
-000000  point: type=line comment=if hier=vibration_core
+000980  point: type=line comment=else hier=vibration_core
 000980             else relu_quant = rounded[7:0];
+000980  point: type=line comment=else hier=vibration_core
                end
            endfunction
%000000     function automatic [7:0] power_quant;
-000000  point: type=line comment=block hier=vibration_core
                input [32:0] value;
                input [7:0] shift;
%000000         reg [32:0] quotient, remainder, halfway;
-000000  point: type=line comment=block hier=vibration_core
%000000         reg [33:0] rounded;
-000000  point: type=line comment=block hier=vibration_core
%000000         begin
-000000  point: type=line comment=block hier=vibration_core
%000000             quotient = 0; remainder = 0; halfway = 0; rounded = 0;
-000000  point: type=line comment=block hier=vibration_core
%000000             if (shift == 0) rounded = {1'b0,value};
-000000  point: type=line comment=elsif hier=vibration_core
%000000             else if (shift <= 33) begin
-000000  point: type=branch comment=if hier=vibration_core
-000000  point: type=branch comment=else hier=vibration_core
%000000                 quotient = value >> shift;
-000000  point: type=branch comment=if hier=vibration_core
%000000                 remainder = value & ((33'd1 << shift)-1);
-000000  point: type=branch comment=if hier=vibration_core
%000000                 halfway = 33'd1 << (shift-1);
-000000  point: type=branch comment=if hier=vibration_core
%000000                 rounded = {1'b0,quotient} + (((remainder > halfway) || ((remainder == halfway) && quotient[0])) ? 34'd1 : 34'd0);
-000000  point: type=branch comment=if hier=vibration_core
-000000  point: type=expr comment=((remainder == halfway)==1 && quotient[0]==1) => 1 hier=vibration_core
-000000  point: type=expr comment=((remainder > halfway)==0 && (remainder == halfway)==0) => 0 hier=vibration_core
-000000  point: type=expr comment=((remainder > halfway)==0 && quotient[0]==0) => 0 hier=vibration_core
-000000  point: type=expr comment=((remainder > halfway)==1) => 1 hier=vibration_core
                    end
%000000             power_quant = rounded > 127 ? 8'd127 : rounded[7:0];
-000000  point: type=line comment=block hier=vibration_core
-000000  point: type=expr comment=((rounded > 34'h7f)==0) => 0 hier=vibration_core
-000000  point: type=expr comment=((rounded > 34'h7f)==1) => 1 hier=vibration_core
-000000  point: type=branch comment=cond_then hier=vibration_core
-000000  point: type=branch comment=cond_else hier=vibration_core
                end
            endfunction
        
            vib_coeff_rom #(.N(N), .MODEL_DIR(MODEL_DIR), .HANN(1)) hann_rom (
                .clk(clk), .en(state == PRE_READ), .phase(point), .coefficient(hann_q)
            );
            genvar lane;
 6185860     generate for (lane=0; lane<LANES; lane=lane+1) begin: g_lane
+6185860  point: type=branch comment=if hier=vibration_core
                vib_coeff_rom #(.N(N), .MODEL_DIR(MODEL_DIR)) coeff_rom (
                    .clk(clk), .en(state == DFT_READ), .phase(phase[lane]),
                    .coefficient(coefficient[lane])
                );
                (* ram_style = "block" *) reg signed [7:0] weights [0:WEIGHT_WORDS-1];
                localparam BANK_FILE = LANES == 1 ? "/weights_l1_0.hex" :
                                           lane == 0 ? "/weights_l4_0.hex" :
                                           lane == 1 ? "/weights_l4_1.hex" :
                                           lane == 2 ? "/weights_l4_2.hex" : "/weights_l4_3.hex";
 004582         reg signed [7:0] selected_weight;
+004292  point: type=toggle comment=g_lane[0].selected_weight[0]:0->1 hier=vibration_core
+004292  point: type=toggle comment=g_lane[0].selected_weight[0]:1->0 hier=vibration_core
+004524  point: type=toggle comment=g_lane[0].selected_weight[1]:0->1 hier=vibration_core
+004524  point: type=toggle comment=g_lane[0].selected_weight[1]:1->0 hier=vibration_core
+004582  point: type=toggle comment=g_lane[0].selected_weight[2]:0->1 hier=vibration_core
+004580  point: type=toggle comment=g_lane[0].selected_weight[2]:1->0 hier=vibration_core
+004408  point: type=toggle comment=g_lane[0].selected_weight[3]:0->1 hier=vibration_core
+004406  point: type=toggle comment=g_lane[0].selected_weight[3]:1->0 hier=vibration_core
+004350  point: type=toggle comment=g_lane[0].selected_weight[4]:0->1 hier=vibration_core
+004350  point: type=toggle comment=g_lane[0].selected_weight[4]:1->0 hier=vibration_core
+003944  point: type=toggle comment=g_lane[0].selected_weight[5]:0->1 hier=vibration_core
+003944  point: type=toggle comment=g_lane[0].selected_weight[5]:1->0 hier=vibration_core
+002668  point: type=toggle comment=g_lane[0].selected_weight[6]:0->1 hier=vibration_core
+002666  point: type=toggle comment=g_lane[0].selected_weight[6]:1->0 hier=vibration_core
+002842  point: type=toggle comment=g_lane[0].selected_weight[7]:0->1 hier=vibration_core
+002840  point: type=toggle comment=g_lane[0].selected_weight[7]:1->0 hier=vibration_core
 000002         initial $readmemh({MODEL_DIR, BANK_FILE}, weights);
+000002  point: type=line comment=block hier=vibration_core
 18621238         always @(posedge clk) begin
+18621238  point: type=line comment=block hier=vibration_core
 18603604             if (state == NN_READ) selected_weight <= weights[weight_address];
+017634  point: type=branch comment=if hier=vibration_core
+18603604  point: type=branch comment=else hier=vibration_core
                    // The only multiplication expression in each lane.
 12435378             if (multiply_enable) product[lane] <= operand_a[lane] * operand_b[lane];
+6185860  point: type=branch comment=if hier=vibration_core
+12435378  point: type=branch comment=else hier=vibration_core
                end
                assign weight_q[lane] = selected_weight;
            end endgenerate
        
            integer m;
 93254438     always @* begin
+93254438  point: type=line comment=block hier=vibration_core
 93254438         multiply_enable = 0;
+93254438  point: type=line comment=block hier=vibration_core
 93254438         for (m=0; m<LANES; m=m+1) begin operand_a[m]=0; operand_b[m]=0; end
+93254438  point: type=line comment=block hier=vibration_core
+93254438  point: type=line comment=block hier=vibration_core
 93254438         case (state)
+93254438  point: type=line comment=block hier=vibration_core
 340670             PRE_MUL: begin
+340670  point: type=line comment=case hier=vibration_core
 340670                 multiply_enable=1;
+340670  point: type=line comment=case hier=vibration_core
 340670                 operand_a[0]=sat12(rne($signed({{24{raw_q[15]}},raw_q})-$signed({{24{mean[15]}},mean}),5));
+340670  point: type=line comment=case hier=vibration_core
 340670                 operand_b[0]=hann_q;
+340670  point: type=line comment=case hier=vibration_core
                    end
 30492167             DFT_MUL: begin
+30492167  point: type=line comment=case hier=vibration_core
 30492167                 multiply_enable=1;
+30492167  point: type=line comment=case hier=vibration_core
 30492167                 for (m=0; m<LANES; m=m+1) begin operand_a[m]=sample_q; operand_b[m]=coefficient[m]; end
+30492167  point: type=line comment=case hier=vibration_core
+30492167  point: type=line comment=block hier=vibration_core
                    end
 014430             POWER_RE_MUL: begin multiply_enable=1; operand_a[0]=real_part[power_index]; operand_b[0]=real_part[power_index]; end
+014430  point: type=line comment=case hier=vibration_core
 014430             POWER_IM_MUL: begin multiply_enable=1; operand_a[0]=imag_part[power_index]; operand_b[0]=imag_part[power_index]; end
+014430  point: type=line comment=case hier=vibration_core
 088170             NN_MUL: begin
+088170  point: type=line comment=case hier=vibration_core
 088170                 multiply_enable=1;
+088170  point: type=line comment=case hier=vibration_core
 088170                 for (m=0; m<LANES; m=m+1) begin operand_a[m]=$signed({8'd0,activation_q}); operand_b[m]={{8{weight_q[m][7]}},weight_q[m]}; end
+088170  point: type=line comment=case hier=vibration_core
+088170  point: type=line comment=block hier=vibration_core
                    end
 62304571             default: begin end
+62304571  point: type=line comment=case hier=vibration_core
                endcase
            end
        
            // Dedicated synchronous RAM ports have no reset: reset invalidates ownership.
 18621238     always @(posedge clk) begin
+18621238  point: type=line comment=block hier=vibration_core
 18547452         if (!rst && in_valid && in_ready && (restart_input || !draining)) begin
+18547452  point: type=branch comment=else hier=vibration_core
+7772215  point: type=expr comment=(in_ready==0) => 0 hier=vibration_core
+11968943  point: type=expr comment=(in_valid==0) => 0 hier=vibration_core
+000002  point: type=expr comment=(restart_input==0 && draining==1) => 0 hier=vibration_core
+073784  point: type=expr comment=(rst==0 && in_valid==1 && in_ready==1 && draining==0) => 1 hier=vibration_core
+000078  point: type=expr comment=(rst==0 && in_valid==1 && in_ready==1 && restart_input==1) => 1 hier=vibration_core
+000104  point: type=expr comment=(rst==1) => 0 hier=vibration_core
+073786  point: type=branch comment=if hier=vibration_core
 043032             if (write_bank) raw1[restart_input ? 0 : input_index] <= in_sample;
+030754  point: type=branch comment=if hier=vibration_core
+043032  point: type=branch comment=else hier=vibration_core
+030722  point: type=expr comment=(restart_input==0) => 0 hier=vibration_core
+000032  point: type=expr comment=(restart_input==1) => 1 hier=vibration_core
 043032             else raw0[restart_input ? 0 : input_index] <= in_sample;
+043032  point: type=branch comment=else hier=vibration_core
+042986  point: type=expr comment=(restart_input==0) => 0 hier=vibration_core
+000046  point: type=expr comment=(restart_input==1) => 1 hier=vibration_core
                end
 18553650         if (state == PRE_READ) begin
+18553650  point: type=branch comment=else hier=vibration_core
+067588  point: type=branch comment=if hier=vibration_core
 067588             raw_q <= active_bank ? raw1[point] : raw0[point];
+067588  point: type=branch comment=if hier=vibration_core
+038914  point: type=expr comment=(active_bank==0) => 0 hier=vibration_core
+028674  point: type=expr comment=(active_bank==1) => 1 hier=vibration_core
+028674  point: type=branch comment=cond_then hier=vibration_core
+038914  point: type=branch comment=cond_else hier=vibration_core
                end
 18553652         if (state == PRE_STORE) windowed[point] <= sat12(rne({{8{product[0][31]}},product[0]},14));
+18553652  point: type=branch comment=else hier=vibration_core
+067586  point: type=branch comment=if hier=vibration_core
 12526368         if (state == DFT_READ) sample_q <= windowed[point];
+12526368  point: type=branch comment=else hier=vibration_core
+6094870  point: type=branch comment=if hier=vibration_core
            end
        
            integer k;
 18621238     always @(posedge clk) begin
+18621238  point: type=line comment=block hier=vibration_core
 18621134         if (rst) begin
+18621134  point: type=branch comment=else hier=vibration_core
+000104  point: type=branch comment=if hier=vibration_core
 000104             state<=IDLE; full<=0; busy<=0; write_bank<=0; read_bank<=0;
+000104  point: type=branch comment=if hier=vibration_core
 000104             active_bank<=0; receiving<=0; draining<=0; input_index<=0;
+000104  point: type=branch comment=if hier=vibration_core
 000104             receiving_id<=0; input_sum<=0; active_id<=0;
+000104  point: type=branch comment=if hier=vibration_core
 000104             out_valid<=0; out_frame_id<=0; out_logits<=0; out_class<=0; out_error<=0;
+000104  point: type=branch comment=if hier=vibration_core
 000104             cycles_pre<=0; cycles_dft<=0; cycles_power<=0; cycles_nn<=0; cycles_total<=0;
+000104  point: type=branch comment=if hier=vibration_core
 000104             protocol_errors<=0; dbg_valid<=0; dbg_kind<=0; dbg_index<=0; dbg_value<=0;
+000104  point: type=branch comment=if hier=vibration_core
 000104             point<=0; mean<=0; dft_group<=0; store_lane<=0; feature_index<=0; power_index<=0; band_part<=0; band_sum<=0;
+000104  point: type=branch comment=if hier=vibration_core
 000104             power_sum<=0; quant_work<=0; quant_remaining<=0; quant_guard<=0; quant_sticky<=0; nn_layer<=0; nn_group<=0; nn_input<=0; activation_q<=0;
+000104  point: type=branch comment=if hier=vibration_core
 000104             arithmetic_errors<=0; count_pre<=0; count_dft<=0; count_power<=0; count_nn<=0; count_total<=0;
+000104  point: type=branch comment=if hier=vibration_core
 000104             for (k=0; k<LANES; k=k+1) begin accumulator[k]<=0; phase[k]<=0; end
+000104  point: type=branch comment=if hier=vibration_core
+000104  point: type=line comment=block hier=vibration_core
 000312             for (k=0; k<3; k=k+1) logits[k]<=0;
+000104  point: type=branch comment=if hier=vibration_core
+000312  point: type=line comment=block hier=vibration_core
 18621134         end else begin
+18621134  point: type=branch comment=else hier=vibration_core
 18621134             dbg_valid<=0;
+18621134  point: type=branch comment=else hier=vibration_core
 18547348             if (in_valid && in_ready) begin
+073786  point: type=branch comment=if hier=vibration_core
+18547348  point: type=branch comment=else hier=vibration_core
+7772111  point: type=expr comment=(in_ready==0) => 0 hier=vibration_core
+11968839  point: type=expr comment=(in_valid==0) => 0 hier=vibration_core
+073786  point: type=expr comment=(in_valid==1 && in_ready==1) => 1 hier=vibration_core
 000078                 if (restart_input) begin
+000078  point: type=line comment=elsif hier=vibration_core
 000074                     if (receiving) protocol_errors<=protocol_errors+1;
+000004  point: type=branch comment=if hier=vibration_core
+000074  point: type=branch comment=else hier=vibration_core
 000078                     receiving_id<=in_frame_id; input_sum<=extended_sample;
+000078  point: type=line comment=elsif hier=vibration_core
 000078                     input_index<=1; draining<=0;
+000078  point: type=line comment=elsif hier=vibration_core
~000078                     if (in_last) begin
-000000  point: type=branch comment=if hier=vibration_core
+000078  point: type=branch comment=else hier=vibration_core
%000000                         receiving<=0; protocol_errors<=protocol_errors+1;
-000000  point: type=branch comment=if hier=vibration_core
 000078                     end else receiving<=1;
+000078  point: type=branch comment=else hier=vibration_core
~073708                 end else if (draining) begin
-000000  point: type=line comment=if hier=vibration_core
+073708  point: type=line comment=else hier=vibration_core
%000000                     if (in_last) begin receiving<=0; draining<=0; end
-000000  point: type=branch comment=if hier=vibration_core
-000000  point: type=branch comment=else hier=vibration_core
 073708                 end else begin
+073708  point: type=line comment=else hier=vibration_core
 073708                     input_sum<=input_sum+extended_sample;
+073708  point: type=line comment=else hier=vibration_core
 000072                     if (in_last) begin
+000072  point: type=line comment=elsif hier=vibration_core
 000072                         receiving<=0;
+000072  point: type=line comment=elsif hier=vibration_core
 000070                         if (input_index == P'(N-1)) begin
+000070  point: type=branch comment=if hier=vibration_core
+000002  point: type=branch comment=else hier=vibration_core
 000070                             full[write_bank]<=1; frame_ids[write_bank]<=receiving_id;
+000070  point: type=branch comment=if hier=vibration_core
 000070                             frame_sums[write_bank]<=input_sum+extended_sample;
+000070  point: type=branch comment=if hier=vibration_core
 000070                             write_bank<=!write_bank;
+000070  point: type=branch comment=if hier=vibration_core
+000040  point: type=expr comment=(write_bank==0) => 1 hier=vibration_core
+000030  point: type=expr comment=(write_bank==1) => 0 hier=vibration_core
 000002                         end else protocol_errors<=protocol_errors+1;
+000002  point: type=branch comment=else hier=vibration_core
 073634                     end else if (input_index == P'(N-1)) begin
+000002  point: type=line comment=if hier=vibration_core
+073634  point: type=line comment=else hier=vibration_core
 000002                         draining<=1; protocol_errors<=protocol_errors+1;
+000002  point: type=line comment=if hier=vibration_core
 073634                     end else input_index<=input_index+1;
+073634  point: type=line comment=else hier=vibration_core
                        end
                    end
        
 18418308             if (state >= PRE_MEAN && state <= PRE_STORE) count_pre<=count_pre+1;
+202826  point: type=branch comment=if hier=vibration_core
+18418308  point: type=branch comment=else hier=vibration_core
+18375044  point: type=expr comment=((state <= PRE_STORE)==0) => 0 hier=vibration_core
+043264  point: type=expr comment=((state >= PRE_MEAN)==0) => 0 hier=vibration_core
+202826  point: type=expr comment=((state >= PRE_MEAN)==1 && (state <= PRE_STORE)==1) => 1 hier=vibration_core
 18296510             if (state >= DFT_INIT && state <= DFT_STORE) count_dft<=count_dft+1;
+18296510  point: type=branch comment=if hier=vibration_core
+324624  point: type=branch comment=else hier=vibration_core
+078534  point: type=expr comment=((state <= DFT_STORE)==0) => 0 hier=vibration_core
+246090  point: type=expr comment=((state >= DFT_INIT)==0) => 0 hier=vibration_core
+18296510  point: type=expr comment=((state >= DFT_INIT)==1 && (state <= DFT_STORE)==1) => 1 hier=vibration_core
 18604068             if (state >= POWER_RE_MUL && state <= POWER_QUANT) count_power<=count_power+1;
+017066  point: type=branch comment=if hier=vibration_core
+18604068  point: type=branch comment=else hier=vibration_core
+061468  point: type=expr comment=((state <= POWER_QUANT)==0) => 0 hier=vibration_core
+18542600  point: type=expr comment=((state >= POWER_RE_MUL)==0) => 0 hier=vibration_core
+017066  point: type=expr comment=((state >= POWER_RE_MUL)==1 && (state <= POWER_QUANT)==1) => 1 hier=vibration_core
 18566028             if (state >= NN_INIT && state <= NN_STORE) count_nn<=count_nn+1;
+055106  point: type=branch comment=if hier=vibration_core
+18566028  point: type=branch comment=else hier=vibration_core
+006362  point: type=expr comment=((state <= NN_STORE)==0) => 0 hier=vibration_core
+18559666  point: type=expr comment=((state >= NN_INIT)==0) => 0 hier=vibration_core
+055106  point: type=expr comment=((state >= NN_INIT)==1 && (state <= NN_STORE)==1) => 1 hier=vibration_core
 18571508             if (state != IDLE && state != HOLD && state != FINISH) count_total<=count_total+1;
+18571508  point: type=branch comment=if hier=vibration_core
+049626  point: type=branch comment=else hier=vibration_core
+000056  point: type=expr comment=((state != FINISH)==0) => 0 hier=vibration_core
+006306  point: type=expr comment=((state != HOLD)==0) => 0 hier=vibration_core
+043264  point: type=expr comment=((state != IDLE)==0) => 0 hier=vibration_core
+18571508  point: type=expr comment=((state != IDLE)==1 && (state != HOLD)==1 && (state != FINISH)==1) => 1 hier=vibration_core
        
 18621134             case (state)
+18621134  point: type=branch comment=else hier=vibration_core
 043264                 IDLE: if (full[read_bank]) begin
+043264  point: type=line comment=case hier=vibration_core
+000070  point: type=branch comment=if hier=vibration_core
+043194  point: type=branch comment=else hier=vibration_core
 000070                     active_bank<=read_bank; active_id<=frame_ids[read_bank];
+000070  point: type=branch comment=if hier=vibration_core
 000070                     full[read_bank]<=0; busy[read_bank]<=1; read_bank<=!read_bank;
+000070  point: type=branch comment=if hier=vibration_core
+000040  point: type=expr comment=(read_bank==0) => 1 hier=vibration_core
+000030  point: type=expr comment=(read_bank==1) => 0 hier=vibration_core
 000070                     point<=0; arithmetic_errors<=0;
+000070  point: type=branch comment=if hier=vibration_core
 000070                     count_pre<=0; count_dft<=0; count_power<=0; count_nn<=0; count_total<=0;
+000070  point: type=branch comment=if hier=vibration_core
 000070                     state<=PRE_MEAN;
+000070  point: type=branch comment=if hier=vibration_core
                        end
 000070                 PRE_MEAN: begin
+000070  point: type=line comment=case hier=vibration_core
 000070                     mean<=16'(rne({{(40-SUM_W){frame_sums[active_bank][SUM_W-1]}},frame_sums[active_bank]},P));
+000070  point: type=line comment=case hier=vibration_core
 000070                     dbg_valid<=1; dbg_kind<=0; dbg_index<=0; dbg_value<=40'(rne({{(40-SUM_W){frame_sums[active_bank][SUM_W-1]}},frame_sums[active_bank]},P));
+000070  point: type=line comment=case hier=vibration_core
 000070                     state<=PRE_READ;
+000070  point: type=line comment=case hier=vibration_core
                        end
 067586                 PRE_READ: state<=PRE_MUL;
+067586  point: type=line comment=case hier=vibration_core
 067586                 PRE_MUL: state<=PRE_STORE;
+067586  point: type=line comment=case hier=vibration_core
 067584                 PRE_STORE: begin
+067584  point: type=line comment=case hier=vibration_core
 067584                     dbg_valid<=1; dbg_kind<=1; dbg_index<=16'(point); dbg_value<=40'(sat12(rne({{8{product[0][31]}},product[0]},14)));
+067584  point: type=line comment=case hier=vibration_core
 067518                     if (point == P'(N-1)) begin busy[active_bank]<=0; point<=0; dft_group<=0; state<=DFT_INIT; end
+000066  point: type=branch comment=if hier=vibration_core
+067518  point: type=branch comment=else hier=vibration_core
 067518                     else begin point<=point+1; state<=PRE_READ; end
+067518  point: type=branch comment=else hier=vibration_core
                        end
 005956                 DFT_INIT: begin
+005956  point: type=line comment=case hier=vibration_core
 005956                     point<=0;
+005956  point: type=line comment=case hier=vibration_core
 005956                     for (k=0; k<LANES; k=k+1) begin accumulator[k]<=0; phase[k]<=((int'(dft_group)+k)%2 == 1) ? P'(N/4) : P'(0); end
+005956  point: type=line comment=case hier=vibration_core
+002980  point: type=expr comment=((((dft_group + k) %25 32'sh2) == 32'sh1)==0) => 0 hier=vibration_core
+002976  point: type=expr comment=((((dft_group + k) %25 32'sh2) == 32'sh1)==1) => 1 hier=vibration_core
+002976  point: type=branch comment=cond_then hier=vibration_core
+002980  point: type=branch comment=cond_else hier=vibration_core
+005956  point: type=line comment=block hier=vibration_core
 005956                     state<=DFT_READ;
+005956  point: type=line comment=case hier=vibration_core
                        end
 6094868                 DFT_READ: state<=DFT_MUL;
+6094868  point: type=line comment=case hier=vibration_core
 6094868                 DFT_MUL: state<=DFT_ACC;
+6094868  point: type=line comment=case hier=vibration_core
 6094866                 DFT_ACC: begin
+6094866  point: type=line comment=case hier=vibration_core
 6094866                     for (k=0; k<LANES; k=k+1) begin
+6094866  point: type=line comment=case hier=vibration_core
+6094866  point: type=line comment=block hier=vibration_core
 6094866                         accumulator[k]<=accumulator[k]+$signed({{8{product[k][31]}},product[k]});
+6094866  point: type=line comment=block hier=vibration_core
 6094866                         phase[k]<=phase[k]+P'(frequency_bins[(int'(dft_group)+k)>>1]);
+6094866  point: type=line comment=block hier=vibration_core
                            end
 6088914                     if (point == P'(N-1)) begin store_lane<=0; state<=DFT_STORE; end
+005952  point: type=branch comment=if hier=vibration_core
+6088914  point: type=branch comment=else hier=vibration_core
 6088914                     else begin point<=point+1; state<=DFT_READ; end
+6088914  point: type=branch comment=else hier=vibration_core
                        end
 005952                 DFT_STORE: begin
+005952  point: type=line comment=case hier=vibration_core
 002976                     if (dft_component[0]) imag_part[dft_bin_index]<=sat16(rne(selected_accumulator,P+10));
+002976  point: type=branch comment=if hier=vibration_core
+002976  point: type=branch comment=else hier=vibration_core
 002976                     else real_part[dft_bin_index]<=sat16(rne(selected_accumulator,P+10));
+002976  point: type=branch comment=else hier=vibration_core
 005952                     dbg_valid<=1; dbg_kind<=dft_component[0] ? 3 : 2;
+005952  point: type=line comment=case hier=vibration_core
+002976  point: type=expr comment=(dft_component[0]==0) => 0 hier=vibration_core
+002976  point: type=expr comment=(dft_component[0]==1) => 1 hier=vibration_core
+002976  point: type=branch comment=cond_then hier=vibration_core
+002976  point: type=branch comment=cond_else hier=vibration_core
 005952                     dbg_index<=16'(dft_bin_index); dbg_value<=40'(sat16(rne(selected_accumulator,P+10)));
+005952  point: type=line comment=case hier=vibration_core
~005952                     if (store_lane == LB'(LANES-1)) begin
+005952  point: type=branch comment=if hier=vibration_core
-000000  point: type=branch comment=else hier=vibration_core
 005890                         if (int'(dft_group)+LANES == COMPONENTS) begin feature_index<=0; power_index<=0; band_part<=0; band_sum<=0; state<=POWER_RE_MUL; end
+000062  point: type=branch comment=if hier=vibration_core
+005890  point: type=branch comment=else hier=vibration_core
 005890                         else begin dft_group<=dft_group+CW'(LANES); state<=DFT_INIT; end
+005890  point: type=branch comment=else hier=vibration_core
%000000                     end else store_lane<=store_lane+1;
-000000  point: type=branch comment=else hier=vibration_core
                        end
 002886                 POWER_RE_MUL: state<=POWER_RE_ADD;
+002886  point: type=line comment=case hier=vibration_core
 002886                 POWER_RE_ADD: begin power_sum<={1'b0,product[0]}; state<=POWER_IM_MUL; end
+002886  point: type=line comment=case hier=vibration_core
 002886                 POWER_IM_MUL: state<=POWER_IM_ADD;
+002886  point: type=line comment=case hier=vibration_core
 002886                 POWER_IM_ADD: begin
+002886  point: type=line comment=case hier=vibration_core
~001924                     if (BANDS == 1 || band_part == 2'(BANDS-1)) begin
+000962  point: type=branch comment=if hier=vibration_core
+001924  point: type=branch comment=else hier=vibration_core
+001924  point: type=expr comment=((BANDS == 32'sh1)==0 && (band_part == (BANDS - 32'sh1)[1:0])==0) => 0 hier=vibration_core
-000000  point: type=expr comment=((BANDS == 32'sh1)==1) => 1 hier=vibration_core
+000962  point: type=expr comment=((band_part == (BANDS - 32'sh1)[1:0])==1) => 1 hier=vibration_core
 000962                         power_sum<=band_sum_next[32:0];
+000962  point: type=branch comment=if hier=vibration_core
 000962                         dbg_valid<=1; dbg_kind<=4; dbg_index<={12'd0,feature_index};
+000962  point: type=branch comment=if hier=vibration_core
 000962                         dbg_value<=$signed({6'd0,band_sum_next});
+000962  point: type=branch comment=if hier=vibration_core
 000962                         band_sum<=0; band_part<=0; state<=POWER_Q_INIT;
+000962  point: type=branch comment=if hier=vibration_core
 001924                     end else begin
+001924  point: type=branch comment=else hier=vibration_core
 001924                         band_sum<=band_sum_next[32:0]; band_part<=band_part+1;
+001924  point: type=branch comment=else hier=vibration_core
 001924                         power_index<=power_index+1; state<=POWER_RE_MUL;
+001924  point: type=branch comment=else hier=vibration_core
                            end
                        end
 000962                 POWER_Q_INIT: begin
+000962  point: type=line comment=case hier=vibration_core
 000962                     quant_work<=power_sum; quant_remaining<=feature_shifts[feature_index];
+000962  point: type=line comment=case hier=vibration_core
 000962                     quant_guard<=0; quant_sticky<=0;
+000962  point: type=line comment=case hier=vibration_core
 000120                     if (feature_shifts[feature_index] == 0) state<=POWER_QUANT;
+000120  point: type=line comment=elsif hier=vibration_core
~000842                     else if (feature_shifts[feature_index] > 33) begin quant_work<=0; state<=POWER_QUANT; end
-000000  point: type=line comment=if hier=vibration_core
+000842  point: type=line comment=else hier=vibration_core
 000842                     else state<=POWER_Q_SHIFT;
+000842  point: type=line comment=else hier=vibration_core
                        end
 003600                 POWER_Q_SHIFT: begin
+003600  point: type=line comment=case hier=vibration_core
 003600                     quant_sticky<=quant_sticky | quant_guard;
+003600  point: type=line comment=case hier=vibration_core
+000401  point: type=expr comment=(quant_guard==1) => 1 hier=vibration_core
+002923  point: type=expr comment=(quant_sticky==0 && quant_guard==0) => 0 hier=vibration_core
+000472  point: type=expr comment=(quant_sticky==1) => 1 hier=vibration_core
 003600                     quant_guard<=quant_work[0];
+003600  point: type=line comment=case hier=vibration_core
 003600                     quant_work<={1'b0,quant_work[32:1]};
+003600  point: type=line comment=case hier=vibration_core
 003600                     quant_remaining<=quant_remaining-1;
+003600  point: type=line comment=case hier=vibration_core
 002760                     if (quant_remaining == 1) state<=POWER_QUANT;
+000840  point: type=branch comment=if hier=vibration_core
+002760  point: type=branch comment=else hier=vibration_core
                        end
 000960                 POWER_QUANT: begin
+000960  point: type=line comment=case hier=vibration_core
 000960                     features[feature_index]<=quant_result;
+000960  point: type=line comment=case hier=vibration_core
 000960                     dbg_valid<=1; dbg_kind<=5; dbg_index<={12'd0,feature_index}; dbg_value<=$signed({32'd0,quant_result});
+000960  point: type=line comment=case hier=vibration_core
 000900                     if (feature_index == 15) begin nn_layer<=0; nn_group<=0; state<=NN_INIT; end
+000060  point: type=branch comment=if hier=vibration_core
+000900  point: type=branch comment=else hier=vibration_core
 000900                     else begin feature_index<=feature_index+1; power_index<=power_index+1; state<=POWER_RE_MUL; end
+000900  point: type=branch comment=else hier=vibration_core
                        end
 001104                 NN_INIT: begin
+001104  point: type=line comment=case hier=vibration_core
 001104                     nn_input<=0;
+001104  point: type=line comment=case hier=vibration_core
 001104                     for (k=0; k<LANES; k=k+1) begin
+001104  point: type=line comment=case hier=vibration_core
+001104  point: type=line comment=block hier=vibration_core
 000930                         if (!nn_layer) accumulator[k]<=40'(bias1[int'(nn_group)+k]);
+000930  point: type=line comment=elsif hier=vibration_core
+000930  point: type=expr comment=(nn_layer==0) => 1 hier=vibration_core
+000174  point: type=expr comment=(nn_layer==1) => 0 hier=vibration_core
~000174                         else if (int'(nn_group)+k < 3) accumulator[k]<=40'(bias2[int'(nn_group)+k]);
+000174  point: type=line comment=if hier=vibration_core
-000000  point: type=line comment=else hier=vibration_core
%000000                         else accumulator[k]<=0;
-000000  point: type=line comment=else hier=vibration_core
                            end
 001104                     state<=NN_READ;
+001104  point: type=line comment=case hier=vibration_core
                        end
 017634                 NN_READ: begin activation_q<=nn_layer ? hidden[nn_input] : features[nn_input]; state<=NN_MUL; end
+017634  point: type=line comment=case hier=vibration_core
+014850  point: type=expr comment=(nn_layer==0) => 0 hier=vibration_core
+002784  point: type=expr comment=(nn_layer==1) => 1 hier=vibration_core
+002784  point: type=branch comment=cond_then hier=vibration_core
+014850  point: type=branch comment=cond_else hier=vibration_core
 017634                 NN_MUL: state<=NN_ACC;
+017634  point: type=line comment=case hier=vibration_core
 017632                 NN_ACC: begin
+017632  point: type=line comment=case hier=vibration_core
 017632                     for (k=0; k<LANES; k=k+1) accumulator[k]<=accumulator[k]+$signed({{8{product[k][31]}},product[k]});
+017632  point: type=line comment=case hier=vibration_core
+017632  point: type=line comment=block hier=vibration_core
 016530                     if (nn_input == 15) begin store_lane<=0; state<=NN_STORE; end
+001102  point: type=branch comment=if hier=vibration_core
+016530  point: type=branch comment=else hier=vibration_core
 016530                     else begin nn_input<=nn_input+1; state<=NN_READ; end
+016530  point: type=branch comment=else hier=vibration_core
                        end
 001102                 NN_STORE: begin
+001102  point: type=line comment=case hier=vibration_core
~001102                     if (selected_accumulator > 40'sd2147483647 || selected_accumulator < -40'sd2147483648) arithmetic_errors[0]<=1;
-000000  point: type=branch comment=if hier=vibration_core
+001102  point: type=branch comment=else hier=vibration_core
-000000  point: type=expr comment=((selected_accumulator < (- 40'sh80000000))==1) => 1 hier=vibration_core
+001102  point: type=expr comment=((selected_accumulator > 40'sh7fffffff)==0 && (selected_accumulator < (- 40'sh80000000))==0) => 0 hier=vibration_core
-000000  point: type=expr comment=((selected_accumulator > 40'sh7fffffff)==1) => 1 hier=vibration_core
 000928                     if (!nn_layer) begin
+000928  point: type=line comment=elsif hier=vibration_core
+000928  point: type=expr comment=(nn_layer==0) => 1 hier=vibration_core
+000174  point: type=expr comment=(nn_layer==1) => 0 hier=vibration_core
 000928                         hidden[nn_output_index]<=relu_quant(selected_accumulator);
+000928  point: type=line comment=elsif hier=vibration_core
 000928                         dbg_valid<=1; dbg_kind<=6; dbg_index<={12'd0,nn_output_index};
+000928  point: type=line comment=elsif hier=vibration_core
 000928                         dbg_value<=$signed({32'd0,relu_quant(selected_accumulator)});
+000928  point: type=line comment=elsif hier=vibration_core
~000174                     end else if (nn_output_index < 4'd3) begin
+000174  point: type=branch comment=if hier=vibration_core
-000000  point: type=branch comment=else hier=vibration_core
 000174                         logits[nn_output_index[1:0]]<=selected_accumulator[31:0];
+000174  point: type=branch comment=if hier=vibration_core
 000174                         dbg_valid<=1; dbg_kind<=7; dbg_index<={12'd0,nn_output_index}; dbg_value<=selected_accumulator;
+000174  point: type=branch comment=if hier=vibration_core
                            end
~001102                     if (store_lane == LB'(LANES-1)) begin
+001102  point: type=branch comment=if hier=vibration_core
-000000  point: type=branch comment=else hier=vibration_core
 001044                         if (!nn_layer && int'(nn_group)+LANES == 16) begin nn_layer<=1; nn_group<=0; state<=NN_INIT; end
+000058  point: type=line comment=elsif hier=vibration_core
+001044  point: type=expr comment=(((nn_group + LANES) == 32'sh10)==0) => 0 hier=vibration_core
+000058  point: type=expr comment=(nn_layer==0 && ((nn_group + LANES) == 32'sh10)==1) => 1 hier=vibration_core
+000174  point: type=expr comment=(nn_layer==1) => 0 hier=vibration_core
 000986                         else if (nn_layer && int'(nn_group)+LANES >= 3) state<=FINISH;
+000058  point: type=line comment=if hier=vibration_core
+000986  point: type=line comment=else hier=vibration_core
+000232  point: type=expr comment=(((nn_group + LANES) >= 32'sh3)==0) => 0 hier=vibration_core
+000870  point: type=expr comment=(nn_layer==0) => 0 hier=vibration_core
+000058  point: type=expr comment=(nn_layer==1 && ((nn_group + LANES) >= 32'sh3)==1) => 1 hier=vibration_core
 000986                         else begin nn_group<=nn_group+4'(LANES); state<=NN_INIT; end
+000986  point: type=line comment=else hier=vibration_core
%000000                     end else store_lane<=store_lane+1;
-000000  point: type=branch comment=else hier=vibration_core
                        end
 000056                 FINISH: begin
+000056  point: type=line comment=case hier=vibration_core
 000056                     out_valid<=1; out_frame_id<=active_id; out_logits<={logits[2],logits[1],logits[0]}; out_error<=arithmetic_errors;
+000056  point: type=line comment=case hier=vibration_core
 000050                     if (logits[0]>=logits[1] && logits[0]>=logits[2]) out_class<=0;
+000004  point: type=line comment=elsif hier=vibration_core
+000050  point: type=expr comment=(((logits[2'h0]) >= (logits[2'h1]))==0) => 0 hier=vibration_core
+000004  point: type=expr comment=(((logits[2'h0]) >= (logits[2'h1]))==1 && ((logits[2'h0]) >= (logits[2'h2]))==1) => 1 hier=vibration_core
+000047  point: type=expr comment=(((logits[2'h0]) >= (logits[2'h2]))==0) => 0 hier=vibration_core
 000046                     else if (logits[1]>=logits[2]) out_class<=1; else out_class<=2;
+000006  point: type=line comment=if hier=vibration_core
+000046  point: type=line comment=else hier=vibration_core
 000056                     cycles_pre<=32'(count_pre); cycles_dft<=32'(count_dft); cycles_power<=32'(count_power); cycles_nn<=32'(count_nn); cycles_total<=32'(count_total);
+000056  point: type=line comment=case hier=vibration_core
 000056                     state<=HOLD;
+000056  point: type=line comment=case hier=vibration_core
                        end
 18621080                 HOLD: if (out_valid && out_ready) begin out_valid<=0; state<=IDLE; end
+006306  point: type=line comment=case hier=vibration_core
+000054  point: type=branch comment=if hier=vibration_core
+006252  point: type=branch comment=else hier=vibration_core
+18621080  point: type=expr comment=(out_ready==0) => 0 hier=vibration_core
+18614828  point: type=expr comment=(out_valid==0) => 0 hier=vibration_core
+000054  point: type=expr comment=(out_valid==1 && out_ready==1) => 1 hier=vibration_core
%000000                 default: state<=IDLE;
-000000  point: type=line comment=case hier=vibration_core
                    endcase
                end
            end
        `ifdef VIB_ASSERT
 000002     initial begin
+000002  point: type=line comment=block hier=vibration_core
~000002         assert (N >= 8 && (N & (N-1)) == 0);
+000002  point: type=line comment=block hier=vibration_core
-000000  point: type=expr comment=(((N & (N - 32'sh1)) == 32'sh0)==0) => 0 hier=vibration_core
-000000  point: type=expr comment=((N >= 32'sh8)==0) => 0 hier=vibration_core
+000002  point: type=expr comment=((N >= 32'sh8)==1 && ((N & (N - 32'sh1)) == 32'sh0)==1) => 1 hier=vibration_core
~000002         assert (LANES == 1 || LANES == 4);
+000002  point: type=line comment=block hier=vibration_core
-000000  point: type=expr comment=((LANES == 32'sh1)==0 && (LANES == 32'sh4)==0) => 0 hier=vibration_core
+000002  point: type=expr comment=((LANES == 32'sh1)==1) => 1 hier=vibration_core
-000000  point: type=expr comment=((LANES == 32'sh4)==1) => 1 hier=vibration_core
~000002         assert (BANDS == 1 || BANDS == 3);
+000002  point: type=line comment=block hier=vibration_core
-000000  point: type=expr comment=((BANDS == 32'sh1)==0 && (BANDS == 32'sh3)==0) => 0 hier=vibration_core
-000000  point: type=expr comment=((BANDS == 32'sh1)==1) => 1 hier=vibration_core
+000002  point: type=expr comment=((BANDS == 32'sh3)==1) => 1 hier=vibration_core
            end
 18621238     always @(posedge clk) if (!rst) begin
+18621134  point: type=branch comment=if hier=vibration_core
+000104  point: type=branch comment=else hier=vibration_core
+18621134  point: type=expr comment=(rst==0) => 1 hier=vibration_core
+000104  point: type=expr comment=(rst==1) => 0 hier=vibration_core
+18621238  point: type=line comment=block hier=vibration_core
 18621134         assert ((full & busy) == 0);
+18621134  point: type=branch comment=if hier=vibration_core
 18547348         if (in_valid && in_ready && (restart_input || !draining))
+18547348  point: type=branch comment=else hier=vibration_core
+7772111  point: type=expr comment=(in_ready==0) => 0 hier=vibration_core
+11968839  point: type=expr comment=(in_valid==0) => 0 hier=vibration_core
+073784  point: type=expr comment=(in_valid==1 && in_ready==1 && draining==0) => 1 hier=vibration_core
+000078  point: type=expr comment=(in_valid==1 && in_ready==1 && restart_input==1) => 1 hier=vibration_core
+000002  point: type=expr comment=(restart_input==0 && draining==1) => 0 hier=vibration_core
+073786  point: type=branch comment=if hier=vibration_core
~073786             assert (!full[write_bank] && !busy[write_bank]);
+073786  point: type=branch comment=if hier=vibration_core
-000000  point: type=expr comment=(busy[write_bank+:1]==1) => 0 hier=vibration_core
+073786  point: type=expr comment=(full[write_bank+:1]==0 && busy[write_bank+:1]==0) => 1 hier=vibration_core
-000000  point: type=expr comment=(full[write_bank+:1]==1) => 0 hier=vibration_core
 18553548         if (state == PRE_READ) assert (busy[active_bank]);
+18553548  point: type=branch comment=else hier=vibration_core
+067586  point: type=branch comment=if hier=vibration_core
~18615182         if (state == DFT_STORE) assert (int'(dft_group)+int'(store_lane) < COMPONENTS && int'(store_lane) < LANES);
+18615182  point: type=branch comment=else hier=vibration_core
-000000  point: type=expr comment=(((dft_group + store_lane) < COMPONENTS)==0) => 0 hier=vibration_core
+005952  point: type=expr comment=(((dft_group + store_lane) < COMPONENTS)==1 && (store_lane < LANES)==1) => 1 hier=vibration_core
-000000  point: type=expr comment=((store_lane < LANES)==0) => 0 hier=vibration_core
+005952  point: type=branch comment=if hier=vibration_core
 18603500         if (state == NN_READ) assert (int'(weight_address) < WEIGHT_WORDS);
+18603500  point: type=branch comment=else hier=vibration_core
+017634  point: type=branch comment=if hier=vibration_core
~18618248         if (state == POWER_IM_ADD) assert (!band_sum_next[33]);
+18618248  point: type=branch comment=else hier=vibration_core
+002886  point: type=expr comment=(band_sum_next[33]==0) => 1 hier=vibration_core
-000000  point: type=expr comment=(band_sum_next[33]==1) => 0 hier=vibration_core
+002886  point: type=branch comment=if hier=vibration_core
            end
            assert property (@(posedge clk) disable iff (rst)
                out_valid && !out_ready |=> out_valid && $stable({out_frame_id,
                out_logits,out_class,out_error,cycles_pre,cycles_dft,cycles_power,
                cycles_nn,cycles_total}));
        `endif
        endmodule
        
