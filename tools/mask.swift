// Cuts the bear out of its picture with macOS Vision (the same subject lift as "Copy Subject" in Photos)
// and writes a mask at the dither grid size: 255 inside the bear, 0 outside.
//
//   swift tools/mask.swift bear/original.jpg bear/bear-mask.pgm 160 [fill-from]
//
// On the rainy-window picture Vision keeps the head, scarf and arm but drops the mug and the dark
// sweater front, which melt into the night. fill-from (a fraction of the height, e.g. 0.62) closes that:
// from there down, each row is filled between its outermost bear cells. Leave it out for pictures on a
// plain background.
import CoreVideo
import Foundation
import Vision

let args = CommandLine.arguments
guard args.count == 4 || args.count == 5, let size = Int(args[3]), size > 0 else {
    FileHandle.standardError.write("usage: mask.swift <image> <mask.pgm> <size> [fill-from]\n".data(using: .utf8)!)
    exit(2)
}
let fillFrom = args.count == 5 ? Double(args[4]) : nil

let handler = VNImageRequestHandler(url: URL(fileURLWithPath: args[1]))
let request = VNGenerateForegroundInstanceMaskRequest()
try handler.perform([request])
guard let observation = request.results?.first else {
    FileHandle.standardError.write("Vision found no subject in \(args[1])\n".data(using: .utf8)!)
    exit(1)
}
let mask = try observation.generateScaledMaskForImage(forInstances: observation.allInstances, from: handler)

CVPixelBufferLockBaseAddress(mask, .readOnly)
defer { CVPixelBufferUnlockBaseAddress(mask, .readOnly) }
let width = CVPixelBufferGetWidth(mask)
let height = CVPixelBufferGetHeight(mask)
let rowBytes = CVPixelBufferGetBytesPerRow(mask)
let base = CVPixelBufferGetBaseAddress(mask)!
let format = CVPixelBufferGetPixelFormatType(mask)

func coverage(_ x: Int, _ y: Int) -> Float {
    switch format {
    case kCVPixelFormatType_OneComponent32Float:
        return base.advanced(by: y * rowBytes).assumingMemoryBound(to: Float.self)[x]
    case kCVPixelFormatType_OneComponent8:
        return Float(base.advanced(by: y * rowBytes).assumingMemoryBound(to: UInt8.self)[x]) / 255
    default:
        fatalError("unexpected mask pixel format \(format)")
    }
}

// Each grid cell is in the bear when at least half of the pixels it covers are.
var cells = [UInt8](repeating: 0, count: size * size)
for gy in 0..<size {
    let y0 = gy * height / size, y1 = max(y0 + 1, (gy + 1) * height / size)
    for gx in 0..<size {
        let x0 = gx * width / size, x1 = max(x0 + 1, (gx + 1) * width / size)
        var sum: Float = 0
        for y in y0..<y1 { for x in x0..<x1 { sum += coverage(x, y) } }
        cells[gy * size + gx] = sum / Float((y1 - y0) * (x1 - x0)) >= 0.5 ? 255 : 0
    }
}

if let fillFrom {
    for gy in Int(fillFrom * Double(size))..<size {
        let row = cells[(gy * size)..<((gy + 1) * size)]
        if let first = row.firstIndex(of: 255), let last = row.lastIndex(of: 255) {
            for i in first...last { cells[i] = 255 }
        }
    }
}

var data = "P5\n\(size) \(size)\n255\n".data(using: .ascii)!
data.append(contentsOf: cells)
try data.write(to: URL(fileURLWithPath: args[2]))
print("mask: \(width)x\(height) -> \(size)x\(size), \(cells.filter { $0 == 255 }.count) of \(size * size) cells in the bear")
