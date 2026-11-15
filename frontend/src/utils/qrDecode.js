export async function readQrText(file) {
  try {
    const { default: jsQR } = await import("jsqr");
    const bitmap = await createImageBitmap(file);
    for (const maxSide of [1000, 700, 1400, 450]) {
      const scale = Math.min(1, maxSide / Math.max(bitmap.width, bitmap.height));
      const width = Math.round(bitmap.width * scale);
      const height = Math.round(bitmap.height * scale);
      const canvas = document.createElement("canvas");
      canvas.width = width;
      canvas.height = height;
      const context = canvas.getContext("2d", { willReadFrequently: true });
      context.fillStyle = "#fff";
      context.fillRect(0, 0, width, height);
      context.drawImage(bitmap, 0, 0, width, height);
      const found = jsQR(context.getImageData(0, 0, width, height).data, width, height, { inversionAttempts: "attemptBoth" });
      if (found?.data) return found.data;
    }
  } catch {
  }
  return null;
}
