// Atkinson dithering in hardware: one 8-bit grey pixel in per clock, in raster order, and one
// black-or-white pixel out a clock later. Each pixel passes 1/8 of its error to six neighbours and
// drops the other 2/8, which keeps highlights and shadows clean (the look of the first Macintosh):
//
//               x   x+1  x+2
//        y          1/8  1/8
//        y+1  1/8  1/8  1/8      (x-1, x, x+1)
//        y+2      1/8
//
// Three line buffers take turns as "errors arriving in this row", "the next row" and "the row after".
// in_keep marks the bear; pixels outside it come out white and pass no error on, so the background
// never bleeds into the bear's edge. tools/golden.py is the reference model; `make check` compares
// the two bit for bit.
module bear_dither #(
    parameter int W = 160
) (
    input  logic       clk,
    input  logic       rst_n,
    input  logic       in_valid,
    input  logic [7:0] in_pix,
    input  logic       in_keep,
    output logic       out_valid,
    output logic       out_white
);
  localparam int XW = $clog2(W);
  localparam logic [XW-1:0] LAST = XW'(W - 1);

  // A share is within -16..15 and at most six land on one pixel, so 10 signed bits are plenty.
  typedef logic signed [9:0] err_t;

  err_t          lb               [3][W];
  logic    [1:0] cur, nxt, aft;  // which buffer plays which role in the current row
  logic [XW-1:0] x;
  err_t          carry1, carry2;  // this row's error waiting for x+1 and x+2

  err_t level, diff, share;
  logic white;

  always_comb begin
    level = err_t'({2'b00, in_pix}) + lb[cur][x] + carry1;
    white = level >= 10'sd128;
    diff  = white ? level - 10'sd255 : level;
    // Keep every operand signed: an unsigned '0 here would make the whole ?: unsigned,
    // and >>> would quietly turn into a logical shift.
    share = in_keep ? diff >>> 3 : 10'sd0;
  end

  always_ff @(posedge clk) begin
    if (!rst_n) begin
      for (int b = 0; b < 3; b++) for (int i = 0; i < W; i++) lb[b][i] <= '0;
      {cur, nxt, aft}        <= {2'd0, 2'd1, 2'd2};
      x                      <= '0;
      {carry1, carry2}       <= '0;
      {out_valid, out_white} <= '0;
    end else begin
      out_valid <= in_valid;
      if (in_valid) begin
        out_white  <= white || !in_keep;
        lb[aft][x] <= share;  // (x, y+2): only this pixel feeds it, so overwrite the stale value
        lb[nxt][x] <= lb[nxt][x] + share;
        if (x != '0) lb[nxt][x-1'b1] <= lb[nxt][x-1'b1] + share;
        if (x != LAST) lb[nxt][x+1'b1] <= lb[nxt][x+1'b1] + share;
        if (x == LAST) begin
          x                <= '0;
          {carry1, carry2} <= '0;
          {cur, nxt, aft}  <= {nxt, aft, cur};
        end else begin
          x      <= x + 1'b1;
          carry1 <= carry2 + share;
          carry2 <= share;
        end
      end
    end
  end
endmodule
