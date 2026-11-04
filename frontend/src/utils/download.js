// Downloads a file that sits behind the admin login (a plain link cannot send the token).
export async function downloadFile(client, url, params, fallbackName) {
  const res = await client.get(url, { params, responseType: "blob" });
  const disposition = res.headers?.["content-disposition"] || "";
  const name = /filename="?([^";]+)"?/.exec(disposition)?.[1] || fallbackName;
  const href = URL.createObjectURL(res.data);
  const link = document.createElement("a");
  link.href = href;
  link.download = name;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(href), 2000);
}
