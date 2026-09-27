// Draws SF Symbols for hued map. Reads one line of space-separated symbol names
// at a time and answers each with one line of JSON: {"<name>": "<base64 PNG>"}.
// Names AppKit does not know are left out. Exits when stdin closes.
import AppKit
import Foundation

func png(_ name: String) -> String? {
  guard let base = NSImage(systemSymbolName: name, accessibilityDescription: nil),
        let symbol = base.withSymbolConfiguration(NSImage.SymbolConfiguration(pointSize: 28, weight: .medium))
  else { return nil }
  let size = symbol.size
  guard let rep = NSBitmapImageRep(
    bitmapDataPlanes: nil, pixelsWide: Int(size.width * 2), pixelsHigh: Int(size.height * 2),
    bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true, isPlanar: false,
    colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)
  else { return nil }
  rep.size = size
  NSGraphicsContext.saveGraphicsState()
  NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: rep)
  symbol.draw(in: NSRect(origin: .zero, size: size))
  NSGraphicsContext.restoreGraphicsState()
  return rep.representation(using: .png, properties: [:])?.base64EncodedString()
}

while let line = readLine() {
  var out: [String: String] = [:]
  for name in line.split(separator: " ") {
    if let image = png(String(name)) { out[String(name)] = image }
  }
  let json = (try? JSONSerialization.data(withJSONObject: out)) ?? Data("{}".utf8)
  FileHandle.standardOutput.write(json)
  FileHandle.standardOutput.write(Data("\n".utf8))
}
