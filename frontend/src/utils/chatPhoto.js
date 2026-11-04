// Prepares a photo for the live chat: shrinks it in the browser so it stays small enough to send
// (the server accepts about 1 MB), and returns it as a JPEG data URL.

export const MAX_PHOTO_FILE_BYTES = 10 * 1024 * 1024; // the file the person picks, before shrinking
const MAX_SIDE = 1280;
const TARGET_CHARS = 1_200_000; // the server's limit is 1,500,000

function load(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error("That photo could not be read."));
    reader.onload = () => {
      const img = new Image();
      img.onerror = () => reject(new Error("That file is not a photo we can open."));
      img.onload = () => resolve(img);
      img.src = reader.result;
    };
    reader.readAsDataURL(file);
  });
}

function draw(img, scale, quality) {
  const canvas = document.createElement("canvas");
  canvas.width = Math.max(1, Math.round(img.width * scale));
  canvas.height = Math.max(1, Math.round(img.height * scale));
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = "#fff"; // transparent PNGs would turn black as a JPEG
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
  return canvas.toDataURL("image/jpeg", quality);
}

export async function readChatPhoto(file) {
  if (!file || !String(file.type || "").startsWith("image/")) {
    throw new Error("Please choose a photo (JPG, PNG, WEBP or GIF).");
  }
  if (file.size > MAX_PHOTO_FILE_BYTES) {
    throw new Error("That photo is too large. Please choose one under 10 MB.");
  }
  const img = await load(file);
  let scale = Math.min(1, MAX_SIDE / Math.max(img.width, img.height));
  let url = draw(img, scale, 0.82);
  for (const [factor, quality] of [[0.75, 0.7], [0.55, 0.6]]) {
    if (url.length <= TARGET_CHARS) break;
    scale *= factor;
    url = draw(img, scale, quality);
  }
  if (url.length > TARGET_CHARS) throw new Error("That photo is still too large. Please choose a smaller one.");
  return url;
}
