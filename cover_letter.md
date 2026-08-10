# Cover Letter

*Draft. Check the editor's name on the journal homepage before sending, and
adjust the tone to your own. Paste the body into the Editorial Manager cover
letter box, or upload it as a "Cover Letter" item.*

---

Dear Editor,

We wish to submit the enclosed manuscript, *An Ethernet-Enabled Customizable
Neural Inference Framework on Low-Cost FPGA SoC for High-Frequency Trading*, for
consideration as a research article in the Journal of Systems Architecture.

The paper describes a neural inference engine embedded in the programmable logic
of a low-cost Xilinx Zynq-7000 SoC and fed over Ethernet. The network shape is a
run-time parameter rather than an elaboration-time one, so networks of different
topologies are deployed into an unchanged bitstream over AXI-Lite with no
synthesis step. The core completes an inference in 768 ns at 125 MHz using 192
DSP-based multipliers in a 13-stage pipeline.

Three aspects may be of particular interest to the journal's readership.

First, the latency is not only low but invariant. An on-chip cycle counter read
back after every inference returns the same value on all of 100,000 consecutive
inferences, with zero standard deviation. We report the distribution rather than
a representative oscilloscope capture, because a worst-case guarantee is what
the application requires.

Second, correctness of the deployed arithmetic is established rather than
assumed. The whole datapath was reproduced in an independent bit-accurate
reference model and compared against the hardware over 400,000 inferences and
1,200,000 raw output values across four topologies, with no discrepancy. That
process first exposed three pipeline-alignment defects that neither synthesis
nor end-to-end testing had revealed, and we report those defects and their
correction in the paper.

Third, the evaluation is anchored to baselines measured on the same device: a
software implementation of the same network on the SoC's own Cortex-A9 using
identical fixed-point arithmetic, and an earlier sequential hardware
implementation of the same network. We state the compilation settings of the
software baseline explicitly, since an unoptimized baseline would have
overstated the speed-up by almost a factor of six.

The manuscript is original, has not been published elsewhere, and is not under
consideration by another journal. All authors have approved the submission and
declare no competing interests. The work received no external funding. The
hardware and software artifacts are publicly available at the repositories
listed in the Data Availability statement.

Thank you for considering our submission. We look forward to the reviewers'
comments.

Yours sincerely,

Ahmet Batuhan Özkaner
Istanbul Bilgi University
ozkanerbatuhan@gmail.com

on behalf of the authors: Ahmet Batuhan Özkaner, Mustafa Alper Ilık,
Baykal Sarıoğlu

---

## Suggested reviewers

*Editorial Manager may ask for three. Suggest researchers who have published on
FPGA neural inference or low-latency financial hardware and who are not at your
institution and have no recent co-authorship with you. Candidates whose work you
already cite are the natural place to start. Give name, affiliation, email and
one line of justification for each.*

| Name | Area | Why |
|---|---|---|
|  |  |  |
|  |  |  |
|  |  |  |
