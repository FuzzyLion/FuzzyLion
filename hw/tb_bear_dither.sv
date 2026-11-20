// Streams an 8-bit PGM through bear_dither, one pixel per clock, and writes the result as an ASCII PBM.
//   build/Vtb +in=bear/bear.pgm +mask=bear/bear-mask.pgm +out=build/bear_rtl.pbm
// +mask is optional; without it every pixel is kept.
module tb_bear_dither;
  localparam int W = 160;
  localparam int H = 160;

  logic       clk;
  logic       rst_n;
  logic       in_valid;
  logic [7:0] in_pix;
  logic       in_keep;
  logic       out_valid;
  logic       out_white;

  bear_dither #(.W(W)) dut (.*);

  initial begin
    clk = 1'b0;
    forever #5 clk = ~clk;
  end

  logic [7:0] img [W*H];
  logic [7:0] msk [W*H];
  logic       res [W*H];
  int         got;

  // Outputs change on the rising edge, so sample them on the falling one.
  always @(negedge clk) begin
    if (!rst_n) got <= 0;
    else if (out_valid) begin
      res[got] <= out_white;
      got      <= got + 1;
    end
  end

  // Reads a WxH 8-bit binary PGM into img (to_mask = 0) or msk (to_mask = 1).
  task automatic read_pgm(input string path, input bit to_mask);
    int fd, w, h, maxval, c;
    fd = $fopen(path, "rb");
    if (fd == 0) $fatal(1, "cannot open %s", path);
    if ($fgetc(fd) != "P" || $fgetc(fd) != "5") $fatal(1, "%s: not a binary PGM", path);
    if ($fscanf(fd, "%d %d %d", w, h, maxval) != 3 || w != W || h != H || maxval != 255)
      $fatal(1, "%s: expected %0dx%0d pixels with maxval 255", path, W, H);
    c = $fgetc(fd);  // the one whitespace byte after maxval
    for (int i = 0; i < W * H; i++) begin
      c = $fgetc(fd);
      if (c < 0) $fatal(1, "%s: truncated at pixel %0d", path, i);
      if (to_mask) msk[i] = c[7:0];
      else img[i] = c[7:0];
    end
    $fclose(fd);
  endtask

  initial begin
    string in_path, mask_path, out_path;
    int fd;

    rst_n    = 1'b0;
    in_valid = 1'b0;
    in_pix   = '0;
    in_keep  = 1'b0;
    if (!$value$plusargs("in=%s", in_path) || !$value$plusargs("out=%s", out_path))
      $fatal(1, "usage: +in=<pgm> [+mask=<pgm>] +out=<pbm>");
    read_pgm(in_path, 1'b0);
    if ($value$plusargs("mask=%s", mask_path)) read_pgm(mask_path, 1'b1);
    else foreach (msk[i]) msk[i] = 8'hFF;

    repeat (2) @(negedge clk);
    rst_n = 1'b1;
    for (int i = 0; i < W * H; i++) begin
      @(negedge clk);
      in_valid = 1'b1;
      in_pix   = img[i];
      in_keep  = msk[i] != 8'h00;
    end
    @(negedge clk);
    in_valid = 1'b0;
    repeat (2) @(negedge clk);
    if (got != W * H) $fatal(1, "expected %0d pixels out, got %0d", W * H, got);

    fd = $fopen(out_path, "w");
    if (fd == 0) $fatal(1, "cannot write %s", out_path);
    $fwrite(fd, "P1\n%0d %0d\n", W, H);  // PBM: 1 is black
    for (int y = 0; y < H; y++) begin
      for (int x = 0; x < W; x++) $fwrite(fd, "%0d", !res[y*W+x]);
      $fwrite(fd, "\n");
    end
    $fclose(fd);
    $display("bear_dither: %0d x %0d pixels -> %s", W, H, out_path);
    $finish;
  end
endmodule
