// Things the field screens need from the phone or laptop: GPS position and the camera photo.
import { useCallback, useEffect, useState } from "react";

// Asks the browser for the current position once. status: "finding" | "ok" | "none".
// It never blocks: if GPS is off, refused or slow, the status becomes "none" and work continues without it.
export function usePosition() {
  const [state, setState] = useState({ status: "finding", coords: null });

  const find = useCallback(() => {
    setState({ status: "finding", coords: null });
    let done = false;
    const finish = (coords) => {
      if (done) return;
      done = true;
      setState({ status: coords ? "ok" : "none", coords });
    };
    setTimeout(() => finish(null), 8000); // also covers a permission prompt nobody answers
    if (!navigator.geolocation) {
      finish(null);
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (p) => finish({ latitude: p.coords.latitude, longitude: p.coords.longitude }),
      () => finish(null),
      { enableHighAccuracy: true, timeout: 7000, maximumAge: 60000 }
    );
  }, []);

  useEffect(() => {
    find();
  }, [find]);

  return { ...state, retry: find };
}

// Phone photos are several MB. Shrink to at most 1600 px so uploads stay fast on a weak network.
// If anything goes wrong, the original file is used.
export async function shrinkPhoto(file, maxSide = 1600) {
  try {
    const bitmap = await createImageBitmap(file);
    const scale = Math.min(1, maxSide / Math.max(bitmap.width, bitmap.height));
    if (scale === 1 && file.size < 1_500_000) return file;
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(bitmap.width * scale);
    canvas.height = Math.round(bitmap.height * scale);
    canvas.getContext("2d").drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.8));
    return blob ? new File([blob], "photo.jpg", { type: "image/jpeg" }) : file;
  } catch {
    return file;
  }
}
